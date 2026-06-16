"""Демо-данные для каталога чаёв.

Запуск: cd backend && uv run python -m app.seed

Создаёт категории, товары с вариантами (граммовки и цены), баннеры, FAQ,
пункт самовывоза и тестового админа. Идемпотентно — если данные уже есть,
не дублирует (проверяет по slug/username).
"""

from __future__ import annotations

import asyncio

from passlib.hash import bcrypt
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
    async with factory()() as session:
        for cat_data in CATEGORIES:
            exists = await session.execute(
                select(Category).where(Category.slug == cat_data["slug"])
            )
            if exists.scalar_one_or_none() is not None:
                cat = exists.scalar_one()
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
    async with factory()() as session:
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
    async with factory()() as session:
        for b in BANNERS:
            exists = await session.execute(
                select(Banner).where(Banner.image_path == b["image_path"])
            )
            if exists.scalar_one_or_none() is not None:
                continue
            session.add(Banner(**b))
        await session.commit()


async def _seed_faq(factory) -> None:
    async with factory()() as session:
        for f in FAQ_ITEMS:
            exists = await session.execute(select(FaqItem).where(FaqItem.question == f["question"]))
            if exists.scalar_one_or_none() is not None:
                continue
            session.add(FaqItem(**f))
        await session.commit()


async def _seed_pickup_points(factory) -> None:
    async with factory()() as session:
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
    async with factory()() as session:
        exists = await session.execute(
            select(AdminUser).where(AdminUser.username == settings.admin_username)
        )
        if exists.scalar_one_or_none() is not None:
            return
        session.add(
            AdminUser(
                username=settings.admin_username,
                password_hash=bcrypt.hash(settings.admin_password.get_secret_value()),
                is_superuser=True,
            )
        )
        await session.commit()


async def _seed_notification_targets(factory) -> None:
    """Создаёт дефолтный магазинный чат (telegram_id берётся из ADMIN_TELEGRAM_IDS)."""
    from app.config import get_settings

    settings = get_settings()
    async with factory()() as session:
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

    print("\nSeed completed!")


if __name__ == "__main__":
    asyncio.run(run_seed())
