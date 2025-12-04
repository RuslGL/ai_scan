"""
Главная точка входа FastAPI-приложения.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.endpoints.register import router as register_router
from app.endpoints.track import router as track_router

from app.db import refresh_active_sites


# ------------------------------------------------------
# Lifespan — выполняется один раз при запуске приложения
# ------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Загружаем активные сайты (кэш)
    await refresh_active_sites()
    yield  # ← передаём управление FastAPI
    # На shutdown нет действий


# ------------------------------------------------------
# Инициализация приложения
# ------------------------------------------------------
app: FastAPI = FastAPI(
    title="AI Scan API",
    lifespan=lifespan
)


# ------------------------------------------------------
# CORS (пока полностью открыт)
# ------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # временно, можно ограничить доменами
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------
# Безопасная заглушка GET /track  (очень важно!)
# Чтобы браузеры НЕ воспринимали домен как вредоносный.
# ------------------------------------------------------
@app.get("/track")
async def track_get_stub():
    return {
        "status": "ok",
        "message": "Tracking endpoint expects POST requests only."
    }


# ------------------------------------------------------
# Подключение роутов
# ------------------------------------------------------
app.include_router(register_router)
app.include_router(track_router)
