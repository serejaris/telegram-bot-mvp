"""Модуль Telegram бота."""

from .bot import create_bot
from .handlers import message_handler, edited_message_handler

__all__ = ["create_bot", "message_handler", "edited_message_handler"]
