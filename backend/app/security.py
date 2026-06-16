"""Безопасность: валидация Telegram initData и JWT-токены.

1. Telegram Mini App аутентификация:
   - Фронтенд получает `window.Telegram.WebApp.initData` (query-string).
   - Шлёт в API в заголовке `Authorization: Bearer <initData>` или `X-Telegram-Init-Data`.
   - Бэкенд валидирует HMAC-SHA256 подпись по `bot_token`.
   - Проверяет `auth_date` на свежесть (защита от replay).
   - Извлекает user payload (id, name, username).

2. JWT:
   - После успешной валидации initData выдаём access JWT (15 мин).
   - Refresh JWT (30 дней) для продления сессии без повторной initData.
   - JWT содержит: sub=telegram_id, exp, type (access/refresh).

Секреты (bot_token, jwt_secret) берутся из Settings и никогда не логируются.
"""

from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt as pyjwt
from jwt.exceptions import InvalidTokenError

from app.config import get_settings
from app.logging import get_logger

log = get_logger("app.security")


# ---------------------------------------------------------------------------
# Telegram initData
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TelegramUser:
    """Извлечённые данные пользователя из Telegram initData."""

    id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


@dataclass(frozen=True, slots=True)
class InitDataResult:
    """Результат валидации initData."""

    user: TelegramUser
    auth_date: int


def parse_init_data(init_data: str, bot_token: str) -> InitDataResult:
    """Валидирует подпись Telegram initData и извлекает user.

    Алгоритм (из документации Telegram):
    1. initData — это query-string: key=value&key=value&hash=...
    2. Убираем hash из пар.
    3. Сортируем пары по ключу, склеиваем в "key1=value1\nkey2=value2\n..."
    4. HMAC-SHA256(secret_key=SHA256(bot_token), message=data_check_string).
    5. HEX(hmac) == hash → подпись валидна.
    6. auth_date — unix timestamp, проверяем свежесть.

    Raises:
        ValueError: подпись невалидна, auth_date отсутствует или протух.
    """
    settings = get_settings()

    # Разбираем query-string
    try:
        parsed = urllib.parse.parse_qs(init_data, keep_blank_values=True)
    except Exception as exc:
        raise ValueError(f"Invalid initData format: {exc}") from exc

    hash_value = parsed.get("hash", [None])[0]
    if not hash_value:
        raise ValueError("Missing 'hash' in initData")

    auth_date_raw = parsed.get("auth_date", [None])[0]
    if not auth_date_raw:
        raise ValueError("Missing 'auth_date' in initData")

    auth_date = int(auth_date_raw)

    # Проверяем свежесть (защита от replay)
    now = int(time.time())
    max_age = settings.telegram_initdata_max_age_seconds
    if now - auth_date > max_age:
        log.warning("initData expired", auth_date=auth_date, now=now, max_age=max_age)
        raise ValueError("initData expired")

    # Формируем data-check string: сортируем пары (кроме hash) по ключу
    pairs = sorted((k, v) for k, vals in parsed.items() for v in vals if k != "hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in pairs)

    # HMAC-SHA256 (Mini App: ключ = HMAC("WebAppData", bot_token))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, hash_value):
        log.warning("initData signature mismatch")
        raise ValueError("Invalid initData signature")

    # Извлекаем user payload
    user_raw = parsed.get("user", [None])[0]
    if not user_raw:
        raise ValueError("Missing 'user' in initData")

    # user_raw — это URL-encoded JSON (т.к. был в query-string)
    user_str = urllib.parse.unquote(user_raw)
    try:
        import json

        user_dict = json.loads(user_str)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Invalid user payload: {exc}") from exc

    user = TelegramUser(
        id=int(user_dict.get("id", 0)),
        first_name=user_dict.get("first_name"),
        last_name=user_dict.get("last_name"),
        username=user_dict.get("username"),
        language_code=user_dict.get("language_code"),
    )

    log.info("initData validated", user_id=user.id)
    return InitDataResult(user=user, auth_date=auth_date)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


def create_access_token(telegram_id: int) -> str:
    """Создаёт access JWT (короткоживущий)."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(telegram_id),
        "type": "access",
        "exp": now + timedelta(minutes=settings.jwt_access_ttl_minutes),
        "iat": now,
    }
    return pyjwt.encode(
        payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def create_refresh_token(telegram_id: int) -> str:
    """Создаёт refresh JWT (долгоживущий)."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(telegram_id),
        "type": "refresh",
        "exp": now + timedelta(days=settings.jwt_refresh_ttl_days),
        "iat": now,
    }
    return pyjwt.encode(
        payload, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def verify_token(token: str, expected_type: str = "access") -> int:
    """Проверяет JWT и возвращает telegram_id.

    Raises:
        ValueError: токен невалиден, протух или не того типа.
    """
    settings = get_settings()
    try:
        payload = pyjwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError as exc:
        log.warning("JWT verification failed", reason=str(exc))
        raise ValueError(f"Invalid token: {exc}") from exc

    if payload.get("type") != expected_type:
        raise ValueError(f"Expected '{expected_type}' token, got '{payload.get('type')}'")

    try:
        return int(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Invalid token subject: {exc}") from exc


def create_token_pair(telegram_id: int) -> tuple[str, str]:
    """Возвращает (access_token, refresh_token)."""
    return create_access_token(telegram_id), create_refresh_token(telegram_id)
