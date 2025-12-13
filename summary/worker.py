import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

import aiohttp

from sql import (
    get_pending_session_ids,
    load_events_for_session,
    insert_session_summary,
    delete_events_for_session,
)
from aggregator import build_session_summaries


# ---------------------------------------------------------------------
# GEO (внутри worker, отказоустойчиво)
# ---------------------------------------------------------------------

async def geo_from_ip(ip: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    if not ip:
        return None, None

    url = f"http://ip-api.com/json/{ip}?fields=status,country,city"

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as s:
            async with s.get(url) as r:
                data = await r.json()
                if data.get("status") == "success":
                    return data.get("country"), data.get("city")
    except Exception:
        pass

    return None, None


# ---------------------------------------------------------------------
# USER AGENT (минимальный парсер)
# ---------------------------------------------------------------------

def parse_user_agent(ua: Optional[str]) -> Dict[str, Optional[str]]:
    if not ua:
        return {"device_type": None, "os": None, "browser": None}

    ua_l = ua.lower()

    device_type = "mobile" if any(x in ua_l for x in ["mobile", "android", "iphone"]) else "desktop"

    if "windows" in ua_l:
        os = "Windows"
    elif "mac os" in ua_l or "macintosh" in ua_l:
        os = "macOS"
    elif "android" in ua_l:
        os = "Android"
    elif "iphone" in ua_l or "ipad" in ua_l:
        os = "iOS"
    else:
        os = None

    if "chrome" in ua_l and "safari" in ua_l:
        browser = "Chrome"
    elif "safari" in ua_l and "chrome" not in ua_l:
        browser = "Safari"
    elif "firefox" in ua_l:
        browser = "Firefox"
    else:
        browser = None

    return {
        "device_type": device_type,
        "os": os,
        "browser": browser,
    }


# ---------------------------------------------------------------------
# WORKER LOGIC
# ---------------------------------------------------------------------

async def process_session(session_id: str):
    events = await load_events_for_session(session_id)

    if not events:
        return

    summaries = build_session_summaries(events)

    # данные для enrichment берём из первого события сессии
    first_event = events[0]

    client_ip = first_event.get("client_ip")
    user_agent = first_event.get("user_agent")

    country, city = await geo_from_ip(client_ip)
    ua_info = parse_user_agent(user_agent)

    for summary in summaries:
        summary["country"] = country
        summary["city"] = city
        summary["device_type"] = ua_info["device_type"]
        summary["os"] = ua_info["os"]
        summary["browser"] = ua_info["browser"]

        await insert_session_summary(summary)

    # после успешной агрегации — чистим raw
    await delete_events_for_session(session_id)


async def run_worker():
    session_ids = await get_pending_session_ids()

    for session_id in session_ids:
        try:
            await process_session(session_id)
        except Exception as e:
            # здесь позже можно добавить логирование
            print(f"[worker] error processing session {session_id}: {e}")


# ---------------------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(run_worker())
