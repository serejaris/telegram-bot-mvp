"""
Модуль Telegram бота для сбора сообщений.
"""

import logging
from typing import Callable

from psycopg_pool import AsyncConnectionPool
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

from .config import Config
from .database import save_user, save_chat, save_message

logger = logging.getLogger(__name__)


def create_message_handler(pool: AsyncConnectionPool) -> Callable:
    """
    Создаёт обработчик для сохранения текстовых сообщений.

    Args:
        pool: Пул соединений к базе данных.

    Returns:
        Асинхронный обработчик сообщений.
    """
    async def store_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.effective_message

        if not msg or not msg.text:
            return

        if msg.chat.type not in ['group', 'supergroup']:
            logger.debug(f"Ignoring message from non-group chat: {msg.chat.type}")
            return

        if not msg.from_user:
            logger.debug("Ignoring message without from_user")
            return

        try:
            async with pool.connection() as conn:
                async with conn.cursor() as cur:
                    await save_user(cur, msg.from_user)
                    await save_chat(cur, msg.chat)
                    await save_message(cur, msg)

                    logger.info(
                        f"Stored message {msg.message_id} from user {msg.from_user.id} "
                        f"in chat {msg.chat_id} ({msg.chat.title or 'No title'})"
                    )
        except Exception as e:
            logger.error(f"Failed to store message {msg.message_id}: {e}")

    return store_message


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик ошибок бота.

    Args:
        update: Объект обновления от Telegram.
        context: Контекст с информацией об ошибке.
    """
    logger.error(f"Update {update} caused error {context.error}")


def create_application(config: Config, pool: AsyncConnectionPool) -> Application:
    """
    Создаёт и настраивает приложение Telegram бота.

    Args:
        config: Конфигурация приложения.
        pool: Пул соединений к базе данных.

    Returns:
        Настроенное приложение бота.
    """
    application = Application.builder().token(config.telegram_token).build()

    message_handler = create_message_handler(pool)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler
        )
    )

    application.add_error_handler(error_handler)

    return application
