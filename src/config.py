"""
Конфигурация приложения из переменных окружения.
"""

import os
import logging
from dataclasses import dataclass


@dataclass
class Config:
    """Конфигурация приложения."""
    telegram_token: str
    database_url: str
    port: int
    public_chat_id: int
    db_pool_min_size: int = 1
    db_pool_max_size: int = 10


def load_config() -> Config:
    """
    Загружает конфигурацию из переменных окружения.

    Raises:
        KeyError: Если обязательная переменная окружения не установлена.
    """
    return Config(
        telegram_token=os.environ["TELEGRAM_TOKEN"],
        database_url=os.environ["DATABASE_URL"],
        port=int(os.getenv("PORT", "8000")),
        public_chat_id=int(os.environ["PUBLIC_CHAT_ID"]),
        db_pool_min_size=int(os.getenv("DB_POOL_MIN_SIZE", "1")),
        db_pool_max_size=int(os.getenv("DB_POOL_MAX_SIZE", "10")),
    )


def setup_logging() -> logging.Logger:
    """Настраивает и возвращает логгер."""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    return logging.getLogger(__name__)
