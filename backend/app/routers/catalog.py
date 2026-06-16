"""Роутер каталога: категории, товары (список + фильтр + поиск), детали."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.category import Category
from app.models.product import Product
from app.schemas import CategoryBrief, ProductDetail, ProductListItem

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/categories", response_model=list[CategoryBrief])
async def list_categories(
    session: AsyncSession = Depends(get_db),
) -> list[CategoryBrief]:
    """Список активных категорий (упорядочен по sort_order)."""
    stmt = (
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.sort_order, Category.id)
    )
    result = await session.execute(stmt)
    return [CategoryBrief.model_validate(c) for c in result.scalars().all()]


@router.get("/products", response_model=list[ProductListItem])
async def list_products(
    category_slug: str | None = Query(None, description="Фильтр по slug категории"),
    q: str | None = Query(None, description="Поиск по названию/описанию"),
    session: AsyncSession = Depends(get_db),
) -> list[ProductListItem]:
    """Список активных товаров с фильтрацией и поиском."""
    stmt = (
        select(Product)
        .where(Product.is_active.is_(True))
        .order_by(Product.sort_order, Product.id)
    )

    if category_slug is not None:
        stmt = stmt.join(Category).where(Category.slug == category_slug)

    if q is not None:
        pattern = f"%{q}%"
        stmt = stmt.where(
            Product.name.ilike(pattern) | Product.description.ilike(pattern)
        )

    result = await session.execute(stmt)
    products = result.scalars().all()

    items: list[ProductListItem] = []
    for p in products:
        # Главное фото.
        main_image = None
        for img in p.images:
            if img.is_main:
                main_image = img.path
                break
        if not main_image and p.images:
            main_image = p.images[0].path

        items.append(
            ProductListItem(
                id=p.id,
                name=p.name,
                slug=p.slug,
                base_price=float(p.base_price),
                origin=p.origin,
                category=CategoryBrief.model_validate(p.category),
                main_image=main_image,
                variants=[v for v in p.variants if v.in_stock],
            )
        )
    return items


@router.get("/products/{slug}", response_model=ProductDetail)
async def get_product(
    slug: str,
    session: AsyncSession = Depends(get_db),
) -> ProductDetail:
    """Детали товара по slug."""
    stmt = select(Product).where(Product.slug == slug, Product.is_active.is_(True))
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()
    if product is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Product not found")

    tags_list = product.tags.split(",") if product.tags else []

    return ProductDetail(
        id=product.id,
        name=product.name,
        slug=product.slug,
        description=product.description,
        base_price=float(product.base_price),
        origin=product.origin,
        tags=tags_list,
        category=CategoryBrief.model_validate(product.category),
        variants=product.variants,
        images=product.images,
    )
