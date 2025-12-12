from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import asyncpg
from fastapi import APIRouter, Depends, Request

from app.db import get_connection

router = APIRouter()


@router.post("/track")
async def track_batch(
    request: Request,
    payload: Dict[str, Any],
    conn: asyncpg.Connection = Depends(get_connection),
):
    site_url = payload.get("site")
    uid = payload.get("uid")
    session_id = payload.get("sid")
    user_agent = payload.get("ua")
    events: List[Dict[str, Any]] = payload.get("ev", [])

    if not site_url or not isinstance(events, list):
        return {"status": "bad payload"}

    client_ip = (
        request.headers.get("x-real-ip")
        or request.headers.get("x-forwarded-for")
        or request.client.host
    )

    inserted = 0
    skipped = 0

    for ev in events:
        try:
            if not isinstance(ev, dict):
                skipped += 1
                continue

            et = ev.get("et")
            ts = ev.get("ts")
            p: Dict[str, Any] = ev.get("p", {})

            if et not in {"hb", "click"}:
                skipped += 1
                continue

            # timestamp
            if isinstance(ts, int):
                event_time = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            else:
                event_time = datetime.now(tz=timezone.utc)

            # defaults
            event_type = None
            scroll_position_percent = None
            button_text = None
            button_id = None
            button_class = None

            # HEARTBEAT → SCROLL
            if et == "hb":
                event_type = "scroll"
                try:
                    scroll_position_percent = int(p.get("sp"))
                except (TypeError, ValueError):
                    scroll_position_percent = None

            # CLICK
            elif et == "click":
                event_type = "click"
                button_text = p.get("button_text")
                button_id = p.get("id")
                button_class = p.get("cls")

            await conn.execute(
                """
                INSERT INTO events (
                    site_url,
                    uid,
                    session_id,
                    event_type,
                    event_time,
                    received_at,

                    scroll_position_percent,

                    button_text,
                    button_id,
                    button_class,

                    user_agent,
                    client_ip
                )
                VALUES (
                    $1,$2,$3,$4,$5,$6,
                    $7,
                    $8,$9,$10,
                    $11,$12
                )
                """,
                site_url,
                uid,
                session_id,
                event_type,
                event_time,
                datetime.now(tz=timezone.utc),

                scroll_position_percent,

                button_text,
                button_id,
                button_class,

                user_agent,
                client_ip,
            )

            inserted += 1

        except Exception:
            skipped += 1
            continue

    return {
        "status": "ok",
        "received": len(events),
        "inserted": inserted,
        "skipped": skipped,
    }
