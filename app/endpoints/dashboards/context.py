from fastapi import APIRouter, Depends
import asyncpg

from app.endpoints.dashboards.auth import get_dashboard_token
from app.db import get_connection

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/")
async def dashboards(
    dashboard_token: asyncpg.Record = Depends(get_dashboard_token),
    conn: asyncpg.Connection = Depends(get_connection),
):
    site_url = dashboard_token["site_url"]

    rows = await conn.fetch(
        """
        SELECT
            date_trunc('day', visit_start) AS dt,
            count(*)                       AS visits
        FROM session_summary
        WHERE site_url = $1
        GROUP BY dt
        ORDER BY dt
        """,
        site_url,
    )

    visits_over_time = [
        {
            "datetime": row["dt"].isoformat(),
            "value": row["visits"],
        }
        for row in rows
    ]

    return {
        "site_url": site_url,
        "charts": {
            "visits_over_time": visits_over_time,
        },
    }
