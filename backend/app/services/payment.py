"""Сервис платежей: создание Telegram-инвойса и обработка webhook.

Процесс оплаты товаров через Telegram Payments + ЮKassa:

1. POST /api/payments/{order_number}/invoice
   → вызываем Bot API createInvoiceLink
   → клиент открывает ссылку через tg.openInvoice()

2. Telegram шлёт pre_checkout_query на наш webhook
   → мы проверяем заказ и отвечаем answerPreCheckoutQuery(ok=True/False)

3. После успешной оплаты Telegram шлёт successful_payment
   → обновляем order.status_payment = "paid" + paid_at
   → сохраняем PaymentEvent

Безопасность webhook: URL содержит bot_token — знает только Telegram.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.logging import get_logger
from app.models.order import Order
from app.models.payment import PaymentEvent

log = get_logger("app.services.payment")

_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _tg_url(method: str) -> str:
    return _TELEGRAM_API.format(token=get_settings().bot_token.get_secret_value(), method=method)


async def _call_telegram(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Вызывает метод Telegram Bot API. Бросает RuntimeError при ошибке."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(_tg_url(method), json=payload)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API {method} error: {data.get('description', data)}")
    return data["result"]


async def create_invoice_link(session: AsyncSession, order: Order) -> str:
    """Создаёт Telegram invoice link для заказа.

    Бросает ValueError если заказ уже оплачен или отменён.
    Возвращает ссылку вида https://t.me/$xxxx
    """
    if order.status_payment != "pending":
        raise ValueError(f"Заказ {order.number} не в статусе pending (сейчас: {order.status_payment})")

    settings = get_settings()
    if not settings.yookassa_provider_token.get_secret_value():
        raise RuntimeError("YOOKASSA_PROVIDER_TOKEN не настроен")

    # Описание товаров (до 255 символов)
    items_desc = ", ".join(
        f"{oi.snapshot_name} {oi.snapshot_weight_g}г×{oi.quantity}"
        for oi in order.items
    )
    if len(items_desc) > 200:
        items_desc = items_desc[:200] + "..."

    # Сумма в копейках (Telegram требует целые числа)
    amount_kopecks = int(round(float(order.total_amount) * 100))

    result = await _call_telegram("createInvoiceLink", {
        "title": f"Заказ {order.number}",
        "description": items_desc or "Товары из магазина Чайное Дерево",
        "payload": order.number,  # вернётся в successful_payment.invoice_payload
        "provider_token": settings.yookassa_provider_token.get_secret_value(),
        "currency": "RUB",
        "prices": [{"label": "Товары", "amount": amount_kopecks}],
        "need_phone_number": False,
        "send_phone_number_to_provider": False,
    })

    # Логируем создание инвойса
    event = PaymentEvent(
        order_id=order.id,
        provider="telegram_yookassa",
        external_id=None,
        status="invoice_created",
        raw_payload=None,
    )
    session.add(event)
    await session.commit()

    log.info("invoice_created", order_number=order.number)
    return f"https://t.me/${result}"  # Telegram возвращает только slug


async def handle_pre_checkout(
    session: AsyncSession,
    query_id: str,
    order_number: str,
    total_amount: int,
) -> dict[str, Any]:
    """Обрабатывает pre_checkout_query от Telegram.

    Должен ответить в течение 10 секунд.
    Возвращает payload для answerPreCheckoutQuery.
    """
    stmt = select(Order).where(Order.number == order_number)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        log.warning("pre_checkout_unknown_order", order_number=order_number)
        return {"pre_checkout_query_id": query_id, "ok": False, "error_message": "Заказ не найден"}

    if order.status_payment != "pending":
        return {
            "pre_checkout_query_id": query_id,
            "ok": False,
            "error_message": "Заказ уже оплачен или отменён",
        }

    # Проверяем сумму (защита от подмены)
    expected = int(round(float(order.total_amount) * 100))
    if total_amount != expected:
        log.error("pre_checkout_amount_mismatch", expected=expected, got=total_amount, order=order_number)
        return {
            "pre_checkout_query_id": query_id,
            "ok": False,
            "error_message": "Сумма не совпадает",
        }

    return {"pre_checkout_query_id": query_id, "ok": True}


async def handle_successful_payment(
    session: AsyncSession,
    order_number: str,
    telegram_payment_charge_id: str,
    provider_payment_charge_id: str,
    total_amount: int,
    raw_payload: dict[str, Any],
) -> Order | None:
    """Обрабатывает successful_payment: помечает заказ как оплаченный."""
    stmt = select(Order).where(Order.number == order_number)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        log.error("successful_payment_unknown_order", order_number=order_number)
        return None

    if order.status_payment == "paid":
        log.warning("successful_payment_already_paid", order_number=order_number)
        return order

    order.status_payment = "paid"
    order.paid_at = datetime.now(UTC)

    event = PaymentEvent(
        order_id=order.id,
        provider="telegram_yookassa",
        external_id=provider_payment_charge_id or telegram_payment_charge_id,
        status="paid",
        raw_payload=json.dumps(raw_payload, ensure_ascii=False),
    )
    session.add(event)
    await session.commit()
    await session.refresh(order)

    log.info(
        "payment_success",
        order_number=order_number,
        charge_id=telegram_payment_charge_id,
    )
    return order
