from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
import asyncpg

from app.endpoints.dashboards.auth import get_dashboard_token
from app.db import get_connection

router = APIRouter(
    prefix="/dashboards/metrics",
    tags=["dashboards-metrics"],
)


@router.get("/daily-target-actions")
async def daily_target_actions(
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
    # 1. Проверяем, есть ли целевое действие
    # -------------------------------------------------
    site_filter_sql = ""
    site_params = []

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
        WHERE is_active = true
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

    target_action_text = target_row["target_action_text"]

    # -------------------------------------------------
    # 2. Фильтры для session_summary
    # -------------------------------------------------
    session_filter_sql = ""
    params = [date_from, now]

    if role != "admin":
        session_filter_sql += " AND dss.owner_user_id = $3"
        params.append(user_id)

    if site_url:
        session_filter_sql += f" AND dss.site_url = ${len(params) + 1}"
        params.append(site_url)

    target_param_idx = len(params) + 1
    params.append(target_action_text)

    # -------------------------------------------------
    # 3. Один запрос: визиты + цели
    # -------------------------------------------------
    rows = await conn.fetch(
        f"""
        WITH base AS (
            SELECT
                date_trunc('day', dss.visit_start) AS day,
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
            day,
            COUNT(*)::int AS visits,
            COUNT(DISTINCT session_id)
                FILTER (WHERE has_target)::int AS target_actions
        FROM base
        GROUP BY day
        ORDER BY day
        """,
        *params,
    )

    # -------------------------------------------------
    # 4. Заполняем пропущенные дни нулями
    # -------------------------------------------------
    rows_map = {
        row["day"].date(): {
            "visits": row["visits"],
            "target_actions": row["target_actions"],
        }
        for row in rows
    }

    data = []
    current = date_from.date()
    end = now.date()

    while current <= end:
        day_data = rows_map.get(current)

        if day_data:
            visits = day_data["visits"]
            target_actions = day_data["target_actions"]
        else:
            visits = 0
            target_actions = 0

        conversion_rate = (
            round(target_actions / visits, 4) if visits > 0 else 0
        )

        data.append(
            {
                "date": current.isoformat(),
                "visits": visits,
                "target_actions": target_actions,
                "conversion_rate": conversion_rate,
            }
        )

        current += timedelta(days=1)

    return {
        "has_target_action": True,
        "target_action_text": target_action_text,
        "data": data,
    }
