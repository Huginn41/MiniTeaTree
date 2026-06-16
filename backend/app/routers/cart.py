"""Роутер корзины: просмотр, добавление, обновление, удаление."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models.cart import Cart, CartItem
from app.models.product import Product, ProductVariant
from app.schemas import CartItemAdd, CartItemOut, CartItemUpdate, CartOut, VariantOut

router = APIRouter(prefix="/cart", tags=["cart"])


async def _ensure_cart(
    session: AsyncSession, user_id: int
) -> Cart:
    """Получить или создать корзину пользователя."""
    stmt = select(Cart).where(Cart.user_id == user_id)
    result = await session.execute(stmt)
    cart = result.scalar_one_or_none()
    if cart is None:
        cart = Cart(user_id=user_id)
        session.add(cart)
        await session.flush()
    return cart


@router.get("", response_model=CartOut)
async def get_cart(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CartOut:
    """Получить корзину пользователя."""
    cart = await _ensure_cart(session, user.user.id)
    await session.refresh(cart, ["items"])

    items_out: list[CartItemOut] = []
    total = 0.0
    for ci in cart.items:
        v = ci.variant
        # Ищем товар для имени и фото.
        product_stmt = select(Product).where(Product.id == v.product_id)
        product_result = await session.execute(product_stmt)
        product = product_result.scalar_one_or_none()
        product_name = product.name if product else ""
        product_slug = product.slug if product else ""
        main_image = None
        if product:
            for img in product.images:
                if img.is_main:
                    main_image = img.path
                    break
            if not main_image and product.images:
                main_image = product.images[0].path

        unit_price = float(v.price) if v else 0
        total += unit_price * ci.quantity

        items_out.append(
            CartItemOut(
                id=ci.id,
                variant=VariantOut.model_validate(v),
                quantity=ci.quantity,
                product_name=product_name,
                product_slug=product_slug,
                main_image=main_image,
            )
        )

    return CartOut(items=items_out, total_amount=total)


@router.post("/items", response_model=CartItemOut, status_code=201)
async def add_to_cart(
    body: CartItemAdd,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CartItemOut:
    """Добавить вариант товара в корзину."""
    # Проверяем, что вариант существует и в наличии.
    stmt = select(ProductVariant).where(
        ProductVariant.id == body.variant_id,
        ProductVariant.in_stock.is_(True),
    )
    result = await session.execute(stmt)
    variant = result.scalar_one_or_none()
    if variant is None:
        raise HTTPException(status_code=404, detail="Variant not found or not in stock")

    cart = await _ensure_cart(session, user.user.id)
    await session.refresh(cart, ["items"])

    # Ищем существующую позицию.
    existing = None
    for ci in cart.items:
        if ci.variant_id == body.variant_id:
            existing = ci
            break

    if existing is not None:
        existing.quantity += body.quantity
    else:
        existing = CartItem(cart_id=cart.id, variant_id=body.variant_id, quantity=body.quantity)
        session.add(existing)

    await session.commit()
    await session.refresh(existing)

    # Данные товара.
    product_stmt = select(Product).where(Product.id == variant.product_id)
    product_result = await session.execute(product_stmt)
    product = product_result.scalar_one_or_none()

    return CartItemOut(
        id=existing.id,
        variant=VariantOut.model_validate(variant),
        quantity=existing.quantity,
        product_name=product.name if product else "",
        product_slug=product.slug if product else "",
        main_image=None,
    )


@router.patch("/items/{item_id}", response_model=CartItemOut)
async def update_cart_item(
    item_id: int,
    body: CartItemUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CartItemOut:
    """Обновить количество (или удалить при quantity=0)."""
    cart = await _ensure_cart(session, user.user.id)
    await session.refresh(cart, ["items"])

    target = None
    for ci in cart.items:
        if ci.id == item_id:
            target = ci
            break
    if target is None:
        raise HTTPException(status_code=404, detail="Cart item not found")

    if body.quantity == 0:
        await session.delete(target)
        await session.commit()
        raise HTTPException(status_code=204, detail="Removed")

    target.quantity = body.quantity
    await session.commit()
    await session.refresh(target)

    variant = target.variant
    product_stmt = select(Product).where(Product.id == variant.product_id)
    product_result = await session.execute(product_stmt)
    product = product_result.scalar_one_or_none()

    return CartItemOut(
        id=target.id,
        variant=VariantOut.model_validate(variant),
        quantity=target.quantity,
        product_name=product.name if product else "",
        product_slug=product.slug if product else "",
        main_image=None,
    )


@router.delete("/items/{item_id}", status_code=204)
async def delete_cart_item(
    item_id: int,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Удалить позицию из корзины."""
    cart = await _ensure_cart(session, user.user.id)
    await session.refresh(cart, ["items"])

    target = None
    for ci in cart.items:
        if ci.id == item_id:
            target = ci
            break
    if target is None:
        raise HTTPException(status_code=404, detail="Cart item not found")

    await session.delete(target)
    await session.commit()
