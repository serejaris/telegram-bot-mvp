"""Модели и SQL запросы для работы с данными."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from telegram import User, Chat, Message, MessageOriginChat, MessageOriginChannel

from .database import get_cursor, get_connection

logger = logging.getLogger(__name__)


# SQL для создания таблиц
CREATE_TABLES_SQL = """
-- Таблица чатов
CREATE TABLE IF NOT EXISTS chats (
    id BIGINT PRIMARY KEY,
    type VARCHAR(255) NOT NULL,
    title TEXT,
    username VARCHAR(255),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    is_bot BOOLEAN NOT NULL,
    first_name TEXT,
    last_name TEXT,
    username VARCHAR(255),
    language_code VARCHAR(10),
    is_premium BOOLEAN DEFAULT FALSE,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Таблица сообщений (расширенная)
CREATE TABLE IF NOT EXISTS messages (
    message_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    user_id BIGINT,
    message_type VARCHAR(50) NOT NULL DEFAULT 'text',
    text TEXT,
    caption TEXT,
    reply_to_message_id BIGINT,
    forward_from_chat_id BIGINT,
    sent_at TIMESTAMPTZ NOT NULL,
    edited_at TIMESTAMPTZ,
    raw_message JSONB,

    PRIMARY KEY (chat_id, message_id),
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Таблица заявок на вступление (для авто-отклонения "свежих" аккаунтов)
CREATE TABLE IF NOT EXISTS join_requests (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    username VARCHAR(255),
    first_name TEXT,
    bio TEXT,
    request_date TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_join_requests_user_chat UNIQUE (user_id, chat_id),
    CONSTRAINT ck_join_requests_status CHECK (status IN ('pending','declined','expired')),
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Индексы для оптимизации запросов (кроме message_type - создаётся после миграций)
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_sent_at ON messages(sent_at);
CREATE INDEX IF NOT EXISTS idx_chats_username ON chats(username) WHERE username IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_join_requests_chat_status ON join_requests(chat_id, status);
CREATE INDEX IF NOT EXISTS idx_join_requests_user_id ON join_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_join_requests_request_date ON join_requests(request_date);
"""

# SQL для миграции существующих таблиц
MIGRATION_SQL = """
-- Добавляем новые колонки, если их нет
DO $$ 
BEGIN
    -- messages: message_type
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='messages' AND column_name='message_type') THEN
        ALTER TABLE messages ADD COLUMN message_type VARCHAR(50) NOT NULL DEFAULT 'text';
    END IF;
    
    -- messages: caption
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='messages' AND column_name='caption') THEN
        ALTER TABLE messages ADD COLUMN caption TEXT;
    END IF;
    
    -- messages: reply_to_message_id
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='messages' AND column_name='reply_to_message_id') THEN
        ALTER TABLE messages ADD COLUMN reply_to_message_id BIGINT;
    END IF;
    
    -- messages: forward_from_chat_id
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='messages' AND column_name='forward_from_chat_id') THEN
        ALTER TABLE messages ADD COLUMN forward_from_chat_id BIGINT;
    END IF;
    
    -- messages: edited_at
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='messages' AND column_name='edited_at') THEN
        ALTER TABLE messages ADD COLUMN edited_at TIMESTAMPTZ;
    END IF;
    
    -- users: is_premium
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='is_premium') THEN
        ALTER TABLE users ADD COLUMN is_premium BOOLEAN DEFAULT FALSE;
    END IF;
    
    -- users: last_updated_at
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='users' AND column_name='last_updated_at') THEN
        ALTER TABLE users ADD COLUMN last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
    END IF;
END $$;

