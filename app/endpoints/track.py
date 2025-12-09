from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import asyncpg
import aiohttp
from fastapi import APIRouter, Depends, Request

from app.db import get_connection

router = APIRouter()


async def geo_from_ip(ip: str | None):
    if not ip:
        return None, None

    url = f"http://ip-api.com/json/{ip}?fields=status,country,city"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=2) as resp:
                data = await resp.json()
                if data.get("status") == "success":
                    return data.get("country"), data.get("city")
    except:
        pass

    return None, None


@router.post("/track")
async def track_batch(
    request: Request,
    payload: Dict[str, Any],
    conn: asyncpg.Connection = Depends(get_connection)
):
    site_url = payload.get("site_url")
    uid = payload.get("uid")
    session_id = payload.get("session_id")
    events: List[Dict[str, Any]] = payload.get("events", [])

    client_ip = (
        request.headers.get("x-real-ip")
        or request.headers.get("x-forwarded-for")
        or request.client.host
    )

    country, city = await geo_from_ip(client_ip)

    for ev in events:
        event_type = ev.get("event_type")
        ts = ev.get("ts")
        data: Dict[str, Any] = ev.get("payload", {})

        # timestamp (ms -> datetime)
        if isinstance(ts, int):
            event_time = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        else:
            event_time = datetime.now(tz=timezone.utc)

        # CLICK BUTTON
        button_text = data.get("text")
        button_id = data.get("id")
        button_class = data.get("class_name")

        # FORM SUBMIT
        form_id = data.get("form_selector")
        form_button_text = data.get("button_text")
        form_structure = data.get("fields")

        # HEARTBEAT / SCROLL
        hb_scroll_percent = data.get("scroll_percent")
        hb_max_scroll = data.get("max_scroll_percent")
        hb_scroll_y = data.get("scroll_y")
        hb_session_duration_ms = data.get("session_duration_ms")
        hb_since_last_activity_ms = data.get("since_last_activity_ms")

        # DEVICE META
        device = data.get("device", {})
        device_type = device.get("device_type")
        os = device.get("os")
        browser = device.get("browser")
        viewport_width = device.get("viewport_width")
        viewport_height = device.get("viewport_height")
        screen_width = device.get("screen_width")
        screen_height = device.get("screen_height")

        await conn.execute(
            """
            INSERT INTO events (
                site_url,
                uid,
                session_id,
                event_type,
                event_time,

                button_text,
                button_id,
                button_class,

                form_id,
                form_button_text,
                form_structure,

                hb_scroll_percent,
                hb_max_scroll,
                hb_scroll_y,
                hb_session_duration_ms,
                hb_since_last_activity_ms,

                device_type,
                os,
                browser,
                viewport_width,
                viewport_height,
                screen_width,
                screen_height,

                ip_hash,
                country,
                city
            )
            VALUES (
                $1,$2,$3,$4,$5,
                $6,$7,$8,
                $9,$10,$11,
                $12,$13,$14,$15,$16,
                $17,$18,$19,$20,$21,$22,$23,
                $24,$25,$26
            )
            """,
            site_url,
            uid,
            session_id,
            event_type,
            event_time,

            button_text,
            button_id,
            button_class,

            form_id,
            form_button_text,
            form_structure,

            hb_scroll_percent,
            hb_max_scroll,
            hb_scroll_y,
            hb_session_duration_ms,
            hb_since_last_activity_ms,

            device_type,
            os,
            browser,
            viewport_width,
            viewport_height,
            screen_width,
            screen_height,

            client_ip,
            country,
            city,
        )

    return {"status": "ok", "received": len(events)}
