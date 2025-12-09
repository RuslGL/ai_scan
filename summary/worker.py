"""
Фоновый воркер для агрегирования событий в таблицу session_summary.

Задачи воркера:
---------------
1. Найти raw-сессии, для которых завершился очередной "визит"
   (Selector.find_closed_sessions).

2. По каждой такой raw-сессии:
   - загрузить все события (events_loader.load_events_for_session),
   - вырезать события, уже покрытые предыдущим summary,
   - собрать summary (aggregator.build_session_summary),
   - сохранить запись в session_summary (sql.insert_summary),
   - опционально удалить исходные события из events (sql.delete_events_for_session).

Умолчание: воркер запускает проход раз в 5 минут.
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

# Частота запуска воркера (секунды)
# По умолчанию 300 секунд = 5 минут
LOOP_SLEEP_SECONDS = int(os.getenv("SUMMARY_WORKER_SLEEP_SECONDS", "300"))


async def process_closed_sessions() -> None:
    """
    Выполняет один проход:
    - находит закрытые raw-сессии,
    - агрегирует их в summary,
    - при необходимости очищает events.

    Логика:
    -------
    1) Selector возвращает список raw_session_id, у которых:
       - last_real_activity старше таймаута,
       - и этот визит ещё не покрыт предыдущими summary.

    2) Для каждого session_id:
       - загружаем все events,
       - обрезаем события, уже агрегированные ранее,
       - строим summary-объект,
       - вставляем в session_summary,
       - (при включении очистки) удаляем events.
    """
    session_ids: List[str] = await find_closed_sessions()

    if not session_ids:
        logger.debug("summary-worker: нет закрытых сессий для обработки")
        return

    logger.info("summary-worker: найдено %d закрытых сессий", len(session_ids))

    for session_id in session_ids:
        try:
            events = await load_events_for_session(session_id)
            if not events:
                logger.warning(
                    "summary-worker: для session_id=%s нет событий (пропуск)", session_id
                )
                continue

            # -------------------------------------------------------
            #   ВАЖНО: обрезаем события, уже покрытые предыдущими summary
            # -------------------------------------------------------
            last_end = await get_last_summary_end_time(session_id)

            if last_end:
                events = [e for e in events if e["event_time"] > last_end]

                if not events:
                    logger.info(
                        "summary-worker: session_id=%s — нет новых событий после %s (пропуск)",
                        session_id,
                        last_end,
                    )
                    continue

            # -------------------------------------------------------
            #   Формируем summary
            # -------------------------------------------------------
            summary = build_session_summary(events)
            await insert_summary(summary)

            # -------------------------------------------------------
            #   Удаление событий — может быть отключено для тестирования
            # -------------------------------------------------------
            await delete_events_for_session(session_id)

            logger.info(
                "summary-worker: успешно агрегирована session_id=%s", session_id
            )

        except Exception as e:
            logger.exception(
                "summary-worker: ошибка при обработке session_id=%s: %s",
                session_id,
                e,
            )


async def run_worker() -> None:
    """
    Основной цикл воркера.

    Логика:
    -------
    - Бесконечный цикл:
        - один проход process_closed_sessions(),
        - пауза LOOP_SLEEP_SECONDS (по умолчанию 5 минут),
        - повтор.
    - Ошибки логируются, но не останавливают воркер.
    """
    logger.info(
        "summary-worker: старт воркера, интервал=%s сек. (~%s мин.)",
        LOOP_SLEEP_SECONDS,
        LOOP_SLEEP_SECONDS // 60,
    )

    while True:
        try:
            await process_closed_sessions()
        except Exception as e:
            logger.exception("summary-worker: необработанная ошибка цикла: %s", e)

        await asyncio.sleep(LOOP_SLEEP_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run_worker())
