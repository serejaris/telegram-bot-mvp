"""
HTTP API модуль для healthcheck и публичного API.
"""

import json
import logging
from datetime import datetime
from typing import Callable

from aiohttp import web
from psycopg_pool import AsyncConnectionPool

from .config import Config
from .database import check_connection, get_chat_messages

logger = logging.getLogger(__name__)


def create_health_handler(pool: AsyncConnectionPool) -> Callable:
    """
    Создаёт обработчик healthcheck endpoint.

    Args:
        pool: Пул соединений к базе данных.

    Returns:
        Асинхронный обработчик запроса.
    """
    async def health_check(request: web.Request) -> web.Response:
        try:
            is_connected = await check_connection(pool)

            if is_connected:
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

    return health_check


def create_chat_history_handler(pool: AsyncConnectionPool, chat_id: int) -> Callable:
    """
    Создаёт обработчик для получения истории чата.

    Args:
        pool: Пул соединений к базе данных.
        chat_id: ID чата для получения истории.

    Returns:
        Асинхронный обработчик запроса.
    """
    async def get_chat_history(request: web.Request) -> web.Response:
        try:
            messages = await get_chat_messages(pool, chat_id)

            return web.json_response(
                {
                    "chat_id": chat_id,
                    "total_messages": len(messages),
                    "messages": messages
                },
                dumps=lambda x: json.dumps(x, ensure_ascii=False)
            )
        except Exception as e:
            logger.error(f"Failed to get chat history: {e}")
            return web.json_response(
                {
                    "error": "Failed to retrieve chat history",
                    "details": str(e)
                },
                status=500,
                dumps=lambda x: json.dumps(x, ensure_ascii=False)
            )

    return get_chat_history


def create_app(pool: AsyncConnectionPool, config: Config) -> web.Application:
    """
    Создаёт aiohttp приложение с роутами.

    Args:
        pool: Пул соединений к базе данных.
        config: Конфигурация приложения.

    Returns:
        Настроенное aiohttp приложение.
    """
    app = web.Application()

    health_handler = create_health_handler(pool)
    chat_history_handler = create_chat_history_handler(pool, config.public_chat_id)

    app.router.add_get('/health', health_handler)
    app.router.add_get('/', health_handler)
    app.router.add_get('/api/messages', chat_history_handler)

    return app


async def start_server(app: web.Application, port: int) -> web.AppRunner:
    """
    Запускает HTTP сервер.

    Args:
        app: aiohttp приложение.
        port: Порт для прослушивания.

    Returns:
        Runner для управления сервером.
    """
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"HTTP server started on port {port}")
    return runner
