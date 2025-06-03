import base64
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

from keyboards import StyleSelectionKeyboard
from models import User
from service import OpenAIService, UserService
from states import ImageProcessing

router = Router()


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
        "🎌 <b>Аниме</b> - японский стиль анимации\n"
        "🎨 <b>Реализм</b> - улучшение фотореалистичности\n"
        "🖼️ <b>Арт</b> - художественная живопись\n"
        "🌟 <b>Фэнтези</b> - магический стиль\n"
        "🤖 <b>Киберпанк</b> - футуристический стиль\n"
        "🎭 <b>Карикатура</b> - мультяшный стиль\n\n"
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
    openai_service: OpenAIService,
    bot: Bot,
    logger: Logger,
):
    """Обрабатывает выбор стиля и преобразует изображение"""
    style = str(callback.data).split("_")[1]

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
        f"⏳ Обработка займет 30-60 секунд...\n\n"
        f"💰 Списан 1 токен\n"
        f"💳 Остаток: {updated_user.token_count} токенов"
    )

    await callback.message.edit_text(processing_text)  # type: ignore
    await callback.answer("Преобразование началось!")

    data = await state.get_data()
    photo_file_id = str(data.get("photo_file_id"))

    try:
        file = await bot.get_file(photo_file_id)
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

        result_url = await openai_service.transform_image(file_url, style)

        if result_url:
            success_text = (
                f"✅ <b>Преобразование завершено!</b>\n\n"
                f"🎨 Стиль: {get_style_name(style)}\n"
                f"💳 Остаток токенов: {updated_user.token_count}"
            )

            if result_url.startswith("data:image"):
                base64_data = result_url.split(",")[1]
                image_data = base64.b64decode(base64_data)

                photo = BufferedInputFile(image_data, filename=f"styled_{style}.png")

                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Другой стиль", callback_data="new_style")],
                        [InlineKeyboardButton(text="📸 Новое фото", callback_data="new_photo")],
                        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="to_main")],
                    ],
                )

                await callback.message.answer_photo(  # type: ignore
                    photo=photo,
                    caption=success_text,
                    reply_markup=keyboard,
                )
                await callback.message.delete()  # type: ignore
            else:
                # Если обычный URL
                await callback.message.answer_photo(photo=result_url, caption=success_text)  # type: ignore
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

    finally:
        await state.clear()


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
        f"🎌 <b>Аниме</b> - японский стиль анимации\n"
        f"🎨 <b>Реализм</b> - улучшение фотореалистичности\n"
        f"🖼️ <b>Арт</b> - художественная живопись\n"
        f"🌟 <b>Фэнтези</b> - магический стиль\n"
        f"🤖 <b>Киберпанк</b> - футуристический стиль\n"
        f"🎭 <b>Карикатура</b> - мультяшный стиль\n\n"
        f"💰 Стоимость: 1 токен\n"
        f"💳 Ваш баланс: {current_user.token_count} токенов"
    )

    keyboard = StyleSelectionKeyboard()
    await callback.message.edit_text(style_text, reply_markup=keyboard())  # type: ignore
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
    await callback.message.edit_text(instruction_text, reply_markup=keyboard)  # type: ignore
    await callback.answer()


def get_style_name(style: str) -> str:
    """Возвращает читаемое название стиля"""
    style_names = {
        "anime": "🎌 Аниме",
        "realism": "🎨 Реализм",
        "art": "🖼️ Арт",
        "fantasy": "🌟 Фэнтези",
        "cyberpunk": "🤖 Киберпанк",
        "cartoon": "🎭 Карикатура",
    }
    return style_names.get(style, "🎨 Неизвестный стиль")


__all__ = ["router"]
