"""Async-движок SQLAlchemy и фабрика сессий.

Все операции с БД идут через асинхронные сессии (asyncpg под капотом).
Никаких синхронных коннектов в проекте не используем.

Движок создаётся лениво (через _ensure_engine), чтобы импорт модуля в
синхронном контексте (alembic env.py) не пытался сразу строить async-движок
и не падал с MissingGreenlet.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

# Единая конвенция именований для constraint'ов — важна для консистентных
# миграций и автогенерации alembic.
NAMING_CONVENTION: dict[str, Any] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей.

    metadata с фиксированной naming convention — для консистентных миграций.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _build_engine(database_url: str) -> AsyncEngine:
    """Создаёт async-движок с параметрами пула из настроек.

    Для SQLite (тесты) параметры пула Postgres неприменимы — учитываем это.
    """
    settings = get_settings()
    is_sqlite = database_url.startswith("sqlite")
    kwargs: dict[str, Any] = {
        "echo": False,
        "future": True,
        "pool_pre_ping": True,  # проверка соединения перед использованием
    }
    if not is_sqlite:
        kwargs["pool_size"] = settings.db_pool_size
        kwargs["max_overflow"] = settings.db_max_overflow
        kwargs["pool_timeout"] = settings.db_pool_timeout
        kwargs["pool_recycle"] = settings.db_pool_recycle
    else:
        # SQLite: enforcement foreign keys включаем слушателем ниже (каскады
        # иначе игнорируются). check_same_thread — для тестов/asyncio.
        kwargs["connect_args"] = {"check_same_thread": False}
    eng = create_async_engine(database_url, **kwargs)
    if is_sqlite:
        from sqlalchemy import event as _event

        @_event.listens_for(eng.sync_engine, "connect")
        def _enable_fk(dbapi_conn, _record):  # pragma: no cover
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return eng


# Лениво инициализируемые движок и фабрика сессий.
# Сначала — None; создаются при первом обращении (или при прямом вызове
# configure_engine в тестах/старте приложения).
engine: AsyncEngine | None = None
SessionLocal: async_sessionmaker[AsyncSession] | None = None


def configure_engine(database_url: str | None = None) -> None:
    """Инициализирует (или переинициализирует) движок и фабрику сессий.

    Вызывается при старте приложения (lifespan) и в тестах. Без вызова
    `engine`/`SessionLocal` остаются None — это защита от случайного
    использования БД без настройки.
    """
    global engine, SessionLocal
    url = database_url or get_settings().database_url
    engine = _build_engine(url)
    SessionLocal = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        autoflush=False,
        class_=AsyncSession,
    )


def _ensure() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Возвращает (engine, SessionLocal), инициализируя при первом вызове."""
    if engine is None or SessionLocal is None:
        configure_engine()
    assert engine is not None and SessionLocal is not None
    return engine, SessionLocal


def get_engine() -> AsyncEngine:
    return _ensure()[0]


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return _ensure()[1]


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI-dependency: отдаёт сессию и гарантированно закрывает её."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """Корректно закрыть все соединения (используется при shutdown)."""
    global engine, SessionLocal
    if engine is not None:
        await engine.dispose()
    engine = None
    SessionLocal = None
