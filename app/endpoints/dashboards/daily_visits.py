from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
import asyncpg

from app.endpoints.dashboards.auth import get_dashboard_token
from app.db import get_connection

router = APIRouter(prefix="/dashboards/metrics", tags=["dashboards-metrics"])


@router.get("/daily-visits")
async def daily_visits(
    dashboard_token: asyncpg.Record = Depends(get_dashboard_token),
    conn: asyncpg.Connection = Depends(get_connection),

    site_url: str | None = Query(None),
    days: int = Query(..., gt=0),
):
    role = dashboard_token["role"]
    user_id = dashboard_token["user_id"]

    now = datetime.utcnow()
    date_from = now - timedelta(days=days)

    # ------------------------
    # Access control
    # ------------------------
    site_filter_sql = ""
    params = [date_from, now]

    if role != "admin":
        site_filter_sql += " AND owner_user_id = $3"
        params.append(user_id)

    if site_url:
        site_filter_sql += f" AND site_url = ${len(params) + 1}"
        params.append(site_url)

    # ------------------------
    # Query (daily aggregation)
    # ------------------------
    rows = await conn.fetch(
        f"""
        SELECT
            date_trunc('day', visit_start) AS day,
            COUNT(*)::int AS value
        FROM dashboard_session_summary
        WHERE visit_start >= $1
          AND visit_start <= $2
          {site_filter_sql}
        GROUP BY 1
        ORDER BY 1
        """,
        *params,
    )

    return [
        {
            "date": row["day"].isoformat(),
            "value": row["value"],
        }
        for row in rows
    ]
