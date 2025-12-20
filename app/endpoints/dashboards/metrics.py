from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
import asyncpg

from app.endpoints.dashboards.auth import get_dashboard_token
from app.db import get_connection

router = APIRouter(prefix="/dashboards/metrics", tags=["dashboards-metrics"])


@router.get("/visits")
async def visits_over_time(
    dashboard_token: asyncpg.Record = Depends(get_dashboard_token),
    conn: asyncpg.Connection = Depends(get_connection),

    site_url: str | None = Query(None),
    bucket: str = Query("hour", regex="^(hour|day)$"),

    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
):
    role = dashboard_token["role"]
    user_id = dashboard_token["user_id"]

    now = datetime.utcnow()

    # ------------------------
    # Defaults
    # ------------------------
    if bucket == "hour":
        default_from = now - timedelta(days=3)
        max_range = timedelta(days=7)
        trunc = "hour"
    else:
        default_from = now - timedelta(days=14)
        max_range = timedelta(days=90)
        trunc = "day"

    if date_to is None:
        date_to = now
    if date_from is None:
        date_from = default_from

    if date_to - date_from > max_range:
        raise HTTPException(
            status_code=400,
            detail="Date range too large for selected bucket",
        )

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
    # Query
    # ------------------------
    rows = await conn.fetch(
        f"""
        SELECT
            date_trunc('{trunc}', visit_start) AS bucket,
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
            "date": row["bucket"].isoformat(),
            "value": row["value"],
        }
        for row in rows
    ]
