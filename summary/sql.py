from typing import List, Dict, Any
from datetime import datetime

from db import get_connection


# ----------------------------------------------------------------------
# GET SESSION IDS WITH EVENTS
# ----------------------------------------------------------------------

async def get_pending_session_ids(conn) -> List[str]:
    rows = await conn.fetch(
        """
        SELECT DISTINCT session_id
        FROM events
        WHERE session_id IS NOT NULL
        ORDER BY session_id;
        """
    )
    return [r["session_id"] for r in rows]


# ----------------------------------------------------------------------
# LOAD EVENTS FOR SESSION
# ----------------------------------------------------------------------

async def load_events_for_session(conn, session_id: str) -> List[Dict[str, Any]]:
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
            device_type,
            os,
            browser
        FROM events
        WHERE session_id = $1
        ORDER BY event_time ASC;
        """,
        session_id,
    )

    return [dict(r) for r in rows]


# ----------------------------------------------------------------------
# INSERT SESSION SUMMARY
# ----------------------------------------------------------------------

async def insert_session_summary(conn, summary: Dict[str, Any]) -> None:
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
            $1,$2,$3,$4,$5,$6,
            $7,$8,$9,$10,$11,
            $12,$13,$14::jsonb,$15::jsonb,
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
        summary["scroll_stops"],
        summary["click_buttons"],
        summary.get("total_scroll_events", 0),
        summary.get("total_click_events", 0),
    )


# ----------------------------------------------------------------------
# DELETE RAW EVENTS
# ----------------------------------------------------------------------

async def delete_events_for_session(conn, session_id: str) -> None:
    await conn.execute(
        "DELETE FROM events WHERE session_id = $1;",
        session_id,
    )
