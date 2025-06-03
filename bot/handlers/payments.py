import asyncio
from datetime import datetime, timedelta
from logging import Logger

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from keyboards import ProfileKeyboard, TokenPurchaseKeyboard
from models import User
from service import PaymentService, UserService
from states import ImageProcessing

router = Router()

# Словарь для отслеживания активных платежей
active_payments = {}


@router.callback_query(F.data.startswith("buy_tokens_"))
async def process_token_purchase(
    callback: CallbackQuery,
    current_user: User,
    payment_service: PaymentService,
    logger: Logger,
    user_service: UserService,
    bot: Bot,
):
    """Обрабатывает покупку токенов"""
    data_parts = str(callback.data).split("_")
    tokens = int(data_parts[2])
    amount = int(data_parts[3])

    # Создаем платеж через ЮKassa
    payment_data = await payment_service.create_payment(
        amount=amount,
        description=f"Покупка {tokens} токенов",
        user_id=current_user.id,
    )

    if payment_data:
        payment_id = payment_data["payment_id"]

        # Сохраняем информацию о платеже для отслеживания
        active_payments[payment_id] = {
            "user_id": current_user.id,
            "tokens": tokens,
            "amount": amount,
            "created_at": datetime.now(),
            "status": "pending",
        }

        # Запускаем фоновую задачу для отслеживания платежа
        asyncio.create_task(track_payment_background(logger, payment_id, payment_service, bot, user_service))

        payment_text = (
            f"💳 <b>Оплата токенов</b>\n\n"
            f"Пакет: {tokens} токенов\n"
            f"Сумма: {amount}₽\n\n"
            f"Для оплаты перейдите по ссылке ниже:\n"
            f"💡 <i>Токены будут зачислены автоматически после оплаты</i>"
        )

        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить", url=payment_data["confirmation_url"])],
                [
                    InlineKeyboardButton(
                        text="✅ Проверить оплату",
                        callback_data=f"check_payment_{payment_id}_{tokens}",
                    ),
                ],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="profile")],
            ],
        )

        await callback.message.edit_text(payment_text, reply_markup=keyboard)  # type: ignore
    else:
        error_text = "❌ <b>Ошибка создания платежа</b>\n\nПопробуйте позже или обратитесь в поддержку."
        keyboard = ProfileKeyboard()
        await callback.message.edit_text(error_text, reply_markup=keyboard())  # type: ignore

    await callback.answer()


async def track_payment_background(
    logger: Logger,
    payment_id: str,
    payment_service: PaymentService,
    bot: Bot,
    user_service: UserService,
):
    """Фоновая задача для отслеживания платежа"""
    max_attempts = 60  # Проверяем в течение 30 минут
    attempt = 0

    while attempt < max_attempts:
        try:
            payment_status = await payment_service.check_payment(payment_id)

            if payment_status and payment_status.get("paid"):
                await process_successful_payment(payment_id, bot, logger, user_service)
                break
            if payment_status and payment_status.get("status") == "cancelled":
                await process_cancelled_payment(logger, payment_id, bot)
                break

            await asyncio.sleep(30)
            attempt += 1

        except Exception as e:
            logger.error(f"Error tracking payment {payment_id}: {e}")
            await asyncio.sleep(30)
            attempt += 1

    if attempt >= max_attempts and payment_id in active_payments:
        active_payments[payment_id]["status"] = "expired"


async def process_successful_payment(payment_id: str, bot: Bot, logger: Logger, user_service: UserService):
    """Обрабатывает успешный платеж"""
    if payment_id not in active_payments:
        return

    payment_info = active_payments[payment_id]
    if payment_info["status"] != "pending":
        return

    try:
        # Добавляем токены пользователю
        user_id = payment_info["user_id"]
        tokens = payment_info["tokens"]

        current_user = await user_service.get_one(user_id)
        if current_user:
            updated_user = await user_service.update_token_count(user_id, tokens)

            if updated_user:
                # Отправляем уведомление пользователю
                success_text = (
                    f"✅ <b>Платеж успешно обработан!</b>\n\n"
                    f"💰 Зачислено токенов: {tokens}\n"
                    f"💳 Ваш баланс: {updated_user.token_count} токенов\n\n"
                    f"🎉 Спасибо за покупку!\n"
                    f"Теперь вы можете генерировать изображения."
                )

                try:
                    await bot.send_message(chat_id=user_id, text=success_text)
                except Exception as e:
                    logger.error(f"Failed to send success notification to user {user_id}: {e}")

                # Помечаем платеж как обработанный
                active_payments[payment_id]["status"] = "completed"
                logger.info(f"Payment {payment_id} processed successfully for user {user_id}")
            else:
                logger.error(f"Failed to add tokens for payment {payment_id}")
        else:
            logger.error(f"User {user_id} not found for payment {payment_id}")

    except Exception as e:
        logger.error(f"Error processing successful payment {payment_id}: {e}")


