"""
Простое подключение к PostgreSQL для summary-сервиса.

Логика:
- При каждом вызове создаётся новое соединение asyncpg.connect().
- После использования соединение нужно закрыть через conn.close().
- Пул соединений НЕ используется, потому что воркер работает раз в N минут
  и не создаёт высокую нагрузку.
"""

import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_USER: str = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "adminpass")
DB_NAME: str = os.getenv("POSTGRES_DB", "ai_scan_db")
DB_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT: str = os.getenv("POSTGRES_PORT", "5432")


async def get_connection() -> asyncpg.Connection:
    """
    Создаёт новое соединение с PostgreSQL.

    Использование:
    --------------
    conn = await get_connection()
    rows = await conn.fetch(...)
    await conn.close()

    Возвращает:
    -----------
    asyncpg.Connection — активное соединение с базой данных.
    """
    conn = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT,
    )
    return conn
