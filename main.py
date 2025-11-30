"""
Telegram Bot MVP для сбора сообщений из групповых чатов.

Этот бот слушает все текстовые сообщения в групповых чатах и сохраняет
информацию о сообщениях, пользователях и чатах в базу данных PostgreSQL.
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from typing import Optional
from aiohttp import web, ClientSession

import psycopg
from psycopg_pool import AsyncConnectionPool
from telegram import Update, User, Chat
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальный пул соединений к базе данных
DB_POOL: Optional[AsyncConnectionPool] = None

# Target chat ID for public API
PUBLIC_CHAT_ID = -1003339826329


async def create_tables():
    """Создает необходимые таблицы в базе данных, если они не существуют."""
    create_tables_sql = """
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

    try:
        async with DB_POOL.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(create_tables_sql)
                logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


async def save_user_and_chat(cursor, user: User, chat: Chat):
    """
    Сохраняет или обновляет информацию о пользователе и чате в базе данных.
    
    Args:
        cursor: Курсор базы данных
        user: Объект пользователя Telegram
        chat: Объект чата Telegram
    """
    # Сохранение/обновление пользователя с использованием UPSERT
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

    # Сохранение/обновление чата
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


async def store_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик для сохранения текстовых сообщений в базу данных.
    
    Args:
        update: Объект обновления от Telegram
        context: Контекст бота
    """
    msg = update.effective_message
    
    # Проверяем, что сообщение существует и содержит текст
    if not msg or not msg.text:
        return
    
    # Проверяем, что сообщение из группового чата
    if msg.chat.type not in ['group', 'supergroup']:
        logger.debug(f"Ignoring message from non-group chat: {msg.chat.type}")
        return

    # Проверяем, что у сообщения есть автор
    if not msg.from_user:
        logger.debug("Ignoring message without from_user")
        return

    try:
        async with DB_POOL.connection() as conn:
            async with conn.cursor() as cur:
                # В одной транзакции сохраняем пользователя, чат и сообщение
                await save_user_and_chat(cur, msg.from_user, msg.chat)
                
                # Сохраняем сообщение
                await cur.execute("""
                    INSERT INTO messages (message_id, chat_id, user_id, text, sent_at, raw_message)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chat_id, message_id) DO NOTHING;
                """, (
                    msg.message_id,
                    msg.chat_id,
                    msg.from_user.id,
                    msg.text,
                    msg.date,
                    json.dumps(msg.to_dict())
                ))
                
                logger.info(
                    f"Stored message {msg.message_id} from user {msg.from_user.id} "
                    f"in chat {msg.chat_id} ({msg.chat.title or 'No title'})"
                )
                
    except Exception as e:
        logger.error(f"Failed to store message {msg.message_id}: {e}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок бота."""
    logger.error(f"Update {update} caused error {context.error}")


async def health_check(request):
    """Healthcheck endpoint для Railway."""
    try:
        # Проверяем подключение к базе данных
        async with DB_POOL.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                result = await cur.fetchone()
        
        if result and result[0] == 1:
            return web.json_response({
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            return web.json_response({
                "status": "unhealthy",
                "database": "error",
                "timestamp": datetime.utcnow().isoformat()
            }, status=500)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return web.json_response({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, status=500)


async def get_chat_history(request):
    """Public API endpoint to get chat history for the configured chat."""
    try:
        async with DB_POOL.connection() as conn:
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
                """, (PUBLIC_CHAT_ID,))

                rows = await cur.fetchall()

                messages = []
                for row in rows:
                    messages.append({
                        "message_id": row[0],
                        "text": row[1],
                        "sent_at": row[2].isoformat() if row[2] else None,
                        "user": {
                            "first_name": row[3],
                            "last_name": row[4],
                            "username": row[5]
                        }
                    })

                return web.json_response({
                    "chat_id": PUBLIC_CHAT_ID,
                    "total_messages": len(messages),
                    "messages": messages
                })

    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        return web.json_response({
            "error": "Failed to retrieve chat history",
            "details": str(e)
        }, status=500)


async def start_health_server(port: int):
    """Запускает HTTP сервер для healthcheck."""
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)  # Railway может проверять корневой путь
    app.router.add_get('/api/messages', get_chat_history)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"Health check server started on port {port}")
    return runner


async def main():
    """Основная функция для запуска бота."""
    global DB_POOL
    
    # Получаем переменные окружения
    token = os.getenv("TELEGRAM_TOKEN")
    db_url = os.getenv("DATABASE_URL")
    port = int(os.getenv("PORT", 8000))  # Railway автоматически устанавливает PORT

    if not token:
        logger.critical("TELEGRAM_TOKEN environment variable must be set")
        return
    
    if not db_url:
        logger.critical("DATABASE_URL environment variable must be set")
        return

    try:
        # Инициализация пула соединений к базе данных
        logger.info("Connecting to database...")
        DB_POOL = AsyncConnectionPool(
            db_url,
            min_size=1,
            max_size=10,
            open=False
        )
        await DB_POOL.open()
        logger.info("Database connection pool created successfully")

        # Создаем таблицы, если они не существуют
        await create_tables()

        # Запускаем healthcheck сервер для Railway
        health_runner = await start_health_server(port)

        # Создаем приложение бота
        application = Application.builder().token(token).build()

        # Добавляем обработчик для всех текстовых сообщений, которые не являются командами
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                store_message_handler
            )
        )

        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)

        logger.info("Bot is starting with polling...")
        logger.info("Make sure Privacy Mode is disabled in @BotFather for this bot")
        
        # Инициализируем приложение
        await application.initialize()
        await application.start()
        
        # Запускаем polling
        await application.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message"]
        )
        
        # Ждем бесконечно (пока не будет прервано)
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Received shutdown signal")
        finally:
            # Корректно останавливаем бота
            await application.updater.stop()
            await application.stop()
            await application.shutdown()

    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")
        raise
    finally:
        # Закрываем пул соединений при остановке
        if DB_POOL:
            await DB_POOL.close()
            logger.info("Database connection pool closed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")