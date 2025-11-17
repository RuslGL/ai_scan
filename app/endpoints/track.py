"""
Эндпоинты для получения событий с сайтов (MVP версия).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from datetime import datetime
import asyncpg

from app.schemas import TrackEvent, TrackResponse
from app.db import get_connection

router = APIRouter()


@router.post("/track", response_model=TrackResponse)
async def track_event(
    payload: TrackEvent,
    conn: asyncpg.Connection = Depends(get_connection)
) -> TrackResponse:
    """
    Приём события с сайта.

    MVP-логика:
    - сохраняем сырые payload события как JSON
    - события будут использоваться в дашбордах Appsmith
    """

    await conn.execute(
        """
        INSERT INTO events (
            site_id, session_id, event_type, timestamp, payload
        ) VALUES ($1, $2, $3, $4, $5)
        """,
        payload.site_id,
        payload.session_id,
        payload.event_type,
        payload.timestamp or datetime.utcnow().isoformat(),
        payload.payload
    )

    return TrackResponse(status="ok")
