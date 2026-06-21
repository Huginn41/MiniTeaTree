"""Демо-данные для каталога чаёв.

Запуск: cd backend && uv run python -m app.seed

Создаёт категории, товары с вариантами (граммовки и цены), баннеры, FAQ,
пункт самовывоза и тестового админа. Идемпотентно — если данные уже есть,
не дублирует (проверяет по slug/username).
"""

from __future__ import annotations

import asyncio

import bcrypt as _bcrypt_lib
from sqlalchemy import select

from app.db import Base, configure_engine, get_engine, get_session_factory
from app.models import (
    AdminUser,
    Banner,
    Category,
    FaqItem,
    NotificationTarget,
    PickupPoint,
    Product,
    ProductImage,
    ProductVariant,
)
from app.models.enums import NotificationRole

# Telegram IDs < 0 используются только для демо — настоящие ID всегда > 0
DEMO_TG_IDS = [-1, -2, -3, -4, -5]

# ---------------------------------------------------------------------------
# Данные
# ---------------------------------------------------------------------------

CATEGORIES = [
    {"name": "Зелёный чай", "slug": "green", "icon": "🍃", "sort_order": 1},
    {"name": "Чёрный чай", "slug": "black", "icon": "🫖", "sort_order": 2},
    {"name": "Улун", "slug": "oolong", "icon": "🍵", "sort_order": 3},
    {"name": "Пуэр", "slug": "puerh", "icon": "🏔", "sort_order": 4},
    {"name": "Белый чай", "slug": "white", "icon": "🤍", "sort_order": 5},
    {"name": "Травяные сборы", "slug": "herbal", "icon": "🌿", "sort_order": 6},
    {"name": "Чайные наборы", "slug": "gift-sets", "icon": "🎁", "sort_order": 7},
]

