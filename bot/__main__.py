import asyncio
from contextlib import suppress
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio.client import Redis

from config import Config, load_config
from database import DefaultDatabase, PostgresDatabase
from handlers import cleanup_old_payments, commands_router, image_processing_router, payments_router, user_router
from keyboards import setup_menu
from logger import get_logger
from middleware import setup as setup_middlewares
from repository import UserRepository
from service import GeminiImageService, PaymentService, UserService


async def periodic_cleanup(logger: logging.Logger):
    """Периодическая очистка старых платежей"""
    while True:
        try:
            await cleanup_old_payments()
            await asyncio.sleep(30 * 60)  # Очищаем каждые пол часа
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")
            await asyncio.sleep(30 * 60)


async def shutdown(
    bot: Bot,
    dp: Dispatcher,
    logger: logging.Logger,
    redis: Redis | None,
    db: DefaultDatabase,
) -> None:
    """
    Gracefully shutdown bot and resources.
    """

    logger.info("Shutting down bot...")

    logger.debug("Closing storage...")
    await dp.fsm.storage.close()
    if redis:
        try:
            await redis.aclose()
        except Exception as e:
            logger.error("Failed to close Redis storage: %s", str(e))

    logger.debug("Stopping bot...")
    try:
        await bot.session.close()
    except Exception as e:
        logger.error("Failed to close bot session: %s", str(e))

    logger.debug("Closing database connection...")
    try:
        await db.close()
    except Exception as e:
        logger.error("Failed to close database connection: %s", str(e))

    logger.info("Bot shut down successfully.")


async def main() -> None:
    # Loading the config
    config: Config = load_config()

    # Configuring the logging
    logger = get_logger("main", config.logger)
    logger.info("Starting bot...")

    logger.debug("Initializing the storage object...")
    redis = Redis(host=config.redis.host, port=config.redis.port, db=config.redis.db)
    try:
        await redis.ping()
    except Exception as e:
        logger.fatal("Storage initialization failed: %s", str(e))
        return
    storage = RedisStorage(redis=redis)

    logger.debug("Connecting to the database...")
    db = PostgresDatabase(config=config.postgres)
    try:
        await db.init_db()
    except Exception as e:
        logger.fatal("Database connection failed: %s", str(e))
        return

    logger.debug("Initializing the bot...")
    try:
        bot = Bot(token=config.bot.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher(storage=storage)
    except Exception as e:
        logger.fatal("Bot initialization failed: %s", str(e))
        return
    dp.workflow_data["logger"] = logger
    dp.workflow_data["database"] = db

    logger.debug("Loading menu...")
    try:
        await setup_menu(bot)
    except Exception as e:
        logger.fatal("Menu loading failed: %s", str(e))

    logger.debug("Registering repositories...")
    user_repository = UserRepository(db)

    logger.debug("Registering services...")
    user_service = UserService(user_repository, logger)
    dp.workflow_data["user_service"] = user_service
    image_service = GeminiImageService(config.gemini.api_key, logger)
    dp.workflow_data["image_service"] = image_service
    payment_service = PaymentService(config.yookassa.shop_id, config.yookassa.secret_key, logger)
    dp.workflow_data["payment_service"] = payment_service

    logger.debug("Registering routers...")
    dp.include_router(commands_router)
    dp.include_router(payments_router)
    dp.include_router(user_router)
    dp.include_router(image_processing_router)

    logger.debug("Registering middlewares...")
    setup_middlewares(dp, logger, user_service=user_service)

    logger.debug("Starting periodic cleanup task...")
    cleanup_task = asyncio.create_task(periodic_cleanup(logger))

    # Graceful shutdown handling
    try:
        logger.info("Bot was started")
        await dp.start_polling(bot)
    except Exception as e:
        logger.fatal("An error occurred: %s", e)
    finally:
        cleanup_task.cancel()
        await shutdown(bot, dp, logger, redis, db)


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(main())


__all__ = []
