from __future__ import annotations

import os
import asyncio
from pathlib import Path

import asyncpg
from asyncpg import Connection
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# ENV
# ---------------------------------------------------------------------

load_dotenv()

DB_USER: str = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "adminpass")
DB_NAME: str = os.getenv("POSTGRES_DB", "ai_scan_db")
DB_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT: str = os.getenv("POSTGRES_PORT", "5432")

# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
TABLES_SQL_PATH: Path = BASE_DIR / "tables.sql"
VIEWS_SQL_PATH: Path = BASE_DIR / "views.sql"

# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------


async def load_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


async def connect_db() -> Connection:
    return await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT,
    )

# ---------------------------------------------------------------------
# MAIN LOGIC
# ---------------------------------------------------------------------


async def create_tables() -> None:
    print(f"[INFO] Connecting to PostgreSQL {DB_HOST}:{DB_PORT} db={DB_NAME}")

    conn: Connection = await connect_db()

    try:
        # ---------------- TABLES ----------------
        if not TABLES_SQL_PATH.exists():
            raise RuntimeError("tables.sql not found")

        tables_sql = await load_sql(TABLES_SQL_PATH)
        print(f"[INFO] Executing {TABLES_SQL_PATH}")
        await conn.execute(tables_sql)
        print("[INFO] Tables created (or already exist)")

        # ---------------- VIEWS ----------------
        if VIEWS_SQL_PATH.exists():
            views_sql = await load_sql(VIEWS_SQL_PATH)
            print(f"[INFO] Executing {VIEWS_SQL_PATH}")
            await conn.execute(views_sql)
            print("[INFO] Views created / replaced")
        else:
            print("[INFO] views.sql not found — skipped")

    finally:
        await conn.close()
        print("[INFO] DB connection closed")

# ---------------------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------------------


async def main() -> None:
    await create_tables()


if __name__ == "__main__":
    asyncio.run(main())
