"""
Фоновый воркер для агрегирования событий в таблицу session_summary.

Задачи:
-------
1. Найти raw-сессии, у которых завершился очередной визит
   (Selector.find_closed_sessions).

2. Для каждой такой raw-сессии:
   - загрузить события,
   - вырезать события, уже покрытые предыдущим summary,
   - если новых событий нет — пропустить,
   - если нет НИКАКОЙ активности в новых событиях — пропустить,
   - собрать summary,
   - сохранить summary,
   - удалить исходные события (если включено).

Воркер запускается каждые 5 минут.
"""

import asyncio
import logging
import os
from typing import List

from .selector import find_closed_sessions
from .events_loader import load_events_for_session
from .aggregator import build_session_summary
from .sql import (
    insert_summary,
    delete_events_for_session,
    get_last_summary_end_time,
)

logger = logging.getLogger(__name__)

# Интервал в секундах
LOOP_SLEEP_SECONDS = int(os.getenv("SUMMARY_WORKER_SLEEP_SECONDS", "300"))


def _has_real_activity(events: list) -> bool:
    """
    Проверяет, есть ли среди событий хоть какая-то реальная активность:
    - не-heartbeat события,
    - heartbeat, в которых есть scroll (hb_scroll_percent NOT NULL).
    """
    for e in events:
        if e["event_type"] != "heartbeat":
            return True

        # heartbeat с реальным scroll
        if e.get("hb_scroll_percent") is not None:
            return True

    return False


async def process_closed_sessions() -> None:
    """
    Выполняет один проход:
    - находит закрытые raw-сессии,
    - агрегирует их,
    - удаляет события (если включено).
    """

    session_ids: List[str] = await find_closed_sessions()

    if not session_ids:
        logger.debug("summary-worker: нет закрытых сессий для обработки")
        return

    logger.info("summary-worker: найдено закрытых сессий: %d", len(session_ids))

    for session_id in session_ids:
        try:
            events = await load_events_for_session(session_id)

            if not events:
                logger.warning(
                    "summary-worker: session_id=%s — нет событий (пропуск)",
                    session_id
                )
                continue

            # -------------------------
            # Обрезаем по последнему summary
            # -------------------------
            last_end = await get_last_summary_end_time(session_id)

            if last_end:
                events = [e for e in events if e["event_time"] > last_end]

                if not events:
                    logger.info(
                        "summary-worker: session_id=%s — нет новых событий после %s (визита нет)",
                        session_id,
                        last_end
                    )
                    continue

            # -------------------------
            # Проверяем, есть ли реальная активность
            # -------------------------
            if not _has_real_activity(events):
                logger.info(
                    "summary-worker: session_id=%s — есть события, но НЕТ активности (пропуск)",
                    session_id
                )
                continue

            # -------------------------
            # Формируем summary
            # -------------------------
            summary = build_session_summary(events)
            await insert_summary(summary)

            # -------------------------
            # Очищаем события
            # -------------------------
            await delete_events_for_session(session_id)

            logger.info(
                "summary-worker: session_id=%s — summary сохранён",
                session_id
            )

        except Exception as e:
            logger.exception(
                "summary-worker: ошибка при обработке session_id=%s: %s",
                session_id,
                e
            )


async def run_worker() -> None:
    """Бесконечный цикл воркера."""
    logger.info(
        "summary-worker: старт, интервал=%s сек. (~%s мин.)",
        LOOP_SLEEP_SECONDS,
        LOOP_SLEEP_SECONDS // 60,
    )

    while True:
        try:
            await process_closed_sessions()
        except Exception as e:
            logger.exception("summary-worker: необработанная ошибка: %s", e)

        await asyncio.sleep(LOOP_SLEEP_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_worker())
