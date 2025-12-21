from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
import asyncpg

from app.endpoints.dashboards.auth import get_dashboard_token
from app.db import get_connection

router = APIRouter(prefix="/dashboards/metrics", tags=["dashboards-metrics"])


@router.get("/hourly-visits")
async def hourly_visits(
    dashboard_token: asyncpg.Record = Depends(get_dashboard_token),
    conn: asyncpg.Connection = Depends(get_connection),

    site_url: str | None = Query(None),
):
    role = dashboard_token["role"]
    user_id = dashboard_token["user_id"]

    now = datetime.utcnow()
    date_from = now - timedelta(days=3)

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
    # Query (hourly aggregation, fixed 3 days)
    # ------------------------
    rows = await conn.fetch(
        f"""
        SELECT
            date_trunc('hour', visit_start) AS hour,
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
            "date": row["hour"].isoformat(),
            "value": row["value"],
        }
        for row in rows
    ]
