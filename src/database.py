"""
Модуль для работы с базой данных PostgreSQL.
"""

import json
import logging
from typing import Any

from psycopg_pool import AsyncConnectionPool
from telegram import User, Chat, Message

from .config import Config

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
-- Таблица чатов
CREATE TABLE IF NOT EXISTS chats (
    id BIGINT PRIMARY KEY,
    type VARCHAR(255) NOT NULL,
    title TEXT,
    username VARCHAR(255) UNIQUE,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    is_bot BOOLEAN NOT NULL,
    first_name TEXT,
    last_name TEXT,
    username VARCHAR(255) UNIQUE,
    language_code VARCHAR(10),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Таблица сообщений
CREATE TABLE IF NOT EXISTS messages (
    message_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    text TEXT,
    sent_at TIMESTAMPTZ NOT NULL,
    raw_message JSONB,

    PRIMARY KEY (chat_id, message_id),
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_sent_at ON messages(sent_at);
CREATE INDEX IF NOT EXISTS idx_chats_username ON chats(username) WHERE username IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL;
"""


async def create_pool(config: Config) -> AsyncConnectionPool:
    """
    Создаёт и открывает пул соединений к базе данных.

    Args:
        config: Конфигурация приложения.

    Returns:
        Открытый пул соединений.
    """
    logger.info("Connecting to database...")
    pool = AsyncConnectionPool(
        config.database_url,
        min_size=config.db_pool_min_size,
        max_size=config.db_pool_max_size,
        open=False
    )
    await pool.open()
    logger.info("Database connection pool created successfully")
    return pool


async def create_tables(pool: AsyncConnectionPool) -> None:
    """
    Создаёт необходимые таблицы в базе данных.

    Args:
        pool: Пул соединений к базе данных.
    """
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(SCHEMA_SQL)
                logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


async def save_user(cursor: Any, user: User) -> None:
    """
    Сохраняет или обновляет пользователя в базе данных.

    Args:
        cursor: Курсор базы данных.
        user: Объект пользователя Telegram.
    """
    await cursor.execute("""
        INSERT INTO users (id, is_bot, first_name, last_name, username, language_code)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            username = EXCLUDED.username,
            language_code = EXCLUDED.language_code;
    """, (
        user.id,
        user.is_bot,
        user.first_name,
        user.last_name,
        user.username,
        user.language_code
    ))


async def save_chat(cursor: Any, chat: Chat) -> None:
    """
    Сохраняет или обновляет чат в базе данных.

    Args:
        cursor: Курсор базы данных.
        chat: Объект чата Telegram.
    """
    await cursor.execute("""
        INSERT INTO chats (id, type, title, username)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            username = EXCLUDED.username,
            last_updated_at = NOW();
    """, (
        chat.id,
        chat.type,
        chat.title,
        chat.username
    ))


async def save_message(cursor: Any, message: Message) -> None:
    """
    Сохраняет сообщение в базе данных.

    Args:
        cursor: Курсор базы данных.
        message: Объект сообщения Telegram.
    """
    await cursor.execute("""
        INSERT INTO messages (message_id, chat_id, user_id, text, sent_at, raw_message)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (chat_id, message_id) DO NOTHING;
    """, (
        message.message_id,
        message.chat_id,
        message.from_user.id,
        message.text,
        message.date,
        json.dumps(message.to_dict())
    ))


async def get_chat_messages(pool: AsyncConnectionPool, chat_id: int) -> list[dict]:
    """
    Получает все сообщения из указанного чата.

    Args:
        pool: Пул соединений к базе данных.
        chat_id: ID чата.

    Returns:
        Список сообщений с информацией о пользователях.
    """
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                SELECT
                    m.message_id,
                    m.text,
                    m.sent_at,
                    u.first_name,
                    u.last_name,
                    u.username
                FROM messages m
                LEFT JOIN users u ON m.user_id = u.id
                WHERE m.chat_id = %s
                ORDER BY m.sent_at ASC
            """, (chat_id,))

            rows = await cur.fetchall()

            return [
                {
                    "message_id": row[0],
                    "text": row[1],
                    "sent_at": row[2].isoformat() if row[2] else None,
                    "user": {
                        "first_name": row[3],
                        "last_name": row[4],
                        "username": row[5]
                    }
                }
                for row in rows
            ]


async def check_connection(pool: AsyncConnectionPool) -> bool:
    """
    Проверяет подключение к базе данных.

    Args:
        pool: Пул соединений.

    Returns:
        True если подключение успешно.
    """
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
            result = await cur.fetchone()
            return result is not None and result[0] == 1
