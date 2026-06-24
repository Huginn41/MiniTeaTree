"""Роутер заказов и личного кабинета: создание, список, детали, профиль."""

from __future__ import annotations

from decimal import Decimal
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models.bonus import BonusTransaction, BonusTier, ShopSettings
from app.models.referral import ReferralLink
from app.models.cart import Cart, CartItem
from app.models.delivery import DeliveryInfo
from app.models.user import User
from app.models.enums import DELIVERY_TYPE_VALUES, ORDER_STATUS_VALUES
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductVariant
from app.schemas import (
    DeliveryInfoOut,
    OrderBrief,
    OrderCreate,
    OrderDetail,
    OrderItemSnapshot,
    OrderStatusUpdate,
    ProfileOut,
)

router = APIRouter(tags=["orders", "profile"])


# ---------- Profile ----------

@router.get("/profile/me", response_model=ProfileOut)
async def get_profile(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProfileOut:
    """Профиль текущего пользователя."""
    u = user.user

    # Определяем текущий процент кешбэка по сумме покупок пользователя.
    tiers_res = await session.execute(
        select(BonusTier).order_by(BonusTier.min_amount.desc())
    )
    tiers = tiers_res.scalars().all()
    sum_res = await session.execute(
        select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.user_id == u.id)
    )
    total_spent = float(sum_res.scalar() or 0)
    cashback_pct = 0.0
    for t in tiers:
        if total_spent >= float(t.min_amount):
            cashback_pct = float(t.cashback_pct)
            break

    return ProfileOut(
        telegram_id=u.telegram_id,
        first_name=u.first_name,
        last_name=u.last_name,
        username=u.username,
        phone=u.phone,
        bonus_balance=float(u.bonus_balance),
        cashback_pct=cashback_pct,
    )


# ---------- Orders ----------

