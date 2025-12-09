"""
Определение raw-сессий, у которых завершился очередной "визит".

Логика:
-------
1) last_real_activity = последний момент, когда была активность:
   - click (event_type != 'heartbeat')
   - heartbeat с изменением прокрутки

2) Сессия-кандидат:
   now() - last_real_activity >= INACTIVITY_MINUTES

3) НО summary может уже быть создано ранее.
   Значит нужно взять максимум end_time в session_summary для этой raw_session_id.

4) Новый визит:
   last_real_activity > max_summary_end_time(raw_session_id)
"""

import os
from typing import List
from asyncpg import Record
from .db import get_connection

INACTIVITY_MINUTES = int(os.getenv("SUMMARY_INACTIVITY_MINUTES", "15"))


async def find_closed_sessions() -> List[str]:
    """
    Возвращает список raw_session_id, для которых:
    - активность закончилась (timeout),
    - и эта активность ещё НЕ покрыта предыдущим summary.

    Таким образом один raw_session_id может дать
    несколько summary (отдельные визиты).
    """
    conn = await get_connection()
    try:
        query = f"""
        WITH activity AS (
            SELECT
                session_id,
                MAX(event_time) AS last_real_activity
            FROM events
            WHERE (
                event_type != 'heartbeat'
                OR hb_scroll_percent IS NOT NULL
            )
            GROUP BY session_id
        ),

        summary_bounds AS (
            SELECT
                raw_session_id,
                MAX(end_time) AS last_summary_end
            FROM session_summary
            GROUP BY raw_session_id
        )

        SELECT a.session_id
        FROM activity a
        LEFT JOIN summary_bounds sb
            ON sb.raw_session_id = a.session_id
        WHERE
            a.last_real_activity < (NOW() - INTERVAL '{INACTIVITY_MINUTES} minutes')
            AND (
                sb.last_summary_end IS NULL
                OR a.last_real_activity > sb.last_summary_end
            );
        """

        rows: List[Record] = await conn.fetch(query)
        return [r["session_id"] for r in rows]

    finally:
        await conn.close()
