"""
Модуль агрегатора данных для формирования записи в таблице session_summary.

Новая логика (2025):
--------------------
Формируем summary ТОЛЬКО по реальной активности:
- heartbeat со scroll-change;
- любое событие event_type != heartbeat.

heartbeat:
- со scroll NULL → игнорируется,
- без scroll-change → игнорируется,
они НЕ влияют ни на end_time, ни на final_scroll_depth.

final_scroll_depth = последний scroll среди heartbeat, которые были real-activity.
end_time = время последнего события, которое было real-activity.
"""

from datetime import datetime
from typing import List, Dict, Any
import json


def _first_non_null(events: List[Dict[str, Any]], key: str):
    """Возвращает первое непустое значение поля key в списке событий."""
    for e in events:
        v = e.get(key)
        if v is not None:
            return v
    return None


def build_session_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Формирует структуру summary по событиям визита.

    Ожидается:
    - события отсортированы по времени ASC;
    - события не содержат heartbeat со scroll NULL (worker удаляет);
    - события не содержат heartbeat без scroll-change.
    """

    if not events:
        raise ValueError("build_session_summary() received empty event list")

    # ----------- Базовые поля сессии -----------
    raw_session_id = events[0]["session_id"]
    uid = events[0].get("uid")
    site_url = events[0].get("site_url")

    # start_time = первое ДЕЙСТВИЕ визита
    times = [e["event_time"] for e in events]
    start_time: datetime = min(times)

    # end_time = последнее ДЕЙСТВИЕ (scroll-change или click)
    # worker гарантирует, что heartbeat-флуд отсутствует в events
    end_time: datetime = max(times)

    duration_seconds = (end_time - start_time).total_seconds()

    # ----------- Гео + устройство -----------
    country = _first_non_null(events, "country")
    city = _first_non_null(events, "city")
    device_type = _first_non_null(events, "device_type")
    os_name = _first_non_null(events, "os")
    browser = _first_non_null(events, "browser")

    # ----------- Scroll (только реальная активность) -----------
    hb_events = [
        e for e in events
        if e["event_type"] == "heartbeat"
        and e.get("hb_scroll_percent") is not None
    ]

    # Мы знаем: worker гарантирует, что здесь только scroll-change heartbeat
    # → можно просто взять scroll из последнего
    max_scroll_depth = None
    final_scroll_depth = None

    if hb_events:
        scroll_values = [float(e["hb_scroll_percent"]) for e in hb_events]
        max_scroll_depth = max(scroll_values)
        final_scroll_depth = scroll_values[-1]  # последний real-scroll

    # ----------- Scroll stops (только для real-scroll heartbeat) -----------
    scroll_stops = []
    prev_depth = None
    for e in hb_events:
        depth = e.get("hb_scroll_percent")
        since_ms = e.get("hb_since_last_activity_ms")

        if depth is None or since_ms is None:
            prev_depth = depth
            continue

        if since_ms >= 30_000:  # > 30 секунд стоп
            stop_depth = prev_depth if prev_depth is not None else depth
            scroll_stops.append(
                {
                    "depth": float(stop_depth),
                    "duration_sec": float(since_ms / 1000),
                }
            )

        prev_depth = depth

    # ----------- Clicks -----------
    action_events = [e for e in events if e["event_type"] != "heartbeat"]
    total_actions = len(action_events)

    buttons_acc: Dict[tuple, Dict[str, Any]] = {}

    for e in action_events:
        key = (e["event_type"], e.get("button_text"))

        if key not in buttons_acc:
            buttons_acc[key] = {
                "event_type": e["event_type"],
                "text": e.get("button_text"),
                "id": e.get("button_id"),
                "count": 0,
                "first_at": e["event_time"],
                "last_at": e["event_time"],
            }

        btn = buttons_acc[key]
        btn["count"] += 1
        if e["event_time"] < btn["first_at"]:
            btn["first_at"] = e["event_time"]
        if e["event_time"] > btn["last_at"]:
            btn["last_at"] = e["event_time"]

    click_buttons = [
        {
            "event_type": b["event_type"],
            "text": b["text"],
            "id": b["id"],
            "count": b["count"],
            "first_at": b["first_at"].isoformat(),
            "last_at": b["last_at"].isoformat(),
        }
        for b in buttons_acc.values()
    ]

    # ----------- Итоговый объект summary -----------
    return {
        "raw_session_id": raw_session_id,
        "uid": uid,
        "site_url": site_url,
        "start_time": start_time,
        "end_time": end_time,
        "duration_seconds": duration_seconds,
        "country": country,
        "city": city,
        "device_type": device_type,
        "os": os_name,
        "browser": browser,
        "max_scroll_depth": max_scroll_depth,
        "final_scroll_depth": final_scroll_depth,
        "scroll_stops": json.dumps(scroll_stops, ensure_ascii=False),
        "click_buttons": json.dumps(click_buttons, ensure_ascii=False),
        "total_actions": total_actions,
        "is_closed": True,
    }
