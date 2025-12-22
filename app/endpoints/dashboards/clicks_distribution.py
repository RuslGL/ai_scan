from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
import asyncpg

from app.endpoints.dashboards.auth import get_dashboard_token
from app.db import get_connection

router = APIRouter(
    prefix="/dashboards/metrics",
    tags=["dashboards-metrics"],
)


@router.get("/clicks-distribution")
async def clicks_distribution(
    dashboard_token: asyncpg.Record = Depends(get_dashboard_token),
    conn: asyncpg.Connection = Depends(get_connection),

    site_url: str | None = Query(None),
    days: int = Query(..., gt=0),
):
    role = dashboard_token["role"]
    user_id = dashboard_token["user_id"]

    now = datetime.utcnow()
    date_from = now - timedelta(days=days)

    # -------------------------------------------------
    # Access control
    # -------------------------------------------------
    filter_sql = ""
    params = [date_from, now]

    if role != "admin":
        filter_sql += " AND dss.owner_user_id = $3"
        params.append(user_id)

    if site_url:
        filter_sql += f" AND dss.site_url = ${len(params) + 1}"
        params.append(site_url)

    # -------------------------------------------------
    # Aggregation
    # -------------------------------------------------
    rows = await conn.fetch(
        f"""
        WITH clicks AS (
            SELECT
                dss.session_id,
                LOWER(click->>'button') AS button
            FROM dashboard_session_summary dss,
                 jsonb_array_elements(dss.click_buttons) AS click
            WHERE dss.visit_start >= $1
              AND dss.visit_start <= $2
              AND click->>'button' IS NOT NULL
              {filter_sql}
        )
        SELECT
            button,
            COUNT(*)::int AS total_clicks,
            COUNT(DISTINCT session_id)::int AS sessions_with_click
        FROM clicks
        GROUP BY button
        ORDER BY total_clicks DESC
        """,
        *params,
    )

    data = []
    for row in rows:
        sessions = row["sessions_with_click"]
        total = row["total_clicks"]

        data.append(
            {
                "button": row["button"],
                "total_clicks": total,
                "sessions_with_click": sessions,
                "avg_clicks_per_session": (
                    round(total / sessions, 4) if sessions > 0 else 0
                ),
            }
        )

    return {
        "data": data,
    }
