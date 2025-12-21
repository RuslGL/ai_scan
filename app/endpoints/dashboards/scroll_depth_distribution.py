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
    params = [date_from, date_to]

    if role != "admin":
        site_filter_sql += " AND owner_user_id = $3"
        params.append(user_id)

    if site_url:
        site_filter_sql += f" AND site_url = ${len(params) + 1}"
        params.append(site_url)

    # ------------------------
    # Distribution (0–100 only)
    # ------------------------
    rows = await conn.fetch(
        f"""
        SELECT
            width_bucket(max_scroll_depth, 0, 100, 10) AS bucket,
            COUNT(*)::int AS value
        FROM dashboard_session_summary
        WHERE visit_start >= $1
          AND visit_start <= $2
          AND max_scroll_depth IS NOT NULL
          AND max_scroll_depth >= 0
          AND max_scroll_depth <= 100
          {site_filter_sql}
        GROUP BY bucket
        ORDER BY bucket
        """,
        *params,
    )

    if not rows:
        return {
            "has_data": False,
            "distribution": [],
        }

    distribution = []

    for row in rows:
        bucket_index = row["bucket"]
        bucket_from = (bucket_index - 1) * 10
        bucket_to = bucket_from + 10

        # safety guard (на будущее)
        if bucket_from < 0 or bucket_to > 100:
            continue

        distribution.append(
            {
                "from": bucket_from,
                "to": bucket_to,
                "value": row["value"],
            }
        )

    return {
        "has_data": True,
        "distribution": distribution,
    }
