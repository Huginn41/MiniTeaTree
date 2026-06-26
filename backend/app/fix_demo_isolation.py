"""Однократный скрипт: исправляет изоляцию демо-данных после миграции is_demo.

Что делает:
1. Помечает старые демо-только продукты (есть в demo_seed, нет в seed) is_demo=True
2. Помечает emoji_banner баннеры is_demo=True
3. Помечает демо-ПВЗ is_demo=True
4. Удаляет старые DEMO-заказы и демо-клиентов
5. Запускает demo_seed для создания свежих данных (demo-* slug, is_demo=True)

Запуск:
    docker compose exec app python -m app.fix_demo_isolation
"""
from __future__ import annotations

import asyncio

from sqlalchemy import delete, select, update

from app.db import configure_engine, get_session_factory

# Продукты которые есть в old demo_seed, но НЕТ в реальном seed.py
_DEMO_ONLY_PRODUCT_SLUGS = [
    "jasmine-pearl",
    "lapsang-souchong",
    "puerh-cake-2015",
    "gift-set-ceremony",
]

# Адрес демо-ПВЗ (создан demo_seed, не реальный)
_DEMO_PICKUP_ADDRESS = "г. Москва, ул. Чайная, д. 42"


async def run() -> None:
    configure_engine()
    factory = get_session_factory()

    from app.models.banner import Banner
    from app.models.content import FaqItem, PickupPoint
    from app.models.order import Order
    from app.models.product import Product
    from app.models.user import User

    async with factory() as s:
        # 1. Пометить демо-только продукты
        r = await s.execute(
            update(Product)
            .where(Product.slug.in_(_DEMO_ONLY_PRODUCT_SLUGS))
            .values(is_demo=True)
            .returning(Product.slug)
        )
        marked_products = [row[0] for row in r.fetchall()]
        print(f"Помечено продуктов is_demo=True: {len(marked_products)} → {marked_products}")

        # 2. Пометить emoji_banner баннеры
        r = await s.execute(
            update(Banner)
            .where(Banner.image_path.like("emoji_banner:%"))
            .values(is_demo=True)
            .returning(Banner.id)
        )
        marked_banners = r.fetchall()
        print(f"Помечено баннеров is_demo=True: {len(marked_banners)}")

        # 3. Пометить демо-ПВЗ
        r = await s.execute(
            update(PickupPoint)
            .where(PickupPoint.address == _DEMO_PICKUP_ADDRESS)
            .values(is_demo=True)
            .returning(PickupPoint.id)
        )
        marked_pvz = r.fetchall()
        print(f"Помечено ПВЗ is_demo=True: {len(marked_pvz)}")

        # 4. Пометить FAQ-записи demo_seed как is_demo (те же вопросы что в обоих seed)
        # FAQ в admin не отображается, оставляем is_demo=False — они реальные.

        # 5. Удалить старые DEMO-заказы и демо-клиентов
        r = await s.execute(delete(Order).where(Order.number.like("DEMO-%")))
        print(f"Удалено DEMO-заказов: {r.rowcount}")

        r = await s.execute(delete(User).where(User.telegram_id < 0))
        print(f"Удалено демо-клиентов: {r.rowcount}")

        await s.commit()

    print("\nЗапускаю demo_seed для создания свежих демо-данных...")
    from app.demo_seed import run_demo_seed
    await run_demo_seed()

    print("\n✓ Изоляция демо-данных восстановлена.")
    print("  Admin видит: реальные товары (is_demo=False)")
    print("  Demo видит:  demo-* товары (is_demo=True)")


if __name__ == "__main__":
    asyncio.run(run())
