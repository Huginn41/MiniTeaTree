"""Роутер заказов и личного кабинета: создание, список, детали, профиль."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models.cart import Cart, CartItem
from app.models.delivery import DeliveryInfo
from app.models.enums import DELIVERY_TYPE_VALUES, PAYMENT_STATUS_VALUES
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductVariant
from app.schemas import (
    OrderBrief,
    OrderCreate,
    OrderDetail,
    OrderItemSnapshot,
    ProfileOut,
)

router = APIRouter(tags=["orders", "profile"])


# ---------- Profile ----------

@router.get("/profile/me", response_model=ProfileOut)
async def get_profile(
    user: CurrentUser = Depends(get_current_user),
) -> ProfileOut:
    """Профиль текущего пользователя."""
    u = user.user
    return ProfileOut(
        telegram_id=u.telegram_id,
        first_name=u.first_name,
        last_name=u.last_name,
        username=u.username,
        phone=u.phone,
    )


# ---------- Orders ----------

async def _generate_order_number(session: AsyncSession) -> str:
    """Генерирует номер заказа: ЧД-000001, ЧД-000002 ..."""
    from sqlalchemy import func

    stmt = select(func.count()).select_from(Order)
    result = await session.execute(stmt)
    count = result.scalar() or 0
    return f"ЧД-{count + 1:06d}"


@router.get("/orders", response_model=list[OrderBrief])
async def list_orders(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[OrderBrief]:
    """Список заказов пользователя (новые сверху)."""
    stmt = (
        select(Order)
        .where(Order.user_id == user.user.id)
        .order_by(Order.created_at.desc())
    )
    result = await session.execute(stmt)
    orders = result.scalars().all()

    items: list[OrderBrief] = []
    for o in orders:
        items_count = len(o.items)
        items.append(
            OrderBrief(
                id=o.id,
                number=o.number,
                total_amount=float(o.total_amount),
                status_payment=o.status_payment,
                status_delivery=o.status_delivery,
                created_at=o.created_at,
                items_count=items_count,
            )
        )
    return items


@router.get("/orders/{order_number}", response_model=OrderDetail)
async def get_order(
    order_number: str,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> OrderDetail:
    """Детали заказа по номеру."""
    stmt = select(Order).where(
        Order.number == order_number,
        Order.user_id == user.user.id,
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    delivery_out = None
    if order.delivery_info:
        di = order.delivery_info
        delivery_out = {
            "type": di.type,
            "address": di.address or "",
            "contact_phone": di.contact_phone,
        }

    return OrderDetail(
        id=order.id,
        number=order.number,
        total_amount=float(order.total_amount),
        delivery_cost=float(order.delivery_cost),
        status_payment=order.status_payment,
        status_delivery=order.status_delivery,
        comment=order.comment,
        paid_at=order.paid_at,
        delivered_at=order.delivered_at,
        created_at=order.created_at,
        items=[
            OrderItemSnapshot(
                id=oi.id,
                product_id=oi.product_id,
                variant_id=oi.variant_id,
                quantity=oi.quantity,
                unit_price=float(oi.unit_price),
                snapshot_name=oi.snapshot_name,
                snapshot_weight_g=oi.snapshot_weight_g,
            )
            for oi in order.items
        ],
        delivery_info=delivery_out,
    )


@router.post("/orders", response_model=OrderDetail, status_code=201)
async def create_order(
    body: OrderCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> OrderDetail:
    """Создаёт заказ из корзины, очищает корзину.

    Валидирует:
    - Корзина не пуста.
    - delivery_type в допустимых значениях.
    - Все варианты в наличии (на момент заказа).
    """
    # Валидация типа доставки.
    if body.delivery_type not in DELIVERY_TYPE_VALUES:
        raise HTTPException(status_code=400, detail="Invalid delivery_type")

    # Получаем корзину.
    stmt = select(Cart).where(Cart.user_id == user.user.id)
    result = await session.execute(stmt)
    cart = result.scalar_one_or_none()
    if cart is None or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    await session.refresh(cart, ["items"])

    # Собираем позиции, снапшотим цены.
    order_items_data: list[tuple[CartItem, ProductVariant, Product]] = []
    total = 0.0

    for ci in cart.items:
        variant_stmt = select(ProductVariant).where(ProductVariant.id == ci.variant_id)
        v_result = await session.execute(variant_stmt)
        variant = v_result.scalar_one_or_none()
        if variant is None or not variant.in_stock:
            raise HTTPException(
                status_code=400,
                detail=f"Variant {ci.variant_id} not available",
            )

        product_stmt = select(Product).where(Product.id == variant.product_id)
        p_result = await session.execute(product_stmt)
        product = p_result.scalar_one_or_none()
        product_name = product.name if product else "Unknown"

        unit_price = float(variant.price)
        total += unit_price * ci.quantity
        order_items_data.append((ci, variant, product_name))

    # Создаём заказ.
    number = await _generate_order_number(session)
    order = Order(
        user_id=user.user.id,
        number=number,
        total_amount=total,
        status_payment="pending",
        status_delivery="new",
        comment=body.comment,
    )
    session.add(order)
    await session.flush()

    # Создаём позиции заказа (снапшот).
    for ci, variant, product_name in order_items_data:
        oi = OrderItem(
            order_id=order.id,
            product_id=variant.product_id,
            variant_id=variant.id,
            quantity=ci.quantity,
            unit_price=float(variant.price),
            snapshot_name=product_name,
            snapshot_weight_g=variant.weight_g,
        )
        session.add(oi)

    # Информация о доставке.
    delivery = DeliveryInfo(
        order_id=order.id,
        type=body.delivery_type,
        address=body.address,
        contact_phone=body.contact_phone,
    )
    session.add(delivery)

    # Очищаем корзину.
    for ci in cart.items:
        await session.delete(ci)

    await session.commit()
    await session.refresh(order, ["items", "delivery_info"])

    # Уведомляем менеджеров в фоне (ошибка не ломает ответ клиенту).
    try:
        from app.bot.notify import notify_new_order
        await notify_new_order(order, session)
    except Exception:
        pass

    return OrderDetail(
        id=order.id,
        number=order.number,
        total_amount=float(order.total_amount),
        delivery_cost=float(order.delivery_cost),
        status_payment=order.status_payment,
        status_delivery=order.status_delivery,
        comment=order.comment,
        paid_at=order.paid_at,
        delivered_at=order.delivered_at,
        created_at=order.created_at,
        items=[
            OrderItemSnapshot(
                id=oi.id,
                product_id=oi.product_id,
                variant_id=oi.variant_id,
                quantity=oi.quantity,
                unit_price=float(oi.unit_price),
                snapshot_name=oi.snapshot_name,
                snapshot_weight_g=oi.snapshot_weight_g,
            )
            for oi in order.items
        ],
        delivery_info={
            "type": delivery.type,
            "address": delivery.address,
            "contact_phone": delivery.contact_phone,
        },
    )
