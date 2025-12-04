from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

import asyncpg
from fastapi import APIRouter, Depends

from app.db import get_connection, active_sites_cache

router = APIRouter()


# --- схема батча здесь не требуется, работаем вручную ---
@router.post("/track")
async def track_batch(
    payload: Dict[str, Any],
    conn: asyncpg.Connection = Depends(get_connection)
):
    """
    Приём батча событий от SDK.
    Каждое событие сохраняем как отдельную строку в таблице events.
    """

    site_id = payload.get("site_id")
    uid = payload.get("uid")
    session_id = payload.get("session_id")
    events: List[Dict[str, Any]] = payload.get("events", [])

    # 1) Проверяем активность сайта
    if site_id not in active_sites_cache:
        return {"status": "ignored"}

    # 2) Перебираем каждое событие
    for ev in events:
        event_type = ev.get("event_type")
        timestamp = ev.get("ts") or datetime.utcnow()
        data: Dict[str, Any] = ev.get("payload", {})

        click_text = None
        click_block_title = None
        scroll_percent = None
        scroll_max = None
        scroll_milestone = None

        # CLICK
        if event_type == "click":
            click_text = data.get("text")
            click_block_title = data.get("block_title")

        # SCROLL_DEPTH
        elif event_type == "scroll_depth":
            scroll_percent = data.get("current_percent")
            scroll_max = data.get("max_percent")
            scroll_milestone = data.get("milestone")

        # INSERT
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
            site_id,
            uid,
            session_id,
            event_type,
            datetime.utcfromtimestamp(timestamp / 1000)
                if isinstance(timestamp, int)
                else timestamp,
            click_text,
            click_block_title,
            scroll_percent,
            scroll_max,
            scroll_milestone,
        )

    return {"status": "ok", "received": len(events)}