# Цены в рублях за граммовку. Ключ = (slug, вес).
PRODUCTS = [
    {
        "name": "Сенча premiers cru",
        "slug": "sencha-premier",
        "category_slug": "green",
        "description": "Японский зелёный чай высшего сорта. Свежий травянистый вкус "
        "с нотами_umami. Обладает мощным антиоксидантным действием.",
        "origin": "Япония, префектура Сидзуока",
        "tags": "японский,умами,антиоксидант",
        "base_price": 8,
        "variants": {25: 200, 50: 380, 75: 540, 100: 680},
    },
    {
        "name": "Лунцзин «Колодец Дракона»",
        "slug": "longjing-dragon-well",
        "category_slug": "green",
        "description": "Китайский зелёный чай, один из знаменитых Десяти Великих Чаёв. "
        "Жареный каштановый аромат, нежное сладкое послевкусие.",
        "origin": "Китай, провинция Чжэцзян",
        "tags": "китайский,каштановый,поджаренный",
        "base_price": 10,
        "variants": {25: 250, 50: 470, 75: 660, 100: 840},
    },
    {
        "name": "Ассам TGFOP",
        "slug": "assam-tgfop",
        "category_slug": "black",
        "description": "Классический индийский чёрный чай. Насыщенный солодовый вкус "
        "с лёгкой терпкостью. Отличная основа для масалы.",
        "origin": "Индия, Ассам",
        "tags": "индийский,солодовый,крепкий",
        "base_price": 5,
        "variants": {25: 125, 50: 230, 75: 320, 100: 400},
    },
    {
        "name": "Дарджилинг FTGFOP1",
        "slug": "darjeeling-first-flush",
        "category_slug": "black",
        "description": "«Шампанское среди чаёв». Лёгкий цветочно-фруктовый аромат, "
        "муссонный чай первого урожая из Индии.",
        "origin": "Индия, Дарджилинг",
        "tags": "муссонный,цветочный,легкий",
        "base_price": 14,
        "variants": {25: 350, 50: 650, 75: 920, 100: 1150},
    },
    {
        "name": "Те Гуань Инь «Железная Богиня Милосердия»",
        "slug": "tie-guan-yin",
        "category_slug": "oolong",
        "description": "Тёмный улун с насыщенным орхидейным ароматом. Многослойный "
        "вкус: от цветочного до сливочно-орехового.",
        "origin": "Китай, провинция Фуцзянь",
        "tags": "китайский,орхидея,тёмный",
        "base_price": 16,
        "variants": {25: 400, 50: 750, 75: 1050, 100: 1300},
    },
    {
        "name": "Дун Дин «Пик Зимы»",
        "slug": "dong-ding",
        "category_slug": "oolong",
        "description": "Светлый тайваньский улун. Нежный сливочно-цветочный аромат, "
        "маслянистая текстура, долгое сладкое послевкусие.",
        "origin": "Тайвань, уезд Наньтоу",
        "tags": "тайваньский,сливочный,светлый",
        "base_price": 18,
        "variants": {25: 450, 50: 850, 75: 1180, 100: 1450},
    },
    {
        "name": "Пуэр Шу (готовый) «Чайный Шедевр»",
        "slug": "puerh-shu-shedevr",
        "category_slug": "puerh",
        "description": "Постферментированный тёмный чай. Глубокий землистый вкус "
        "с нотками шоколада и сухофруктов. Улучшает пищеварение.",
        "origin": "Китай, провинция Юньнань",
        "tags": "китайский,землистый,постферментированный",
        "base_price": 9,
        "variants": {25: 225, 50: 420, 75: 590, 100: 740},
    },
    {
        "name": "Пуэр Шэн (сырой) 2018",
        "slug": "puerh-sheng-2018",
        "category_slug": "puerh",
        "description": "Выдержанный сырой пуэр. Свежий, с лёгкой терпкостью и "
        "цитрусовыми нотами. С годами становится мягче и глубже.",
        "origin": "Китай, провинция Юньнань, гора Айлао",
        "tags": "китайский,цитрусовый,выдержанный",
        "base_price": 12,
        "variants": {25: 300, 50: 560, 75: 790, 100: 990},
    },
    {
        "name": "Бай Хао Инь Чжэнь «Серебряные Иголки»",
        "slug": "bai-hao-yinzhen",
        "category_slug": "white",
        "description": "Белый чай из нежнейших чайных почек. Деликатный цветочный "
        "аромат, сладковатый медовый вкус. Минимум обработки.",
        "origin": "Китай, провинция Фуцзянь",
        "tags": "китайский,медовый,деликатный",
        "base_price": 20,
        "variants": {25: 500, 50: 940, 75: 1320, 100: 1650},
    },
    {
        "name": "Иван-чай ферментированный",
        "slug": "ivan-chai-fermented",
        "category_slug": "herbal",
        "description": "Русский травяной чай из ферментированных листьев иван-чая. "
        "Мягкий, слегка сладковатый, с карамельным ароматом. Без кофеина.",
        "origin": "Россия, Алтай",
        "tags": "русский,без_кофеина,карамельный",
        "base_price": 7,
        "variants": {25: 175, 50: 330, 75: 465, 100: 580},
    },
    {
        "name": "Ромашка аптечная «Уютный вечер»",
        "slug": "chamomile-cozy",
        "category_slug": "herbal",
        "description": "Цветки ромашки аптечной премиум-качества. Успокаивающий "
        "аромат, мягкий вкус с медовыми нотками. Идеален перед сном.",
        "origin": "Россия, Краснодарский край",
        "tags": "успокаивающий,медовый,без_кофеина",
        "base_price": 6,
        "variants": {25: 150, 50: 280, 75: 390, 100: 490},
    },
]

BANNERS = [
    {
        "title": "Новинки лета",
        "subtitle": "Свежий урожай 2026 уже в продаже",
        "image_path": "banners/banner_new_tea.jpg",
        "link": "catalog:green",
        "sort": 1,
    },
    {
        "title": "Чайные наборы",
        "subtitle": "Идеальный подарок для ценителей чая",
        "image_path": "banners/banner_gift_sets.jpg",
        "link": "catalog:gift-sets",
        "sort": 2,
    },
    {
        "title": "Дарджилинг FTGFOP1",
        "subtitle": "Шампанское среди чаёв — ограниченная партия",
        "image_path": "banners/banner_darjeeling.jpg",
        "link": "product:darjeeling-first-flush",
        "sort": 3,
    },
]

