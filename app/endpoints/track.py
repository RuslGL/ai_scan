from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import hashlib
import os

import asyncpg
from fastapi import APIRouter, Depends, Request

from app.db import get_connection, active_sites_cache

router = APIRouter()

# Попытка подключить локальную GeoIP-базу (если есть)
GEOIP_PATH = os.getenv("GEOIP_DB_PATH", "/app/GeoLite2-City.mmdb")
try:
    import geoip2.database  # type: ignore

    geo_reader: Optional["geoip2.database.Reader"] = geoip2.database.Reader(GEOIP_PATH)
except Exception:
    geo_reader = None


def get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host  # type: ignore[return-value]


def hash_ip(ip: str) -> str:
    # Можно добавить SALT из ENV для усиления
    salt = os.getenv("IP_HASH_SALT", "")
    h = hashlib.sha256()
    h.update((salt + ip).encode("utf-8"))
    return h.hexdigest()


def geo_lookup(ip: str) -> tuple[Optional[str], Optional[str]]:
    if not geo_reader:
        return None, None
    try:
        resp = geo_reader.city(ip)
        country = resp.country.name
        city = resp.city.name
        return country, city
    except Exception:
        return None, None


@router.post("/track")
async def track_batch(
    payload: Dict[str, Any],
    request: Request,
    conn: asyncpg.Connection = Depends(get_connection),
):
    """
    Приём батча событий от SDK.
    SDK передает site_url (hostname), uid, session_id и массив events.
    """

    site_url = payload.get("site_url")
    uid = payload.get("uid")
    session_id = payload.get("session_id")
    events: List[Dict[str, Any]] = payload.get("events", [])

    if not site_url or not events:
        return {"status": "ignored", "reason": "no_site_or_events"}

    # ip / geo вычисляем один раз на весь батч
    client_ip = get_client_ip(request)
    ip_hash = hash_ip(client_ip)
    country, city = geo_lookup(client_ip)

    # if site_url not in active_sites_cache:
    #     return {"status": "ignored"}

    for ev in events:
        event_type: str = ev.get("event_type") or "unknown"
        timestamp = ev.get("ts") or datetime.utcnow()
        data: Dict[str, Any] = ev.get("payload", {}) or {}

        # device info
        device: Dict[str, Any] = data.get("device", {}) or {}
        device_type = device.get("device_type")
        os_name = device.get("os")
        browser = device.get("browser")
        user_agent = device.get("user_agent")
        viewport_width = device.get("viewport_width")
        viewport_height = device.get("viewport_height")
        screen_width = device.get("screen_width")
        screen_height = device.get("screen_height")

        # defaults
        button_text = None
        button_id = None
        button_class = None
        button_type = None

        form_selector = None
        form_button_text = None
        form_structure = None

        hb_scroll_percent = None
        hb_max_scroll = None
        hb_scroll_y = None
        hb_session_duration_ms = None
        hb_since_last_activity_ms = None

        # ---- mapping по типам событий ----

        # CLICK BUTTON
        if event_type.startswith("click_button"):
            button_text = data.get("text")
            button_id = data.get("id")
            button_class = data.get("class_name")
            # тип кнопки иногда можно передавать из SDK, пока None
            button_type = None

        # FORM SUBMIT SUCCESS
        elif event_type.startswith("form_submit_success"):
            form_selector = data.get("form_selector")
            form_button_text = data.get("button_text")
            form_structure = data.get("fields")

        # HEARTBEAT: основное место, где читаем скролл
        if event_type == "heartbeat":
            hb_scroll_percent = data.get("scroll_percent")
            hb_max_scroll = data.get("max_scroll_percent")
            hb_scroll_y = data.get("scroll_y")
            hb_session_duration_ms = data.get("session_duration_ms")
            hb_since_last_activity_ms = data.get("since_last_activity_ms")

        # Приводим timestamp из ms в datetime, если надо
        if isinstance(timestamp, int):
            event_time = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
        else:
            # если это уже datetime (или строка, которую asyncpg съест) — пишем как есть
            if isinstance(timestamp, datetime):
                if timestamp.tzinfo is None:
                    event_time = timestamp.replace(tzinfo=timezone.utc)
                else:
                    event_time = timestamp
            else:
                # на всякий случай
                event_time = datetime.now(tz=timezone.utc)

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
                button_type,

                form_selector,
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
                user_agent,
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
                $6,$7,$8,$9,
                $10,$11,$12,
                $13,$14,$15,$16,$17,
                $18,$19,$20,$21,$22,$23,$24,$25,
                $26,$27,$28
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
            button_type,
            form_selector,
            form_button_text,
            form_structure,
            hb_scroll_percent,
            hb_max_scroll,
            hb_scroll_y,
            hb_session_duration_ms,
            hb_since_last_activity_ms,
            device_type,
            os_name,
            browser,
            user_agent,
            viewport_width,
            viewport_height,
            screen_width,
            screen_height,
            ip_hash,
            country,
            city,
        )

    return {"status": "ok", "received": len(events)}
