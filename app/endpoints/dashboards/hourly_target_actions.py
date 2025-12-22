from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
import asyncpg

from app.endpoints.dashboards.auth import get_dashboard_token
from app.db import get_connection

router = APIRouter(
    prefix="/dashboards/metrics",
    tags=["dashboards-metrics"],
)


@router.get("/hourly-target-actions")
async def hourly_target_actions(
    dashboard_token: asyncpg.Record = Depends(get_dashboard_token),
    conn: asyncpg.Connection = Depends(get_connection),
    site_url: str | None = Query(None),
):
    role = dashboard_token["role"]
    user_id = dashboard_token["user_id"]

    # -------------------------------------------------
    # 1. Временной диапазон: последние 72 часа (UTC)
    # -------------------------------------------------
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    date_from = now - timedelta(hours=71)

    # -------------------------------------------------
    # 2. Проверяем, есть ли целевое действие
    # -------------------------------------------------
    site_filter_sql = ""
    site_params: list[object] = []

    if role != "admin":
        site_filter_sql += " AND user_id = $1"
        site_params.append(user_id)

    if site_url:
        site_filter_sql += f" AND site_url = ${len(site_params) + 1}"
        site_params.append(site_url)

    target_row = await conn.fetchrow(
        f"""
        SELECT target_action_text
        FROM sites
        WHERE is_active = TRUE
          {site_filter_sql}
        LIMIT 1
        """,
        *site_params,
    )

    if not target_row or not target_row["target_action_text"]:
        return {
            "has_target_action": False,
            "data": [],
        }

    target_action_text: str = target_row["target_action_text"]

    # -------------------------------------------------
    # 3. Фильтры для session_summary
    # -------------------------------------------------
    session_filter_sql = ""
    params: list[object] = [date_from, now]

    if role != "admin":
        session_filter_sql += " AND dss.owner_user_id = $3"
        params.append(user_id)

    if site_url:
        session_filter_sql += f" AND dss.site_url = ${len(params) + 1}"
        params.append(site_url)

    target_param_idx = len(params) + 1
    params.append(target_action_text)

    # -------------------------------------------------
    # 4. Агрегация по часам (ТОЛЬКО реальные данные)
    # -------------------------------------------------
    rows = await conn.fetch(
        f"""
        WITH base AS (
            SELECT
                date_trunc('hour', dss.visit_start) AS hour,
                dss.session_id,
                EXISTS (
                    SELECT 1
                    FROM jsonb_array_elements(dss.click_buttons) AS click
                    WHERE LOWER(click->>'button') = LOWER(${target_param_idx})
                ) AS has_target
            FROM dashboard_session_summary dss
            WHERE dss.visit_start >= $1
              AND dss.visit_start <= $2
              {session_filter_sql}
        )
        SELECT
            hour,
            COUNT(*)::int AS visits,
            COUNT(DISTINCT session_id) FILTER (WHERE has_target)::int AS target_actions
        FROM base
        GROUP BY hour
        ORDER BY hour
        """,
        *params,
    )

    # -------------------------------------------------
    # 5. Мапа hour → данные (UTC)
    # -------------------------------------------------
    by_hour: dict[datetime, dict] = {}

    for r in rows:
        hour: datetime = r["hour"]

        if hour.tzinfo is None:
            hour = hour.replace(tzinfo=timezone.utc)
        else:
            hour = hour.astimezone(timezone.utc)

        hour = hour.replace(minute=0, second=0, microsecond=0)

        visits = r["visits"]
        target_actions = r["target_actions"]

        by_hour[hour] = {
            "visits": visits,
            "target_actions": target_actions,
            "conversion_rate": round(target_actions / visits, 4)
            if visits > 0 else 0,
        }

    # -------------------------------------------------
    # 6. Заполняем ВСЕ 72 часа (нули там, где нет данных)
    # -------------------------------------------------
    data: list[dict] = []
    cur = date_from

    while cur <= now:
        row = by_hour.get(
            cur,
            {
                "visits": 0,
                "target_actions": 0,
                "conversion_rate": 0,
            },
        )

        data.append(
            {
                "date": cur.isoformat(),
                **row,
            }
        )

        cur += timedelta(hours=1)

    return {
        "has_target_action": True,
        "target_action_text": target_action_text,
        "data": data,
    }
