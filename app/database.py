"""Модуль для работы с базой данных PostgreSQL."""

import logging
from typing import Optional
from contextlib import asynccontextmanager

from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

# Глобальный пул соединений
_pool: Optional[AsyncConnectionPool] = None


async def init_pool(database_url: str, min_size: int = 1, max_size: int = 10) -> AsyncConnectionPool:
    """Инициализирует пул соединений к базе данных."""
    global _pool
    
    logger.info("Initializing database connection pool...")
    _pool = AsyncConnectionPool(
        database_url,
        min_size=min_size,
        max_size=max_size,
        open=False
    )
    await _pool.open()
    logger.info("Database connection pool initialized successfully")
    return _pool


async def close_pool():
    """Закрывает пул соединений."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


def get_pool() -> AsyncConnectionPool:
    """Возвращает текущий пул соединений."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialized. Call init_pool() first.")
    return _pool


@asynccontextmanager
async def get_connection():
    """Контекстный менеджер для получения соединения из пула."""
    pool = get_pool()
    async with pool.connection() as conn:
        yield conn


@asynccontextmanager
async def get_cursor():
    """Контекстный менеджер для получения курсора."""
    async with get_connection() as conn:
        async with conn.cursor() as cur:
            yield cur
