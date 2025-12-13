import asyncio
from datetime import timezone
from typing import List, Dict, Any

from .db import get_connection
from .sql import (
    get_pending_session_ids,
    load_events_for_session,
    insert_session_summary,
    delete_events_for_session,
)
from .aggregator import build_session_summaries


SLEEP_SECONDS = 30          # как часто запускаться
IDLE_TIMEOUT_SEC = 300      # 5 минут — разрыв визита


async def process_once() -> None:
    conn = await get_connection()
    try:
        session_ids = await get_pending_session_ids(conn)

        if not session_ids:
            return

        for session_id in session_ids:
            events: List[Dict[str, Any]] = await load_events_for_session(
                conn, session_id
            )

            if not events:
                continue

            summaries = build_session_summaries(
                events,
                idle_timeout_sec=IDLE_TIMEOUT_SEC,
            )

            if not summaries:
                continue

            # IMPORTANT:
            # сначала пишем summaries
            for summary in summaries:
                await insert_session_summary(conn, summary)

            # и ТОЛЬКО ПОСЛЕ УСПЕШНОГО INSERT — чистим raw events
            await delete_events_for_session(conn, session_id)

    finally:
        await conn.close()


async def main() -> None:
    while True:
        try:
            await process_once()
        except Exception as e:
            # воркер не должен падать
            print("[SUMMARY WORKER ERROR]", repr(e))

        await asyncio.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
