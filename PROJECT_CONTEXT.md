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

---

## Принятые архитектурные решения

1. **Движок БД ленивый.** `app.db` не создаёт async-engine на верхнем уровне
   импорта — иначе синхронный alembic падает. Используем `configure_engine()`
   в `lifespan` и в тестах. Геттеры: `get_engine()`, `get_session_factory()`.
2. **Тесты на in-memory SQLite** (`aiosqlite`). Модели совместимы с обеими СУБД.
   SQLite: FK enforcement включён через event listener, PKType использует
   `BigInteger().with_variant(Integer, "sqlite")` для autoincrement.
3. **В `APP_ENV=test` Settings не читает `.env`** (`env_file=None`), чтобы
   реальный `.env` не влиял на тесты. Тестовые env фиксируются в conftest.
4. **Alembic использует синхронный URL:** `postgresql+asyncpg://` →
   `postgresql+psycopg://`, `sqlite+aiosqlite://` → `sqlite://`. В deps есть
   `psycopg[binary]`.
5. **Enum'ы:** `StrEnum` / `IntEnum` (Python 3.12+), в БД — `String` + CHECK.
   Не нативный PG ENUM (гибче для миграций и совместимы с SQLite).
6. **Каскады:** ORM-level (`cascade="all, delete-orphan"`) + DB-level
   (`ondelete="CASCADE"`). Работает на обеих СУБД благодаря FK enforcement.
7. **Безопасность:** секреты в `.env`, пароли через bcrypt, CORS ограничен,
   rate-limit (slowapi), валидация через Pydantic, structlog маскирует секреты.
8. **Nginx:** TLS termination + статика; в dev — `--profile nginx`.

---

## План реализации по этапам

1. ✅ **Скелет проекта**
2. ✅ **Модели БД** — 17 таблиц, seed, тесты инвариантов
3. ⬜ **Авторизация и безопасность** — валидация initData, JWT, middleware, rate-limit
4. ⬜ **Каталог API + YML парсер + загрузка фото**
5. ⬜ **Mini App фронтенд**
6. ⬜ **Заказы и личный кабинет**
7. ⬜ **Платежи** — Telegram Payments + ЮKassa webhook
8. ⬜ **Бот aiogram**
9. ⬜ **Админка/CRM (SQLAdmin)**
10. ⬜ **Уведомления о смене статуса**
11. ⬜ **Документация** — DEPLOY.md

---

## Этап 2 — МОДЕЛИ БД (готово ✅)

**Модели (17 таблиц):**
- `users` (Telegram auth, профиль)
- `admin_users` (SQLAdmin login/password, bcrypt)
- `categories` (фильтр каталога, slug, sort)
- `products` (товар, slug, description, base_price, tags)
- `product_variants` (граммовки 25/50/75/100 г, цена, SKU, unique product+weight)
- `product_images` (фото на сервере, is_main, sort, cascade delete)
- `banners` (слайдер: image_path, title, link, sort)
- `carts` (1 на user) + `cart_items` (variant + qty, unique cart+variant)
- `orders` (number, total, status_payment, status_delivery, CHECK constraints)
- `order_items` (снапшот: unit_price, snapshot_name, snapshot_weight_g)
- `delivery_info` (type, address, ym_payment_link — ссылка от менеджера)
- `pickup_points` (адреса ПВЗ/самовывоза, lat/lon для карты)
- `faq_items` (вопрос-ответ)
- `notification_targets` (кому слать уведомления в ТГ, role CHECK)
- `payment_events` (аудит платежей: provider, external_id, raw_payload)
- `yml_imports` (журнал импортов: source, status, counters)
- `enums.py` (StrEnum для статусов, типов, IntEnum для весов)

**Seed (`app/seed.py`):** 7 категорий, 11 товаров с 4 вариантами каждый (44 variant),
3 баннера, 4 FAQ, 1 ПВЗ, админ-пользователь, notification target.

**Тесты (9 модельных):** уникальность telegram_id, уникальность variant weight,
разные веса ок, 1 корзина на user, дефолтные статусы заказа, снапшот цены, CASCADE delete,
valid role CHECK. Итого: 16 passed.

**Git:** commit `e1a931f`.

---

## Этап 3 — АВТОРИЗАЦИЯ И БЕЗОПАСНОСТЬ (далее)

Реализовать:
- `app/security.py`: валидация Telegram initData (HMAC-SHA256), проверка auth_date
- `app/deps.py`: DI-зависимости — текущий пользователь из JWT, опциональный
- JWT: access (15 мин) + refresh (30 дней), создание/верификация
- Middleware: rate-limit (slowapi), request ID
- Middleware: подстановка пользователя в contextvars (для логов/аудита)
- Тесты: валидный initData, replay-атака, подделка подписи, истёкший auth_date

**С чего начать новую сессию:** прочитать `app/security.py` (не существует), создать
его с `validate_telegram_init_data()`, затем JWT-утилиты и DI-зависимости.
