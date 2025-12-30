from __future__ import annotations

import os
import sys
import uuid
import random
import asyncio
import json
from datetime import datetime, timedelta

import asyncpg
from dotenv import load_dotenv


# ---------------------------------------------------------------------
# CONFIG (редактируется вручную перед запуском)
# ---------------------------------------------------------------------
SIMULATION_CONFIG = {
    "site_url": "example-site-1.tilda.ws",

    "days_range": 7,

    "daily_sessions_mean": 120,
    "daily_sessions_variance": 0.25,
    "returning_users_share": 0.18,

    "median_scroll_depth": 68,
    "scroll_depth_variance": 12,
    "pause_intensity": 0.35,
    "sections_dropout_profile": [0.42, 0.58],

    "target_reach_rate": 0.52,
    "target_click_rate": 0.07,
    "multi_click_probability": 0.08,
    "form_fail_rate": 0.03,

    "non_target_click_rate": 0.12,
    "impact_of_non_target_click": 0.20,

    "mobile_share": 0.47,
    "desktop_share": 0.53,
    "device_behavior_bias": {
        "mobile_scroll_penalty": -8,
        "desktop_confidence_bonus": +4,
    },

    "behavior_profiles": {
        "reader": 0.18,
        "scanner": 0.28,
        "searcher": 0.16,
        "decider": 0.20,
        "hesitant": 0.10,
        "confused": 0.08,
    },

    "session_duration_median": 85,
    "time_to_first_scroll": (200, 1200),
    "time_to_first_click": (1200, 6000),

    "noise_level": 0.15,
}


# ---------------------------------------------------------------------
# ENV
# ---------------------------------------------------------------------
load_dotenv()

DB_USER: str = os.getenv("POSTGRES_USER")
DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
DB_NAME: str = os.getenv("POSTGRES_DB")
DB_HOST: str = os.getenv("POSTGRES_HOST")
DB_PORT: str = os.getenv("POSTGRES_PORT")


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------
def choose_behavior_profile(cfg) -> str:
    profiles = cfg["behavior_profiles"]
    r = random.random()
    cumulative = 0
    for name, p in profiles.items():
        cumulative += p
        if r <= cumulative:
            return name
    return list(profiles.keys())[-1]


def biased_depth(cfg, base_depth, device_type):
    bias = cfg["device_behavior_bias"]
    if device_type == "mobile":
        base_depth += bias["mobile_scroll_penalty"]
    else:
        base_depth += bias["desktop_confidence_bonus"]

    base_depth += random.randint(-cfg["scroll_depth_variance"], cfg["scroll_depth_variance"])
    return max(0, min(100, base_depth))


def make_scroll_stops(cfg, profile, max_depth) -> list[dict]:
    stops = []
    t = 0
    depth = random.randint(5, 15)

    for _ in range(random.randint(10, 40)):
        stop_ms = random.randint(5, 500)
        t += stop_ms

        # profile-driven motion
        if profile == "scanner":
            delta = random.randint(5, 20)
        elif profile == "reader":
            delta = random.randint(-3, 8)
        elif profile == "searcher":
            delta = random.randint(-2, 6)
        else:
            delta = random.randint(-5, 12)

        depth = min(100, max(0, depth + delta))

        # long pauses for “reader / hesitant”
        if profile in ("reader", "hesitant") and random.random() < cfg["pause_intensity"]:
            stop_ms *= random.randint(2, 4)

        stops.append({"t": t, "depth": depth, "stop_ms": stop_ms})

        if depth >= max_depth:
            break

    return stops


def random_device(cfg):
    device_type = "mobile" if random.random() < cfg["mobile_share"] else "desktop"

    if device_type == "mobile":
        os_choice = random.choice(["Android", "iOS"])
        browser = "Chrome" if os_choice == "Android" else random.choice(["Safari", "Chrome"])
        return device_type, os_choice, browser

    os_choice = random.choice(["Mac OS", "Windows", "Linux"])
    browser_choice = random.choice(["Chrome", "Safari", "Firefox"])
    return "desktop", os_choice, browser_choice


