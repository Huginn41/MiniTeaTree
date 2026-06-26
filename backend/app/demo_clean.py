"""Удаление всех демо-данных из БД.

Удаляет:
- Заказы с номером DEMO-* (+ позиции и доставка каскадом)
- Пользователей с telegram_id < 0
- Товары, категории, баннеры, FAQ, ПВЗ с is_demo=True

Запуск:
    cd backend && uv run python -m app.demo_clean
    # или через Docker:
    docker compose exec app python -m app.demo_clean
"""

from __future__ import annotations

import asyncio

from sqlalchemy import delete, select

from app.db import configure_engine, get_session_factory


async def run_clean() -> None:
    configure_engine()
    factory = get_session_factory()

    from app.models.banner import Banner
    from app.models.category import Category
    from app.models.content import FaqItem, PickupPoint
    from app.models.order import Order
    from app.models.product import Product
    from app.models.user import User

    async with factory() as session:
        orders_count = (await session.execute(
            select(Order).where(Order.number.like("DEMO-%"))
        )).scalars().all()
        users_count = (await session.execute(
            select(User).where(User.telegram_id < 0)
        )).scalars().all()
        products_count = (await session.execute(
            select(Product).where(Product.is_demo.is_(True))
        )).scalars().all()
        categories_count = (await session.execute(
            select(Category).where(Category.is_demo.is_(True))
        )).scalars().all()
        banners_count = (await session.execute(
            select(Banner).where(Banner.is_demo.is_(True))
        )).scalars().all()
        faq_count = (await session.execute(
            select(FaqItem).where(FaqItem.is_demo.is_(True))
        )).scalars().all()
        pickup_count = (await session.execute(
            select(PickupPoint).where(PickupPoint.is_demo.is_(True))
        )).scalars().all()

        print(f"Найдено демо-заказов:    {len(orders_count)}")
        print(f"Найдено демо-клиентов:   {len(users_count)}")
        print(f"Найдено демо-товаров:    {len(products_count)}")
        print(f"Найдено демо-категорий:  {len(categories_count)}")
        print(f"Найдено демо-баннеров:   {len(banners_count)}")
        print(f"Найдено демо-FAQ:        {len(faq_count)}")
        print(f"Найдено демо-ПВЗ:        {len(pickup_count)}")

        total = sum(len(x) for x in [
            orders_count, users_count, products_count,
            categories_count, banners_count, faq_count, pickup_count,
        ])
        if total == 0:
            print("Нечего удалять.")
            return

        confirm = input("Удалить? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Отменено.")
            return

        await session.execute(delete(Order).where(Order.number.like("DEMO-%")))
        await session.execute(delete(User).where(User.telegram_id < 0))
        await session.execute(delete(Product).where(Product.is_demo.is_(True)))
        await session.execute(delete(Category).where(Category.is_demo.is_(True)))
        await session.execute(delete(Banner).where(Banner.is_demo.is_(True)))
        await session.execute(delete(FaqItem).where(FaqItem.is_demo.is_(True)))
        await session.execute(delete(PickupPoint).where(PickupPoint.is_demo.is_(True)))
        await session.commit()

        print(f"✓ Удалено всего {total} демо-записей.")


if __name__ == "__main__":
    asyncio.run(run_clean())
