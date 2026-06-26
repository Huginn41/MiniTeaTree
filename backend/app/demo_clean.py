"""Удаление всех демо-данных из БД.

Удаляет:
- Заказы с номером DEMO-* (+ позиции и доставка каскадом)
- Пользователей с telegram_id < 0

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

    from app.models.order import Order
    from app.models.user import User

    async with factory() as session:
        # Считаем что удалим
        orders_count = (await session.execute(
            select(Order).where(Order.number.like("DEMO-%"))
        )).scalars().all()
        users_count = (await session.execute(
            select(User).where(User.telegram_id < 0)
        )).scalars().all()

        print(f"Найдено демо-заказов: {len(orders_count)}")
        print(f"Найдено демо-клиентов: {len(users_count)}")

        if not orders_count and not users_count:
            print("Нечего удалять.")
            return

        confirm = input("Удалить? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Отменено.")
            return

        await session.execute(delete(Order).where(Order.number.like("DEMO-%")))
        await session.execute(delete(User).where(User.telegram_id < 0))
        await session.commit()

        print(f"✓ Удалено {len(orders_count)} заказов и {len(users_count)} клиентов.")


if __name__ == "__main__":
    asyncio.run(run_clean())
