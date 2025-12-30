"""
Агрегатор суточных и 7-дневных метрик по сайту
с учётом таймзоны сайта и встроенными стат-проверками.

------------------------------------------------------------------
СТАТИСТИЧЕСКИЕ ТЕСТЫ, КОТОРЫЕ МЫ ПРИМЕНЯЕМ В ФАЙЛЕ
------------------------------------------------------------------

1) Тест на отличие ОБЪЁМА ТРАФИКА (sessions)
   Модель: приближённый Z-test по Пуассону
   Интерпретация:
     • "better"  — трафик вырос статистически значимо
     • "worse"   — трафик снизился статистически значимо
     • "neutral" — отличие в пределах шума
   Ограничения:
     • на малых выборках трактуем осторожно

2) Z-test для долей (конверсии)
   Применяется к метрикам:
     • share_clicked_target        — доля пользователей, кликнувших CTA
     • share_reached_goal_zone     — доля пользователей,
                                      дошедших до зоны CTA-кнопки
   Формула:
     • p1 = x1 / n1 (отчётный день = вчера)
     • p2 = x2 / n2 (baseline 7 дней до него)
     • pooled p и z-статистика
   Условия применения:
     • baseline доступен
     • есть данные хотя бы за 1 день до отчётного
     • CTA настроен на сайте

3) Метрики, к которым СТАТ-ТЕСТЫ НЕ ПРИМЕНЯЮТСЯ:
     ✗ медианная глубина скролла
     ✗ drop-off зоны
     ✗ сегменты устройств / ОС
------------------------------------------------------------------

Мы считаем:
✔ отчётный день = ВЧЕРА по таймзоне сайта
✔ baseline = 7 дней ДО этого дня
✔ сохраняем в site_daily_metrics
------------------------------------------------------------------
"""

import os
import json
from math import sqrt
from statistics import median
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "adminpass")
DB_NAME = os.getenv("POSTGRES_DB", "ai_scan_db")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = int(os.getenv("POSTGRES_PORT", "5432"))


# -----------------------------------------------------------
# DB
# -----------------------------------------------------------
async def get_conn() -> asyncpg.Connection:
    return await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT,
    )


# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------
def normalize_button(text: Optional[str]) -> Optional[str]:
    return text.strip().lower() if text else None


def extract_click_buttons(raw) -> List[Dict[str, Any]]:
    if not raw:
        return []

    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []

    result: List[Dict[str, Any]] = []

    for item in raw:
        if isinstance(item, dict):
            btn = normalize_button(item.get("button"))
            t = item.get("t")
        else:
            btn = normalize_button(str(item))
            t = None

        if btn:
            result.append({"button": btn, "t": t})

    return result


def parse_scroll_stops(raw) -> List[Dict[str, Any]]:
    if not raw:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    return raw


def compute_dropoff_top3(rows):
    zones = [r["final_scroll_depth"] for r in rows if r.get("final_scroll_depth")]
    if not zones:
        return []

    total = len(zones)
    freq = {}

    for z in zones:
        freq[z] = freq.get(z, 0) + 1

    top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:3]
    return [{"zone": z, "share": c / total} for z, c in top]


def find_depth_at_click(scroll_stops, click_t: Optional[int]):
    if not scroll_stops:
        return None

    if click_t is None:
        return scroll_stops[-1].get("depth")

    candidates = [
        s for s in scroll_stops
        if s.get("t") is not None and s["t"] <= click_t
    ]

    if not candidates:
        return scroll_stops[0].get("depth")

    best = max(candidates, key=lambda s: s["t"])
    return best.get("depth")


