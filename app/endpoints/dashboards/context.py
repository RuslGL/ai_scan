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

    if role == "admin":
        rows = await conn.fetch(
            """
            SELECT id, site_url, user_id
            FROM sites
            WHERE is_active = TRUE
            ORDER BY created_at DESC
            """
        )
    else:
        rows = await conn.fetch(
            """
            SELECT id, site_url, user_id
            FROM sites
            WHERE user_id = $1
              AND is_active = TRUE
            ORDER BY created_at DESC
            """,
            user_id,
        )

    return {
        "role": role,
        "sites": [
            {
                "id": row["id"],
                "site_url": row["site_url"],
                "user_id": row["user_id"],
            }
            for row in rows
        ],
    }