FAQ_ITEMS = [
    {
        "question": "Какие способы доставки вы предлагаете?",
        "answer": "Самовывоз по адресу магазина (бесплатно) или доставка через "
        "пункты выдачи Яндекс Маркет. После оформления заказа наш "
        "менеджер свяжется с вами для уточнения деталей доставки.",
        "sort": 1,
    },
    {
        "question": "Как долго хранится чай?",
        "answer": "При правильном хранении (сухое тёмное место, герметичная упаковка) "
        "зелёный и белый чай — до 12 месяцев, чёрный и пуэр — до 2-3 лет, "
        "а выдержанный шэн-пуэр — десятилетиями.",
        "sort": 2,
    },
    {
        "question": "Как правильно заваривать чай?",
        "answer": "Зависит от сорта. Базовые правила: свежая вода 80-95°C, "
        "количество — 1 грамм на 100 мл. Зелёный чай — 2-3 минуты, "
        "чёрный — 3-5 минут, пуэр — 5-7 минут. На каждой карточке "
        "товара есть рекомендации по завариванию.",
        "sort": 3,
    },
    {
        "question": "Можно ли вернуть товар?",
        "answer": "Если товар не вскрывали и сохранили упаковку — возврат в течение "
        "7 дней. Свяжитесь с нами через личный кабинет или напишите "
        "менеджеру.",
        "sort": 4,
    },
]

PICKUP_POINTS = [
    {
        "name": "Магазин «Чайное Дерево»",
        "address": "г. Москва, ул. Чайная, д. 42",
        "work_hours": "Пн-Сб 10:00-20:00, Вс 11:00-18:00",
        "phone": "+7 (999) 123-45-67",
        "sort_order": 1,
    },
]


async def _seed_categories(factory) -> dict[str, int]:
    """Создаёт категории, возвращает {slug: id}."""
    slug_to_id: dict[str, int] = {}
    async with factory() as session:
        for cat_data in CATEGORIES:
            exists = await session.execute(
                select(Category).where(Category.slug == cat_data["slug"])
            )
            cat = exists.scalar_one_or_none()
            if cat is not None:
                slug_to_id[cat.slug] = cat.id
                continue
            cat = Category(**cat_data)
            session.add(cat)
            await session.commit()
            await session.refresh(cat)
            slug_to_id[cat.slug] = cat.id
    return slug_to_id


async def _seed_products(slug_to_id: dict[str, int], factory) -> None:
    """Создаёт товары с вариантами."""
    async with factory() as session:
        for prod_data in PRODUCTS:
            exists = await session.execute(select(Product).where(Product.slug == prod_data["slug"]))
            if exists.scalar_one_or_none() is not None:
                continue

            cat_id = slug_to_id[prod_data["category_slug"]]
            product = Product(
                name=prod_data["name"],
                slug=prod_data["slug"],
                description=prod_data["description"],
                origin=prod_data.get("origin"),
                tags=prod_data.get("tags"),
                base_price=prod_data["base_price"],
                category_id=cat_id,
            )
            session.add(product)
            await session.commit()
            await session.refresh(product)

            for weight, price in prod_data["variants"].items():
                session.add(
                    ProductVariant(
                        product_id=product.id,
                        weight_g=weight,
                        price=price,
                        in_stock=True,
                    )
                )

            # Главная картинка (плейсхолдер — реальная будет загружена через админку/YML)
            session.add(
                ProductImage(
                    product_id=product.id,
                    path=f"products/{prod_data['slug']}.jpg",
                    is_main=True,
                    sort=0,
                )
            )
            await session.commit()


async def _seed_banners(factory) -> None:
    async with factory() as session:
        for b in BANNERS:
            exists = await session.execute(
                select(Banner).where(Banner.image_path == b["image_path"])
            )
            if exists.scalar_one_or_none() is not None:
                continue
            session.add(Banner(**b))
        await session.commit()


async def _seed_faq(factory) -> None:
    async with factory() as session:
        for f in FAQ_ITEMS:
            exists = await session.execute(select(FaqItem).where(FaqItem.question == f["question"]))
            if exists.scalar_one_or_none() is not None:
                continue
            session.add(FaqItem(**f))
        await session.commit()


