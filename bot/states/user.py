from aiogram.fsm.state import State, StatesGroup


class ImageProcessing(StatesGroup):
    waiting_for_photo = State()
    choosing_style = State()
    waiting_for_payment = State()


class UserProfile(StatesGroup):
    viewing_profile = State()


__all__ = ["ImageProcessing", "UserProfile"]