def _order_number_from_id(order_id: int) -> str:
    """Генерирует номер заказа на основе ID — без race condition."""
    return f"ЧД-{order_id:06d}"


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
                status=o.status,
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
    return OrderDetail(
        id=order.id,
        number=order.number,
        total_amount=float(order.total_amount),
        bonus_used=float(order.bonus_used),
        delivery_cost=float(order.delivery_cost),
        status=order.status,
        payment_link=order.payment_link,
        tracking_link=order.tracking_link,
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
        delivery_info=DeliveryInfoOut.model_validate(order.delivery_info) if order.delivery_info else None,
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

    # Загружаем настройки магазина для валидации бонусов.
    settings_res = await session.execute(select(ShopSettings).where(ShopSettings.id == 1))
    settings = settings_res.scalar_one_or_none()
    max_bonus_pct = settings.bonus_max_payment_pct if settings else 0
    no_cashback_on_redemption = settings.bonus_no_cashback_on_redemption if settings else False

    use_bonus = round(float(body.use_bonus_amount or 0), 2)
    # Блокируем строку пользователя, чтобы исключить race condition при списании бонусов
    u_result = await session.execute(
        select(User).where(User.id == user.user.id).with_for_update()
    )
    u = u_result.scalar_one()
    if use_bonus > 0:
        if max_bonus_pct == 0:
            raise HTTPException(status_code=400, detail="Оплата баллами отключена")
        max_allowed = round(total * max_bonus_pct / 100, 2)
        if use_bonus > max_allowed:
            use_bonus = max_allowed
        if use_bonus > float(u.bonus_balance):
            use_bonus = round(float(u.bonus_balance), 2)
        use_bonus = round(use_bonus, 2)

    # Создаём заказ. number присваивается после flush() — на основе order.id без гонки.
    import uuid as _uuid
    order = Order(
        user_id=u.id,
        number=_uuid.uuid4().hex,  # уникальный placeholder до получения ID
        total_amount=total,
        bonus_used=use_bonus,
        status="new",
        comment=body.comment,
    )
    session.add(order)
    await session.flush()
    order.number = _order_number_from_id(order.id)

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

    # Списание баллов.
    if use_bonus > 0:
        u.bonus_balance = Decimal(str(float(u.bonus_balance) - use_bonus))
        session.add(BonusTransaction(
            user_id=u.id,
            order_id=order.id,
            delta=Decimal(str(-use_bonus)),
            reason="order_redemption",
            note=f"Списание по заказу {order.number}",
        ))

    # Начисление кешбэка (после списания, если не отключено настройкой).
    accrue_cashback = not (use_bonus > 0 and no_cashback_on_redemption)
    if accrue_cashback:
        tiers_r = await session.execute(
            select(BonusTier).order_by(BonusTier.min_amount.desc())
        )
        tiers_list = tiers_r.scalars().all()
        sum_r = await session.execute(
            select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.user_id == u.id)
        )
        total_spent = float(sum_r.scalar() or 0)
        cashback_pct_val = 0.0
        for t in tiers_list:
            if total_spent >= float(t.min_amount):
                cashback_pct_val = float(t.cashback_pct)
                break
        if cashback_pct_val > 0:
            cashback_amount = round(total * cashback_pct_val / 100, 2)
            u.bonus_balance = Decimal(str(float(u.bonus_balance) + cashback_amount))
            session.add(BonusTransaction(
                user_id=u.id,
                order_id=order.id,
                delta=Decimal(str(cashback_amount)),
                reason="order_cashback",
                note=f"Кешбэк {cashback_pct_val}% за заказ {order.number}",
            ))
            session.add(u)

    # ── Реферальные хуки ──────────────────────────────────────────────────────

    # Блок А: активируем велком-слоты при первой покупке донора.
    orders_count_r = await session.execute(
        select(func.count()).select_from(Order).where(Order.user_id == u.id)
    )
    orders_count = orders_count_r.scalar() or 0
    # orders_count включает текущий заказ (flush уже выполнен выше)
    if orders_count == 1 and u.referral_slots == 0:
        from app.config import get_settings as _get_settings
        _s = _get_settings()
        u.referral_slots = _s.referral_slots_per_donor
        session.add(u)

    # Блок Б: вознаграждение донора (5% от покупки реципиента, до 3 покупок).
    if u.referrer_id:
        ref_link_r = await session.execute(
            select(ReferralLink)
            .where(ReferralLink.recipient_id == u.id)
            .with_for_update()
        )
        ref_link = ref_link_r.scalar_one_or_none()
        if ref_link and ref_link.welcome_paid:
            from app.config import get_settings as _get_settings
            _s = _get_settings()
            max_purchases = _s.referral_max_rewarded_purchases
            reward_pct = _s.referral_donor_reward_pct
            if ref_link.purchases_rewarded < max_purchases:
                reward = round(total * reward_pct / 100, 2)
                if reward > 0:
                    donor_r = await session.execute(
                        select(User).where(User.id == u.referrer_id).with_for_update()
                    )
                    donor = donor_r.scalar_one_or_none()
                    if donor:
                        donor.bonus_balance = Decimal(
                            str(float(donor.bonus_balance) + reward)
                        )
                        session.add(BonusTransaction(
                            user_id=donor.id,
                            order_id=order.id,
                            delta=Decimal(str(reward)),
                            reason="referral_purchase_reward",
                            note=(
                                f"{reward_pct}% с покупки реципиента "
                                f"#{u.id} (заказ {order.number}), "
                                f"покупка {ref_link.purchases_rewarded + 1}/{max_purchases}"
                            ),
                        ))
                        session.add(donor)
                ref_link.purchases_rewarded += 1
                session.add(ref_link)

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
        bonus_used=float(order.bonus_used),
        delivery_cost=float(order.delivery_cost),
        status=order.status,
        payment_link=order.payment_link,
        tracking_link=order.tracking_link,
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
        delivery_info=DeliveryInfoOut.model_validate(delivery),
    )


@router.patch("/orders/{order_number}/status", response_model=OrderDetail)
async def update_order_status(
    order_number: str,
    body: OrderStatusUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> OrderDetail:
    """Обновляет статус доставки заказа (только для is_admin=True).

    После смены статуса отправляет уведомление клиенту через бота.
    """
    if not user.user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    if body.status not in ORDER_STATUS_VALUES:
        raise HTTPException(status_code=400, detail="Invalid status")

    stmt = select(Order).where(Order.number == order_number)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    old_status = order.status
    order.status = body.status

    if body.status == "delivered":
        order.delivered_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(order, ["items", "delivery_info", "user"])

    # Уведомляем клиента если статус изменился
    if old_status != body.status and order.user:
        try:
            from app.bot.status_notify import notify_status_changed
            await notify_status_changed(order, body.status, order.user.telegram_id)
        except Exception:
            pass

    di = order.delivery_info
    return OrderDetail(
        id=order.id,
        number=order.number,
        total_amount=float(order.total_amount),
        bonus_used=float(order.bonus_used),
        delivery_cost=float(order.delivery_cost),
        status=order.status,
        payment_link=order.payment_link,
        tracking_link=order.tracking_link,
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
        delivery_info=DeliveryInfoOut.model_validate(di) if di else None,
    )
