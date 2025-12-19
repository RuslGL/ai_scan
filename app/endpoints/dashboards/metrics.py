from fastapi import APIRouter, Query, Depends, HTTPException
import asyncpg

from app.db import get_pool
from app.endpoints.dashboards.auth import get_dashboard_token

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/metrics/visits")
async def visits_over_time(
    site_url: str = Query(...),
    days: int = Query(14, ge=1, le=90),
    dashboard_token: asyncpg.Record = Depends(get_dashboard_token),
):
    role = dashboard_token["role"]
    token_site = dashboard_token["site_url"]

    # user-токен может быть ограничен конкретным сайтом
    if role != "admin" and token_site is not None and token_site != site_url:
        raise HTTPException(status_code=403, detail="Access denied for this site")

    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                date_trunc('day', visit_start) AS date,
                count(*) AS visits
            FROM session_summary
            WHERE site_url = $1
              AND visit_start >= now() - make_interval(days => $2)
            GROUP BY date
            ORDER BY date
            """,
            site_url,
            days,
        )

    return [
        {
            "date": r["date"].date().isoformat(),
            "value": r["visits"],
        }
        for r in rows
    ]
