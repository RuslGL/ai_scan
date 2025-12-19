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
# ENV
# ---------------------------------------------------------------------
load_dotenv()

DB_USER: str = os.getenv("POSTGRES_USER")
DB_PASSWORD: str = os.getenv("POSTGRES_PASSWORD")
DB_NAME: str = os.getenv("POSTGRES_DB")
DB_HOST: str = os.getenv("POSTGRES_HOST")
DB_PORT: str = os.getenv("POSTGRES_PORT")


# ---------------------------------------------------------------------
# UTILS
# ---------------------------------------------------------------------
def random_scroll_stops() -> list[dict]:
    stops = []
    t = 0
    depth = random.randint(5, 20)

    for _ in range(random.randint(10, 40)):
        stop_ms = random.randint(5, 500)
        t += stop_ms
        depth = min(100, max(0, depth + random.randint(-5, 10)))
        stops.append(
            {
                "t": t,
                "depth": depth,
                "stop_ms": stop_ms,
            }
        )

    return stops


def random_clicks() -> list[dict]:
    buttons = [
        "ПОДКЛЮЧИТЬ",
        "ЗАВЕРШИТЬ РЕГИСТРАЦИЮ",
        "КУПИТЬ",
        "ОТПРАВИТЬ",
        None,
    ]

    clicks = []
    t = 0

    for _ in range(random.randint(0, 5)):
        t += random.randint(500, 5000)
        clicks.append(
            {
                "t": t,
                "button": random.choice(buttons),
            }
        )

    return clicks


# ---------------------------------------------------------------------
# MAIN SEED LOGIC
# ---------------------------------------------------------------------
async def seed(base_sessions: int) -> None:
    conn: asyncpg.Connection = await asyncpg.connect(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT,
    )

    try:
        sites = await conn.fetch(
            "SELECT site_url FROM sites WHERE is_active = TRUE"
        )

        if not sites:
            print("❌ Нет сайтов в таблице sites")
            return

        print(f"Найдено сайтов: {len(sites)}")

        for site in sites:
            site_url = site["site_url"]

            sessions_count = random.randint(
                int(base_sessions * 0.7),
                int(base_sessions * 1.3),
            )

            print(f"→ {site_url}: {sessions_count} sessions")

            for _ in range(sessions_count):
                uid = uuid.uuid4().hex
                session_id = uuid.uuid4().hex

                visit_start = datetime.utcnow() - timedelta(
                    minutes=random.randint(0, 60 * 24 * 7)
                )

                duration = random.randint(10, 600)
                visit_end = visit_start + timedelta(seconds=duration)

                scroll_stops = random_scroll_stops()
                click_buttons = random_clicks()

                await conn.execute(
                    """
                    INSERT INTO session_summary (
                        id,
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
                        total_click_events,
                        created_at
                    )
                    VALUES (
                        $1, $2, $3, $4,
                        $5, $6, $7,
                        $8, $9,
                        $10, $11, $12,
                        $13, $14,
                        $15::jsonb,
                        $16::jsonb,
                        $17, $18,
                        NOW()
                    )
                    """,
                    uuid.uuid4(),
                    site_url,
                    uid,
                    session_id,
                    visit_start,
                    visit_end,
                    duration,
                    "TestCountry",
                    "TestCity",
                    random.choice(["mobile", "desktop"]),
                    random.choice(["Mac OS", "Windows", "Linux"]),
                    random.choice(["Chrome", "Safari", "Firefox"]),
                    max(s["depth"] for s in scroll_stops),
                    scroll_stops[-1]["depth"],
                    json.dumps(scroll_stops),
                    json.dumps(click_buttons),
                    len(scroll_stops),
                    len(click_buttons),
                )

        print("✅ Генерация session_summary завершена")

    finally:
        await conn.close()


# ---------------------------------------------------------------------
# ENTRYPOINT
# ---------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python db/test_data_generator.py <base_sessions_per_site>")
        sys.exit(1)

    base_sessions = int(sys.argv[1])
    asyncio.run(seed(base_sessions))
