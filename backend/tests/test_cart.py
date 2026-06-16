"""Тесты корзины: добавление, обновление, удаление, persistence между запросами."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.category import Category
from app.models.product import Product, ProductVariant
from app.models.user import User
from app.security import create_token_pair

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def setup(db_session):
    """Пользователь + товар с двумя вариантами."""
    user = User(telegram_id=111222333, first_name="Покупатель")
    db_session.add(user)
    await db_session.flush()

    cat = Category(name="Пуэр", slug="puer", sort_order=0)
    db_session.add(cat)
    await db_session.flush()

    prod = Product(category_id=cat.id, name="Шу Пуэр", slug="shu-puer", base_price=800, sort_order=0)
    db_session.add(prod)
    await db_session.flush()

    v50 = ProductVariant(product_id=prod.id, weight_g=50, price=800, in_stock=True)
    v100 = ProductVariant(product_id=prod.id, weight_g=100, price=1400, in_stock=True)
    v_oos = ProductVariant(product_id=prod.id, weight_g=25, price=450, in_stock=False)
    db_session.add_all([v50, v100, v_oos])
    await db_session.commit()

    return {"user": user, "v50": v50, "v100": v100, "v_oos": v_oos}


def _auth(user: User) -> dict:
    access, _ = create_token_pair(user.telegram_id)
    return {"Authorization": f"Bearer {access}"}


# ── GET /cart ──────────────────────────────────────────────────────────────────

async def test_get_empty_cart(client: AsyncClient, setup):
    resp = await client.get("/api/cart", headers=_auth(setup["user"]))
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total_amount"] == 0


async def test_get_cart_unauthorized(client: AsyncClient, setup):
    resp = await client.get("/api/cart")
    assert resp.status_code == 401


# ── POST /cart/items ───────────────────────────────────────────────────────────

async def test_add_item_to_cart(client: AsyncClient, setup):
    user, v50 = setup["user"], setup["v50"]
    resp = await client.post(
        "/api/cart/items",
        headers=_auth(user),
        json={"variant_id": v50.id, "quantity": 1},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["quantity"] == 1
    assert data["variant"]["id"] == v50.id


async def test_add_item_persists_between_requests(client: AsyncClient, setup):
    """Ключевой тест: добавленный товар виден в следующем запросе (проверяет commit)."""
    user, v50 = setup["user"], setup["v50"]
    headers = _auth(user)

    await client.post("/api/cart/items", headers=headers, json={"variant_id": v50.id, "quantity": 2})

    resp = await client.get("/api/cart", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["quantity"] == 2
    assert items[0]["variant"]["id"] == v50.id


async def test_add_same_item_increments_quantity(client: AsyncClient, setup):
    user, v50 = setup["user"], setup["v50"]
    headers = _auth(user)

    await client.post("/api/cart/items", headers=headers, json={"variant_id": v50.id, "quantity": 1})
    await client.post("/api/cart/items", headers=headers, json={"variant_id": v50.id, "quantity": 2})

    resp = await client.get("/api/cart", headers=headers)
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["quantity"] == 3


async def test_add_two_different_variants(client: AsyncClient, setup):
    user = setup["user"]
    headers = _auth(user)

    await client.post("/api/cart/items", headers=headers, json={"variant_id": setup["v50"].id, "quantity": 1})
    await client.post("/api/cart/items", headers=headers, json={"variant_id": setup["v100"].id, "quantity": 1})

    resp = await client.get("/api/cart", headers=headers)
    assert len(resp.json()["items"]) == 2


async def test_add_out_of_stock_variant(client: AsyncClient, setup):
    resp = await client.post(
        "/api/cart/items",
        headers=_auth(setup["user"]),
        json={"variant_id": setup["v_oos"].id, "quantity": 1},
    )
    assert resp.status_code == 404


async def test_add_nonexistent_variant(client: AsyncClient, setup):
    resp = await client.post(
        "/api/cart/items",
        headers=_auth(setup["user"]),
        json={"variant_id": 99999, "quantity": 1},
    )
    assert resp.status_code == 404


# ── PATCH /cart/items/{id} ─────────────────────────────────────────────────────

async def test_update_cart_item_quantity(client: AsyncClient, setup):
    user, v50 = setup["user"], setup["v50"]
    headers = _auth(user)

    add = await client.post("/api/cart/items", headers=headers, json={"variant_id": v50.id, "quantity": 1})
    item_id = add.json()["id"]

    await client.patch(f"/api/cart/items/{item_id}", headers=headers, json={"quantity": 5})

    cart = await client.get("/api/cart", headers=headers)
    assert cart.json()["items"][0]["quantity"] == 5


async def test_update_quantity_zero_removes_item(client: AsyncClient, setup):
    user, v50 = setup["user"], setup["v50"]
    headers = _auth(user)

    add = await client.post("/api/cart/items", headers=headers, json={"variant_id": v50.id, "quantity": 3})
    item_id = add.json()["id"]

    resp = await client.patch(f"/api/cart/items/{item_id}", headers=headers, json={"quantity": 0})
    assert resp.status_code == 204

    # Позиция должна исчезнуть из корзины
    cart = await client.get("/api/cart", headers=headers)
    assert cart.json()["items"] == []


async def test_update_nonexistent_item(client: AsyncClient, setup):
    resp = await client.patch(
        "/api/cart/items/99999",
        headers=_auth(setup["user"]),
        json={"quantity": 2},
    )
    assert resp.status_code == 404


# ── DELETE /cart/items/{id} ────────────────────────────────────────────────────

async def test_delete_cart_item(client: AsyncClient, setup):
    user, v50 = setup["user"], setup["v50"]
    headers = _auth(user)

    add = await client.post("/api/cart/items", headers=headers, json={"variant_id": v50.id, "quantity": 1})
    item_id = add.json()["id"]

    resp = await client.delete(f"/api/cart/items/{item_id}", headers=headers)
    assert resp.status_code == 204

    cart = await client.get("/api/cart", headers=headers)
    assert cart.json()["items"] == []


async def test_delete_nonexistent_item(client: AsyncClient, setup):
    resp = await client.delete("/api/cart/items/99999", headers=_auth(setup["user"]))
    assert resp.status_code == 404


# ── Total amount ───────────────────────────────────────────────────────────────

async def test_cart_total_amount(client: AsyncClient, setup):
    user = setup["user"]
    headers = _auth(user)

    await client.post("/api/cart/items", headers=headers, json={"variant_id": setup["v50"].id, "quantity": 2})
    await client.post("/api/cart/items", headers=headers, json={"variant_id": setup["v100"].id, "quantity": 1})

    cart = await client.get("/api/cart", headers=headers)
    data = cart.json()
    expected = setup["v50"].price * 2 + setup["v100"].price * 1
    assert data["total_amount"] == pytest.approx(expected)