async def process_cancelled_payment(logger: Logger, payment_id: str, bot: Bot):
    """Обрабатывает отмененный платеж"""
    if payment_id not in active_payments:
        return

    payment_info = active_payments[payment_id]
    if payment_info["status"] != "pending":
        return

    try:
        user_id = payment_info["user_id"]

        cancel_text = (
            "❌ <b>Платеж отменен</b>\n\n"
            "Ваш платеж был отменен или не завершен.\n"
            "Если у вас возникли проблемы, обратитесь в поддержку."
        )

        try:
            await bot.send_message(chat_id=user_id, text=cancel_text)
        except Exception as e:
            logger.error(f"Failed to send cancel notification to user {user_id}: {e}")

        # Помечаем платеж как отмененный
        active_payments[payment_id]["status"] = "cancelled"

    except Exception as e:
        logger.error(f"Error processing cancelled payment {payment_id}: {e}")


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_status(
    callback: CallbackQuery,
    current_user: User,
    user_service: UserService,
    payment_service: PaymentService,
    bot: Bot,
    logger: Logger,
):
    """Проверяет статус платежа вручную"""
    data_parts = str(callback.data).split("_")
    payment_id = data_parts[2]
    tokens = int(data_parts[3])

    # Проверяем, не был ли платеж уже обработан в фоне
    if payment_id in active_payments:
        payment_info = active_payments[payment_id]
        if payment_info["status"] == "completed":
            success_text = (
                "✅ <b>Платеж уже обработан!</b>\n\n"
                "Токены были зачислены на ваш счет.\n"
                "Проверьте ваш баланс в профиле."
            )
            keyboard = ProfileKeyboard()
            await callback.message.edit_text(success_text, reply_markup=keyboard())  # type: ignore
            await callback.answer("Платеж уже обработан!")
            return
        if payment_info["status"] == "cancelled":
            # Платеж отменен
            cancel_text = "❌ <b>Платеж отменен</b>\n\nВаш платеж был отменен или не завершен."
            keyboard = ProfileKeyboard()
            await callback.message.edit_text(cancel_text, reply_markup=keyboard())  # type: ignore
            await callback.answer("Платеж отменен")
            return

    # Проверяем статус платежа в реальном времени
    payment_status = await payment_service.check_payment(payment_id)

    if payment_status and payment_status["paid"]:
        await process_successful_payment(payment_id, bot, logger, user_service)

        updated_user = await user_service.get_one(current_user.id)

        success_text = (
            f"✅ <b>Оплата успешна!</b>\n\n"
            f"Добавлено токенов: {tokens}\n"
            f"Ваш баланс: {updated_user.token_count if updated_user else 'Неизвестно'} токенов\n\n"
            f"Спасибо за покупку! 🎉"
        )
        keyboard = ProfileKeyboard()
        await callback.message.edit_text(success_text, reply_markup=keyboard())  # type: ignore
    else:
        pending_text = (
            "⏳ <b>Платеж в обработке</b>\n\n"
            "Платеж еще не завершен.\n"
            "💡 <i>Токены будут зачислены автоматически после оплаты</i>\n\n"
            "Вы можете закрыть это окно - мы уведомим вас о зачислении."
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Проверить снова", callback_data=f"check_payment_{payment_id}_{tokens}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="profile")],
            ],
        )

        await callback.message.edit_text(pending_text, reply_markup=keyboard)  # type: ignore

    await callback.answer()


@router.callback_query(F.data.startswith("pay_"))
async def process_image_payment(callback: CallbackQuery, state: FSMContext, current_user: User):
    """Обрабатывает оплату за генерацию изображения"""
    if current_user.token_count <= 0:
        no_tokens_text = (
            "😔 <b>Недостаточно токенов</b>\n\n"
            "У вас нет токенов для генерации изображений.\n"
            "Купите токены для продолжения работы!"
        )

        keyboard = TokenPurchaseKeyboard()
        await callback.message.edit_text(no_tokens_text, reply_markup=keyboard())  # type: ignore
        await callback.answer()
        return

    # Продолжаем процесс генерации
    await state.set_state(ImageProcessing.waiting_for_payment)

    processing_text = (
        "⚡ <b>Начинаем генерацию</b>\n\n"
        "Ваше изображение обрабатывается...\n"
        "Это может занять несколько минут.\n\n"
        "💰 Списан 1 токен"
    )

    await callback.message.edit_text(processing_text)  # type: ignore
    await callback.answer("Генерация началась!")


# Функция для очистки старых платежей (вызывать периодически)
async def cleanup_old_payments():
    """Очищает информацию о старых платежах"""
    current_time = datetime.now()
    expired_payments = []

    for payment_id, payment_info in active_payments.items():
        # Удаляем платежи старше 1 часа
        if current_time - payment_info["created_at"] > timedelta(hours=1):
            expired_payments.append(payment_id)

    for payment_id in expired_payments:
        del active_payments[payment_id]


__all__ = ["router", "cleanup_old_payments"]
