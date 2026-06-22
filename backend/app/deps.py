"""DI-зависимости FastAPI: сессия БД, текущий пользователь, опциональная авторизация.

Используется в роутерах:

    from app.deps import CurrentUser, get_current_user, get_optional_user

    @router.get("/profile")
    async def profile(user: CurrentUser):
        return {"id": user.id}
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_db
from app.models.user import User
from app.security import (
    TelegramUser,
    parse_init_data,
    verify_token,
)

# HTTPBearer из fastapi.security — стандартный способ передать Bearer-токен.
_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class CurrentUser:
    """Текущий аутентифицированный пользователь (для FastAPI Depends)."""

    user: User
    telegram_user: TelegramUser


async def _get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    """Возвращает User из БД по telegram_id (или None если нет)."""
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def _upsert_user(session: AsyncSession, telegram_user: TelegramUser) -> User:
    """Создаёт или обновляет User из Telegram-данных.

    Вызывается при первой авторизации через initData. Имя/username могут
    меняться в Telegram — обновляем их при каждом входе.
    """
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    user = await _get_user_by_telegram_id(session, telegram_user.id)
    if user is None:
        user = User(
            telegram_id=telegram_user.id,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            username=telegram_user.username,
            language_code=telegram_user.language_code,
            last_seen_at=now,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        # Обновляем профильные поля при входе.
        if telegram_user.first_name:
            user.first_name = telegram_user.first_name
        if telegram_user.last_name is not None:
            user.last_name = telegram_user.last_name
        if telegram_user.username is not None:
            user.username = telegram_user.username
        if telegram_user.language_code:
            user.language_code = telegram_user.language_code
        user.last_seen_at = now
        await session.commit()
        await session.refresh(user)
    return user


async def _auth_by_init_data(
    session: AsyncSession,
    credentials: HTTPAuthorizationCredentials | None,
) -> User:
    """Авторизация через Telegram initData.

    credentials.scheme == "Bearer", credentials.credentials == initData.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth")

    settings = get_settings()
    init_data = credentials.credentials

    try:
        result = parse_init_data(init_data, settings.bot_token.get_secret_value())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return await _upsert_user(session, result.user)


async def _auth_by_jwt(
    session: AsyncSession,
    credentials: HTTPAuthorizationCredentials | None,
) -> User:
    """Авторизация через JWT (access token)."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth")

    try:
        telegram_id = verify_token(credentials.credentials, expected_type="access")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = await _get_user_by_telegram_id(session, telegram_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser:
    """FastAPI-зависимость: аутентифицированный пользователь.

    Поддерживает два варианта авторизации:
    1. Bearer <initData> — валидирует подпись Telegram.
    2. Bearer <JWT> — проверяет access token.

    initData принимается всегда (для Mini App). JWT — для refresh и API-вызовов
    из бота/админки.
    """
    token = credentials.credentials if credentials else ""

    # Пытаемся сначала JWT (быстрее, без HMAC), потом initData.
    if token.startswith("eyJ"):  # heuristic: JWT всегда начинается с eyJ
        user = await _auth_by_jwt(session, credentials)
        return CurrentUser(
            user=user,
            telegram_user=TelegramUser(
                id=user.telegram_id,
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
            ),
        )

    # Иначе — initData
    settings = get_settings()
    try:
        result = parse_init_data(token, settings.bot_token.get_secret_value())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = await _upsert_user(session, result.user)
    return CurrentUser(user=user, telegram_user=result.user)


async def get_optional_user(
    session: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> CurrentUser | None:
    """Опциональная авторизация: возвращает None если не авторизован.

    Полезна для эндпоинтов, которые работают без авторизации, но могут
    показывать персонализированные данные (например, корзину — если авторизован).
    """
    if credentials is None or not credentials.credentials:
        return None
    try:
        return await get_current_user(session, credentials)
    except HTTPException:
        return None
