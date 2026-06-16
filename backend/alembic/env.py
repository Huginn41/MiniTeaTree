"""Alembic environment.

Использует СИНХРОННЫЙ URL для миграций (alembic работает синхронно):
преобразует postgresql+asyncpg:// → postgresql+psycopg:// автоматически.
Для SQLite (тесты) оставляем как есть.

ВАЖНО: импортируем app.models, чтобы autogenerate «видел» все таблицы.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.db import Base

# Импорт всех моделей, чтобы они зарегистрировались в метаданных Base.
# По мере добавления моделей — добавляем сюда (или используем пакет models/__init__).
import app.models  # noqa: F401, E402  (см. app/models/__init__.py)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()


def _sync_url(url: str) -> str:
    """Преобразует async-URL в синхронный для alembic.

    alembic работает синхронно, поэтому asyncpg/aiosqlite не подходят:
      postgresql+asyncpg://  → postgresql+psycopg://
      sqlite+aiosqlite://    → sqlite://
    """
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if url.startswith("sqlite+aiosqlite://"):
        return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return url


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (генерация SQL без подключения)."""
    url = _sync_url(settings.database_url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (с подключением к БД)."""
    url = _sync_url(settings.database_url)
    config.set_main_option("sqlalchemy.url", url)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
