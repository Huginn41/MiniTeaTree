"""Демо-наполнение: 15 товаров, 8 клиентов, ~60 заказов за 90 дней.

Полностью изолировано от основного seed.py — предназначено для демо-среды
(docker-compose.demo.yml с отдельной БД). Идемпотентно.

Запуск:
    cd backend && uv run python -m app.demo_seed
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt_lib
from sqlalchemy import select

from app.db import Base, configure_engine, get_engine, get_session_factory
from app.models import (
    AdminUser,
    Banner,
    Category,
    FaqItem,
    PickupPoint,
    Product,
    ProductImage,
    ProductVariant,
)

# Фиксированный seed — чтобы каждый запуск давал одинаковые данные
_rng = random.Random(42)

# ---------------------------------------------------------------------------
# Каталог
# ---------------------------------------------------------------------------

_CATEGORIES = [
    {"name": "Зелёный чай",   "slug": "green",     "icon": "🍃", "sort_order": 1},
    {"name": "Чёрный чай",    "slug": "black",      "icon": "🫖", "sort_order": 2},
    {"name": "Улун",          "slug": "oolong",     "icon": "🍵", "sort_order": 3},
    {"name": "Пуэр",          "slug": "puerh",      "icon": "🏔",  "sort_order": 4},
    {"name": "Белый чай",     "slug": "white",      "icon": "🤍", "sort_order": 5},
    {"name": "Травяные сборы","slug": "herbal",     "icon": "🌿", "sort_order": 6},
    {"name": "Чайные наборы", "slug": "gift-sets",  "icon": "🎁", "sort_order": 7},
]

# is_unit=False — весовой (варианты 25/50/75/100 г)
# is_unit=True  — штучный (один вариант weight_g=0)
_PRODUCTS = [
    # ── Зелёный ──────────────────────────────────────────────────────
    {
        "name": "Сенча premiers cru",
        "slug": "sencha-premier",
        "category_slug": "green",
        "description": "Японский зелёный чай высшего сорта. Свежий травянистый вкус с нотами умами. "
                       "Обладает мощным антиоксидантным действием. Сбор апрель 2026.",
        "origin": "Япония, префектура Сидзуока",
        "tags": "японский,умами,антиоксидант",
        "base_price": 8,
        "emoji": "🍃",
        "variants": {25: 200, 50: 380, 75: 540, 100: 680},
    },
    {
        "name": "Лунцзин «Колодец Дракона»",
        "slug": "longjing-dragon-well",
        "category_slug": "green",
        "description": "Один из Десяти Великих Чаёв Китая. Жареный каштановый аромат, нежное сладкое "
                       "послевкусие. Плоские листья характерной формы.",
        "origin": "Китай, провинция Чжэцзян",
        "tags": "китайский,каштановый,поджаренный",
        "base_price": 10,
        "emoji": "🫧",
        "variants": {25: 250, 50: 470, 75: 660, 100: 840},
    },
    {
        "name": "Жасминовый жемчуг",
        "slug": "jasmine-pearl",
        "category_slug": "green",
        "description": "Зелёный чай, скрученный в жемчужины и ароматизированный свежим жасмином. "
                       "Нежный цветочный аромат, мягкий сладковатый вкус.",
        "origin": "Китай, провинция Фуцзянь",
        "tags": "жасмин,цветочный,нежный",
        "base_price": 9,
        "emoji": "🌸",
        "variants": {25: 225, 50: 420, 75: 590, 100: 740},
    },
    # ── Чёрный ───────────────────────────────────────────────────────
    {
        "name": "Ассам TGFOP",
        "slug": "assam-tgfop",
        "category_slug": "black",
        "description": "Классический индийский чёрный чай. Насыщенный солодовый вкус с лёгкой "
                       "терпкостью. Отличная основа для масала-чая.",
        "origin": "Индия, Ассам",
        "tags": "индийский,солодовый,крепкий",
        "base_price": 5,
        "emoji": "🫖",
        "variants": {25: 125, 50: 230, 75: 320, 100: 400},
    },
    {
        "name": "Дарджилинг FTGFOP1",
        "slug": "darjeeling-first-flush",
        "category_slug": "black",
        "description": "«Шампанское среди чаёв». Лёгкий цветочно-фруктовый аромат, первый урожай. "
                       "Ограниченная партия 2026 года.",
        "origin": "Индия, Дарджилинг",
        "tags": "муссонный,цветочный,легкий",
        "base_price": 14,
        "emoji": "🌹",
        "variants": {25: 350, 50: 650, 75: 920, 100: 1150},
    },
    {
        "name": "Лапсанг Сушонг «Дымный»",
        "slug": "lapsang-souchong",
        "category_slug": "black",
        "description": "Китайский копчёный чай из провинции Фуцзянь. Листья подсушиваются над "
                       "огнём сосновых дров. Насыщенный дымный аромат — на любителя.",
        "origin": "Китай, провинция Фуцзянь",
        "tags": "копчёный,дымный,фуцзянь",
        "base_price": 7,
        "emoji": "🔥",
        "variants": {25: 175, 50: 330, 75: 465, 100: 580},
    },
    # ── Улун ─────────────────────────────────────────────────────────
    {
        "name": "Те Гуань Инь «Железная Богиня»",
        "slug": "tie-guan-yin",
        "category_slug": "oolong",
        "description": "Тёмный улун с насыщенным орхидейным ароматом. Многослойный вкус: "
                       "от цветочного до сливочно-орехового. Один из самых известных улунов.",
        "origin": "Китай, провинция Фуцзянь",
        "tags": "китайский,орхидея,тёмный",
        "base_price": 16,
        "emoji": "🌺",
        "variants": {25: 400, 50: 750, 75: 1050, 100: 1300},
    },
    {
        "name": "Дун Дин «Пик Зимы»",
        "slug": "dong-ding",
        "category_slug": "oolong",
        "description": "Светлый тайваньский улун. Нежный сливочно-цветочный аромат, маслянистая "
                       "текстура, долгое сладкое послевкусие.",
        "origin": "Тайвань, уезд Наньтоу",
        "tags": "тайваньский,сливочный,светлый",
        "base_price": 18,
        "emoji": "🌿",
        "variants": {25: 450, 50: 850, 75: 1180, 100: 1450},
    },
    # ── Пуэр ─────────────────────────────────────────────────────────
    {
        "name": "Пуэр Шу «Чайный Шедевр»",
        "slug": "puerh-shu-shedevr",
        "category_slug": "puerh",
        "description": "Постферментированный тёмный чай. Глубокий землистый вкус с нотками "
                       "шоколада и сухофруктов. Улучшает пищеварение.",
        "origin": "Китай, провинция Юньнань",
        "tags": "китайский,землистый,постферментированный",
        "base_price": 9,
        "emoji": "🏔",
        "variants": {25: 225, 50: 420, 75: 590, 100: 740},
    },
    {
        "name": "Пуэр Шэн (сырой) 2018",
        "slug": "puerh-sheng-2018",
        "category_slug": "puerh",
        "description": "Выдержанный сырой пуэр. Свежий, с лёгкой терпкостью и цитрусовыми "
                       "нотами. С годами становится мягче и глубже.",
        "origin": "Китай, провинция Юньнань, гора Айлао",
        "tags": "китайский,цитрусовый,выдержанный",
        "base_price": 12,
        "emoji": "🌱",
        "variants": {25: 300, 50: 560, 75: 790, 100: 990},
    },
    {
        "name": "Блин пуэра 2015",
        "slug": "puerh-cake-2015",
        "category_slug": "puerh",
        "description": "Прессованный сырой пуэр в форме классического блина 357 г. "
                       "Выдержан 9 лет — мягкий, с нотами сухофруктов и осенних листьев. "
                       "Коллекционный экземпляр.",
        "origin": "Китай, провинция Юньнань",
        "tags": "прессованный,блин,коллекционный,выдержанный",
        "base_price": 1890,
        "emoji": "🟤",
        "is_unit": True,
        "unit_label": "блин 357 г",
        "variants": {0: 1890},
    },
    # ── Белый ────────────────────────────────────────────────────────
    {
        "name": "Бай Хао Инь Чжэнь «Серебряные Иголки»",
        "slug": "bai-hao-yinzhen",
        "category_slug": "white",
        "description": "Белый чай из нежнейших чайных почек. Деликатный цветочный аромат, "
                       "сладковатый медовый вкус. Минимум обработки.",
        "origin": "Китай, провинция Фуцзянь",
        "tags": "китайский,медовый,деликатный",
        "base_price": 20,
        "emoji": "🤍",
        "variants": {25: 500, 50: 940, 75: 1320, 100: 1650},
    },
    # ── Травяные ─────────────────────────────────────────────────────
    {
        "name": "Иван-чай ферментированный",
        "slug": "ivan-chai-fermented",
        "category_slug": "herbal",
        "description": "Русский травяной чай из ферментированных листьев иван-чая. "
                       "Мягкий, слегка сладковатый, с карамельным ароматом. Без кофеина.",
        "origin": "Россия, Алтай",
        "tags": "русский,без_кофеина,карамельный",
        "base_price": 7,
        "emoji": "🌾",
        "variants": {25: 175, 50: 330, 75: 465, 100: 580},
    },
    {
        "name": "Ромашка «Уютный вечер»",
        "slug": "chamomile-cozy",
        "category_slug": "herbal",
        "description": "Цветки ромашки аптечной премиум-качества. Успокаивающий аромат, "
                       "мягкий вкус с медовыми нотками. Идеален перед сном.",
        "origin": "Россия, Краснодарский край",
        "tags": "успокаивающий,медовый,без_кофеина",
        "base_price": 6,
        "emoji": "🌼",
        "variants": {25: 150, 50: 280, 75: 390, 100: 490},
    },
    # ── Наборы ───────────────────────────────────────────────────────
    {
        "name": "Подарочный набор «Чайная церемония»",
        "slug": "gift-set-ceremony",
        "category_slug": "gift-sets",
        "description": "5 сортов элитного чая по 25 г + чайник из красной глины 150 мл. "
                       "Красивая подарочная коробка. Идеально для ценителей чая.",
        "origin": "Ассорти",
        "tags": "подарок,церемония,чайник",
        "base_price": 3200,
        "emoji": "🎁",
        "is_unit": True,
        "unit_label": "набор",
        "variants": {0: 3200},
    },
]

# ---------------------------------------------------------------------------
# Баннеры
# ---------------------------------------------------------------------------

_BANNERS = [
    {
        "title": "Новинки лета 2026",
        "subtitle": "Свежий урожай уже в продаже",
        "image_path": "emoji_banner:🍃",
        "link": "catalog:green",
        "sort": 1,
    },
    {
        "title": "Подарочные наборы",
        "subtitle": "Идеальный подарок для ценителей чая",
        "image_path": "emoji_banner:🎁",
        "link": "catalog:gift-sets",
        "sort": 2,
    },
    {
        "title": "Дарджилинг FTGFOP1",
        "subtitle": "Шампанское среди чаёв — ограниченная партия",
        "image_path": "emoji_banner:🌹",
        "link": "product:darjeeling-first-flush",
        "sort": 3,
    },
]

# ---------------------------------------------------------------------------
# FAQ
# ---------------------------------------------------------------------------

_FAQ_ITEMS = [
    {
        "question": "Какие способы доставки вы предлагаете?",
        "answer": "Самовывоз из магазина (бесплатно) или доставка через пункты выдачи. "
                  "После оформления заказа менеджер свяжется с вами для уточнения деталей.",
        "sort": 1,
    },
    {
        "question": "Как долго хранится чай?",
        "answer": "При правильном хранении (сухое тёмное место, герметичная упаковка): "
                  "зелёный и белый — до 12 месяцев, чёрный и пуэр — до 2–3 лет, "
                  "выдержанный шэн-пуэр — десятилетиями.",
        "sort": 2,
    },
    {
        "question": "Как правильно заваривать чай?",
        "answer": "Базовые правила: свежая вода 80–95°C, 1 г на 100 мл. "
                  "Зелёный — 2–3 минуты, чёрный — 3–5 минут, пуэр — 5–7 минут.",
        "sort": 3,
    },
    {
        "question": "Можно ли вернуть товар?",
        "answer": "Если товар не вскрывали и сохранили упаковку — возврат в течение 7 дней. "
                  "Свяжитесь с нами через личный кабинет.",
        "sort": 4,
    },
]

# ---------------------------------------------------------------------------
# Демо-пользователи
# ---------------------------------------------------------------------------

_DEMO_USERS = [
    {"telegram_id": -101, "first_name": "Анна",      "last_name": "Смирнова",  "username": "demo_anna",   "phone": "+7 999 111-22-33"},
    {"telegram_id": -102, "first_name": "Михаил",    "last_name": "Петров",    "username": "demo_misha",  "phone": "+7 999 444-55-66"},
    {"telegram_id": -103, "first_name": "Елена",     "last_name": "Козлова",   "username": "demo_lena",   "phone": "+7 999 777-88-99"},
    {"telegram_id": -104, "first_name": "Дмитрий",   "last_name": "Новиков",   "username": "demo_dima",   "phone": "+7 999 000-11-22"},
    {"telegram_id": -105, "first_name": "Ольга",     "last_name": "Соколова",  "username": "demo_olga",   "phone": "+7 999 333-44-55"},
    {"telegram_id": -106, "first_name": "Сергей",    "last_name": "Волков",    "username": "demo_serg",   "phone": "+7 999 666-77-88"},
    {"telegram_id": -107, "first_name": "Татьяна",   "last_name": "Морозова",  "username": "demo_tanya",  "phone": "+7 999 222-33-44"},
    {"telegram_id": -108, "first_name": "Алексей",   "last_name": "Зайцев",    "username": "demo_alex",   "phone": "+7 999 555-66-77"},
]

# ---------------------------------------------------------------------------
# Сценарии заказов (60 штук за 90 дней)
# ---------------------------------------------------------------------------

def _build_orders_plan() -> list[dict]:
    """Генерирует список параметров для 60 демо-заказов."""
    plans = []

    delivery_types = ["pickup", "courier", "pvz"]
    addresses = [
        "ул. Ленина, 10, кв. 5",
        "пр. Мира, 45, кв. 12",
        "ул. Гагарина, 7, кв. 33",
        "ПВЗ Боксберри, Садовая 3",
        "ПВЗ СДЭК, Пушкина 22",
        "ул. Советская, 18, кв. 101",
        "пер. Комсомольский, 3",
        "ПВЗ Яндекс, Строителей 5",
    ]

    # Заказы за 30–90 дней (35 штук) → все delivered
    for i in range(35):
        days_ago = _rng.randint(30, 90)
        dtype = _rng.choice(delivery_types)
        addr = None if dtype == "pickup" else _rng.choice(addresses)
        plans.append({
            "idx": i + 1,
            "user_idx": _rng.randint(0, len(_DEMO_USERS) - 1),
            "days_ago": days_ago,
            "status": "delivered",
            "delivery_type": dtype,
            "address": addr,
            "items_count": _rng.randint(1, 3),
        })

    # Заказы за 7–29 дней (12 штук) → delivered + in_delivery
    for i in range(12):
        days_ago = _rng.randint(7, 29)
        dtype = _rng.choice(delivery_types)
        addr = None if dtype == "pickup" else _rng.choice(addresses)
        status = "delivered" if days_ago > 14 else _rng.choice(["delivered", "in_delivery", "at_pvz"])
        plans.append({
            "idx": i + 36,
            "user_idx": _rng.randint(0, len(_DEMO_USERS) - 1),
            "days_ago": days_ago,
            "status": status,
            "delivery_type": dtype,
            "address": addr,
            "items_count": _rng.randint(1, 4),
        })

    # Заказы за 1–6 дней (10 штук) → активные статусы
    active_statuses = [
        "in_delivery", "in_delivery", "in_delivery",
        "at_pvz", "at_pvz",
        "awaiting_payment", "awaiting_payment", "awaiting_payment",
        "assembling", "ready",
    ]
    for i in range(10):
        days_ago = _rng.randint(1, 6)
        status = _rng.choice(active_statuses)
        dtype = _rng.choice(delivery_types)
        if status in ("assembling", "ready") and dtype != "pickup":
            dtype = "pickup"
        addr = None if dtype == "pickup" else _rng.choice(addresses)
        plans.append({
            "idx": i + 48,
            "user_idx": _rng.randint(0, len(_DEMO_USERS) - 1),
            "days_ago": days_ago,
            "status": status,
            "delivery_type": dtype,
            "address": addr,
            "items_count": _rng.randint(1, 3),
        })

    # Самые свежие (сегодня/вчера, 3 штуки)
    for i in range(3):
        days_ago = _rng.randint(0, 1)
        dtype = _rng.choice(delivery_types)
        addr = None if dtype == "pickup" else _rng.choice(addresses)
        plans.append({
            "idx": i + 58,
            "user_idx": _rng.randint(0, len(_DEMO_USERS) - 1),
            "days_ago": days_ago,
            "status": "new",
            "delivery_type": dtype,
            "address": addr,
            "items_count": _rng.randint(1, 2),
        })

    return plans


# ---------------------------------------------------------------------------
# Сидеры
# ---------------------------------------------------------------------------

async def _seed_categories(factory) -> dict[str, int]:
    slug_to_id: dict[str, int] = {}
    async with factory() as session:
        for cat_data in _CATEGORIES:
            res = await session.execute(select(Category).where(Category.slug == cat_data["slug"]))
            cat = res.scalar_one_or_none()
            if cat is not None:
                slug_to_id[cat.slug] = cat.id
                continue
            cat = Category(**{k: v for k, v in cat_data.items()})
            session.add(cat)
            await session.commit()
            await session.refresh(cat)
            slug_to_id[cat.slug] = cat.id
    return slug_to_id


async def _seed_products(slug_to_id: dict[str, int], factory) -> list[tuple]:
    """Создаёт товары с вариантами. Возвращает список (variant, product_name)."""
    all_variants: list[tuple] = []
    async with factory() as session:
        for prod_data in _PRODUCTS:
            res = await session.execute(select(Product).where(Product.slug == prod_data["slug"]))
            existing = res.scalar_one_or_none()
            if existing is not None:
                # Загрузим варианты для последующего использования
                for v in existing.variants:
                    if v.in_stock:
                        all_variants.append((v, existing.name))
                continue

            cat_id = slug_to_id[prod_data["category_slug"]]
            is_unit = prod_data.get("is_unit", False)
            product = Product(
                name=prod_data["name"],
                slug=prod_data["slug"],
                description=prod_data["description"],
                origin=prod_data.get("origin"),
                tags=prod_data.get("tags"),
                base_price=prod_data["base_price"],
                category_id=cat_id,
                is_unit=is_unit,
                unit_label=prod_data.get("unit_label"),
            )
            session.add(product)
            await session.commit()
            await session.refresh(product)

            for weight, price in prod_data["variants"].items():
                v = ProductVariant(
                    product_id=product.id,
                    weight_g=weight,
                    price=price,
                    in_stock=True,
                )
                session.add(v)
                all_variants.append((v, product.name))

            # Эмодзи вместо фото
            session.add(
                ProductImage(
                    product_id=product.id,
                    path=f"emoji:{prod_data['emoji']}",
                    is_main=True,
                    alt=prod_data["name"],
                    sort=0,
                )
            )
            await session.commit()

    return all_variants


async def _seed_banners(factory) -> None:
    async with factory() as session:
        for b in _BANNERS:
            res = await session.execute(select(Banner).where(Banner.image_path == b["image_path"]))
            if res.scalar_one_or_none() is not None:
                continue
            session.add(Banner(**b))
        await session.commit()


async def _seed_faq(factory) -> None:
    async with factory() as session:
        for f in _FAQ_ITEMS:
            res = await session.execute(select(FaqItem).where(FaqItem.question == f["question"]))
            if res.scalar_one_or_none() is not None:
                continue
            session.add(FaqItem(**f))
        await session.commit()


async def _seed_pickup(factory) -> None:
    async with factory() as session:
        res = await session.execute(select(PickupPoint).where(PickupPoint.address == "г. Москва, ул. Чайная, д. 42"))
        if res.scalar_one_or_none() is None:
            session.add(PickupPoint(
                name="Магазин «Чайное Дерево»",
                address="г. Москва, ул. Чайная, д. 42",
                work_hours="Пн-Сб 10:00-20:00, Вс 11:00-18:00",
                phone="+7 (999) 123-45-67",
                sort_order=1,
            ))
            await session.commit()


async def _seed_admin(factory) -> None:
    async with factory() as session:
        res = await session.execute(select(AdminUser).where(AdminUser.username == "admin"))
        if res.scalar_one_or_none() is None:
            session.add(AdminUser(
                username="admin",
                password_hash=_bcrypt_lib.hashpw(b"demo1234", _bcrypt_lib.gensalt()).decode(),
                is_superuser=True,
            ))
            await session.commit()

        # Отдельный read-only демо-логин
        res = await session.execute(select(AdminUser).where(AdminUser.username == "demo"))
        if res.scalar_one_or_none() is None:
            session.add(AdminUser(
                username="demo",
                password_hash=_bcrypt_lib.hashpw(b"demo1234", _bcrypt_lib.gensalt()).decode(),
                is_superuser=False,
            ))
            await session.commit()


async def _seed_orders(all_variants: list[tuple], factory) -> None:
    from app.models.delivery import DeliveryInfo
    from app.models.order import Order, OrderItem
    from app.models.user import User

    if not all_variants:
        print("  ⚠ Нет вариантов товаров — пропускаем заказы")
        return

    now = datetime.now(timezone.utc)
    plans = _build_orders_plan()

    async with factory() as session:
        # Создаём демо-пользователей
        user_ids: dict[int, int] = {}
        for u in _DEMO_USERS:
            res = await session.execute(select(User).where(User.telegram_id == u["telegram_id"]))
            user = res.scalar_one_or_none()
            if user is None:
                user = User(**u)
                session.add(user)
                await session.flush()
            user_ids[u["telegram_id"]] = user.id

        vi = 0  # индекс варианта по кругу
        created_count = 0

        for plan in plans:
            number = f"DEMO-{plan['idx']:06d}"
            res = await session.execute(select(Order).where(Order.number == number))
            if res.scalar_one_or_none() is not None:
                continue

            uid_key = _DEMO_USERS[plan["user_idx"]]["telegram_id"]
            uid = user_ids[uid_key]
            created_at = now - timedelta(days=plan["days_ago"], hours=_rng.randint(0, 23))

            status = plan["status"]
            paid_at = None
            delivered_at = None
            if status == "delivered":
                paid_at = created_at + timedelta(hours=_rng.randint(1, 4))
                delivered_at = paid_at + timedelta(days=_rng.randint(1, 4))
            elif status in ("in_delivery", "at_pvz"):
                paid_at = created_at + timedelta(hours=_rng.randint(1, 6))

            # Подбираем товарные позиции
            items_count = plan["items_count"]
            order_items_data = []
            order_total = 0.0
            for _ in range(items_count):
                variant, prod_name = all_variants[vi % len(all_variants)]
                vi += 1
                qty = _rng.randint(1, 2)
                unit_price = float(variant.price)
                order_total += unit_price * qty
                order_items_data.append({
                    "product_id": variant.product_id,
                    "variant_id": variant.id,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "snapshot_name": prod_name,
                    "snapshot_weight_g": variant.weight_g,
                })

            order = Order(
                user_id=uid,
                number=number,
                total_amount=round(order_total, 2),
                status=status,
                created_at=created_at,
                paid_at=paid_at,
                delivered_at=delivered_at,
            )
            session.add(order)
            await session.flush()

            for oid in order_items_data:
                session.add(OrderItem(
                    order_id=order.id,
                    **oid,
                ))

            phone = _DEMO_USERS[plan["user_idx"]]["phone"]
            session.add(DeliveryInfo(
                order_id=order.id,
                type=plan["delivery_type"],
                address=plan["address"],
                contact_phone=phone,
            ))
            created_count += 1

        await session.commit()
        print(f"  → создано {created_count} новых заказов (итого в плане: {len(plans)})")


# ---------------------------------------------------------------------------
# Точка входа
# ---------------------------------------------------------------------------

async def run_demo_seed() -> None:
    configure_engine()

    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = get_session_factory()

    print("Demo seed: категории...")
    slug_to_id = await _seed_categories(factory)
    print(f"  → {len(slug_to_id)} категорий")

    print("Demo seed: товары с эмодзи...")
    all_variants = await _seed_products(slug_to_id, factory)
    print(f"  → {len(_PRODUCTS)} товаров ({len(all_variants)} вариантов)")

    print("Demo seed: баннеры...")
    await _seed_banners(factory)

    print("Demo seed: FAQ...")
    await _seed_faq(factory)

    print("Demo seed: точка самовывоза...")
    await _seed_pickup(factory)

    print("Demo seed: администратор (admin / demo1234)...")
    await _seed_admin(factory)

    print("Demo seed: заказы за 90 дней...")
    await _seed_orders(all_variants, factory)

    print("\n✓ Demo seed завершён!")
    print("  Логин в админку: admin / demo1234")
    print("  Read-only логин: demo / demo1234")


if __name__ == "__main__":
    asyncio.run(run_demo_seed())
