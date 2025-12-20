from __future__ import annotations

from datetime import datetime, timedelta
import asyncpg
from fastapi import APIRouter, Depends, Query, HTTPException

from app.endpoints.dashboards.auth import get_dashboard_token
from app.db import get_connection

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/")
async def dashboards_overview(
    dashboard_token: asyncpg.Record = Depends(get_dashboard_token),
    conn: asyncpg.Connection = Depends(get_connection),
    site_url: str | None = Query(default=None),
):
    """
    Единый overview-дашборд.

    Пример:
    /dashboards/?token=XXXX
    """

    role = dashboard_token["role"]
    user_id = dashboard_token["user_id"]

    # -----------------------------
    # TIME RANGE (fixed for now)
    # -----------------------------
    date_to = datetime.utcnow()
    date_from = date_to - timedelta(days=3)

    # -----------------------------
    # ACCESS CONTROL
    # -----------------------------
    params: list = [date_from, date_to]
    site_sql = ""

    if role == "admin":
        if site_url and site_url != "*":
            site_sql = "AND ss.site_url = $3"
            params.append(site_url)
    else:
        if not site_url:
            raise HTTPException(
                status_code=400,
                detail="site_url is required for user",
            )
        site_sql = "AND ss.site_url = $3"
        params.append(site_url)

    # -----------------------------
    # VISITS OVER TIME (hourly)
    # -----------------------------
    rows = await conn.fetch(
        f"""
        SELECT
            date_trunc('hour', ss.visit_start) AS dt,
            COUNT(*)::int AS value
        FROM session_summary ss
        WHERE ss.visit_start BETWEEN $1 AND $2
        {site_sql}
        GROUP BY dt
        ORDER BY dt
        """,
        *params,
    )

    visits_over_time = [
        {
            "datetime": r["dt"].isoformat(),
            "value": r["value"],
        }
        for r in rows
    ]

    return {
        "context": {
            "role": role,
            "site_url": site_url or "*",
        },
        "overview": {
            "from": date_from.isoformat(),
            "to": date_to.isoformat(),
        },
        "charts": {
            "visits_over_time": visits_over_time,
        },
    }
