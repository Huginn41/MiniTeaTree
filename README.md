# 🍵 Чайное Дерево — Telegram Mini App

Backend для Telegram Mini App магазина чая: каталог, корзина, заказы,
оплата (Telegram Payments / ЮKassa), личный кабинет, админка/CRM (SQLAdmin),
бот с уведомлениями.

> **Статус:** в разработке и деплое. Текущий прогресс — см. [`PROJECT_CONTEXT.md`](./PROJECT_CONTEXT.md).

## Демо

| | |
|---|---|
| 🤖 Telegram-бот | [@teatree96_bot](https://t.me/teatree96_bot) |
| 🛍 Mini App | открывается кнопкой в боте |
| 🔧 Админ-панель | [чайноедерево.рф/admin](https://чайноедерево.рф/admin) |

Для просмотра Mini App — написать боту `/start` и нажать кнопку «Открыть магазин».

## Стек

| Слой | Технология |
|------|-----------|
| Backend API | FastAPI + uvicorn |
| ORM / БД | SQLAlchemy 2 (async) + asyncpg + PostgreSQL 16 |
| Миграции | Alembic |
| Бот | aiogram 3.x |
| Авторизация | валидация Telegram `initData` + JWT |
| Платежи | Telegram Payments (ЮKassa) |
| Админка/CRM | SQLAdmin |
| Frontend Mini App | ванильный JS + Tailwind |
| Инфраструктура | Docker Compose (FastAPI + Postgres + Nginx) |

## Быстрый старт (локально)

```bash
# 1. Зависимости
cp .env.example .env       # отредактируйте секреты
make install               # uv sync (в backend/)

# 2. Вариант A — docker dev (рекомендуется)
make dev                   # поднимет db + app с хот-релоадом

# 2. Вариант B — без docker (нужен локальный Postgres)
make migrate               # применить миграции
uv run --directory backend uvicorn app.main:app --reload

# 3. Проверка
curl http://localhost:8000/health        # {"status":"ok",...}
open http://localhost:8000/api/docs      # Swagger UI (не в prod)
```

## Команды (Make)

```bash
make help         # список всех команд
make dev          # docker dev-окружение
make up           # docker prod-окружение
make down         # остановить контейнеры
make logs         # логи (tail -f)
make migrate      # alembic upgrade head
make migrate-new m="описание"   # новая миграция
make seed         # демо-данные
make test         # pytest
make test-cov     # pytest + покрытие
make lint         # ruff check
make format       # ruff format + check --fix
```

## Структура проекта

```
miniteatree/
├── backend/          # FastAPI + бот + админка
│   ├── app/
│   ├── alembic/      # миграции
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── miniapp/          # фронтенд Mini App (JS + Tailwind)
├── nginx/            # reverse proxy + TLS
├── docker-compose.yml
├── .env.example
├── Makefile
├── PROJECT_CONTEXT.md  # журнал прогресса
└── README.md
```

## Безопасность

- Секреты — только в `.env` (в `.gitignore`), шаблон в `.env.example`.
- Авторизация Mini App — через криптографическую проверку подписи `initData`.
- Пароли — bcrypt, JWT с коротким TTL.
- SQL только через ORM (параметризованные запросы).
- Валидация всех входов через Pydantic.
- CORS ограничен доменом Mini App.
- Проверка подписи webhook ЮKassa.
- Маскировка секретов в логах (structlog).
- Rate-limiting на публичных эндпоинтах.

## Лицензия

Собственность владельца проекта.
