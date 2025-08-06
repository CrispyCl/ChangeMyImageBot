from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import MainUserKeyboard
from models import User

router = Router()


@router.callback_query(F.data == "to_main")
async def to_main_menu(callback: CallbackQuery, state: FSMContext, current_user: User):
    await state.clear()
    await process_start_command(callback.message, state, current_user=current_user)
    await callback.answer()
    await callback.message.delete()  # type: ignore


@router.message(CommandStart())
@router.message(F.text == "🏠 Главное меню")
async def process_start_command(message: Message, state: FSMContext, current_user: User) -> None:
    await state.clear()

    welcome_text = (
        "👋 <b>Добро пожаловать в MASC!</b>\n\n"
        "🎨 Здесь ты можешь превратить любое своё фото в настоящее произведение искусства.\n"
        "Выбери стиль — и MASC изменит изображение за секунды!\n\n"
        "📷 Просто отправь фото, а остальное мы сделаем за тебя."
    )

    keyboard = MainUserKeyboard()(is_admin=current_user.is_staff)

    await message.answer(welcome_text, reply_markup=keyboard)


__all__ = ["router"]
