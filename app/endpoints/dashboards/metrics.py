from fastapi import APIRouter, Query
from app.db import get_pool

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/metrics/visits")
async def visits_over_time(
    site_url: str = Query(...),
    days: int = Query(14, ge=1, le=90),
):
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
