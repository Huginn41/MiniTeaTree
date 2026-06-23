"""Тесты конфигурации приложения (Settings).

Тесты изолированы от переменных окружения, которые conftest выставляет
для других тестов (APP_ENV=test, DEBUG=true), через monkeypatch.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_parses_admin_telegram_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """Список админов парсится из строки через запятую; мусор игнорируется."""
    monkeypatch.delenv("APP_ENV", raising=False)
    s = Settings(
        app_env="production",
        admin_telegram_ids="111, 222 , 333,bad,",
        jwt_secret="x" * 32,
    )
    assert s.admin_telegram_id_list == [111, 222, 333]


def test_cors_origin_list_splits_and_trims() -> None:
    s = Settings(
        cors_origins="https://a.com , https://b.com,, ",
        jwt_secret="x" * 32,
    )
    assert s.cors_origin_list == ["https://a.com", "https://b.com"]


def test_jwt_secret_must_be_long_enough() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret="short")


def test_defaults_are_safe_for_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    """Дефолты не должны включать debug-режим и лишние привилегии."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEBUG", "false")
    s = Settings(jwt_secret="x" * 32)
    assert s.debug is False
    assert s.is_production is True
    assert s.is_test is False
    assert s.max_upload_bytes == 5 * 1024 * 1024


def test_helpers_for_env_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    s = Settings(jwt_secret="x" * 32)
    assert s.is_test is True
    assert s.is_production is False