-- Создаём индекс для message_type если его нет
CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(message_type);
"""


async def create_tables():
    """Создает таблицы в базе данных."""
    async with get_cursor() as cur:
        await cur.execute(CREATE_TABLES_SQL)
        logger.info("Database tables created/verified")


async def run_migrations():
    """Запускает миграции для обновления схемы."""
    async with get_cursor() as cur:
        await cur.execute(MIGRATION_SQL)
        logger.info("Database migrations completed")


async def init_database():
    """Инициализирует базу данных: создаёт таблицы и запускает миграции."""
    # Сначала создаём базовые таблицы
    await create_tables()
    # Затем запускаем миграции (добавляют новые колонки)
    await run_migrations()
    # Создаём индекс на message_type после миграций
    async with get_cursor() as cur:
        await cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(message_type);")
        logger.info("Message type index created/verified")


def detect_message_type(msg: Message) -> str:
    """Определяет тип сообщения."""
    if msg.text:
        return "text"
    elif msg.photo:
        return "photo"
    elif msg.video:
        return "video"
    elif msg.audio:
        return "audio"
    elif msg.voice:
        return "voice"
    elif msg.video_note:
        return "video_note"
    elif msg.document:
        return "document"
    elif msg.sticker:
        return "sticker"
    elif msg.animation:
        return "animation"
    elif msg.poll:
        return "poll"
    elif msg.location:
        return "location"
    elif msg.contact:
        return "contact"
    elif msg.dice:
        return "dice"
    else:
        return "other"


def get_forward_chat_id(msg: Message) -> Optional[int]:
    """Извлекает ID чата-источника для пересланных сообщений.
    
    В python-telegram-bot v21+ forward_from_chat заменён на forward_origin.
    """
    if not msg.forward_origin:
        return None
    
    # MessageOriginChat - сообщение переслано от имени чата
    if isinstance(msg.forward_origin, MessageOriginChat):
        return msg.forward_origin.sender_chat.id
    
    # MessageOriginChannel - сообщение переслано из канала
    if isinstance(msg.forward_origin, MessageOriginChannel):
        return msg.forward_origin.chat.id
    
    # MessageOriginUser, MessageOriginHiddenUser - нет chat ID
    return None


async def save_user(user: User):
    """Сохраняет или обновляет пользователя."""
    async with get_cursor() as cur:
        await cur.execute("""
            INSERT INTO users (id, is_bot, first_name, last_name, username, language_code, is_premium, last_updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (id) DO UPDATE SET
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                username = EXCLUDED.username,
                language_code = EXCLUDED.language_code,
                is_premium = EXCLUDED.is_premium,
                last_updated_at = NOW();
        """, (
            user.id,
            user.is_bot,
            user.first_name,
            user.last_name,
            user.username,
            user.language_code,
            getattr(user, 'is_premium', False) or False,
        ))


async def save_chat(chat: Chat):
    """Сохраняет или обновляет чат."""
    async with get_cursor() as cur:
        await cur.execute("""
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
            chat.username,
        ))


async def save_message(msg: Message, is_edit: bool = False):
    """Сохраняет сообщение в базу данных."""
    if not msg.from_user:
        return
    
    # Сохраняем пользователя и чат
    await save_user(msg.from_user)
    await save_chat(msg.chat)
    
    message_type = detect_message_type(msg)
    text_content = msg.text or None
    caption = msg.caption or None
    reply_to_id = msg.reply_to_message.message_id if msg.reply_to_message else None
    forward_chat_id = get_forward_chat_id(msg)
    
    async with get_cursor() as cur:
        if is_edit:
            # Обновляем существующее сообщение
            await cur.execute("""
                UPDATE messages 
                SET text = %s, caption = %s, edited_at = %s, raw_message = %s
                WHERE chat_id = %s AND message_id = %s;
            """, (
                text_content,
                caption,
                msg.edit_date,
                json.dumps(msg.to_dict()),
                msg.chat_id,
                msg.message_id,
            ))
        else:
            # Вставляем новое сообщение
            await cur.execute("""
                INSERT INTO messages (
                    message_id, chat_id, user_id, message_type, text, caption,
                    reply_to_message_id, forward_from_chat_id, sent_at, raw_message
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chat_id, message_id) DO NOTHING;
            """, (
                msg.message_id,
                msg.chat_id,
                msg.from_user.id,
                message_type,
                text_content,
                caption,
                reply_to_id,
                forward_chat_id,
                msg.date,
                json.dumps(msg.to_dict()),
            ))


