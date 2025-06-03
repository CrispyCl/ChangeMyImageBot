from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


class MainUserKeyboard:
    def __call__(self, is_admin: bool) -> ReplyKeyboardMarkup:
        buttons: list[list[KeyboardButton]] = [
            [KeyboardButton(text="🎨 Изменить изображение")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💰 Баланс токенов")],
        ]
        return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


class ToMainMenuKeyboard:
    def __call__(self) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="🏠 Главное меню")]],
            resize_keyboard=True,
        )


class RequestPhoneNumberKeyboard:
    def __call__(self) -> ReplyKeyboardMarkup:
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📱 Поделиться номером", request_contact=True)],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        )


class StyleSelectionKeyboard:
    def __call__(self) -> InlineKeyboardMarkup:
        buttons = [
            [InlineKeyboardButton(text="🎌 Аниме", callback_data="style_anime")],
            [InlineKeyboardButton(text="🎨 Реализм", callback_data="style_realism")],
            [InlineKeyboardButton(text="🖼️ Арт", callback_data="style_art")],
            [InlineKeyboardButton(text="🌟 Фэнтези", callback_data="style_fantasy")],
            [InlineKeyboardButton(text="🤖 Киберпанк", callback_data="style_cyberpunk")],
            [InlineKeyboardButton(text="🎭 Карикатура", callback_data="style_cartoon")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="to_main")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)


class PaymentKeyboard:
    def __call__(self, amount: int) -> InlineKeyboardMarkup:
        buttons = [
            [InlineKeyboardButton(text=f"💳 Оплатить {amount}₽", callback_data=f"pay_{amount}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="to_main")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)


class ProfileKeyboard:
    def __call__(self) -> InlineKeyboardMarkup:
        buttons = [
            [InlineKeyboardButton(text="💰 Купить токены", callback_data="buy_tokens")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="to_main")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)


class TokenPurchaseKeyboard:
    def __call__(self) -> InlineKeyboardMarkup:
        buttons = [
            [InlineKeyboardButton(text="150 токенов - 990₽", callback_data="buy_tokens_150_990")],
            [InlineKeyboardButton(text="350 токенов - 1990₽", callback_data="buy_tokens_350_1990")],
            [InlineKeyboardButton(text="800 токенов - 3990₽", callback_data="buy_tokens_800_3990")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="profile")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)


__all__ = [
    "MainUserKeyboard",
    "ToMainMenuKeyboard",
    "StyleSelectionKeyboard",
    "PaymentKeyboard",
    "ProfileKeyboard",
    "TokenPurchaseKeyboard",
]
