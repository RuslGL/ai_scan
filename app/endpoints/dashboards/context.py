from fastapi import APIRouter, Depends
import asyncpg

from app.endpoints.dashboards.auth import get_dashboard_token
from app.db import get_connection

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.get("/context")
async def get_dashboard_context(
    dashboard_token: asyncpg.Record = Depends(get_dashboard_token),
    conn: asyncpg.Connection = Depends(get_connection),
):
    role = dashboard_token["role"]
    user_id = dashboard_token["user_id"]

    # ADMIN: полный доступ
    if role == "admin":
        return {
            "role": "admin",
            "sites": "*",
            "default_site": None,
        }

    # USER: сайты строго по user_id
    rows = await conn.fetch(
        """
        SELECT site_url
        FROM sites
        WHERE user_id = $1
          AND is_active = TRUE
        ORDER BY created_at ASC
        """,
        user_id,
    )

    sites = [row["site_url"] for row in rows]

    return {
        "role": "user",
        "sites": sites,
        "default_site": sites[0] if sites else None,
    }
