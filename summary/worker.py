"""
Фоновый воркер для агрегирования событий в таблицу session_summary.

Новая логика (2025):
--------------------
1. Summary создаётся только когда визит ЗАКРЫТ:
   - нет активности (scroll-change или кликов) >= 15 минут.
   - selector гарантирует, что визит закрыт.

2. После закрытия визита:
   - heartbeat со scroll NULL → удалить.
   - heartbeat без scroll-change → удалить.
   - heartbeat со scroll-change → это начало НОВОГО визита (но summary пока не создаём).

3. Worker формирует summary ТОЛЬКО по real-activity:
   - heartbeat со scroll-change,
   - клики.

4. Все мусорные heartbeat удаляются.
"""

import asyncio
import logging
import os
from typing import List, Dict, Any

from .selector import find_closed_sessions
from .events_loader import load_events_for_session
from .aggregator import build_session_summary
from .sql import (
    insert_summary,
    delete_events_for_session,
    get_last_summary_info,
)

logger = logging.getLogger(__name__)

LOOP_SLEEP_SECONDS = int(os.getenv("SUMMARY_WORKER_SLEEP_SECONDS", "300"))


# -----------------------------------------------------------------------------
#  Фильтрация REAL-ACTIVITY
# -----------------------------------------------------------------------------

def _filter_real_activity_events(
    events: List[Dict[str, Any]],
    last_final_scroll: float | None
) -> List[Dict[str, Any]]:
    """
    Оставляет только real-activity:

    heartbeat:
      - NULL scroll → удалить
      - scroll == last_final_scroll → удалить
      - scroll == предыдущий scroll → удалить
      - scroll-change → real-activity

    Любые клики — real-activity.

    Возвращает список событий, пригодных для aggregator.
    """

    real_events = []
    prev_scroll = last_final_scroll  # состояние scroll до визита

    for e in events:
        if e["event_type"] != "heartbeat":
            real_events.append(e)  # 100% активность
            continue

        # Heartbeat
        s = e.get("hb_scroll_percent")

        if s is None:
            # полностью игнорируем NULL scroll
            continue

        s = float(s)

        # не изменился scroll → игнорируем
        if prev_scroll is not None and s == float(prev_scroll):
            continue

        # scroll-change → активность
        real_events.append(e)
        prev_scroll = s

    return real_events


# -----------------------------------------------------------------------------
#  Основная обработка закрытых визитов
# -----------------------------------------------------------------------------

async def process_closed_sessions() -> None:
    """
    Основная логика:
    1. selector возвращает session_id, где визит закрыт.
    2. worker загружает события.
    3. worker удаляет всё, что было до последнего summary.
    4. worker фильтрует только real-activity.
    5. Если real-activity нет → всё удалить.
    6. Если есть → собрать summary и удалить события.
    """

    session_ids: List[str] = await find_closed_sessions()

    if not session_ids:
        logger.debug("summary-worker: нет закрытых сессий для обработки")
        return

    logger.info("summary-worker: найдено закрытых сессий: %d", len(session_ids))

    for session_id in session_ids:
        try:
            # ------------------------------------------------------------
            # 1. Загружаем все события сессии
            # ------------------------------------------------------------
            events = await load_events_for_session(session_id)

            if not events:
                logger.warning(
                    "summary-worker: session_id=%s — нет событий", session_id
                )
                continue

            # ------------------------------------------------------------
            # 2. Получаем summary-info (end_time + final_scroll_depth)
            # ------------------------------------------------------------
            summary_info = await get_last_summary_info(session_id)
            last_end = None
            last_final_scroll = None

            if summary_info:
                last_end = summary_info["last_end"]
                last_final_scroll = summary_info["last_final_scroll"]

            # ------------------------------------------------------------
            # 3. Удаляем события, которые уже учтены в summary
            # ------------------------------------------------------------
            if last_end:
                events = [e for e in events if e["event_time"] > last_end]

            if not events:
                continue

            # ------------------------------------------------------------
            # 4. Фильтруем только real-activity
            # ------------------------------------------------------------
            real_events = _filter_real_activity_events(events, last_final_scroll)

            if not real_events:
                # Мусорные heartbeat (NULL scroll или не изменить scroll)
                logger.info(
                    "summary-worker: session_id=%s — нет real-activity, удаление мусора",
                    session_id
                )
                await delete_events_for_session(session_id)
                continue

            # ------------------------------------------------------------
            # 5. Selector гарантирует, что визит закрыт → создаём summary
            # ------------------------------------------------------------
            summary = build_session_summary(real_events)
            await insert_summary(summary)

            # ------------------------------------------------------------
            # 6. Удаляем события визита
            # ------------------------------------------------------------
            await delete_events_for_session(session_id)

            logger.info("summary-worker: session_id=%s — summary сохранён", session_id)

        except Exception as e:
            logger.exception(
                "summary-worker: ошибка при обработке session_id=%s: %s",
                session_id, e
            )


# -----------------------------------------------------------------------------
#  Запуск цикла воркера
# -----------------------------------------------------------------------------

async def run_worker() -> None:
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
