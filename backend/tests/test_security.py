"""Тесты безопасности: валидация initData, JWT, DI-зависимости."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import urllib.parse
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.config import get_settings
from app.models.user import User
from app.security import (
    create_access_token,
    create_refresh_token,
    create_token_pair,
    parse_init_data,
    verify_token,
)

BOT_TOKEN = "123456:ABC-DEF"


def _build_init_data(
    bot_token: str,
    user: dict,
    auth_date: int | None = None,
) -> str:
    """Генерирует валидный initData для тестов (подписывает как Telegram)."""
    if auth_date is None:
        auth_date = int(time.time())

    user_str = urllib.parse.quote(json.dumps(user, separators=(",", ":")))
    query = f"user={user_str}&auth_date={auth_date}"

    # data-check string: сортируем пары
    pairs = sorted(urllib.parse.parse_qs(query, keep_blank_values=True).items())
    data_check = "\n".join(f"{k}={v[0]}" for k, v in pairs)

    secret = hashlib.sha256(bot_token.encode()).digest()
    h = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return f"{query}&hash={h}"


# ---------------------------------------------------------------------------
# parse_init_data
# ---------------------------------------------------------------------------


async def test_valid_init_data(db_session) -> None:
    """Валидный initData проходит проверку и извлекает user."""
    user_data = {"id": 1001, "first_name": "Иван", "username": "ivantea"}
    init_data = _build_init_data(BOT_TOKEN, user_data)

    result = parse_init_data(init_data, BOT_TOKEN)
    assert result.user.id == 1001
    assert result.user.first_name == "Иван"
    assert result.user.username == "ivantea"


async def test_init_data_wrong_hash_fails(db_session) -> None:
    """Поддельный hash отклоняется."""
    user_data = {"id": 1001, "first_name": "Иван"}
    init_data = _build_init_data(BOT_TOKEN, user_data) + "x"  # ломаем hash

    with pytest.raises(ValueError, match="signature"):
        parse_init_data(init_data, BOT_TOKEN)


async def test_init_data_wrong_bot_token_fails(db_session) -> None:
    """Подпись другим токеном отклоняется."""
    user_data = {"id": 1001}
    init_data = _build_init_data(BOT_TOKEN, user_data)

    with pytest.raises(ValueError, match="signature"):
        parse_init_data(init_data, "other-token")


async def test_init_data_expired_fails(db_session) -> None:
    """Протухший initData (auth_date слишком старый) отклоняется."""
    user_data = {"id": 1001}
    old_date = int(time.time()) - 999999  # очень старый
    init_data = _build_init_data(BOT_TOKEN, user_data, auth_date=old_date)

    with pytest.raises(ValueError, match="expired"):
        parse_init_data(init_data, BOT_TOKEN)


async def test_init_data_missing_user_fails(db_session) -> None:
    """initData без 'user' отклоняется."""
    auth_date = int(time.time())
    secret = hashlib.sha256(BOT_TOKEN.encode()).digest()
    data = f"auth_date={auth_date}"
    h = hmac.new(secret, data.encode(), hashlib.sha256).hexdigest()

    with pytest.raises(ValueError, match="user"):
        parse_init_data(f"auth_date={auth_date}&hash={h}", BOT_TOKEN)


async def test_init_data_missing_hash_fails(db_session) -> None:
    """initData без 'hash' отклоняется."""
    with pytest.raises(ValueError, match="hash"):
        parse_init_data("user=test&auth_date=12345", BOT_TOKEN)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------


async def test_create_and_verify_access_token(db_session) -> None:
    """Access-токен создаётся и верифицируется."""
    token = create_access_token(telegram_id=42)
    assert verify_token(token, expected_type="access") == 42


async def test_create_and_verify_refresh_token(db_session) -> None:
    """Refresh-токен создаётся и верифицируется."""
    token = create_refresh_token(telegram_id=42)
    assert verify_token(token, expected_type="refresh") == 42


async def test_token_pair(db_session) -> None:
    """create_token_pair возвращает оба токена."""
    access, refresh = create_token_pair(telegram_id=77)
    assert verify_token(access, expected_type="access") == 77
    assert verify_token(refresh, expected_type="refresh") == 77


async def test_wrong_token_type_fails(db_session) -> None:
    """Refresh-токен не принимается как access."""
    refresh = create_refresh_token(telegram_id=42)
    with pytest.raises(ValueError, match="refresh"):
        verify_token(refresh, expected_type="access")


async def test_expired_token_fails(db_session) -> None:
    """Протухший токен отклоняется."""
    # Создаём токен с ttl=0, чтобы он сразу протух.
    settings = get_settings()
    with patch.object(settings, "jwt_access_ttl_minutes", 0):
        token = create_access_token(telegram_id=42)
    with pytest.raises(ValueError):
        verify_token(token)


async def test_invalid_token_fails(db_session) -> None:
    """Случайная строка не является токеном."""
    with pytest.raises(ValueError):
        verify_token("not.a.valid.jwt")


# ---------------------------------------------------------------------------
# DI: get_current_user через API
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# API: /api/auth/refresh
# ---------------------------------------------------------------------------


async def test_auth_refresh_success(client: AsyncClient, db_session) -> None:
    """Refresh с валидным токеном и существующим user → 200 + новые токены."""
    user = User(telegram_id=5001, first_name="Тест", username="testuser")
    db_session.add(user)
    await db_session.commit()

    _access, refresh = create_token_pair(5001)
    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert "refresh_token" in body
    # Новый access-токен валиден.
    assert verify_token(body["access_token"], expected_type="access") == 5001


async def test_auth_refresh_invalid_token(client: AsyncClient) -> None:
    """Refresh с невалидным токеном → 401."""
    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": "garbage"},
    )
    assert resp.status_code == 401


async def test_auth_refresh_missing_body(client: AsyncClient) -> None:
    """Refresh без тела → 400."""
    resp = await client.post("/api/auth/refresh", json={})
    assert resp.status_code == 400


async def test_auth_refresh_missing_token_field(client: AsyncClient) -> None:
    """Refresh с полем, но без refresh_token → 400."""
    resp = await client.post(
        "/api/auth/refresh",
        json={"wrong_field": "value"},
    )
    assert resp.status_code == 400


async def test_auth_refresh_user_not_found(client: AsyncClient, db_session) -> None:
    """Refresh для несуществующего пользователя → 401."""
    _access, refresh = create_token_pair(99999)
    resp = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert resp.status_code == 401
