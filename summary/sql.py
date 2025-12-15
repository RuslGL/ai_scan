from typing import List, Dict, Any
from datetime import datetime

from .db import get_connection


# ----------------------------------------------------------------------
# LOAD RAW EVENTS FOR ONE SESSION
# ----------------------------------------------------------------------

async def load_events_for_session(session_id: str) -> List[Dict[str, Any]]:
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT
                site_url,
                uid,
                session_id,
                event_type,
                event_time,
                scroll_position_percent,
                button_text,
                button_id,
                button_class,
                device_type,
                os,
                browser,
                user_agent,
                client_ip
            FROM events
            WHERE session_id = $1
            ORDER BY event_time ASC;
            """,
            session_id,
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# ----------------------------------------------------------------------
# INSERT SESSION SUMMARY
# ----------------------------------------------------------------------

async def insert_session_summary(summary: Dict[str, Any]) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO session_summary (
                site_url,
                uid,
                session_id,
                visit_start,
                visit_end,
                duration_seconds,
                country,
                city,
                device_type,
                os,
                browser,
                max_scroll_depth,
                final_scroll_depth,
                scroll_stops,
                click_buttons,
                total_scroll_events,
                total_click_events
            )
            VALUES (
                $1,$2,$3,
                $4,$5,$6,
                $7,$8,
                $9,$10,$11,
                $12,$13,$14::jsonb,
                $15::jsonb,
                $16,$17
            );
            """,
            summary["site_url"],
            summary.get("uid"),
            summary["session_id"],
            summary["visit_start"],
            summary["visit_end"],
            summary["duration_seconds"],
            summary.get("country"),
            summary.get("city"),
            summary.get("device_type"),
            summary.get("os"),
            summary.get("browser"),
            summary.get("max_scroll_depth"),
            summary.get("final_scroll_depth"),
            summary.get("scroll_stops"),
            summary.get("click_buttons"),
            summary.get("total_scroll_events", 0),
            summary.get("total_click_events", 0),
        )
    finally:
        await conn.close()


# ----------------------------------------------------------------------
# DELETE RAW EVENTS
# ----------------------------------------------------------------------

async def delete_events_for_session(session_id: str) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            "DELETE FROM events WHERE session_id = $1;",
            session_id,
        )
    finally:
        await conn.close()


# ----------------------------------------------------------------------
# GET DISTINCT SESSION IDS
# ----------------------------------------------------------------------

async def get_pending_session_ids(limit: int = 100) -> List[str]:
    conn = await get_connection()
    try:
        rows = await conn.fetch(
            """
            SELECT DISTINCT session_id
            FROM events
            WHERE session_id IS NOT NULL
            LIMIT $1;
            """,
            limit,
        )
        return [r["session_id"] for r in rows]
    finally:
        await conn.close()
