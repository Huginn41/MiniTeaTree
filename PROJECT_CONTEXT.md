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
5. ✅ **Mini App фронтенд** — commit `7712265`
6. ✅ **Заказы и личный кабинет** — 9 тестов — commit `f0bc8db`
7. ⬜ **Платежи** — Telegram Payments + ЮKassa webhook
8. ⬜ **Бот aiogram**
9. ✅ **Админка/CRM (SQLAdmin)** — commit `289ad2e`
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

## Этап 5 — ЗАКАЗЫ И ЛИЧНЫЙ КАБИНЕТ (готово ✅)

**`app/routers/orders.py`** — роутер подключён в `main.py`:
- `GET /api/profile/me` → профиль пользователя
- `GET /api/orders` → список заказов (новые сверху)
- `GET /api/orders/{order_number}` → детали заказа
- `POST /api/orders` → создать заказ из корзины, очистить корзину

Логика: валидация `delivery_type`, снапшот цен, номер `ЧД-000001` через `COUNT(*)`.

**Git:** commit `f0bc8db`. Тестов: 9 passed (итого 58).

---

## Этап 5 (фронт) — MINI APP ФРОНТЕНД (готово ✅)

**`frontend/index.html`** — Single-page Mini App на ванильном JS + Tailwind CDN:
- Авторизация через Telegram initData (Mini App) или JWT из localStorage (dev)
- Главная: баннеры + категории + популярные товары
- Каталог: фильтрация по категориям, карточки товаров
- Страница товара: галерея, описание, варианты, добавление в корзину
- Корзина: управление количеством, удаление, переход к оформлению
- Форма оформления (`checkout`): самовывоз / курьер, адрес, телефон, комментарий
- Детали заказа (`order-detail`): статусы, состав, сумма
- Профиль: данные Telegram + список заказов

**Git:** commit `7712265`.

---

## Этап 9 — АДМИНКА/CRM SQLAdmin (готово ✅)

**`app/admin/__init__.py`** — `setup_admin()` вызывается в lifespan:
- Маршрут: `/admin`
- Авторизация: `AdminUser` (bcrypt) или `admin_username`/`admin_password` из `.env`
- `SessionMiddleware` добавлена в `main.py` (secret_key из `jwt_secret`)

**15 представлений** (3 раздела):
- Каталог: Category, Product, ProductVariant, ProductImage, Banner
- Заказы: Order (только статусы + delivery_cost), OrderItem (read-only), DeliveryInfo (ссылка менеджера)
- CRM: User (только phone/is_admin), FaqItem, PickupPoint, NotificationTarget
- Система: AdminUser, YmlImport (read-only), PaymentEvent (read-only)

**Git:** commit `289ad2e`.

---

## Что дальше

**С чего начать новую сессию:**
- **Этап 7: Платежи** — `POST /api/payments/create-invoice` (Telegram Payments + ЮKassa), webhook `POST /api/payments/webhook`, обновление `status_payment` заказа.
- **Этап 8: Бот aiogram** — уведомление магазина о новом заказе, кнопка «Оформить» → Mini App.
- **Этап 10: Уведомления** — отправка клиенту при смене `status_delivery`.
- **Этап 11: DEPLOY.md** — инструкция по деплою на VPS.