async def _seed_pickup_points(factory) -> None:
    async with factory() as session:
        for pp in PICKUP_POINTS:
            exists = await session.execute(
                select(PickupPoint).where(PickupPoint.address == pp["address"])
            )
            if exists.scalar_one_or_none() is not None:
                continue
            session.add(PickupPoint(**pp))
        await session.commit()


async def _seed_admin(factory) -> None:
    from app.config import get_settings

    settings = get_settings()
    async with factory() as session:
        exists = await session.execute(
            select(AdminUser).where(AdminUser.username == settings.admin_username)
        )
        if exists.scalar_one_or_none() is None:
            session.add(
                AdminUser(
                    username=settings.admin_username,
                    password_hash=_bcrypt_lib.hashpw(
                        settings.admin_password.get_secret_value().encode(),
                        _bcrypt_lib.gensalt(),
                    ).decode(),
                    is_superuser=True,
                )
            )
            await session.commit()

    # Демо-пользователь (read-only)
    async with factory() as session:
        demo_exists = await session.execute(
            select(AdminUser).where(AdminUser.username == "demo")
        )
        if demo_exists.scalar_one_or_none() is None:
            session.add(
                AdminUser(
                    username="demo",
                    password_hash=_bcrypt_lib.hashpw(b"demo1234", _bcrypt_lib.gensalt()).decode(),
                    is_superuser=False,
                )
            )
            await session.commit()


async def _seed_notification_targets(factory) -> None:
    """Создаёт дефолтный магазинный чат (telegram_id берётся из ADMIN_TELEGRAM_IDS)."""
    from app.config import get_settings

    settings = get_settings()
    async with factory() as session:
        for tid in settings.admin_telegram_id_list:
            exists = await session.execute(
                select(NotificationTarget).where(NotificationTarget.telegram_id == tid)
            )
            if exists.scalar_one_or_none() is not None:
                continue
            session.add(
                NotificationTarget(
                    telegram_id=tid,
                    name="Магазин",
                    role=NotificationRole.SHOP.value,
                    is_active=True,
                )
            )
        await session.commit()


