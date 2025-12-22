from __future__ import annotations

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
import asyncpg

from app.endpoints.dashboards.auth import get_dashboard_token
from app.db import get_connection

router = APIRouter(
    prefix="/dashboards/metrics",
    tags=["dashboards-metrics"],
)

# Фиксированные бины (ВСЕГДА)
BINS = [
    (0, 10),
    (10, 20),
    (20, 30),
    (30, 40),
    (40, 50),
    (50, 60),
    (60, 70),
    (70, 80),
    (80, 90),
    (90, 100),
]


@router.get("/scroll-depth-distribution")
async def scroll_depth_distribution(
    dashboard_token: asyncpg.Record = Depends(get_dashboard_token),
    conn: asyncpg.Connection = Depends(get_connection),
    days: int = Query(7, ge=1, le=90),
    site_url: str | None = Query(None),
):
    role = dashboard_token["role"]
    user_id = dashboard_token["user_id"]

    date_to = datetime.utcnow()
    date_from = date_to - timedelta(days=days)

    # ------------------------
    # Access control
    # ------------------------
    site_filter_sql = ""
    params: list = [date_from, date_to]

    if role != "admin":
        site_filter_sql += " AND owner_user_id = $3"
        params.append(user_id)

    if site_url:
        site_filter_sql += f" AND site_url = ${len(params) + 1}"
        params.append(site_url)

    # ------------------------
    # Один корректный запрос
    # Кумулятивное распределение
    # ------------------------
    rows = await conn.fetch(
        f"""
        WITH sessions AS (
            SELECT
                max_scroll_depth
            FROM dashboard_session_summary
            WHERE visit_start >= $1
              AND visit_start <= $2
              AND max_scroll_depth IS NOT NULL
              AND max_scroll_depth >= 0
              AND max_scroll_depth <= 100
              {site_filter_sql}
        ),
        total AS (
            SELECT COUNT(*)::int AS total_sessions FROM sessions
        )
        SELECT
            b.from_depth,
            b.to_depth,
            CASE
                WHEN total.total_sessions = 0 THEN 0
                ELSE ROUND(
                    COUNT(s.max_scroll_depth) * 100.0 / total.total_sessions,
                    1
                )
            END AS value
        FROM (
            SELECT
                UNNEST(ARRAY[0,10,20,30,40,50,60,70,80,90]) AS from_depth,
                UNNEST(ARRAY[10,20,30,40,50,60,70,80,90,100]) AS to_depth
        ) b
        LEFT JOIN sessions s
            ON s.max_scroll_depth >= b.from_depth
        CROSS JOIN total
        GROUP BY
            b.from_depth,
            b.to_depth,
            total.total_sessions
        ORDER BY
            b.from_depth
        """,
        *params,
    )

    # rows ВСЕГДА есть (10 бинов), даже если данных 0
    distribution = [
        {
            "from": row["from_depth"],
            "to": row["to_depth"],
            "value": row["value"],
        }
        for row in rows
    ]

    return {
        "has_data": True,
        "distribution": distribution,
    }
