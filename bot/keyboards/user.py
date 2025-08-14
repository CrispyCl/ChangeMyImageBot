from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from config import PAYMENT

STYLE_NAMES = {
    "anime": "🎌 Аниме",
    "manga": "📖 Манга",
    "oilpainting": "🖌 Масляная живопись",
    "watercolor": "💧 Акварель",
    "comic": "📰 Комикс",
    "cartoon": "🎭 Карикатура",
    "isometric": "📐 Изометрия",
    "sketch": "✏️ Карандашный скетч",
    "ink": "🖋 Чернильный рисунок",
    "3d_render": "🖥 3D Рендер",
    "minimalism": "⚪ Минимализм",
}


class MainUserKeyboard:
    def __call__(self, is_admin: bool) -> ReplyKeyboardMarkup:
        buttons: list[list[KeyboardButton]] = [
            [KeyboardButton(text="🎨 Изменить изображение")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💰 Баланс токенов")],
        ]
        return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


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
    def __call__(self):
        buttons = []
        row = []
        for style_id, label in STYLE_NAMES.items():
            row.append(InlineKeyboardButton(text=label, callback_data=f"style_{style_id}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
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
            [
                InlineKeyboardButton(
                    text=f"{PAYMENT[key]['token_count']} токенов - {PAYMENT[key]['price']}₽",
                    callback_data=f"buy_tokens_{PAYMENT[key]['token_count']}_{PAYMENT[key]['price']}",
                ),
            ]
            for key in PAYMENT
        ] + [[InlineKeyboardButton(text="🔙 В профиль", callback_data="profile")]]

        return InlineKeyboardMarkup(inline_keyboard=buttons)


__all__ = [
    "MainUserKeyboard",
    "StyleSelectionKeyboard",
    "PaymentKeyboard",
    "ProfileKeyboard",
    "TokenPurchaseKeyboard",
    "STYLE_NAMES",
]
