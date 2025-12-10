"""
Определение raw-сессий, у которых завершился визит
и которые нужно отправить в aggregator для формирования Summary.

Новая логика 2025:
------------------
1) Реальная активность:
   - любое событие, event_type != 'heartbeat';
   - heartbeat, у которого hb_scroll_percent ИЗМЕНИЛСЯ
     относительно предыдущего НЕ-NULL heartbeat.

   heartbeat:
     - с NULL scroll → полностью игнорируются;
     - с тем же scroll → не активность.

2) Визит считается закрытым, если:
       now() - last_real_activity >= 15 минут.
   И только тогда мы создаём Summary.

3) После создания Summary:
   - В summary пишется final_scroll_depth = последний scroll heartbeat.
   - Все события визита удаляются (это делает worker).

4) После закрытия визита:
   - HEARTBEAT со scroll NULL → просто удаляем (worker).
   - HEARTBEAT со scroll без изменений → удаляем (worker).
   - HEARTBEAT со scroll-change → это новый визит.

5) selector выбирает session_id только если:
   - визит закрыт по неактивности
   И К ТОМУ ЖЕ:
   - после последнего summary был scroll-change или другое реальное событие.

То есть selector НЕ должен возвращать:
   - heartbeat-флуд после закрытия визита с тем же scroll.
"""

import os
from typing import List
from asyncpg import Record

from .db import get_connection

INACTIVITY_MINUTES = int(os.getenv("SUMMARY_INACTIVITY_MINUTES", "15"))


async def find_closed_sessions() -> List[str]:
    """
    Возвращает список session_id, которые:

    1) Имеют last_real_activity > last_summary_end.
    2) last_real_activity < NOW() - 15 minutes.
    3) last_real_activity определяется:
        - клики, сабмиты и т.п.
        - heartbeat со scroll-change.
        - heartbeat со scroll NULL → полностью игнорируется.
        - heartbeat без scroll-change → тоже игнорируется.

    Это гарантирует:
    - Мы НЕ создаём summary от heartbeat-флуда после закрытия сессии.
    - Мы создаём новый визит только если scroll реально изменился.
    """

    conn = await get_connection()
    try:
        query = f"""
        ----------------------------------------------------------------------
        -- 1. Берём heartbeat со scroll NOT NULL
        ----------------------------------------------------------------------
        WITH hb_clean AS (
            SELECT
                session_id,
                event_time,
                hb_scroll_percent
            FROM events
            WHERE event_type = 'heartbeat'
              AND hb_scroll_percent IS NOT NULL
        ),

        ----------------------------------------------------------------------
        -- 2. Помечаем heartbeat, где scroll изменился
        ----------------------------------------------------------------------
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

        ----------------------------------------------------------------------
        -- 3. Любые не-HEARTBEAT события — 100% активность
        ----------------------------------------------------------------------
        clicks AS (
            SELECT
                session_id,
                event_time
            FROM events
            WHERE event_type != 'heartbeat'
        ),

        ----------------------------------------------------------------------
        -- 4. Объединяем только РЕАЛЬНУЮ активность
        ----------------------------------------------------------------------
        activity AS (
            SELECT
                session_id,
                MAX(event_time) AS last_real_activity
            FROM (
                -- scroll-change heartbeat
                SELECT
                    session_id,
                    event_time
                FROM hb_marked
                WHERE changed = TRUE

                UNION ALL

                -- клики, сабмиты, формы
                SELECT
                    session_id,
                    event_time
                FROM clicks
            ) AS t
            GROUP BY session_id
        ),

        ----------------------------------------------------------------------
        -- 5. Последний summary для session_id
        ----------------------------------------------------------------------
        summary_bounds AS (
            SELECT
                raw_session_id,
                MAX(end_time) AS last_summary_end,
                MAX(final_scroll_depth) AS last_final_scroll
            FROM session_summary
            GROUP BY raw_session_id
        )

        ----------------------------------------------------------------------
        -- 6. Выбираем СЕССИИ, которые требует СУММАРИЗАЦИИ
        ----------------------------------------------------------------------
        SELECT a.session_id
        FROM activity a
        LEFT JOIN summary_bounds sb
            ON sb.raw_session_id = a.session_id
        WHERE
            ------------------------------------------------------------------
            -- Визит ЗАКРЫТ (нет активности 15 минут)
            ------------------------------------------------------------------
            a.last_real_activity < (NOW() - INTERVAL '{INACTIVITY_MINUTES} minutes')

            ------------------------------------------------------------------
            -- Активность НЕ покрыта предыдущим Summary
            ------------------------------------------------------------------
            AND (
                sb.last_summary_end IS NULL         -- нет Summary → первый визит
                OR a.last_real_activity > sb.last_summary_end
            );
        """

        rows: List[Record] = await conn.fetch(query)
        return [r["session_id"] for r in rows]

    finally:
        await conn.close()
