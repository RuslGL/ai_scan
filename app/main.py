"""
Главная точка входа FastAPI-приложения.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.endpoints.register import router as register_router
from app.endpoints.track import router as track_router

from app.db import refresh_active_sites   # <--- добавлено


# --- Lifespan вместо deprecated on_event ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Старт приложения
    await refresh_active_sites()          # <--- загружаем активные сайты один раз
    yield
    # Остановка приложения (ничего не делаем)


app: FastAPI = FastAPI(
    title="AI Scan API",
    lifespan=lifespan                     # <--- активируем lifespan
)


# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # временно
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Подключение роутов ---
app.include_router(register_router)
app.include_router(track_router)
