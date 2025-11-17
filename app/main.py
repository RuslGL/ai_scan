# app/main.py

"""
Главная точка входа FastAPI-приложения.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.endpoints.register import router as register_router
from app.endpoints.track import router as track_router

app: FastAPI = FastAPI(title="AI Scan API")

# Подключение эндпоинтов
app.include_router(register_router)
app.include_router(track_router)
