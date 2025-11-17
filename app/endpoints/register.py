from __future__ import annotations

from fastapi import APIRouter, Depends
from uuid import uuid4, UUID
from datetime import datetime
import asyncpg

from app.schemas import RegisterRequest, RegisterResponse
from app.db import get_connection

router = APIRouter()


@router.post("/register", response_model=RegisterResponse)
async def register_user(
    payload: RegisterRequest,
    conn: asyncpg.Connection = Depends(get_connection)
) -> RegisterResponse:
    """
    Регистрация пользователя через Telegram.
    """

    # Проверяем — есть ли пользователь
    existing_user: asyncpg.Record | None = await conn.fetchrow(
        "SELECT id FROM users WHERE telegram_id = $1",
        payload.telegram_id
    )

    if existing_user:
        user_id: UUID = existing_user["id"]
    else:
        user_id = uuid4()
        await conn.execute(
            """
            INSERT INTO users (
                id, email, telegram_id, joined_at, source,
                auth_method, category, dashboard_token, dashboard_token_created_at
            )
            VALUES ($1, $2, $3, NOW(), $4, $5, $6, NULL, NULL)
            """,
            user_id,
            payload.email,
            payload.telegram_id,
            payload.source,
            payload.auth_method,
            payload.user_category,
        )

    # Добавляем сайт
    site_id: UUID = uuid4()
    await conn.execute(
        """
        INSERT INTO sites (
            id, user_id, site_url, api_key, category,
            created_at, last_scan_at, is_active
        )
        VALUES ($1, $2, $3, NULL, $4, NOW(), NULL, TRUE)
        """,
        site_id,
        user_id,
        payload.site_url,
        payload.site_category,
    )

    # Токен
    dashboard_token: str = f"token_{uuid4()}"
    dashboard_token_created_at: datetime = datetime.utcnow()

    await conn.execute(
        """
        UPDATE users
        SET dashboard_token = $1,
            dashboard_token_created_at = $2
        WHERE id = $3
        """,
        dashboard_token,
        dashboard_token_created_at,
        user_id
    )

    return RegisterResponse(
        user_id=user_id,
        site_id=site_id,
        dashboard_token=dashboard_token,
        dashboard_token_created_at=dashboard_token_created_at
    )
