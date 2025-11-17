"""
Скрипт для создания всех необходимых таблиц в PostgreSQL.

Особенности:
- читает SQL из db/tables.sql,
- выполняет CREATE TABLE IF NOT EXISTS,
- существующие таблицы НЕ изменяются и НЕ удаляются.

Запуск:
    uv run python db/create_tables.py
"""

from __future__ import annotations

import os
import asyncio
from typing import Optional

import asyncpg
from asyncpg import Connection
from dotenv import load_dotenv
from pathlib import Path

# Загружаем .env
load_dotenv()

# Аннотированные переменные окружения
DB_USER: str = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "adminpass")
DB_NAME: str = os.getenv("POSTGRES_DB", "ai_scan_db")
DB_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT: str = os.getenv("POSTGRES_PORT", "5432")

# Путь к SQL-файлу
TABLES_SQL_PATH: Path = Path(__file__).parent / "tables.sql"


async def load_sql() -> str:
    """
    Загружает SQL-скрипт из файла tables.sql.

    Returns:
        str: содержимое SQL-файла.
    """
    return TABLES_SQL_PATH.read_text(encoding="utf-8")


async def connect_db() -> Connection:
    """
    Устанавливает соединение с PostgreSQL.

    Returns:
        Connection: объект asyncpg.Connection.
    """
    conn: Connection = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT,
    )
    return conn


async def create_tables() -> None:
    """
    Выполняет SQL-скрипт создания таблиц.
    CREATE TABLE IF NOT EXISTS предотвращает дублирование.
    """
    print(f"[INFO] Подключение к PostgreSQL: {DB_HOST}:{DB_PORT}, DB={DB_NAME}")

    conn: Connection = await connect_db()

    try:
        sql: str = await load_sql()
        print(f"[INFO] Загружен SQL-файл: {TABLES_SQL_PATH}")

        await conn.execute(sql)
        print("[INFO] Таблицы созданы (или уже существовали).")

    finally:
        await conn.close()
        print("[INFO] Соединение закрыто.")


async def main() -> None:
    """
    Точка входа для асинхронного скрипта.
    """
    await create_tables()


if __name__ == "__main__":
    asyncio.run(main())
