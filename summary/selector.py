"""
Определение raw-сессий, у которых завершился очередной "визит".

Логика:
-------
1) last_real_activity = последний момент, когда была реальная активность:
   - любой event_type != 'heartbeat' (клики, сабмиты и т.п.);
   - ИЛИ heartbeat, в котором ИЗМЕНИЛСЯ hb_scroll_percent
     относительно предыдущего НЕ-NULL значения для этой session_id.

   Важно:
   - heartbeat с hb_scroll_percent IS NULL полностью игнорируются
     (они не участвуют ни в лаге, ни в определении активности);
   - если скролл не меняется и кликов нет — пользователь считается неактивным,
     даже если heartbeat продолжает приходить раз в N секунд.

2) Сессия-кандидат на закрытие:
   now() - last_real_activity >= INACTIVITY_MINUTES.

3) Один raw_session_id может иметь несколько "визитов".
   Поэтому смотрим, не перекрыт ли last_real_activity уже существующим summary:
   - берём MAX(end_time) для raw_session_id в session_summary;
   - новый визит, если last_real_activity > last_summary_end.
"""

import os
from typing import List

from asyncpg import Record

from .db import get_connection

INACTIVITY_MINUTES = int(os.getenv("SUMMARY_INACTIVITY_MINUTES", "15"))


async def find_closed_sessions() -> List[str]:
    """
    Возвращает список raw_session_id, для которых:
    - последняя реальная активность была старше INACTIVITY_MINUTES,
    - и эта активность ещё НЕ покрыта предыдущим summary.

    Реальная активность:
    --------------------
    - любые события с event_type != 'heartbeat' (клики, сабмиты и т.п.);
    - heartbeat, у которых hb_scroll_percent ИЗМЕНИЛСЯ
      относительно предыдущего НЕ-NULL значения (lag по session_id).

    Подробности:
    ------------
    1) Heartbeat без hb_scroll_percent (NULL) полностью исключаются
       из расчёта активности:
       - они не участвуют в лаге;
       - не считаются активностью.

    2) Лаг считается только по heartbeat с hb_scroll_percent IS NOT NULL.
       Если hb_scroll_percent == prev_scroll → активности нет.

    3) Если вкладка "висит" и скролл не меняется, а heartbeat продолжает
       приходить, last_real_activity не обновляется, и через INACTIVITY_MINUTES
       сессия будет считаться закрытой.
    """
    conn = await get_connection()
    try:
        query = f"""
        WITH hb_clean AS (
            SELECT
                session_id,
                event_time,
                hb_scroll_percent
            FROM events
            WHERE event_type = 'heartbeat'
              AND hb_scroll_percent IS NOT NULL
        ),

        hb_marked AS (
            SELECT
                session_id,
                event_time,
                hb_scroll_percent,
                LAG(hb_scroll_percent) OVER (
                    PARTITION BY session_id
                    ORDER BY event_time
                ) AS prev_scroll,
                (
                    hb_scroll_percent IS DISTINCT FROM
                    LAG(hb_scroll_percent) OVER (
                        PARTITION BY session_id
                        ORDER BY event_time
                    )
                ) AS changed
            FROM hb_clean
        ),

        clicks AS (
            SELECT
                session_id,
                event_time
            FROM events
            WHERE event_type != 'heartbeat'
        ),

        activity AS (
            SELECT
                session_id,
                MAX(event_time) AS last_real_activity
            FROM (
                -- heartbeat только в моменты ИЗМЕНЕНИЯ скролла
                SELECT
                    session_id,
                    event_time
                FROM hb_marked
                WHERE changed = TRUE

                UNION ALL

                -- любые не-heartbeat события (клики и т.п.)
                SELECT
                    session_id,
                    event_time
                FROM clicks
            ) AS t
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
