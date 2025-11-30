"""
Telegram Bot MVP для сбора сообщений из групповых чатов.

Точка входа приложения.
"""

import asyncio
import logging

from src.config import load_config, setup_logging
from src.database import create_pool, create_tables
from src.bot import create_application
from src.api import create_app, start_server

logger = logging.getLogger(__name__)


async def main() -> None:
    """Основная функция для запуска бота."""
    setup_logging()

    try:
        config = load_config()
    except KeyError as e:
        logger.critical(f"Missing required environment variable: {e}")
        return

    pool = None
    try:
        pool = await create_pool(config)
        await create_tables(pool)

        # Запускаем HTTP сервер
        await start_server(create_app(pool, config), config.port)

        # Создаём и запускаем бота
        application = create_application(config, pool)

        logger.info("Bot is starting with polling...")
        logger.info("Make sure Privacy Mode is disabled in @BotFather for this bot")

        await application.initialize()
        await application.start()

        await application.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message"]
        )

        # Ожидаем завершения
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Received shutdown signal")
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()

    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")
        raise
    finally:
        if pool:
            await pool.close()
            logger.info("Database connection pool closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")
