from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import ProfileKeyboard, TokenPurchaseKeyboard, ToMainMenuKeyboard
from models import User
from states import UserProfile

router = Router()


@router.message(F.text == "👤 Профиль")
async def show_profile(message: Message, state: FSMContext, current_user: User):
    """Показывает профиль пользователя"""
    await state.set_state(UserProfile.viewing_profile)

    profile_text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{current_user.id}</code>\n"
        f"👤 Имя: {current_user.username}\n"
        f"💰 Токены: {current_user.token_count}\n"
        f"📅 Дата регистрации: {current_user.date_joined.strftime('%d.%m.%Y')}\n"
    )

    if current_user.phone_number:
        profile_text += f"📱 Телефон: {current_user.phone_number}\n"

    keyboard = ProfileKeyboard()
    await message.answer(profile_text, reply_markup=keyboard())


@router.callback_query(F.data == "profile")
async def show_profile_callback(callback: CallbackQuery, state: FSMContext, current_user: User):
    """Показывает профиль пользователя через callback"""
    await state.set_state(UserProfile.viewing_profile)

    profile_text = (
        f"👤 <b>Ваш профиль</b>\n\n"
        f"🆔 ID: <code>{current_user.id}</code>\n"
        f"👤 Имя: {current_user.username}\n"
        f"💰 Токены: {current_user.token_count}\n"
        f"📅 Дата регистрации: {current_user.date_joined.strftime('%d.%m.%Y')}\n"
    )

    if current_user.phone_number:
        profile_text += f"📱 Телефон: {current_user.phone_number}\n"

    keyboard = ProfileKeyboard()
    await callback.message.edit_text(profile_text, reply_markup=keyboard())  # type: ignore
    await callback.answer()


@router.message(F.text == "💰 Баланс токенов")
async def show_token_balance(message: Message, current_user: User):
    """Показывает баланс токенов"""
    balance_text = (
        f"💰 <b>Ваш баланс токенов</b>\n\n"
        f"Доступно токенов: <b>{current_user.token_count}</b>\n\n"
        f"ℹ️ Один токен = одна генерация изображения\n"
        f"💡 Купите больше токенов для продолжения работы!"
    )

    keyboard = TokenPurchaseKeyboard()
    await message.answer(balance_text, reply_markup=keyboard())


@router.callback_query(F.data == "buy_tokens")
async def show_token_purchase(callback: CallbackQuery):
    """Показывает варианты покупки токенов"""
    purchase_text = (
        "💰 <b>Покупка токенов</b>\n\n"
        "Выберите пакет токенов:\n\n"
        "🔹 150 токенов - 990₽\n"
        "🔹 350 токенов - 1990₽ (скидка 15%)\n"
        "🔹 800 токенов - 3990₽ (скидка 25%)\n\n"
        "💡 Чем больше пакет, тем выгоднее цена!"
    )

    keyboard = TokenPurchaseKeyboard()
    await callback.message.edit_text(purchase_text, reply_markup=keyboard())  # type: ignore
    await callback.answer()


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

    from states import ImageProcessing

    await state.set_state(ImageProcessing.waiting_for_photo)

    instruction_text = (
        f"📸 <b>Отправьте фотографию</b>\n\n"
        f"Пришлите изображение, которое хотите изменить.\n"
        f"Поддерживаются форматы: JPG, PNG\n\n"
        f"💰 Стоимость: 1 токен\n"
        f"💳 Ваш баланс: {current_user.token_count} токенов"
    )

    keyboard = ToMainMenuKeyboard()
    await message.answer(instruction_text, reply_markup=keyboard())


__all__ = ["router"]
