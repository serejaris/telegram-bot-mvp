"""Инициализация и запуск Telegram бота."""

import logging
from telegram.ext import Application, ChatJoinRequestHandler, MessageHandler, filters

from .handlers import join_request_handler, message_handler, edited_message_handler, error_handler

logger = logging.getLogger(__name__)


def create_bot(token: str) -> Application:
    """Создаёт и настраивает приложение бота."""
    application = Application.builder().token(token).build()

    # Chat join requests (only stored for configured chat_id inside handler).
    application.add_handler(ChatJoinRequestHandler(join_request_handler))
    
    # Обработчик всех сообщений (не только текстовых)
    application.add_handler(
        MessageHandler(
            filters.ALL & ~filters.COMMAND & filters.ChatType.GROUPS,
            message_handler
        )
    )
    
    # Обработчик отредактированных сообщений
    application.add_handler(
        MessageHandler(
            filters.UpdateType.EDITED_MESSAGE & filters.ChatType.GROUPS,
            edited_message_handler
        )
    )
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    logger.info("Bot application created")
    return application


async def start_bot(application: Application):
    """Запускает бота в режиме polling."""
    logger.info("Starting bot polling...")
    logger.info("Make sure Privacy Mode is DISABLED in @BotFather for this bot!")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "edited_message", "chat_join_request"]
    )
    
    logger.info("Bot is running")


async def stop_bot(application: Application):
    """Останавливает бота."""
    logger.info("Stopping bot...")
    await application.updater.stop()
    await application.stop()
    await application.shutdown()
    logger.info("Bot stopped")