async def save_join_request_fields(
    user_id: int,
    chat_id: int,
    username: Optional[str],
    first_name: Optional[str],
    bio: Optional[str],
    request_date: datetime,
    *,
    user: Optional[User] = None,
    chat: Optional[Chat] = None,
) -> Optional[int]:
    """Save (UPSERT) join request by (user_id, chat_id).

    If user/chat objects are provided, we also upsert them into users/chats tables
    so FK constraints on join_requests are satisfied.
    """
    if user is not None:
        await save_user(user)
    if chat is not None:
        await save_chat(chat)

    async with get_cursor() as cur:
        await cur.execute(
            """
            INSERT INTO join_requests (user_id, chat_id, username, first_name, bio, request_date, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
            ON CONFLICT (user_id, chat_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                bio = EXCLUDED.bio,
                request_date = EXCLUDED.request_date,
                status = 'pending'
            RETURNING id;
            """,
            (user_id, chat_id, username, first_name, bio, request_date),
        )
        row = await cur.fetchone()
        return int(row[0]) if row else None


async def get_pending_fresh_join_requests(chat_id: int, min_user_id: int, limit: int) -> List[Dict[str, Any]]:
    """Get pending join requests for chat with user_id >= threshold."""
    async with get_cursor() as cur:
        await cur.execute(
            """
            SELECT id, user_id, chat_id, username, first_name, request_date
            FROM join_requests
            WHERE chat_id = %s
              AND status = 'pending'
              AND user_id >= %s
            ORDER BY request_date ASC
            LIMIT %s;
            """,
            (chat_id, min_user_id, limit),
        )
        rows = await cur.fetchall()

    return [
        {
            "id": row[0],
            "user_id": row[1],
            "chat_id": row[2],
            "username": row[3],
            "first_name": row[4],
            "request_date": row[5],
        }
        for row in rows
    ]


async def mark_join_requests_status(ids: List[int], status: str) -> int:
    """Update join_requests.status for given primary keys, return updated count."""
    if not ids:
        return 0

    async with get_cursor() as cur:
        await cur.execute(
            "UPDATE join_requests SET status = %s WHERE id = ANY(%s::bigint[]);",
            (status, ids),
        )
        return int(cur.rowcount or 0)


