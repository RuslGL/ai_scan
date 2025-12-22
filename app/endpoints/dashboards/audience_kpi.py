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


@router.get("/audience-kpi")
async def audience_kpi(
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
    uid_filter_sql = ""

    if role != "admin":
        site_filter_sql = "AND owner_user_id = $3"
        uid_filter_sql = "AND s2.user_id = $3"
        params.append(user_id)

    row = await conn.fetchrow(
        f"""
        SELECT
            COUNT(DISTINCT dss.session_id) AS sessions,
            AVG(dss.duration_seconds)::float AS avg_session_duration,
            (
                SELECT COUNT(DISTINCT ss2.uid)
                FROM session_summary ss2
                JOIN sites s2 ON s2.site_url = ss2.site_url
                WHERE ss2.visit_start >= $1
                  AND ss2.visit_start <= $2
                  {uid_filter_sql}
            ) AS unique_users
        FROM dashboard_session_summary dss
        WHERE dss.visit_start >= $1
          AND dss.visit_start <= $2
          {site_filter_sql}
        """,
        *params,
    )

    if not row or row["sessions"] == 0:
        return {
            "has_data": False,
        }

    return {
        "has_data": True,
        "sessions": row["sessions"],
        "unique_users": row["unique_users"],
        "avg_session_duration": round(row["avg_session_duration"], 1),
    }
