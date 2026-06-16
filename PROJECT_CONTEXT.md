# PROJECT_CONTEXT — журнал прогресса «Чайное Дерево»

Этот файл ведётся по мере разработки. Здесь фиксируются: текущий этап,
что готово, что дальше, принятые архитектурные решения и известные проблемы.
Цель — можно продолжить работу с любого места (в новой сессии).

Дата последнего обновления: 2026-06-16 (сессия 2)

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

1. ✅ **Скелет проекта** — commit `8182ed3`
2. ✅ **Модели БД** — 17 таблиц, seed, тесты инвариантов — commit `e1a931f`
3. ✅ **Авторизация и безопасность** — валидация initData, JWT, middleware, rate-limit, 33 теста — commit `0aaafbc`
4. ✅ **Каталог API + YML парсер + загрузка фото** — 49 тестов — commit `6a42666`
5. 🔄 **Mini App фронтенд** — `frontend/index.html` начат, не закоммичен
6. 🔄 **Заказы и личный кабинет** — роутер и тесты написаны, не закоммичены
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

## Этап 3 — АВТОРИЗАЦИЯ И БЕЗОПАСНОСТЬ (готово ✅)

- `app/security.py`: валидация Telegram initData (HMAC-SHA256), проверка auth_date, JWT access (15 мин) + refresh (30 дней)
- `app/deps.py`: DI-зависимости `CurrentUser`, `OptionalUser`, `_get_user_by_telegram_id`
- Middleware: rate-limit (slowapi), X-Request-ID
- `/api/auth/refresh` endpoint в `main.py`
- Тесты: валидный initData, replay-атака, подделка подписи, истёкший auth_date

**Git:** commit `0aaafbc`. Итого тестов: 33 passed.

---

## Этап 4 — КАТАЛОГ API + YML + ФОТО (готово ✅)

- `app/routers/catalog.py`: категории, товары, варианты, поиск, фильтрация
- `app/routers/cart.py`: корзина (get/add/update/clear)
- `app/routers/info.py`: FAQ, баннеры, ПВЗ
- YML-парсер: импорт товаров из Яндекс.Маркет YML
- Image service: загрузка фото товаров
- Все схемы в `app/schemas/`

**Git:** commit `6a42666`. Итого тестов: 49 passed.

---

## Этап 5 — ЗАКАЗЫ И ЛИЧНЫЙ КАБИНЕТ (в работе 🔄)

### Что сделано (не закоммичено):

**`app/routers/orders.py`** — роутер подключён в `main.py`:
- `GET /api/profile/me` → профиль пользователя
- `GET /api/orders` → список заказов (новые сверху)
- `GET /api/orders/{order_number}` → детали заказа
- `POST /api/orders` → создать заказ из корзины, очистить корзину

**Логика создания заказа:**
- Валидация `delivery_type` из `DELIVERY_TYPE_VALUES`
- Снапшот цен и названий в `order_items`
- Номер заказа: `ЧД-000001` (через `COUNT(*)`)
- Создаётся `delivery_info`, корзина очищается

**`backend/tests/test_orders.py`** — 10 тестов:
- `test_get_profile` — профиль авторизованного пользователя
- `test_list_orders_empty` — пустой список заказов
- `test_create_order` — создание заказа, проверка снапшота и итоговой суммы
- `test_create_order_clears_cart` — корзина пуста после заказа
- `test_create_order_empty_cart` — 400 при пустой корзине
- `test_create_order_invalid_delivery_type` — 400 при невалидном типе доставки
- `test_get_order_detail` — детали по номеру заказа
- `test_get_order_not_found` — 404 для несуществующего заказа
- `test_unauthorized_orders` — 401 без токена

**С чего начать новую сессию:**
1. Запустить тесты: `cd backend && pytest tests/test_orders.py -v`
2. Если все зелёные — закоммитить этап 5
3. Перейти к фронтенду (`frontend/index.html`) или этапу 6 (платежи)
