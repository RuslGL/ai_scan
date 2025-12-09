"""
Загрузка событий по одному raw_session_id.

Функция:
- подключается к базе через asyncpg,
- выбирает все события данной raw-сессии,
- сортирует по времени,
- приводит строки к list[dict].

Loader НЕ решает, закрыта сессия или нет.
Этим занимается Selector.
"""

from typing import List, Dict, Any
from asyncpg import Record
from .db import get_connection


async def load_events_for_session(session_id: str) -> List[Dict[str, Any]]:
    """
    Загружает все события для указанного raw_session_id.

    Параметры:
    ----------
    session_id : str
        Технический идентификатор сессии браузера.

    Возвращает:
    -----------
    List[Dict[str, Any]]
        Упорядоченные по времени события.
    """
    conn = await get_connection()
    try:
        query = """
        SELECT
            id,
            session_id,
            uid,
            site_url,
            event_type,
            event_time,
            button_text,
            button_id,
            country,
            city,
            device_type,
            os,
            browser,
            hb_scroll_percent,
            hb_since_last_activity_ms
        FROM events
        WHERE session_id = $1
        ORDER BY event_time ASC;
        """

        rows: List[Record] = await conn.fetch(query, session_id)
        return [dict(r) for r in rows]

    finally:
        await conn.close()
