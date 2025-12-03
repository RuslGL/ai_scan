"""
Модуль для работы с подключением к PostgreSQL (asyncpg + пул подключений).
"""

from __future__ import annotations

import os
from typing import AsyncGenerator, Optional, Set

import asyncpg
from asyncpg import Connection, Pool
from dotenv import load_dotenv

load_dotenv()

DB_USER: str = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "adminpass")
DB_NAME: str = os.getenv("POSTGRES_DB", "ai_scan_db")
DB_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT: str = os.getenv("POSTGRES_PORT", "5432")

# глобальный пул подключений
_pool: Optional[Pool] = None

# кэш активных сайтов: сюда будем грузить id, у которых is_active = TRUE
active_sites_cache: Set[str] = set()


async def get_pool() -> Pool:
    """
    Возвращает (или создаёт) пул подключений asyncpg.

    Returns:
        Pool: пул соединений asyncpg.
    """
    global _pool

    if _pool is None:
        _pool = await asyncpg.create_pool(
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            host=DB_HOST,
            port=DB_PORT,
            min_size=1,
            max_size=10,
        )

    return _pool


async def get_connection() -> AsyncGenerator[Connection, None]:
    """
    FastAPI dependency:
    выдаёт соединение из пула и возвращает его обратно.

    Yields:
        Connection: активное соединение c PostgreSQL.
    """
    pool: Pool = await get_pool()
    conn: Connection = await pool.acquire()

    try:
        yield conn
    finally:
        await pool.release(conn)


async def refresh_active_sites() -> None:
    """
    Обновляет кэш active_sites_cache:
    загружает id всех сайтов, у которых is_active = TRUE.
    """
    global active_sites_cache
    pool: Pool = await get_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id FROM sites WHERE is_active = TRUE"
        )

    active_sites_cache = {row["id"] for row in rows}