def simulate_clicks(cfg, profile, reached_target: bool) -> list[dict]:
    clicks = []
    t = 0

    buttons = [
        "ПОДКЛЮЧИТЬ",
        "ЗАВЕРШИТЬ РЕГИСТРАЦИЮ",
        "КУПИТЬ",
        "ОТПРАВИТЬ",
        None,
    ]

    # non-target clicks
    if random.random() < cfg["non_target_click_rate"]:
        for _ in range(random.randint(1, 3)):
            t += random.randint(*cfg["time_to_first_click"])
            clicks.append({"t": t, "button": random.choice(buttons)})

    # target flow
    if reached_target:
        t += random.randint(*cfg["time_to_first_click"])
        clicks.append({"t": t, "button": "TARGET"})

        # multi-click behavior
        if random.random() < cfg["multi_click_probability"]:
            clicks.append({"t": t + random.randint(200, 900), "button": "TARGET"})

    return clicks


def profile_max_depth(cfg, profile, device_type):
    base = cfg["median_scroll_depth"]

    if profile == "scanner":
        base -= 15
    elif profile == "reader":
        base += 10
    elif profile == "searcher":
        base = random.randint(40, 65)
    elif profile == "decider":
        base += 5
    elif profile == "hesitant":
        base = random.randint(55, 75)
    elif profile == "confused":
        base = random.randint(35, 55)

    return biased_depth(cfg, base, device_type)


# ---------------------------------------------------------------------
# MAIN SEED LOGIC
# ---------------------------------------------------------------------
async def seed(cfg):
    conn: asyncpg.Connection = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT,
    )

    try:
        site_url = cfg["site_url"]
        print(f"▶ Симуляция для сайта: {site_url}")

        now = datetime.utcnow()
        start_date = now - timedelta(days=cfg["days_range"])

        total_days = cfg["days_range"]

        for day_index in range(total_days):
            day_date = start_date + timedelta(days=day_index)

            # sessions per day
            base = cfg["daily_sessions_mean"]
            var = cfg["daily_sessions_variance"]
            sessions_count = random.randint(int(base * (1 - var)), int(base * (1 + var)))

            print(f"  {day_date.date()} → {sessions_count} sessions")

            for _ in range(sessions_count):
                profile = choose_behavior_profile(cfg)

                device_type, os_name, browser = random_device(cfg)

                max_depth = profile_max_depth(cfg, profile, device_type)

                scroll_stops = make_scroll_stops(cfg, profile, max_depth)

                reached_target = False
                if random.random() < cfg["target_reach_rate"] and max_depth > 50:
                    reached_target = True

                # applying impact of non-target clicks
                if random.random() < cfg["non_target_click_rate"]:
                    if random.random() < cfg["impact_of_non_target_click"]:
                        reached_target = False

                clicks = simulate_clicks(cfg, profile, reached_target)

                visit_start = day_date + timedelta(
                    seconds=random.randint(0, 86399)
                )
                duration = max(8, int(random.gauss(cfg["session_duration_median"], 20)))
                visit_end = visit_start + timedelta(seconds=duration)

                await conn.execute(
                    """
                    INSERT INTO session_summary (
                        id, site_url, uid, session_id,
                        visit_start, visit_end, duration_seconds,
                        country, city,
                        device_type, os, browser,
                        max_scroll_depth, final_scroll_depth,
                        scroll_stops, click_buttons,
                        total_scroll_events, total_click_events,
                        created_at
                    )
                    VALUES (
                        $1,$2,$3,$4,
                        $5,$6,$7,
                        $8,$9,
                        $10,$11,$12,
                        $13,$14,
                        $15::jsonb,$16::jsonb,
                        $17,$18,
                        NOW()
                    )
                    """,
                    uuid.uuid4(),
                    site_url,
                    uuid.uuid4().hex,
                    uuid.uuid4().hex,
                    visit_start,
                    visit_end,
                    duration,
                    "TestCountry",
                    "TestCity",
                    device_type,
                    os_name,
                    browser,
                    max(s["depth"] for s in scroll_stops),
                    scroll_stops[-1]["depth"],
                    json.dumps(scroll_stops),
                    json.dumps(clicks),
                    len(scroll_stops),
                    len(clicks),
                )

        print("✅ Симуляция session_summary завершена")

    finally:
        await conn.close()


# ---------------------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(seed(SIMULATION_CONFIG))

# docker compose up -d --build fastapi # блидим без переустановки зависимостей и дальше запускаем файл по синтетич данным
# docker exec -it ai_scan_fastapi python db/complex_test_data_generator.py