async def get_join_requests(
    chat_id: int,
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get join requests for a chat (for admin/API inspection)."""
    async with get_cursor() as cur:
        query = """
            SELECT
                id,
                user_id,
                chat_id,
                username,
                first_name,
                bio,
                request_date,
                status,
                created_at
            FROM join_requests
            WHERE chat_id = %s
        """
        params: List[Any] = [chat_id]

        if status:
            query += " AND status = %s"
            params.append(status)

        query += " ORDER BY request_date DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        await cur.execute(query, params)
        rows = await cur.fetchall()

    return [
        {
            "id": row[0],
            "user_id": row[1],
            "chat_id": row[2],
            "username": row[3],
            "first_name": row[4],
            "bio": row[5],
            "request_date": row[6],
            "status": row[7],
            "created_at": row[8],
        }
        for row in rows
    ]


# ========== Запросы для админки ==========

@dataclass
class ChatStats:
    """Статистика по чату."""
    id: int
    type: str
    title: Optional[str]
    username: Optional[str]
    message_count: int
    user_count: int
    last_message_at: Optional[datetime]
    first_seen_at: datetime


@dataclass
class Stats:
    """Общая статистика."""
    total_chats: int
    total_users: int
    total_messages: int
    messages_today: int
    messages_by_type: Dict[str, int]


async def get_stats() -> Stats:
    """Получает общую статистику."""
    async with get_cursor() as cur:
        # Общие счётчики
        await cur.execute("SELECT COUNT(*) FROM chats")
        total_chats = (await cur.fetchone())[0]
        
        await cur.execute("SELECT COUNT(*) FROM users")
        total_users = (await cur.fetchone())[0]
        
        await cur.execute("SELECT COUNT(*) FROM messages")
        total_messages = (await cur.fetchone())[0]
        
        await cur.execute("""
            SELECT COUNT(*) FROM messages 
            WHERE sent_at >= CURRENT_DATE
        """)
        messages_today = (await cur.fetchone())[0]
        
        # Сообщения по типам
        await cur.execute("""
            SELECT message_type, COUNT(*) as cnt 
            FROM messages 
            GROUP BY message_type 
            ORDER BY cnt DESC
        """)
        messages_by_type = {row[0]: row[1] for row in await cur.fetchall()}
        
        return Stats(
            total_chats=total_chats,
            total_users=total_users,
            total_messages=total_messages,
            messages_today=messages_today,
            messages_by_type=messages_by_type,
        )


async def get_chats_with_stats() -> List[ChatStats]:
    """Получает список чатов со статистикой."""
    async with get_cursor() as cur:
        await cur.execute("""
            SELECT 
                c.id,
                c.type,
                c.title,
                c.username,
                COUNT(DISTINCT m.message_id) as message_count,
                COUNT(DISTINCT m.user_id) as user_count,
                MAX(m.sent_at) as last_message_at,
                c.first_seen_at
            FROM chats c
            LEFT JOIN messages m ON c.id = m.chat_id
            GROUP BY c.id, c.type, c.title, c.username, c.first_seen_at
            ORDER BY message_count DESC
        """)
        
        rows = await cur.fetchall()
        return [
            ChatStats(
                id=row[0],
                type=row[1],
                title=row[2],
                username=row[3],
                message_count=row[4],
                user_count=row[5],
                last_message_at=row[6],
                first_seen_at=row[7],
            )
            for row in rows
        ]


async def get_chat_messages(
    chat_id: int, 
    limit: int = 100, 
    offset: int = 0,
    message_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Получает сообщения чата."""
    async with get_cursor() as cur:
        query = """
            SELECT 
                m.message_id,
                m.message_type,
                m.text,
                m.caption,
                m.sent_at,
                m.edited_at,
                m.reply_to_message_id,
                u.id as user_id,
                u.first_name,
                u.last_name,
                u.username
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.chat_id = %s
        """
        params = [chat_id]
        
        if message_type:
            query += " AND m.message_type = %s"
            params.append(message_type)
        
        query += " ORDER BY m.sent_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        await cur.execute(query, params)
        rows = await cur.fetchall()
        
        return [
            {
                "message_id": row[0],
                "message_type": row[1],
                "text": row[2],
                "caption": row[3],
                "sent_at": row[4],
                "edited_at": row[5],
                "reply_to_message_id": row[6],
                "user": {
                    "id": row[7],
                    "first_name": row[8],
                    "last_name": row[9],
                    "username": row[10],
                } if row[7] else None
            }
            for row in rows
        ]


async def get_chat_by_id(chat_id: int) -> Optional[Dict[str, Any]]:
    """Получает информацию о чате по ID."""
    async with get_cursor() as cur:
        await cur.execute("""
            SELECT id, type, title, username, first_seen_at, last_updated_at
            FROM chats WHERE id = %s
        """, (chat_id,))
        row = await cur.fetchone()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "type": row[1],
            "title": row[2],
            "username": row[3],
            "first_seen_at": row[4],
            "last_updated_at": row[5],
        }


async def get_chat_messages_by_date(
    chat_id: int,
    date_str: str,  # format: YYYY-MM-DD
) -> List[Dict[str, Any]]:
    """Получает все сообщения чата за конкретный календарный день (UTC+3)."""
    async with get_cursor() as cur:
        # UTC+3: день начинается в 00:00 UTC+3 = 21:00 UTC предыдущего дня
        await cur.execute("""
            SELECT 
                m.message_id,
                m.message_type,
                m.text,
                m.caption,
                m.sent_at,
                m.edited_at,
                m.reply_to_message_id,
                u.id as user_id,
                u.first_name,
                u.last_name,
                u.username
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.chat_id = %s
              AND (m.sent_at AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Moscow')::date = %s::date
            ORDER BY m.sent_at ASC
        """, (chat_id, date_str))
        
        rows = await cur.fetchall()
        return [
            {
                "message_id": row[0],
                "message_type": row[1],
                "text": row[2],
                "caption": row[3],
                "sent_at": row[4],
                "edited_at": row[5],
                "reply_to_message_id": row[6],
                "user": {
                    "id": row[7],
                    "first_name": row[8],
                    "last_name": row[9],
                    "username": row[10],
                } if row[7] else None
            }
            for row in rows
        ]


