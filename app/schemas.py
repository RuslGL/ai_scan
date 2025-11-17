"""
Pydantic-схемы (DTO) для API.
Telegram-first регистрация для MVP.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


# ============================================================
#  /register
# ============================================================

class RegisterRequest(BaseModel):
    """
    Модель входных данных для /register.

    MVP-логика:
    - Авторизация ТОЛЬКО через Telegram.
    - Telegram ID обязателен.
    - Username опционален.
    - Email опционален.
    - Пользователь передаёт URL сайта.
    """

    telegram_id: str
    telegram_username: Optional[str] = None

    email: Optional[EmailStr] = None
    site_url: str

    source: str = Field(default="telegram")
    auth_method: str = Field(default="telegram")

    user_category: Optional[str] = None
    site_category: Optional[str] = None


class RegisterResponse(BaseModel):
    """
    Ответ API на регистрацию пользователя.

    Attributes:
        user_id: UUID пользователя.
        site_id: UUID сайта.
        dashboard_token: токен Appsmith.
        dashboard_token_created_at: timestamp.
    """

    user_id: UUID
    site_id: UUID
    dashboard_token: str
    dashboard_token_created_at: datetime


# ============================================================
#  /track  (временно упрощено)
# ============================================================

class TrackEvent(BaseModel):
    """
    DTO для приёма событий с сайтов.
    На MVP структура событий гибкая.
    """

    site_id: str
    session_id: Optional[str] = None
    event_type: str
    timestamp: Optional[str] = None
    payload: Any  # сырые данные — JSON


class TrackResponse(BaseModel):
    """
    Ответ API на успешную запись события.
    """
    status: str = "ok"
