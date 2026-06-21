"""Тесты заказов и профиля."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.category import Category
from app.models.cart import Cart, CartItem
from app.models.product import Product, ProductVariant
from app.models.user import User
from app.security import create_token_pair

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def user_with_cart(db_session):
    """Создаёт пользователя, категорию, товар, корзину с позицией."""
    user = User(telegram_id=998877, first_name="Тест", username="testuser")
    db_session.add(user)
    await db_session.flush()

    cat = Category(name="Зелёный чай", slug="green", sort_order=0)
    db_session.add(cat)
    await db_session.flush()

    product = Product(
        category_id=cat.id, name="Сенча", slug="sencha",
        base_price=1200, sort_order=0,
    )
    db_session.add(product)
    await db_session.flush()

    v25 = ProductVariant(product_id=product.id, weight_g=25, price=350, in_stock=True)
    v50 = ProductVariant(product_id=product.id, weight_g=50, price=650, in_stock=True)
    db_session.add_all([v25, v50])
    await db_session.flush()

    cart = Cart(user_id=user.id)
    db_session.add(cart)
    await db_session.flush()

    ci = CartItem(cart_id=cart.id, variant_id=v25.id, quantity=2)
    db_session.add(ci)
    await db_session.commit()

    return {
        "user": user,
        "product": product,
        "v25": v25,
        "v50": v50,
        "cart": cart,
        "ci": ci,
    }


def _auth_header(user):
    """Bearer токен для тестов."""
    access, _ = create_token_pair(user.telegram_id)
    return {"Authorization": f"Bearer {access}"}


async def test_get_profile(client: AsyncClient, user_with_cart):
    headers = _auth_header(user_with_cart["user"])
    resp = await client.get("/api/profile/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["first_name"] == "Тест"
    assert data["telegram_id"] == 998877


async def test_list_orders_empty(client: AsyncClient, user_with_cart):
    headers = _auth_header(user_with_cart["user"])
    resp = await client.get("/api/orders", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_create_order(client: AsyncClient, user_with_cart):
    headers = _auth_header(user_with_cart["user"])
    body = {
        "delivery_type": "pickup",
        "address": "ул. Тестовая, 1",
        "contact_phone": "+79991234567",
        "comment": "Быстрее",
    }
    resp = await client.post("/api/orders", headers=headers, json=body)
    assert resp.status_code == 201
    data = resp.json()
    assert data["number"].startswith("ЧД-")
    assert data["total_amount"] == 700.0  # 350 * 2
    assert data["status"] == "new"
    assert len(data["items"]) == 1
    assert data["items"][0]["snapshot_name"] == "Сенча"
    assert data["items"][0]["snapshot_weight_g"] == 25
    assert data["items"][0]["quantity"] == 2
    assert data["delivery_info"]["type"] == "pickup"
    assert data["delivery_info"]["address"] == "ул. Тестовая, 1"


async def test_create_order_clears_cart(client: AsyncClient, user_with_cart):
    headers = _auth_header(user_with_cart["user"])
    resp = await client.post("/api/orders", headers=headers, json={"delivery_type": "pickup"})
    assert resp.status_code == 201

    # Корзина должна быть пустой.
    resp2 = await client.get("/api/cart", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["items"] == []


async def test_create_order_empty_cart(client: AsyncClient, db_session):
    user = User(telegram_id=111222, first_name="Empty")
    db_session.add(user)
    await db_session.commit()
    headers = _auth_header(user)
    resp = await client.post("/api/orders", headers=headers, json={"delivery_type": "pickup"})
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


async def test_create_order_invalid_delivery_type(client: AsyncClient, user_with_cart):
    headers = _auth_header(user_with_cart["user"])
    resp = await client.post("/api/orders", headers=headers, json={"delivery_type": "invalid"})
    assert resp.status_code == 400


async def test_get_order_detail(client: AsyncClient, user_with_cart):
    headers = _auth_header(user_with_cart["user"])
    resp = await client.post("/api/orders", headers=headers, json={"delivery_type": "courier", "address": "ул. Ленина, 5"})
    assert resp.status_code == 201
    number = resp.json()["number"]

    resp2 = await client.get(f"/api/orders/{number}", headers=headers)
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["number"] == number
    assert data["delivery_info"]["type"] == "courier"


async def test_get_order_not_found(client: AsyncClient, user_with_cart):
    headers = _auth_header(user_with_cart["user"])
    resp = await client.get("/api/orders/ЧД-999999", headers=headers)
    assert resp.status_code == 404


async def test_unauthorized_orders(client: AsyncClient):
    resp = await client.get("/api/orders")
    assert resp.status_code == 401