async def get_chat_messages_by_date_range(
    chat_id: int,
    date_from: str,  # format: YYYY-MM-DD
    date_to: str,    # format: YYYY-MM-DD
) -> List[Dict[str, Any]]:
    """Получает все сообщения чата за диапазон дат (включительно, UTC+3)."""
    async with get_cursor() as cur:
        await cur.execute("""
            SELECT
                m.message_id,
                m.message_type,
                m.text,
                m.caption,
                m.sent_at,
                m.edited_at,
                m.reply_to_message_id,
                u.id as user_id,
                u.first_name,
                u.last_name,
                u.username
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.chat_id = %s
              AND (m.sent_at AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Moscow')::date >= %s::date
              AND (m.sent_at AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Moscow')::date <= %s::date
            ORDER BY m.sent_at ASC
        """, (chat_id, date_from, date_to))

        rows = await cur.fetchall()
        return [
            {
                "message_id": row[0],
                "message_type": row[1],
                "text": row[2],
                "caption": row[3],
                "sent_at": row[4],
                "edited_at": row[5],
                "reply_to_message_id": row[6],
                "user": {
                    "id": row[7],
                    "first_name": row[8],
                    "last_name": row[9],
                    "username": row[10],
                } if row[7] else None
            }
            for row in rows
        ]


