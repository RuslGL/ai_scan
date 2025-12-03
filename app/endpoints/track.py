"""
Эндпоинты для получения событий с сайтов (универсальная таблица без JSON).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import asyncpg
from fastapi import APIRouter, Depends

from app.schemas import TrackEvent, TrackResponse
from app.db import get_connection, active_sites_cache  # <--- добавлено

router = APIRouter()


@router.post("/track", response_model=TrackResponse)
async def track_event(
    payload: TrackEvent,
    conn: asyncpg.Connection = Depends(get_connection)
) -> TrackResponse:
    """
    Приём события с сайта.
    Храним только структурированные данные, без JSON.
    """

    # --- NEW: проверка активности сайта ---
    if payload.site_id not in active_sites_cache:
        return TrackResponse(status="ignored")  # сайт не активен → игнорируем событие

    # timestamp из события или текущий
    event_time = payload.timestamp or datetime.utcnow()

    # Значения по умолчанию
    click_text = None
    click_block_title = None

    scroll_percent = None
    scroll_max = None
    scroll_milestone = None

    # Данные события (SDK присылает в поле payload)
    data: Dict[str, Any] = payload.payload or {}

    # CLICK
    if payload.event_type == "click":
        click_text = data.get("text")
        click_block_title = data.get("block_title")

    # SCROLL_DEPTH
    elif payload.event_type == "scroll_depth":
        scroll_percent = data.get("current_percent")
        scroll_max = data.get("max_percent")
        scroll_milestone = data.get("milestone")

    # Запись в БД
    await conn.execute(
        """
        INSERT INTO events (
            site_id,
            uid,
            session_id,
            event_type,
            event_time,
            click_text,
            click_block_title,
            scroll_percent,
            scroll_max,
            scroll_milestone
        )
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        """,
        payload.site_id,
        payload.uid,
        payload.session_id,
        payload.event_type,
        event_time,
        click_text,
        click_block_title,
        scroll_percent,
        scroll_max,
        scroll_milestone,
    )

    return TrackResponse(status="ok")
