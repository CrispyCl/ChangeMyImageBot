from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import PAYMENT
from keyboards import ProfileKeyboard, TokenPurchaseKeyboard
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
        + "\n".join(f"🔹 {PAYMENT[key]['token_count']} токенов - {PAYMENT[key]['price']}₽" for key in PAYMENT.keys())
        + "\n\n💡 Чем больше пакет, тем выгоднее цена!"
    )

    keyboard = TokenPurchaseKeyboard()
    await callback.message.edit_text(purchase_text, reply_markup=keyboard())  # type: ignore
    await callback.answer()


__all__ = ["router"]