async def get_users(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """Получает список пользователей."""
    async with get_cursor() as cur:
        await cur.execute("""
            SELECT 
                u.id,
                u.first_name,
                u.last_name,
                u.username,
                u.is_bot,
                u.is_premium,
                u.language_code,
                u.first_seen_at,
                COUNT(m.message_id) as message_count
            FROM users u
            LEFT JOIN messages m ON u.id = m.user_id
            GROUP BY u.id, u.first_name, u.last_name, u.username, 
                     u.is_bot, u.is_premium, u.language_code, u.first_seen_at
            ORDER BY message_count DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        
        rows = await cur.fetchall()
        return [
            {
                "id": row[0],
                "first_name": row[1],
                "last_name": row[2],
                "username": row[3],
                "is_bot": row[4],
                "is_premium": row[5],
                "language_code": row[6],
                "first_seen_at": row[7],
                "message_count": row[8],
            }
            for row in rows
        ]


@dataclass
class DashboardChat:
    """Данные чата для дашборда."""
    id: int
    title: Optional[str]
    total_messages: int
    today_messages: int
    last_message_text: Optional[str]
    last_message_author: Optional[str]
    last_message_at: Optional[datetime]
    top_users: List[Dict[str, Any]]


async def get_dashboard_data() -> List[DashboardChat]:
    """Получает данные для дашборда: чаты с полной статистикой."""
    async with get_cursor() as cur:
        # Получаем все данные одним запросом через CTE и LATERAL
        await cur.execute("""
            WITH stats AS (
                SELECT
                    c.id,
                    c.title,
                    COUNT(m.message_id) as total_messages,
                    COUNT(m.message_id) FILTER (WHERE m.sent_at >= CURRENT_DATE) as today_messages
                FROM chats c
                LEFT JOIN messages m ON c.id = m.chat_id
                GROUP BY c.id, c.title
            )
            SELECT
                s.id,
                s.title,
                s.total_messages,
                s.today_messages,
                lm.text,
                lm.author,
                lm.sent_at,
                COALESCE(tu.data, '[]'::json) as top_users
            FROM stats s
            LEFT JOIN LATERAL (
                SELECT
                    m.text,
                    COALESCE(u.username, u.first_name, 'Unknown') as author,
                    m.sent_at
                FROM messages m
                LEFT JOIN users u ON m.user_id = u.id
                WHERE m.chat_id = s.id AND m.text IS NOT NULL
                ORDER BY m.sent_at DESC
                LIMIT 1
            ) lm ON TRUE
            LEFT JOIN LATERAL (
                SELECT
                    json_agg(json_build_object('name', t.name, 'count', t.count)) as data
                FROM (
                    SELECT
                        COALESCE(u.username, u.first_name, 'Unknown') as name,
                        COUNT(*) as count
                    FROM messages m
                    JOIN users u ON m.user_id = u.id
                    WHERE m.chat_id = s.id
                      AND m.sent_at >= NOW() - INTERVAL '7 days'
                    GROUP BY u.id, u.username, u.first_name
                    ORDER BY count DESC
                    LIMIT 3
                ) t
            ) tu ON TRUE
            ORDER BY s.total_messages DESC
        """)
        rows = await cur.fetchall()

        result = []
        for row in rows:
            # Обработка top_users: psycopg 3 может вернуть список или json строку
            top_users_raw = row[7]
            if isinstance(top_users_raw, str):
                try:
                    top_users = json.loads(top_users_raw)
                except json.JSONDecodeError:
                    top_users = []
            else:
                top_users = top_users_raw or []

            result.append(DashboardChat(
                id=row[0],
                title=row[1],
                total_messages=row[2],
                today_messages=row[3],
                last_message_text=row[4],
                last_message_author=row[5],
                last_message_at=row[6],
                top_users=top_users,
            ))

        return result


async def get_messages_for_summary(chat_id: int, limit: int = 500) -> List[Dict[str, Any]]:
    """Получает сообщения за последние 24 часа для генерации саммари."""
    async with get_cursor() as cur:
        await cur.execute("""
            SELECT
                m.text,
                COALESCE(u.username, u.first_name, 'Unknown') as author,
                m.sent_at
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.chat_id = %s
              AND m.sent_at >= NOW() - INTERVAL '24 hours'
              AND m.text IS NOT NULL
            ORDER BY m.sent_at ASC
            LIMIT %s
        """, (chat_id, limit))

        rows = await cur.fetchall()
        return [
            {"text": row[0], "author": row[1], "sent_at": row[2]}
            for row in rows
        ]


async def get_daily_message_counts(chat_id: int, days: int = 7) -> List[Dict[str, Any]]:
    """Получает количество сообщений по дням за последние N дней."""
    async with get_cursor() as cur:
        await cur.execute(f"""
            SELECT
                (m.sent_at AT TIME ZONE 'UTC' AT TIME ZONE 'Europe/Moscow')::date as day,
                COUNT(*) as count
            FROM messages m
            WHERE m.chat_id = %s
              AND m.sent_at >= NOW() - INTERVAL '{days} days'
            GROUP BY day
            ORDER BY day ASC
        """, (chat_id,))

        rows = await cur.fetchall()
        return [
            {"date": row[0].isoformat(), "count": row[1]}
            for row in rows
        ]


async def get_messages_for_period(
    chat_id: int,
    days: int,
    limit: int = 500
) -> List[Dict[str, Any]]:
    """Получает сообщения за указанный период для анализа."""
    async with get_cursor() as cur:
        await cur.execute(f"""
            SELECT
                m.text,
                m.caption,
                COALESCE(u.username, u.first_name, 'Unknown') as author,
                m.sent_at,
                m.message_type
            FROM messages m
            LEFT JOIN users u ON m.user_id = u.id
            WHERE m.chat_id = %s
              AND m.sent_at >= NOW() - INTERVAL '{days} days'
              AND (m.text IS NOT NULL OR m.caption IS NOT NULL)
            ORDER BY m.sent_at DESC
            LIMIT %s
        """, (chat_id, limit))

        rows = await cur.fetchall()
        return [
            {
                "text": row[0] or row[1],
                "author": row[2],
                "sent_at": row[3],
                "type": row[4],
            }
            for row in rows
        ]
