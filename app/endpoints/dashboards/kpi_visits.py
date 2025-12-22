from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
import asyncpg

from app.endpoints.dashboards.auth import get_dashboard_token
from app.db import get_connection

router = APIRouter(prefix="/dashboards/metrics", tags=["dashboards-metrics"])


@router.get("/visits-kpi")
async def visits_kpi(
    dashboard_token: asyncpg.Record = Depends(get_dashboard_token),
    conn: asyncpg.Connection = Depends(get_connection),

    days: int = Query(..., gt=0),
    site_url: str | None = Query(None),
):
    role = dashboard_token["role"]
    user_id = dashboard_token["user_id"]

    now = datetime.utcnow()
    current_from = now - timedelta(days=days)
    previous_from = current_from - timedelta(days=days)

    # ------------------------
    # Access control
    # ------------------------
    site_filter_sql = ""
    params_current = [current_from, now]
    params_previous = [previous_from, current_from]

    if role != "admin":
        site_filter_sql += " AND owner_user_id = $3"
        params_current.append(user_id)
        params_previous.append(user_id)

    if site_url:
        site_filter_sql += f" AND site_url = ${len(params_current) + 1}"
        params_current.append(site_url)
        params_previous.append(site_url)

    # ------------------------
    # Current period (daily)
    # ------------------------
    current_rows = await conn.fetch(
        f"""
        SELECT
            date_trunc('day', visit_start) AS day,
            COUNT(*)::int AS visits
        FROM dashboard_session_summary
        WHERE visit_start >= $1
          AND visit_start < $2
          {site_filter_sql}
        GROUP BY 1
        """,
        *params_current,
    )

    if not current_rows:
        return {
            "has_data": False,
            "total": None,
            "avg_per_day": None,
            "max_per_day": None,
            "delta_percent": None,
            "delta_note": None,
        }

    total_current = sum(r["visits"] for r in current_rows)
    max_per_day = max(r["visits"] for r in current_rows)

    # ✅ КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ:
    # среднее считаем по ЗАПРОШЕННОМУ периоду, а не по дням с визитами
    avg_per_day = total_current / days

    # ------------------------
    # Previous period (total)
    # ------------------------
    prev_row = await conn.fetchrow(
        f"""
        SELECT
            COUNT(*)::int AS visits
        FROM dashboard_session_summary
        WHERE visit_start >= $1
          AND visit_start < $2
          {site_filter_sql}
        """,
        *params_previous,
    )

    if not prev_row or not prev_row["visits"]:
        delta_percent = None
        delta_note = "no_previous_data"
    else:
        prev_total = prev_row["visits"]

        if prev_total <= 0:
            delta_percent = None
            delta_note = "no_previous_data"
        else:
            delta_percent = round(
                (total_current - prev_total) / prev_total * 100, 1
            )
            delta_note = None

    return {
        "has_data": True,
        "total": total_current,
        "avg_per_day": round(avg_per_day, 1),
        "max_per_day": max_per_day,
        "delta_percent": delta_percent,
        "delta_note": delta_note,
    }
