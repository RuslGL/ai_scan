from datetime import datetime
from typing import List, Dict, Any


def build_session_summaries(
    events: List[Dict[str, Any]],
    idle_timeout_sec: int = 300,  # 5 минут
) -> List[Dict[str, Any]]:
    """
    Принимает raw events ОДНОЙ session_id,
    возвращает список summary-визитов.
    """

    if not events:
        return []

    summaries: List[Dict[str, Any]] = []

    # события уже предполагаются отсортированными
    current_events: List[Dict[str, Any]] = []
    visit_start_time: datetime | None = None
    last_event_time: datetime | None = None

    def flush_visit(events_chunk: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Собирает summary одного визита"""
        start_time = events_chunk[0]["event_time"]
        end_time = events_chunk[-1]["event_time"]

        duration_seconds = int((end_time - start_time).total_seconds())

        # device meta — берём из первого события
        first = events_chunk[0]

        max_scroll = 0
        final_scroll = 0
        scroll_events_count = 0
        click_events_count = 0

        scroll_stops: List[Dict[str, Any]] = []
        click_buttons: List[Dict[str, Any]] = []

        last_scroll_depth = None
        last_scroll_time = None

        for e in events_chunk:
            t_from_start = int((e["event_time"] - start_time).total_seconds() * 1000)

            if e["event_type"] == "scroll":
                scroll_events_count += 1
                depth = e.get("scroll_position_percent")

                if depth is None:
                    continue

                max_scroll = max(max_scroll, depth)
                final_scroll = depth

                # scroll stop detection
                if last_scroll_depth is not None and last_scroll_time is not None:
                    if depth != last_scroll_depth:
                        stop_ms = int(
                            (e["event_time"] - last_scroll_time).total_seconds() * 1000
                        )
                        if stop_ms > 0:
                            scroll_stops.append(
                                {
                                    "t": int(
                                        (last_scroll_time - start_time).total_seconds()
                                        * 1000
                                    ),
                                    "depth": last_scroll_depth,
                                    "stop_ms": stop_ms,
                                }
                            )

                last_scroll_depth = depth
                last_scroll_time = e["event_time"]

            elif e["event_type"] == "click":
                click_events_count += 1
                click_buttons.append(
                    {
                        "t": t_from_start,
                        "button": e.get("button_text"),
                    }
                )

        return {
            "site_url": first["site_url"],
            "uid": first.get("uid"),
            "session_id": first["session_id"],
            "visit_start": start_time,
            "visit_end": end_time,
            "duration_seconds": duration_seconds,
            # geo — позже
            "country": None,
            "city": None,
            # device
            "device_type": first.get("device_type"),
            "os": first.get("os"),
            "browser": first.get("browser"),
            # scroll
            "max_scroll_depth": max_scroll,
            "final_scroll_depth": final_scroll,
            "scroll_stops": scroll_stops,
            # clicks
            "click_buttons": click_buttons,
            # aggregates
            "total_scroll_events": scroll_events_count,
            "total_click_events": click_events_count,
        }

    # основной проход
    for event in events:
        event_time = event["event_time"]

        if visit_start_time is None:
            visit_start_time = event_time
            last_event_time = event_time
            current_events.append(event)
            continue

        gap = (event_time - last_event_time).total_seconds()

        if gap > idle_timeout_sec:
            # закрываем визит
            summaries.append(flush_visit(current_events))
            current_events = [event]
            visit_start_time = event_time
        else:
            current_events.append(event)

        last_event_time = event_time

    # финальный визит
    if current_events:
        summaries.append(flush_visit(current_events))

    return summaries
