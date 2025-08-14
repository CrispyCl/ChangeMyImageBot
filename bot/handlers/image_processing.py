from logging import Logger

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PhotoSize,
)

from keyboards import STYLE_NAMES, StyleSelectionKeyboard, TokenPurchaseKeyboard
from models import User
from service import GeminiImageService, UserService
from states import ImageProcessing

STYLE_DESCRIPTIONS = {
    "anime": "Японский стиль с яркими цветами, четкими контурами и выразительными персонажами.",
    "manga": "Черно-белый или минималистичный стиль, как в японских комиксах.",
    "oilpainting": "Художественная живопись с текстурой мазков кисти и глубиной цвета.",
    "watercolor": "Мягкие переходы и прозрачные цвета, эффект акварельной техники.",
    "comic": "Яркие контуры, выразительные линии и комиксная подача.",
    "cartoon": "Утрированные формы, яркие цвета и мультяшная стилизация.",
    "sketch": "Ручной карандашный набросок с текстурой бумаги.",
    "ink": "Черно-белая графика с четкими контрастами, выполненная тушью.",
    "3d_render": "Фотореалистичный или стилизованный рендер в 3D.",
    "minimalism": "Простота форм, минимум деталей и чистое пространство.",
}

router = Router()


@router.callback_query(F.data == "back_to_send_photo")
async def start_image_processing_callback(callback: CallbackQuery, state: FSMContext, current_user: User):
    await start_image_processing(callback.message, state, current_user)
    await callback.answer()
    await callback.message.delete()  # type: ignore


@router.message(F.text == "🎨 Изменить изображение")
async def start_image_processing(message: Message, state: FSMContext, current_user: User):
    """Начинает процесс обработки изображения"""
    if current_user.token_count <= 0:
        no_tokens_text = (
            "😔 <b>Недостаточно токенов</b>\n\n"
            "У вас нет токенов для генерации изображений.\n"
            "Купите токены для продолжения работы!"
        )
        keyboard = TokenPurchaseKeyboard()
        await message.answer(no_tokens_text, reply_markup=keyboard())
        return

    await state.set_state(ImageProcessing.waiting_for_photo)

    instruction_text = (
        f"📸 <b>Отправьте фотографию</b>\n\n"
        f"Пришлите изображение, которое хотите изменить.\n"
        f"Поддерживаются форматы: JPG, PNG\n\n"
        f"💰 Стоимость: 1 токен\n"
        f"💳 Ваш баланс: {current_user.token_count} токенов"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="to_main")],
        ],
    )
    await message.answer(instruction_text, reply_markup=keyboard)


@router.message(StateFilter(ImageProcessing.waiting_for_photo), F.photo)
async def process_photo(message: Message, state: FSMContext, current_user: User):
    """Обрабатывает полученное фото"""
    if current_user.token_count <= 0:
        no_tokens_text = (
            "😔 <b>Недостаточно токенов</b>\n\n"
            "У вас нет токенов для генерации изображений.\n"
            "Купите токены для продолжения работы!"
        )
        from keyboards import TokenPurchaseKeyboard

        keyboard = TokenPurchaseKeyboard()
        await message.answer(no_tokens_text, reply_markup=keyboard())
        return

    photo: PhotoSize = message.photo[-1]  # type: ignore

    await state.update_data(photo_file_id=photo.file_id)
    await state.set_state(ImageProcessing.choosing_style)

    style_text = (
        "🎨 <b>Выберите стиль преобразования</b>\n\n"
        "Ваше изображение будет преобразовано с сохранением композиции:\n\n"
        f"{generate_style_list_text()}\n\n"
        "💡 <i>Позы и расположение объектов сохранятся!</i>\n"
        "💰 Стоимость: 1 токен"
    )

    keyboard = StyleSelectionKeyboard()
    await message.answer(style_text, reply_markup=keyboard())


@router.message(StateFilter(ImageProcessing.waiting_for_photo))
async def invalid_photo(message: Message):
    """Обрабатывает неправильный тип сообщения"""
    error_text = (
        "❌ <b>Неправильный формат</b>\n\n"
        "Пожалуйста, отправьте изображение в формате фото.\n"
        "Поддерживаются форматы: JPG, PNG"
    )
    await message.answer(error_text)


