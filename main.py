"""Telegram Bot Scraper v2.0
Сбор сообщений из групповых чатов с веб-админкой.
"""

import asyncio
import json
import logging
import signal
from datetime import datetime, timezone

from app.config import get_config
from app.database import init_pool, close_pool
from app.models import init_database
from app.bot.bot import create_bot, start_bot, stop_bot
from app.bot.handlers import clean_join_requests_job
from app.web.routes import create_web_app, start_web_server


class JSONFormatter(logging.Formatter):
    """JSON formatter для структурированных логов (удобно для Railway)."""
    def format(self, record):
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


def setup_logging(level: str = "INFO"):
    """Настраивает логирование."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        handlers=[handler]
    )


async def main():
    """Главная функция запуска приложения."""
    # Загружаем конфигурацию
    config = get_config()

    # Настраиваем логирование
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    logger.info("Starting Telegram Bot Scraper v2.0")

    bot_app = None
    web_runner = None
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Received shutdown signal")
        shutdown_event.set()

    # Регистрируем обработчики сигналов
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        # Инициализируем базу данных
        await init_pool(config.database_url)
        await init_database()
        logger.info("Database initialized")

        # Создаём и запускаем веб-сервер
        web_app = create_web_app()
        web_runner = await start_web_server(web_app, config.port)
        logger.info(f"Admin panel available at http://localhost:{config.port}")

        # Создаём и запускаем бота
        bot_app = create_bot(config.telegram_token)

        if config.vibecoder_chat_id:
            bot_app.job_queue.run_repeating(
                clean_join_requests_job,
                interval=config.join_request_clean_interval_sec,
                first=10,
                name="clean_join_requests",
            )
            logger.info(
                "Scheduled clean_join_requests job: interval=%ss chat_id=%s threshold=%s",
                config.join_request_clean_interval_sec,
                config.vibecoder_chat_id,
                config.fresh_account_id_threshold,
            )
        await start_bot(bot_app)

        # Ждём до получения сигнала остановки
        logger.info("Application is running. Press Ctrl+C to stop.")
        await shutdown_event.wait()

    except Exception as e:
        logger.critical(f"Application error: {e}")
        raise
    finally:
        # Корректно останавливаем всё
        logger.info("Shutting down...")

        if bot_app:
            try:
                await asyncio.wait_for(stop_bot(bot_app), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Bot stop timed out, forcing shutdown")

        if web_runner:
            await web_runner.cleanup()

        await close_pool()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
