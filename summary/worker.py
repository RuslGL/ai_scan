import asyncio
from typing import List, Dict, Any

from summary.sql import (
    get_pending_session_ids,
    load_events_for_session,
    insert_session_summary,
    delete_events_for_session,
)
from summary.aggregator import build_session_summaries


SLEEP_SECONDS = 30
IDLE_TIMEOUT_SEC = 300


async def process_once() -> None:
    session_ids = await get_pending_session_ids()

    if not session_ids:
        return

    for session_id in session_ids:
        events: List[Dict[str, Any]] = await load_events_for_session(session_id)

        if not events:
            continue

        summaries = build_session_summaries(
            events,
            idle_timeout_sec=IDLE_TIMEOUT_SEC,
        )

        if not summaries:
            continue

        # сначала INSERT summaries
        for summary in summaries:
            await insert_session_summary(summary)

        # ТОЛЬКО ПОСЛЕ успешного insert — удаляем raw events
        await delete_events_for_session(session_id)


async def main() -> None:
    while True:
        try:
            await process_once()
        except Exception as e:
            print("[SUMMARY WORKER ERROR]", repr(e))

        await asyncio.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())
