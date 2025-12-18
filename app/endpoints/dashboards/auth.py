from fastapi import Depends, HTTPException, Query
from starlette.status import HTTP_401_UNAUTHORIZED
import asyncpg
from datetime import datetime, timezone

from app.db import get_connection


async def get_dashboard_token(
    token: str = Query(...),
    conn: asyncpg.Connection = Depends(get_connection),
) -> asyncpg.Record:
    record: asyncpg.Record | None = await conn.fetchrow(
        """
        SELECT *
        FROM dashboard_tokens
        WHERE token = $1
          AND is_active = TRUE
        """,
        token,
    )

    if not record:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Invalid dashboard token",
        )

    expires_at = record["expires_at"]

    if expires_at is not None:
        now = datetime.now(timezone.utc)
        if expires_at <= now:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Dashboard token expired",
            )

    return record
