"""Обработчики сообщений Telegram бота."""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from ..models import save_message

logger = logging.getLogger(__name__)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик новых сообщений."""
    msg = update.effective_message
    
    if not msg:
        return
    
    # Только групповые чаты
    if msg.chat.type not in ['group', 'supergroup']:
        logger.debug(f"Ignoring message from non-group chat: {msg.chat.type}")
        return
    
    # Должен быть автор
    if not msg.from_user:
        logger.debug("Ignoring message without from_user")
        return
    
    try:
        await save_message(msg, is_edit=False)
        logger.info(
            f"Saved message {msg.message_id} from {msg.from_user.id} "
            f"in chat {msg.chat_id} ({msg.chat.title or 'No title'})"
        )
    except Exception as e:
        logger.error(f"Failed to save message {msg.message_id}: {e}")


async def edited_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отредактированных сообщений."""
    msg = update.edited_message
    
    if not msg:
        return
    
    # Только групповые чаты
    if msg.chat.type not in ['group', 'supergroup']:
        return
    
    if not msg.from_user:
        return
    
    try:
        await save_message(msg, is_edit=True)
        logger.info(
            f"Updated edited message {msg.message_id} in chat {msg.chat_id}"
        )
    except Exception as e:
        logger.error(f"Failed to update message {msg.message_id}: {e}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок бота."""
    logger.error(f"Update {update} caused error: {context.error}")
