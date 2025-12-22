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


@router.get("/os-distribution")
async def os_distribution(
    dashboard_token: asyncpg.Record = Depends(get_dashboard_token),
    conn: asyncpg.Connection = Depends(get_connection),
    days: int = Query(..., ge=1, le=90),
):
    role = dashboard_token["role"]
    user_id = dashboard_token["user_id"]

    date_to = datetime.utcnow()
    date_from = date_to - timedelta(days=days)

    params = [date_from, date_to]
    site_filter_sql = ""

    if role != "admin":
        site_filter_sql = "AND owner_user_id = $3"
        params.append(user_id)

    rows = await conn.fetch(
        f"""
        SELECT
            os,
            COUNT(DISTINCT session_id) AS sessions
        FROM dashboard_session_summary
        WHERE visit_start >= $1
          AND visit_start <= $2
          {site_filter_sql}
        GROUP BY os
        ORDER BY sessions DESC
        """,
        *params,
    )

    if not rows:
        return {
            "has_data": False,
        }

    total_sessions = sum(row["sessions"] for row in rows)

    return {
        "has_data": True,
        "total_sessions": total_sessions,
        "distribution": [
            {
                "os": row["os"] or "unknown",
                "sessions": row["sessions"],
            }
            for row in rows
        ],
    }
