# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Telegram Mini App чайный магазин «Чайное Дерево». Текущий прогресс — в `PROJECT_CONTEXT.md`.

## Commands

Все команды выполняются через `uv run` из директории `backend/`. Используй `make` для краткости.

```bash
# Зависимости
cd backend && uv sync

# Тесты
make test                          # все тесты
cd backend && uv run python -m pytest tests/test_orders.py -v   # один файл
cd backend && uv run python -m pytest tests/test_orders.py::test_create_order -v  # один тест
make test-cov                      # с покрытием

# Линтинг и форматирование
make lint
make format

# Docker
make dev     # dev-окружение с hot-reload
make up      # prod-образы
make down

# Миграции
make migrate                       # upgrade head
make migrate-new m="описание"      # создать новую миграцию
make seed                          # залить демо-данные

# Локальный сервер (без docker)
cd backend && uv run uvicorn app.main:app --reload
```

## Architecture

### Backend (`backend/app/`)

**Entry point:** `main.py` → `create_app()` (factory). Все роутеры регистрируются через `_register_routers()` под префиксом `/api`. Lifespan вызывает `configure_engine()` при старте.

**Слои:**
- `models/` — SQLAlchemy ORM (17 таблиц). `Base` из `db.py` с naming convention для миграций.
- `schemas/__init__.py` — все Pydantic-схемы в одном файле.
- `routers/` — FastAPI-роутеры (catalog, cart, info, orders). Каждый подключается в `_register_routers`.
- `deps.py` — DI-зависимости. Главное: `get_current_user` → `CurrentUser` (dataclass с `user: User` и `telegram_user: TelegramUser`).
- `security.py` — валидация Telegram initData (HMAC-SHA256) и JWT (access 15 мин, refresh 30 дней).
- `db.py` — ленивый async-движок. **Движок не создаётся при импорте** — только через `configure_engine()`.
- `config.py` — `get_settings()` (lru_cache). В `APP_ENV=test` не читает `.env`.

**Авторизация:** два пути в `get_current_user`:
1. Bearer `eyJ...` → JWT (`verify_token`)
2. Bearer `<initData>` → Telegram HMAC (`parse_init_data`) + upsert пользователя в БД

**Миграции:** `alembic/`. Используют синхронный URL (`asyncpg` → `psycopg`). Автогенерация работает через `Base.metadata`.

### Тесты (`backend/tests/`)

- Все тесты на **in-memory SQLite** (`aiosqlite`), без внешних зависимостей.
- `conftest.py`: фикстуры `db_session` (сессия) и `client` (`AsyncClient` через `ASGITransport`).
- `autouse` фикстура `_prepare_db` пересоздаёт схему перед каждым тестом.
- ENV-переменные выставляются **жёстко** в начале `conftest.py` до импорта `app.*`.
- `asyncio_mode = "auto"` — все тесты `async def` без декоратора.

### Модели

`PKType` = `BigInteger().with_variant(Integer, "sqlite")` — для autoincrement в SQLite.
Enum'ы: `StrEnum`/`IntEnum` в коде, `String + CHECK` в БД (не нативный PG ENUM).
Каскады: ORM-level (`cascade="all, delete-orphan"`) + DB-level (`ondelete="CASCADE"`).

### Ключевые enum-значения

`DELIVERY_TYPE_VALUES`, `PAYMENT_STATUS_VALUES` и другие — из `app/models/enums.py`. Проверяй валидацию роутера через эти константы, не хардкодь строки.

### Frontend (`frontend/`)

Ванильный JS + Tailwind. Точка входа: `frontend/index.html`. Пока в начальной стадии.

### Инфраструктура

- `docker-compose.yml` — prod. `docker-compose.dev.yml` — dev (hot-reload, без nginx по умолчанию).
- Nginx: TLS termination + статика; включается через `--profile nginx` в dev.
- API-документация доступна на `/api/docs` только в не-prod окружении.
