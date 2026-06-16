"""Тесты инвариантов моделей: создание схемы, связи, уникальности, default'ы.

Идут на in-memory SQLite (см. conftest). Проверяем, что DDL генерируется
без ошибок и базовые CRUD/связи работают.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import (
    Cart,
    CartItem,
    Category,
    NotificationTarget,
    Order,
    OrderItem,
    Product,
    ProductImage,
    ProductVariant,
    User,
)
from app.models.enums import OrderDeliveryStatus, OrderPaymentStatus


async def _make_user(db, telegram_id: int = 100500) -> User:
    user = User(telegram_id=telegram_id, first_name="Иван")
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _make_category(db, slug: str = "green") -> Category:
    cat = Category(name="Зелёный чай", slug=slug)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat


async def test_schema_creates_all_tables(db_session) -> None:
    """Все таблицы создаются (DDL валиден и для SQLite, и для Postgres)."""
    from app.db import Base

    # Если фикстура дошла сюда — create_all уже отработал в _prepare_db.
    assert len(Base.metadata.tables) >= 17


async def test_user_unique_telegram_id(db_session) -> None:
    """telegram_id уникален — повтор вызывает IntegrityError."""
    await _make_user(db_session, telegram_id=1)
    db_session.add(User(telegram_id=1))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_product_variant_unique_weight(db_session) -> None:
    """У одного товара не может быть двух вариантов одного веса."""
    cat = await _make_category(db_session)
    p = Product(name="Сенча", slug="sencha", base_price=500, category_id=cat.id)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    db_session.add(ProductVariant(product_id=p.id, weight_g=50, price=300))
    db_session.add(ProductVariant(product_id=p.id, weight_g=50, price=310))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_product_variant_different_weights_ok(db_session) -> None:
    """Разные веса — допустимы."""
    cat = await _make_category(db_session)
    p = Product(name="Сенча", slug="sencha", base_price=500, category_id=cat.id)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    for w, price in [(25, 150), (50, 280), (75, 400), (100, 500)]:
        db_session.add(ProductVariant(product_id=p.id, weight_g=w, price=price))
    await db_session.commit()

    res = await db_session.execute(select(ProductVariant).where(ProductVariant.product_id == p.id))
    variants = res.scalars().all()
    assert {v.weight_g for v in variants} == {25, 50, 75, 100}


async def test_cart_one_per_user_and_items(db_session) -> None:
    """У пользователя одна корзина; позиции ссылаются на варианты."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session)
    p = Product(name="Сенча", slug="sencha", base_price=500, category_id=cat.id)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    v = ProductVariant(product_id=p.id, weight_g=100, price=500)
    db_session.add(v)
    await db_session.commit()
    await db_session.refresh(v)

    cart = Cart(user_id=user.id)
    db_session.add(cart)
    await db_session.commit()
    await db_session.refresh(cart)

    db_session.add(CartItem(cart_id=cart.id, variant_id=v.id, quantity=2))
    await db_session.commit()

    # повторная корзина тому же пользователю — ошибка уникальности
    db_session.add(Cart(user_id=user.id))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_order_statuses_defaults(db_session) -> None:
    """Новый заказ получает дефолтные статусы pending / new."""
    user = await _make_user(db_session)
    order = Order(
        user_id=user.id,
        number="ЧД-000001",
        total_amount=500,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    assert order.status_payment == OrderPaymentStatus.PENDING.value
    assert order.status_delivery == OrderDeliveryStatus.NEW.value
    assert order.delivery_cost == 0
    assert order.total_amount == 500


async def test_order_item_snapshot(db_session) -> None:
    """OrderItem хранит снапшот названия/цены — не зависит от изменения товара."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session)
    p = Product(name="Сенча", slug="sencha", base_price=500, category_id=cat.id)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    v = ProductVariant(product_id=p.id, weight_g=100, price=500)
    db_session.add(v)
    await db_session.commit()
    await db_session.refresh(v)

    order = Order(user_id=user.id, number="ЧД-000002", total_amount=500)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    item = OrderItem(
        order_id=order.id,
        product_id=p.id,
        variant_id=v.id,
        quantity=1,
        unit_price=500,
        snapshot_name="Сенча",
        snapshot_weight_g=100,
    )
    db_session.add(item)
    await db_session.commit()

    # Меняем цену товара — снапшот в заказе не меняется
    v.price = 999
    await db_session.commit()

    await db_session.refresh(item)
    assert item.unit_price == 500
    assert item.snapshot_name == "Сенча"


async def test_notification_target_role_check(db_session) -> None:
    """Роль notification_target проверяется CHECK-констрейнтом.

    Примечание: SQLite enforcement CHECK зависит от настроек; проверяем что
    валидная роль сохраняется. (На Postgres невалидная роль упадёт через
    IntegrityError — это покроем интеграционными тестами.)
    """
    nt = NotificationTarget(telegram_id=999, role="manager", is_active=True)
    db_session.add(nt)
    await db_session.commit()
    await db_session.refresh(nt)
    assert nt.role == "manager"


async def test_product_image_cascade_delete(db_session) -> None:
    """Удаление товара каскадно удаляет его варианты и картинки."""
    cat = await _make_category(db_session)
    p = Product(name="Сенча", slug="sencha", base_price=500, category_id=cat.id)
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)

    v = ProductVariant(product_id=p.id, weight_g=100, price=500)
    img = ProductImage(product_id=p.id, path="products/abc.jpg", is_main=True)
    db_session.add_all([v, img])
    await db_session.commit()

    # Загружаем свежий продукт со связями, чтобы ORM-каскад увидел их.
    fresh = (
        await db_session.execute(
            select(Product).where(Product.id == p.id).execution_options(populate_existing=True)
        )
    ).scalar_one()
    # relationships lazy=selectin → variants/images уже подгружены
    assert len(fresh.variants) == 1
    assert len(fresh.images) == 1

    await db_session.delete(fresh)
    await db_session.commit()

    res = await db_session.execute(select(ProductVariant))
    assert res.scalars().all() == []
    res = await db_session.execute(select(ProductImage))
    assert res.scalars().all() == []
