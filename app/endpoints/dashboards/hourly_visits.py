from datetime import datetime, timedelta, timezone
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

    # -------------------------------------------------
    # 1. Временной диапазон: последние 72 часа
    # -------------------------------------------------
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    date_from = now - timedelta(hours=71)

    # -------------------------------------------------
    # 2. Фильтры доступа
    # -------------------------------------------------
    site_filter_sql = ""
    params: list[object] = [date_from, now]

    if role != "admin":
        site_filter_sql += " AND owner_user_id = $3"
        params.append(user_id)

    if site_url:
        site_filter_sql += f" AND site_url = ${len(params) + 1}"
        params.append(site_url)

    # -------------------------------------------------
    # 3. Агрегация по часам (ТОЛЬКО реальные данные)
    # -------------------------------------------------
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

    # -------------------------------------------------
    # 4. Мапа: hour (UTC) → value
    # -------------------------------------------------
    by_hour: dict[datetime, int] = {}

    for r in rows:
        hour: datetime = r["hour"]

        # КРИТИЧНО: нормализация
        if hour.tzinfo is None:
            hour = hour.replace(tzinfo=timezone.utc)
        else:
            hour = hour.astimezone(timezone.utc)

        hour = hour.replace(minute=0, second=0, microsecond=0)
        by_hour[hour] = r["value"]

    # -------------------------------------------------
    # 5. Заполняем ВСЕ 72 часа, добавляя нули
    # -------------------------------------------------
    data: list[dict] = []
    cur = date_from

    while cur <= now:
        data.append(
            {
                "date": cur.isoformat(),
                "value": by_hour.get(cur, 0),
            }
        )
        cur += timedelta(hours=1)

    return data
