# PROJECT_CONTEXT — журнал прогресса «Чайное Дерево»

Этот файл ведётся по мере разработки. Здесь фиксируются: текущий этап,
что готово, что дальше, принятые архитектурные решения и известные проблемы.
Цель — можно продолжить работу с любого места (в новой сессии).

Дата последнего обновления: 2026-06-16

---

## Краткая справка по проекту

Telegram Mini App магазин чая «Чайное Дерево».

**Стек:** FastAPI + async SQLAlchemy (asyncpg) + PostgreSQL 16 + aiogram 3.x
+ ванильный JS/Tailwind для Mini App + SQLAdmin для админки/CRM + Docker Compose.

**Платежи:** Telegram Payments через ЮKassa (только товары). Доставка
обсуждается менеджером отдельно (он присылает ссылку на оплату доставки).
Поэтому в заказе два независимых статуса: оплаты и доставки.

**Подробный план:** см. раздел «План реализации по этапам» ниже.

---

## Принятые архитектурные решения

1. **Движок БД ленивый.** `app.db` не создаёт async-engine на верхнем уровне
   импорта — иначе синхронный alembic падает с `MissingGreenlet`. Используем
   `configure_engine()` в `lifespan` и в тестах. Геттеры: `get_engine()`,
   `get_session_factory()`.
2. **Тесты на in-memory SQLite** (`aiosqlite`). Модели пишем совместимые с
   Postgres и SQLite. Интеграционные тесты на реальном Postgres — позже.
3. **В `APP_ENV=test` Settings не читает `.env`** (`env_file=None`), чтобы
   реальный `.env` не влиял на тесты. Тестовые env фиксируются в conftest.
4. **Alembic использует синхронный URL:** `postgresql+asyncpg://` →
   `postgresql+psycopg://`, `sqlite+aiosqlite://` → `sqlite://` (см.
   `alembic/env.py::_sync_url`). Поэтому в deps есть `psycopg[binary]`.
5. **Безопасность:** секреты только в `.env` (в `.gitignore`), пароли через
   bcrypt, CORS ограничен, rate-limit (slowapi) — на этапе 3, валидация всех
   входов через Pydantic, structured logging с маскировкой секретов.
6. **Nginx** терминирует TLS и раздаёт статику; в dev поднимается опционально
   через `--profile nginx`, бэкенд ходит напрямую на :8000.

---

## План реализации по этапам

1. ✅ **Скелет проекта** — репозиторий, Docker, FastAPI, async PostgreSQL,
   Alembic, конфиг, healthcheck, базовые тесты.
2. ⬜ **Модели БД** — все таблицы, миграции, демо-данные.
3. ⬜ **Авторизация и безопасность** — валидация initData, JWT, middleware,
   rate-limit, тесты.
4. ⬜ **Каталог API + YML парсер + загрузка фото** — эндпоинты, парсер, тесты.
5. ⬜ **Mini App фронтенд** — главная, каталог, карточка, корзина, профиль, info.
6. ⬜ **Заказы и личный кабинет** — оформление, история, статусы, тесты.
7. ⬜ **Платежи** — Telegram Payments + ЮKassa webhook + тесты.
8. ⬜ **Бот aiogram** — кнопка Mini App, уведомления, кнопка для канала.
9. ⬜ **Админка/CRM (SQLAdmin)** + кастомные вьюхи + YML импорт.
10. ⬜ **Уведомления о смене статуса** → пользователю и менеджерам.
11. ⬜ **Документация** — README, DEPLOY.md, обновление этого файла.

---

## Этап 1 — СКЕЛЕТ (готово ✅)

**Создано:**
- Корневые файлы: `.gitignore`, `.env.example`, `Makefile`,
  `docker-compose.yml`, `docker-compose.dev.yml`.
- `backend/pyproject.toml` (uv, все зависимости включая dev),
  `backend/Dockerfile` (multi-stage: builder + prod + dev),
  `backend/.dockerignore`.
- `backend/app/`: `__init__.py`, `config.py` (pydantic-settings),
  `db.py` (async SQLAlchemy, lazy engine), `logging.py` (structlog + маскировка
  секретов), `main.py` (FastAPI: lifespan, CORS, health/health-ready, error
  handler, каркас роутеров под /api).
- `backend/app/models/__init__.py` — пакет моделей (пока пустой, на этапе 2).
- Пустые пакеты: `schemas`, `routers`, `services`, `bot`, `admin`, `admin/views`.
- `backend/alembic/`: `env.py` (sync URL-преобразование, autogenerate),
  `script.py.mako`, `alembic.ini`.
- `backend/tests/`: `conftest.py` (in-memory SQLite, фикстуры client/db_session),
  `test_meta.py` (healthcheck), `test_config.py` (Settings).
- Структура директорий `miniapp/`, `nginx/`, `scripts/`, `docs/` + gitkeep.

**Проверки (зелёные):**
- `ruff check app tests` → All checks passed.
- `ruff format --check app tests` → 16 files already formatted.
- `pytest -q` → 7 passed.
- `docker compose config --quiet` → валиден.
- `alembic current` (на sqlite) → контекст создаётся (миграций пока нет).

**Команды (через Make):**
- `make install` — `uv sync` зависимостей.
- `make dev` — поднять docker dev-окружение с хот-релоадом.
- `make test` / `make test-cov` — тесты.
- `make lint` / `make format` — ruff.
- `make migrate` / `make migrate-new m="..."` — alembic.

---

## Этап 2 — МОДЕЛИ БД (далее)

Создать все ORM-модели из плана (§4): users, categories, products,
product_variants, product_images, banners, carts/cart_items, orders/order_items,
delivery_info, pickup_points, faq_items, payment_events, yml_imports,
notification_targets, admin_users.

Затем:
- автогенерировать первую миграцию (`make migrate-new m="initial schema"`),
- написать `app/seed.py` для демо-данных (каталог чаёв, баннеры, FAQ),
- тесты на инварианты моделей (уникальность, default'ы, связи).

**С чего начать новую сессию:** прочитать этот файл + план §4, реализовать
модели в `backend/app/models/`, подключить их в `models/__init__.py`.
