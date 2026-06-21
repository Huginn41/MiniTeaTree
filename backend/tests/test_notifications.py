"""Тесты уведомлений о смене статуса доставки."""

from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

from app.models.category import Category
from app.models.delivery import DeliveryInfo
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.security import create_token_pair

pytestmark = pytest.mark.asyncio


def _auth(user: User) -> dict:
    access, _ = create_token_pair(user.telegram_id)
    return {"Authorization": f"Bearer {access}"}


@pytest.fixture
async def admin_and_order(db_session):
    """Админ + обычный пользователь + заказ."""
    admin = User(telegram_id=100200300, first_name="Менеджер", is_admin=True)
    customer = User(telegram_id=400500600, first_name="Клиент")
    db_session.add_all([admin, customer])
    await db_session.flush()

    cat = Category(name="Улун", slug="oolong-notif", sort_order=0)
    db_session.add(cat)
    await db_session.flush()

    prod = Product(category_id=cat.id, name="Те Гуань Инь", slug="tgy-notif", base_price=900, sort_order=0)
    db_session.add(prod)
    await db_session.flush()

    order = Order(
        user_id=customer.id,
        number="ЧД-000300",
        total_amount=900,
        status="new",
    )
    db_session.add(order)
    await db_session.flush()

    di = DeliveryInfo(order_id=order.id, type="courier", address="ул. Ленина, 1", contact_phone="+79001234567")
    db_session.add(di)
    await db_session.commit()

    return {"admin": admin, "customer": customer, "order": order}


# ---------- PATCH /orders/{number}/status ----------

async def test_update_status_ok(client: AsyncClient, admin_and_order):
    """Менеджер меняет статус → 200, статус обновлён."""
    admin = admin_and_order["admin"]
    order = admin_and_order["order"]

    resp = await client.patch(
        f"/api/orders/{order.number}/status",
        headers=_auth(admin),
        json={"status": "in_delivery"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_delivery"


async def test_update_status_delivered_sets_timestamp(client: AsyncClient, admin_and_order, db_session):
    """При статусе delivered устанавливается delivered_at."""
    admin = admin_and_order["admin"]
    order = admin_and_order["order"]

    resp = await client.patch(
        f"/api/orders/{order.number}/status",
        headers=_auth(admin),
        json={"status": "delivered"},
    )
    assert resp.status_code == 200
    assert resp.json()["delivered_at"] is not None


async def test_update_status_non_admin_forbidden(client: AsyncClient, admin_and_order, db_session):
    """Обычный пользователь не может менять статусы → 403."""
    customer = admin_and_order["customer"]
    order = admin_and_order["order"]

    resp = await client.patch(
        f"/api/orders/{order.number}/status",
        headers=_auth(customer),
        json={"status": "in_delivery"},
    )
    assert resp.status_code == 403


async def test_update_status_invalid_value(client: AsyncClient, admin_and_order):
    """Неверный статус → 400."""
    admin = admin_and_order["admin"]
    order = admin_and_order["order"]

    resp = await client.patch(
        f"/api/orders/{order.number}/status",
        headers=_auth(admin),
        json={"status": "invalid_status"},
    )
    assert resp.status_code == 400


async def test_update_status_not_found(client: AsyncClient, admin_and_order):
    """Несуществующий заказ → 404."""
    admin = admin_and_order["admin"]

    resp = await client.patch(
        "/api/orders/ЧД-999999/status",
        headers=_auth(admin),
        json={"status": "in_delivery"},
    )
    assert resp.status_code == 404


async def test_update_status_unauthorized(client: AsyncClient, admin_and_order):
    resp = await client.patch(
        f"/api/orders/{admin_and_order['order'].number}/status",
        json={"status": "in_delivery"},
    )
    assert resp.status_code == 401


# ---------- notify_status_changed ----------

async def test_status_notify_skips_fake_token():
    """С фейковым токеном функция возвращает False без HTTP-вызова."""
    from app.bot.status_notify import notify_status_changed
    from app.models.order import Order

    order = Order(id=1, number="ЧД-000001", total_amount=500, status="in_delivery")
    result = await notify_status_changed(order, "in_delivery", 123456)
    assert result is False


async def test_status_notify_unknown_status():
    """Для неизвестного статуса не отправляем ничего."""
    from app.bot.status_notify import notify_status_changed
    from app.models.order import Order

    order = Order(id=2, number="ЧД-000002", total_amount=500, status="new")
    result = await notify_status_changed(order, "some_future_status", 123456)
    assert result is False
