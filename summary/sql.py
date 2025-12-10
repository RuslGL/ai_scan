"""
SQL-утилиты для summary-сервиса.

Содержит:
- создание таблицы session_summary,
- вставку новой summary-записи,
- получение последнего end_time для raw_session_id,
- получение последнего end_time + final_scroll_depth для raw_session_id,
- проверку: покрыт ли данный last_real_activity предыдущими summary,
- удаление событий (можно отключить для тестов).

Логика:
-------
1. Один raw_session_id может иметь много визитов.
2. Каждый визит → отдельная summary-запись.
3. summary считается новым, если:
   last_real_activity > max(end_time) в session_summary для этого raw_session_id.
"""

from typing import Optional, List, Dict, Any
from .db import get_connection


# ----------------------------------------------------------------------
#  CREATE TABLE
# ----------------------------------------------------------------------


async def create_session_summary_table():
    """
    Создаёт таблицу session_summary, если она отсутствует.
    """
    conn = await get_connection()
    try:
        query = """
        CREATE TABLE IF NOT EXISTS session_summary (
            id SERIAL PRIMARY KEY,
            raw_session_id TEXT NOT NULL,
            uid TEXT,
            site_url TEXT,
            start_time TIMESTAMPTZ NOT NULL,
            end_time TIMESTAMPTZ NOT NULL,
            duration_seconds DOUBLE PRECISION,
            country TEXT,
            city TEXT,
            device_type TEXT,
            os TEXT,
            browser TEXT,
            max_scroll_depth DOUBLE PRECISION,
            final_scroll_depth DOUBLE PRECISION,
            scroll_stops JSONB,
            click_buttons JSONB,
            total_actions INT,
            is_closed BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """
        await conn.execute(query)
    finally:
        await conn.close()


# ----------------------------------------------------------------------
#  INSERT SUMMARY
# ----------------------------------------------------------------------


async def insert_summary(summary: dict):
    """
    Вставляет одну запись summary в таблицу session_summary.

    Параметры:
    ----------
    summary : dict
        Данные, сформированные aggregator.build_session_summary().
    """
    conn = await get_connection()
    try:
        query = """
        INSERT INTO session_summary (
            raw_session_id,
            uid,
            site_url,
            start_time,
            end_time,
            duration_seconds,
            country,
            city,
            device_type,
            os,
            browser,
            max_scroll_depth,
            final_scroll_depth,
            scroll_stops,
            click_buttons,
            total_actions,
            is_closed
        )
        VALUES (
            $1, $2, $3, $4, $5, $6,
            $7, $8, $9, $10, $11,
            $12, $13, $14::jsonb, $15::jsonb,
            $16, $17
        );
        """

        await conn.execute(
            query,
            summary["raw_session_id"],
            summary.get("uid"),
            summary.get("site_url"),
            summary["start_time"],
            summary["end_time"],
            summary.get("duration_seconds"),
            summary.get("country"),
            summary.get("city"),
            summary.get("device_type"),
            summary.get("os"),
            summary.get("browser"),
            summary.get("max_scroll_depth"),
            summary.get("final_scroll_depth"),
            summary["scroll_stops"],
            summary["click_buttons"],
            summary.get("total_actions"),
            summary.get("is_closed", True),
        )

    finally:
        await conn.close()


# ----------------------------------------------------------------------
#  GET LAST SUMMARY END TIME
# ----------------------------------------------------------------------


async def get_last_summary_end_time(raw_session_id: str) -> Optional[str]:
    """
    Возвращает максимальный end_time для указанного raw_session_id.

    Используется для того, чтобы определить:
    - был ли уже создан summary для данного участка активности,
    - и нужно ли создавать новый.

    Возвращает:
    -----------
    TIMESTAMPTZ или None.
    """
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            """
            SELECT MAX(end_time) AS last_end
            FROM session_summary
            WHERE raw_session_id = $1;
            """,
            raw_session_id,
        )
        if row and row["last_end"]:
            return row["last_end"]
        return None
    finally:
        await conn.close()


# ----------------------------------------------------------------------
#  GET LAST SUMMARY INFO (end_time + final_scroll_depth)
# ----------------------------------------------------------------------


async def get_last_summary_info(raw_session_id: str) -> Optional[Dict[str, Any]]:
    """
    Возвращает информацию о последней summary-записи для raw_session_id:

    - last_end: TIMESTAMPTZ end_time последнего визита;
    - last_final_scroll: DOUBLE PRECISION final_scroll_depth последнего визита.

    Используется для логики:
    - определения последней зафиксированной позиции скролла по сессии;
    - понимания, является ли новый heartbeat со скроллом продолжением
      старого визита или началом нового.
    """
    conn = await get_connection()
    try:
        row = await conn.fetchrow(
            """
            SELECT
                end_time AS last_end,
                final_scroll_depth AS last_final_scroll
            FROM session_summary
            WHERE raw_session_id = $1
            ORDER BY end_time DESC
            LIMIT 1;
            """,
            raw_session_id,
        )
        if not row:
            return None

        return {
            "last_end": row["last_end"],
            "last_final_scroll": row["last_final_scroll"],
        }
    finally:
        await conn.close()


# ----------------------------------------------------------------------
#  CHECK IF SUMMARY FOR THIS VISIT ALREADY EXISTS
# ----------------------------------------------------------------------


async def is_visit_already_summarized(raw_session_id: str, last_real_activity) -> bool:
    """
    Проверяет, не перекрывает ли существующий summary
    текущий last_real_activity.

    Если last_summary_end >= last_real_activity → визит уже обработан.

    Возвращает:
    -----------
    True / False
    """
    last_end = await get_last_summary_end_time(raw_session_id)

    if last_end is None:
        return False

    # Если последний summary покрывает этот визит
    return last_end >= last_real_activity


# ----------------------------------------------------------------------
#  DELETE EVENTS AFTER SUMMARY (можно отключить)
# ----------------------------------------------------------------------


async def delete_events_for_session(session_id: str):
    """
    Удаляет события конкретной raw-сессии из таблицы events.

    Для безопасного тестирования можно временно закомментировать вызов
    этой функции в worker-е.
    """
    conn = await get_connection()
    try:
        await conn.execute(
            "DELETE FROM events WHERE session_id = $1;",
            session_id
        )
    finally:
        await conn.close()


# ----------------------------------------------------------------------
#  DEBUG RUNNER
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio
    asyncio.run(create_session_summary_table())
