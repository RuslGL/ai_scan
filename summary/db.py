"""
Простое подключение к PostgreSQL для summary-сервиса.

Логика:
- При каждом вызове создаётся новое соединение asyncpg.connect().
- После использования соединение нужно закрыть через conn.close().
- Пул соединений НЕ используется.
"""

import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "adminpass")
DB_NAME = os.getenv("POSTGRES_DB", "ai_scan_db")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))


async def get_connection() -> asyncpg.Connection:
    return await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT,
    )
