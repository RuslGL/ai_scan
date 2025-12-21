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


@router.get("/clicks-kpi")
async def clicks_kpi(
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
    # Aggregation
    # ------------------------
    row = await conn.fetchrow(
        f"""
        SELECT
            COUNT(DISTINCT session_id)                         AS total_sessions,
            COUNT(DISTINCT CASE
                WHEN total_click_events > 0 THEN session_id
            END)                                               AS sessions_with_clicks,
            COALESCE(SUM(total_click_events), 0)::int          AS total_clicks
        FROM dashboard_session_summary
        WHERE visit_start >= $1
          AND visit_start <= $2
          {site_filter_sql}
        """,
        *params,
    )

    total_sessions = row["total_sessions"]

    if not total_sessions:
        return {
            "has_data": False,
        }

    sessions_with_clicks = row["sessions_with_clicks"]
    total_clicks = row["total_clicks"]

    click_sessions_percent = round(
        sessions_with_clicks / total_sessions * 100, 1
    )

    return {
        "has_data": True,
        "total_clicks": total_clicks,
        "sessions_with_clicks": sessions_with_clicks,
        "click_sessions_percent": click_sessions_percent,
    }