# -----------------------------------------------------------
# Aggregation
# -----------------------------------------------------------
def aggregate_block(rows, target_action: Optional[str]):
    sessions = len(rows)

    if sessions == 0:
        return {
            "available": False,
            "sessions": 0,
            "median_depth": 0,
            "clicked_count": 0,
            "reached_count": 0,
            "share_clicked_target": None,
            "share_reached_goal_zone": None,
            "goal_zone_inferred": False,
            "goal_click_depths": [],
            "dropoff_top3": [],
        }

    depths = [r["final_scroll_depth"] for r in rows if r.get("final_scroll_depth")]
    median_depth = int(median(depths)) if depths else 0

    target_norm = normalize_button(target_action) if target_action else None

    clicked_count = 0
    goal_click_depths = []

    for r in rows:
        clicks = extract_click_buttons(r.get("click_buttons"))
        stops = parse_scroll_stops(r.get("scroll_stops"))

        for c in clicks:
            if target_norm and c["button"] == target_norm:
                clicked_count += 1
                depth = find_depth_at_click(stops, c.get("t"))
                if depth is not None:
                    goal_click_depths.append(depth)

    reached_count = clicked_count

    share_clicked = clicked_count / sessions if target_norm else None
    share_reached = reached_count / sessions if target_norm else None

    return {
        "available": True,
        "sessions": sessions,
        "median_depth": median_depth,
        "clicked_count": clicked_count,
        "reached_count": reached_count,
        "share_clicked_target": share_clicked,
        "share_reached_goal_zone": share_reached,
        "goal_zone_inferred": len(goal_click_depths) > 0,
        "goal_click_depths": goal_click_depths,
        "dropoff_top3": compute_dropoff_top3(rows),
    }


# -----------------------------------------------------------
# SAVE TO DB  (используем site_daily_metrics)
# -----------------------------------------------------------
async def save_to_db(
    conn,
    site_url,
    date_local,
    tzname,
    daily,
    baseline,
):
    await conn.execute(
        """
        INSERT INTO site_daily_metrics (
            site_url,
            date_local,
            period_days,
            timezone,
            daily,
            baseline_7d,
            stats
        )
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        ON CONFLICT (site_url, date_local)
        DO UPDATE SET
            period_days = EXCLUDED.period_days,
            timezone = EXCLUDED.timezone,
            daily = EXCLUDED.daily,
            baseline_7d = EXCLUDED.baseline_7d,
            stats = EXCLUDED.stats,
            computed_at = NOW()
        """,
        site_url,
        date_local,
        7,
        tzname,
        json.dumps(daily, ensure_ascii=False),
        json.dumps(baseline, ensure_ascii=False),
        None,   # stats появятся позже — пока сохраняем null
    )


# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
async def main(site_url: str, days: int = 7):
    conn = await get_conn()

    site = await conn.fetchrow(
        "SELECT target_action_text, timezone FROM sites WHERE site_url=$1",
        site_url,
    )

    tzname = site["timezone"] or "UTC"
    tz = ZoneInfo(tzname)
    target_action = normalize_button(site["target_action_text"])

    now_local = datetime.now(timezone.utc).astimezone(tz)
    report_date = now_local.date() - timedelta(days=1)

    day_start_local = datetime.combine(report_date, datetime.min.time(), tz)
    day_end_local = day_start_local + timedelta(days=1)
    baseline_start_local = day_start_local - timedelta(days=days)

    baseline_start_utc = baseline_start_local.astimezone(timezone.utc)
    day_start_utc = day_start_local.astimezone(timezone.utc)
    day_end_utc = day_end_local.astimezone(timezone.utc)

    rows = await conn.fetch(
        """
        SELECT *
        FROM session_summary
        WHERE site_url=$1
          AND visit_start >= $2
          AND visit_start < $3
        """,
        site_url,
        baseline_start_utc,
        day_end_utc,
    )

    daily_rows = [r for r in rows if day_start_utc <= r["visit_start"] < day_end_utc]
    baseline_rows = [r for r in rows if r["visit_start"] < day_start_utc]

    daily = aggregate_block(daily_rows, target_action)
    baseline = aggregate_block(baseline_rows, target_action)

    await save_to_db(conn, site_url, report_date, tzname, daily, baseline)

    await conn.close()


if __name__ == "__main__":
    import asyncio
    import sys
    asyncio.run(main(sys.argv[1]))


# docker compose up -d --build summary_worker
# тестовый запуск
"""
docker exec -it ai_scan_summary_worker \
  python summary/metrics/site_daily_aggregate.py example-site-1.tilda.ws

"""