async def _seed_demo_data(factory) -> None:
    """Создаёт фейковых клиентов и заказы для демо-режима (telegram_id < 0)."""
    from datetime import datetime, timezone, timedelta
    from app.models.user import User
    from app.models.order import Order, OrderItem
    from app.models.delivery import DeliveryInfo

    _DEMO_USERS = [
        {"telegram_id": -1, "first_name": "Анна",    "last_name": "Смирнова",  "username": "demo_anna",  "phone": "+7 999 111-22-33"},
        {"telegram_id": -2, "first_name": "Михаил",  "last_name": "Петров",    "username": "demo_misha", "phone": "+7 999 444-55-66"},
        {"telegram_id": -3, "first_name": "Елена",   "last_name": "Козлова",   "username": "demo_lena",  "phone": "+7 999 777-88-99"},
        {"telegram_id": -4, "first_name": "Дмитрий", "last_name": "Новиков",   "username": "demo_dima",  "phone": "+7 999 000-11-22"},
        {"telegram_id": -5, "first_name": "Ольга",   "last_name": "Соколова",  "username": "demo_olga",  "phone": "+7 999 333-44-55"},
    ]

    _DEMO_ORDERS = [
        {"user_idx": 0, "number": "DEMO-000001", "total": 875,  "status": "delivered",        "delivery_type": "courier", "address": "ул. Ленина, 10, кв. 5",         "days_ago": 14},
        {"user_idx": 1, "number": "DEMO-000002", "total": 1250, "status": "delivered",        "delivery_type": "pickup",  "address": None,                            "days_ago": 10},
        {"user_idx": 2, "number": "DEMO-000003", "total": 500,  "status": "awaiting_payment", "delivery_type": "courier", "address": "пр. Мира, 45, кв. 12",          "days_ago": 3},
        {"user_idx": 0, "number": "DEMO-000004", "total": 625,  "status": "in_delivery",      "delivery_type": "pvz",     "address": "ПВЗ Боксберри, Садовая 3",      "days_ago": 2},
        {"user_idx": 3, "number": "DEMO-000005", "total": 375,  "status": "new",              "delivery_type": "pickup",  "address": None,                            "days_ago": 1},
        {"user_idx": 4, "number": "DEMO-000006", "total": 1500, "status": "delivered",        "delivery_type": "courier", "address": "ул. Гагарина, 7, кв. 33",       "days_ago": 7},
        {"user_idx": 1, "number": "DEMO-000007", "total": 750,  "status": "awaiting_payment", "delivery_type": "pvz",     "address": "ПВЗ СДЭК, Пушкина 22",         "days_ago": 0},
    ]

    async with factory() as session:
        # Создаём демо-пользователей
        user_ids = {}
        for u in _DEMO_USERS:
            exists = await session.execute(select(User).where(User.telegram_id == u["telegram_id"]))
            user = exists.scalar_one_or_none()
            if user is None:
                user = User(**u)
                session.add(user)
                await session.flush()
            user_ids[u["telegram_id"]] = user.id

        # Получаем первый попавшийся вариант из каждой граммовки для снапшотов
        from app.models.product import ProductVariant, Product as Prod
        variants_res = await session.execute(
            select(ProductVariant, Prod.name)
            .join(Prod, Prod.id == ProductVariant.product_id)
            .where(ProductVariant.in_stock.is_(True))
            .limit(20)
        )
        variants_raw = variants_res.all()
        if not variants_raw:
            await session.commit()
            return
        variants = [(v, name) for v, name in variants_raw]

        now = datetime.now(timezone.utc)
        vi = 0  # индекс варианта по кругу

        for od in _DEMO_ORDERS:
            exists = await session.execute(select(Order).where(Order.number == od["number"]))
            if exists.scalar_one_or_none() is not None:
                continue

            tg_id = _DEMO_USERS[od["user_idx"]]["telegram_id"]
            uid = user_ids[tg_id]
            created = now - timedelta(days=od["days_ago"], hours=od["user_idx"])

            order = Order(
                user_id=uid,
                number=od["number"],
                total_amount=od["total"],
                status=od["status"],
                comment=None,
                created_at=created,
                paid_at=created + timedelta(hours=1) if od["status"] == "delivered" else None,
                delivered_at=created + timedelta(days=3) if od["status"] == "delivered" else None,
            )
            session.add(order)
            await session.flush()

            # 1-2 позиции
            items_count = 1 + (od["user_idx"] % 2)
            for _ in range(items_count):
                variant, prod_name = variants[vi % len(variants)]
                vi += 1
                session.add(OrderItem(
                    order_id=order.id,
                    product_id=variant.product_id,
                    variant_id=variant.id,
                    quantity=1,
                    unit_price=float(variant.price),
                    snapshot_name=prod_name,
                    snapshot_weight_g=variant.weight_g,
                ))

            session.add(DeliveryInfo(
                order_id=order.id,
                type=od["delivery_type"],
                address=od["address"],
                contact_phone=_DEMO_USERS[od["user_idx"]]["phone"],
            ))

        await session.commit()


async def run_seed() -> None:
    configure_engine()

    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = get_session_factory()

    print("Seeding categories...")
    slug_to_id = await _seed_categories(factory)
    print(f"  → {len(slug_to_id)} categories")

    print("Seeding products...")
    await _seed_products(slug_to_id, factory)
    print(f"  → {len(PRODUCTS)} products with variants")

    print("Seeding banners...")
    await _seed_banners(factory)
    print(f"  → {len(BANNERS)} banners")

    print("Seeding FAQ...")
    await _seed_faq(factory)
    print(f"  → {len(FAQ_ITEMS)} FAQ items")

    print("Seeding pickup points...")
    await _seed_pickup_points(factory)
    print(f"  → {len(PICKUP_POINTS)} pickup points")

    print("Seeding admin user...")
    await _seed_admin(factory)
    print("  → done")

    print("Seeding notification targets...")
    await _seed_notification_targets(factory)
    print("  → done")

    print("Seeding demo data...")
    await _seed_demo_data(factory)
    print("  → done")

    print("\nSeed completed!")


if __name__ == "__main__":
    asyncio.run(run_seed())
