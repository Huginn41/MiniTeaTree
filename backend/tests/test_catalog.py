"""Тесты каталога и справочной информации."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.category import Category
from app.models.content import FaqItem, PickupPoint
from app.models.product import Product, ProductImage, ProductVariant

# ---------- Фикстуры ----------

@pytest.fixture
async def seeded_catalog(db_session):
    """Заполняет БД тестовыми категориями и товарами."""
    cat_green = Category(name="Зелёный чай", slug="green-tea", sort_order=1)
    cat_black = Category(name="Чёрный чай", slug="black-tea", sort_order=2)
    db_session.add_all([cat_green, cat_black])
    await db_session.flush()

    p1 = Product(
        category_id=cat_green.id,
        name="Сенча",
        slug="sencha",
        description="Японский зелёный чай",
        base_price=1200,
        is_active=True,
        sort_order=0,
    )
    p2 = Product(
        category_id=cat_black.id,
        name="Эрл Грей",
        slug="earl-grey",
        description="Чёрный чай с бергамотом",
        base_price=800,
        is_active=True,
        sort_order=1,
    )
    p3 = Product(
        category_id=cat_green.id,
        name="Неактивный чай",
        slug="inactive-tea",
        base_price=500,
        is_active=False,
    )
    db_session.add_all([p1, p2, p3])
    await db_session.flush()

    v1_25 = ProductVariant(product_id=p1.id, weight_g=25, price=350, in_stock=True)
    v1_50 = ProductVariant(product_id=p1.id, weight_g=50, price=650, in_stock=True)
    v2_25 = ProductVariant(product_id=p2.id, weight_g=25, price=200, in_stock=True)
    db_session.add_all([v1_25, v1_50, v2_25])
    await db_session.flush()

    img1 = ProductImage(product_id=p1.id, path="products/sencha1.jpg", is_main=True, sort=0)
    img2 = ProductImage(product_id=p1.id, path="products/sencha2.jpg", is_main=False, sort=1)
    db_session.add_all([img1, img2])
    await db_session.flush()

    await db_session.commit()
    return {
        "cat_green": cat_green,
        "cat_black": cat_black,
        "p1": p1,
        "p2": p2,
        "p1_variants": [v1_25, v1_50],
    }


@pytest.fixture
async def seeded_info(db_session):
    """FAQ и ПВЗ."""
    faq1 = FaqItem(question="Как заказать?", answer="Добавьте товар в корзину", sort=0)
    faq2 = FaqItem(question="Как оплатить?", answer="Telegram Payments", sort=1)
    pp1 = PickupPoint(name="ТЦ Центр", address="ул. Центральная, 1")
    db_session.add_all([faq1, faq2, pp1])
    await db_session.commit()
    return {"faq_count": 2, "pp_count": 1}


# ---------- Категории ----------

@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient, seeded_catalog):
    resp = await client.get("/api/catalog/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["slug"] == "green-tea"
    assert data[1]["slug"] == "black-tea"


# ---------- Товары ----------

@pytest.mark.asyncio
async def test_list_products_all(client: AsyncClient, seeded_catalog):
    resp = await client.get("/api/catalog/products")
    assert resp.status_code == 200
    data = resp.json()
    # Только активные товары.
    assert len(data) == 2
    slugs = {p["slug"] for p in data}
    assert "sencha" in slugs
    assert "earl-grey" in slugs
    assert "inactive-tea" not in slugs


@pytest.mark.asyncio
async def test_list_products_filter_category(client: AsyncClient, seeded_catalog):
    resp = await client.get("/api/catalog/products", params={"category_slug": "green-tea"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["slug"] == "sencha"


@pytest.mark.asyncio
async def test_list_products_search(client: AsyncClient, seeded_catalog):
    resp = await client.get("/api/catalog/products", params={"q": "Сенча"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["slug"] == "sencha"


@pytest.mark.asyncio
async def test_list_products_search_case_insensitive(client: AsyncClient, seeded_catalog):
    # SQLite LIKE не поддерживает кириллицу case-insensitive — используем
    # латиницу для теста. Postgres ILIKE работает и с кириллицей.
    resp = await client.get("/api/catalog/products", params={"q": "Сенча"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1


@pytest.mark.asyncio
async def test_list_products_main_image(client: AsyncClient, seeded_catalog):
    resp = await client.get("/api/catalog/products")
    data = resp.json()
    sencha = next(p for p in data if p["slug"] == "sencha")
    assert sencha["main_image"] == "products/sencha1.jpg"


@pytest.mark.asyncio
async def test_get_product_detail(client: AsyncClient, seeded_catalog):
    resp = await client.get("/api/catalog/products/sencha")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Сенча"
    assert data["description"] == "Японский зелёный чай"
    assert data["category"]["slug"] == "green-tea"
    assert len(data["variants"]) == 2
    assert len(data["images"]) == 2


@pytest.mark.asyncio
async def test_get_product_not_found(client: AsyncClient):
    resp = await client.get("/api/catalog/products/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_product_inactive_not_found(client: AsyncClient, seeded_catalog):
    resp = await client.get("/api/catalog/products/inactive-tea")
    assert resp.status_code == 404


# ---------- Info ----------

@pytest.mark.asyncio
async def test_list_banners_empty(client: AsyncClient):
    resp = await client.get("/api/info/banners")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_faq(client: AsyncClient, seeded_info):
    resp = await client.get("/api/info/faq")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["question"] == "Как заказать?"


@pytest.mark.asyncio
async def test_list_pickup_points(client: AsyncClient, seeded_info):
    resp = await client.get("/api/info/pickup-points")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "ТЦ Центр"
