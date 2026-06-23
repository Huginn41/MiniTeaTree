"""Общие фикстуры pytest.

Стратегия тестов:
- Юнит- и API-тесты идут на in-memory SQLite (быстро, без внешних зависимостей).
  SQLAlchemy-модели пишем так, чтобы работали и на Postgres, и на SQLite.
- Интеграционные тесты с реальным Postgres (через testcontainers) добавим позже
  для проверки Postgres-специфики (JSONB, enum и т.д.).
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

# Тестовые env выставляем ДО импорта app.* ЖЁСТКО (не setdefault), чтобы
# реальный .env из корня проекта не мог повлиять на тесты.
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-that-is-at-least-32-chars-long"
os.environ["BOT_TOKEN"] = "0:fake"
os.environ["DEBUG"] = "true"
os.environ["CORS_ORIGINS"] = ""

from app.config import get_settings

get_settings.cache_clear()
_settings = get_settings()

from app.db import (  # noqa: E402
    Base,
    configure_engine,
    get_engine,
    get_session_factory,
)

# Инициализируем движок для тестов (in-memory SQLite).
configure_engine(_settings.database_url)


@pytest.fixture(scope="session")
def event_loop():
    """Один event loop на всю сессию тестов (для asyncio_mode=auto)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def _prepare_db() -> AsyncIterator[None]:
    """Перед каждым тестом создаём чистую схему БД (in-memory SQLite).

    autouse=True гарантирует, что тесты не зависят от порядка выполнения.
    """
    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncIterator:
    """Свежая сессия БД для тестов сервисов/репозиториев."""
    async with get_session_factory()() as session:
        yield session


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """HTTP-клиент к FastAPI приложению (без запуска сервера)."""
    from app.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
