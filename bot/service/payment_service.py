import logging
from typing import Optional
import uuid

from yookassa import Configuration, Payment


class PaymentService:
    def __init__(self, shop_id: str, secret_key: str, logger: logging.Logger):
        Configuration.account_id = shop_id
        Configuration.secret_key = secret_key
        self.logger = logger

    async def create_payment(self, amount: int, description: str, user_id: str, phone_number: str) -> Optional[dict]:
        """Создает платеж в ЮKassa"""
        try:
            payment = Payment.create(
                {
                    "amount": {"value": str(amount), "currency": "RUB"},
                    "payment_method_data": {"type": "bank_card"},
                    "confirmation": {"type": "redirect", "return_url": "https://t.me/change_my_image_bot"},
                    "capture": True,
                    "description": description,
                    "metadata": {"user_id": user_id},
                    "receipt": {
                        "customer": {"phone": phone_number},
                        "items": [
                            {
                                "description": description,
                                "quantity": "1.0",
                                "amount": {"value": str(amount), "currency": "RUB"},
                                "vat_code": 1,  # Без НДС
                                "payment_mode": "full_payment",
                                "payment_subject": "service",
                            },
                        ],
                    },
                },
                uuid.uuid4(),
            )

            return {
                "payment_id": payment.id,
                "confirmation_url": payment.confirmation.confirmation_url,  # type: ignore
                "status": payment.status,
            }

        except Exception as e:
            self.logger.error(f"Error creating payment: {e}")
            return None

    async def check_payment(self, payment_id: str) -> Optional[dict]:
        """Проверяет статус платежа"""
        try:
            payment = Payment.find_one(payment_id)
            return {
                "status": payment.status,
                "paid": payment.paid,
                "amount": payment.amount.value,  # type: ignore
                "metadata": payment.metadata,
            }

        except Exception as e:
            self.logger.error(f"Error checking payment: {e}")
            return None


__all__ = ["PaymentService"]