@router.callback_query(StateFilter(ImageProcessing.choosing_style), F.data.startswith("style_"))
async def process_style_selection(
    callback: CallbackQuery,
    state: FSMContext,
    current_user: User,
    user_service: UserService,
    image_service: GeminiImageService,
    bot: Bot,
    logger: Logger,
):
    """Обрабатывает выбор стиля и преобразует изображение"""
    style = str(callback.data).split("_", 1)[1]

    # Проверяем токены
    if current_user.token_count <= 0:
        no_tokens_text = "😔 <b>Недостаточно токенов</b>\n\nУ вас нет токенов для генерации изображений."
        await callback.message.edit_text(no_tokens_text)  # type: ignore
        await callback.answer()
        return

    # Списываем токен
    updated_user = await user_service.repo.update_token_count(current_user.id, current_user.token_count - 1)

    if not updated_user:
        error_text = "❌ Ошибка при списании токена. Попробуйте позже."
        await callback.message.edit_text(error_text)  # type: ignore
        await callback.answer()
        return

    # Показываем процесс
    processing_text = (
        f"🎨 <b>Преобразуем изображение</b>\n\n"
        f"Стиль: {get_style_name(style)}\n"
        f"⏳ Обработка займет 10-15 секунд...\n\n"
        f"💰 Списан 1 токен\n"
        f"💳 Остаток: {updated_user.token_count} токенов"
    )

    await callback.message.edit_text(processing_text)  # type: ignore
    await callback.answer("Преобразование началось!")

    data = await state.get_data()
    photo_file_id = str(data.get("photo_file_id"))

    try:
        file = await bot.get_file(photo_file_id)
        file_data = await bot.download_file(str(file.file_path))
        if not file_data:
            raise ValueError("Ошибка: не удалось получить данные изображения (пустой файл).")

        image_bytes = file_data.read()

        result_image = await image_service.transform_image(image_bytes=image_bytes, style=style)

        if result_image:
            photo = BufferedInputFile(result_image, filename=f"styled_{style}.png")
            success_text = (
                f"✅ <b>Преобразование завершено!</b>\n\n"
                f"🎨 Стиль: {get_style_name(style)}\n"
                f"💳 Остаток токенов: {updated_user.token_count}"
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Другой стиль", callback_data="new_style")],
                    [InlineKeyboardButton(text="📸 Новое фото", callback_data="new_photo")],
                ],
            )

            await callback.message.answer_photo(  # type: ignore
                photo=photo,
                caption=success_text,
                reply_markup=keyboard,
            )
            await callback.message.delete()  # type: ignore
        else:
            # Возвращаем токен при ошибке
            await user_service.repo.update_token_count(current_user.id, updated_user.token_count + 1)

            error_text = (
                "❌ <b>Ошибка преобразования</b>\n\n"
                "Не удалось преобразовать изображение.\n"
                "💰 Токен возвращен на ваш счет"
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="new_photo")],
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="to_main")],
                ],
            )
            await callback.message.edit_text(error_text, reply_markup=keyboard)  # type: ignore
            await callback.answer()
    except Exception as e:
        # Возвращаем токен при ошибке
        await user_service.repo.update_token_count(current_user.id, updated_user.token_count + 1)
        logger.error(f"Ошибка при обработке изображения: {e}")

        error_text = (
            "❌ <b>Произошла ошибка</b>\n\n" "Не удалось обработать изображение.\n\n" "💰 Токен возвращен на ваш счет"
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="new_photo")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="to_main")],
            ],
        )

        await callback.message.edit_text(error_text, reply_markup=keyboard)  # type: ignore


@router.callback_query(F.data == "new_style")
async def choose_new_style(callback: CallbackQuery, state: FSMContext, current_user: User):
    """Позволяет выбрать новый стиль для того же изображения"""
    if current_user.token_count <= 0:
        no_tokens_text = "😔 <b>Недостаточно токенов</b>\n\nУ вас нет токенов для новой генерации."
        await callback.message.edit_text(no_tokens_text)  # type: ignore
        await callback.answer()
        return

    data = await state.get_data()
    if not data.get("photo_file_id"):
        await callback.message.edit_text("📸 Пожалуйста, загрузите новое изображение для обработки.")  # type: ignore
        await state.set_state(ImageProcessing.waiting_for_photo)
        await callback.answer()
        return

    await state.set_state(ImageProcessing.choosing_style)

    style_text = (
        f"🎨 <b>Выберите новый стиль</b>\n\n"
        f"Преобразуем то же изображение в другом стиле:\n\n"
        f"{generate_style_list_text()}\n\n"
        f"💰 Стоимость: 1 токен\n"
        f"💳 Ваш баланс: {current_user.token_count} токенов"
    )

    keyboard = StyleSelectionKeyboard()
    await callback.message.answer(style_text, reply_markup=keyboard())  # type: ignore
    await callback.answer()


@router.callback_query(F.data == "new_photo")
async def upload_new_photo(callback: CallbackQuery, state: FSMContext, current_user: User):
    """Позволяет загрузить новое фото"""
    await state.clear()
    await state.set_state(ImageProcessing.waiting_for_photo)

    instruction_text = (
        f"📸 <b>Отправьте новое изображение</b>\n\n"
        f"Пришлите фото, которое хотите преобразовать.\n"
        f"Поддерживаются форматы: JPG, PNG\n\n"
        f"💡 Композиция и позы будут сохранены\n"
        f"💰 Стоимость: 1 токен за преобразование\n"
        f"💳 Ваш баланс: {current_user.token_count} токенов"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="to_main")],
        ],
    )
    await callback.message.answer(instruction_text, reply_markup=keyboard)  # type: ignore
    await callback.answer()


def get_style_name(style: str) -> str:
    return STYLE_NAMES.get(style, f"📝 {style.capitalize()}")


def generate_style_list_text() -> str:
    lines = []
    for style_id, style_label in STYLE_NAMES.items():
        if style_id == "custom":
            continue
        emoji, name = style_label.split(" ", 1)
        description = STYLE_DESCRIPTIONS.get(style_id, "Описание отсутствует")
        lines.append(f"{emoji} <b>{name}</b> — {description}")
    return "\n".join(lines)


__all__ = ["router"]
