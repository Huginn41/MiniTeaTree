"""Роутер платежей: создание инвойса и обработка Telegram webhook."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.deps import CurrentUser, get_current_user
from app.models.order import Order
from app.services.payment import (
    create_invoice_link,
    handle_pre_checkout,
    handle_successful_payment,
)

router = APIRouter(tags=["payments"])


class InvoiceResponse(BaseModel):
    invoice_url: str
    order_number: str


@router.post("/payments/{order_number}/invoice", response_model=InvoiceResponse)
async def create_invoice(
    order_number: str,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InvoiceResponse:
    """Создаёт ссылку на оплату заказа через Telegram Payments.

    Клиент вызывает tg.openInvoice(url) для открытия платёжного окна.
    Только для заказов в статусе pending, принадлежащих текущему пользователю.
    """
    stmt = select(Order).where(
        Order.number == order_number,
        Order.user_id == user.user.id,
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    try:
        url = await create_invoice_link(session, order)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return InvoiceResponse(invoice_url=url, order_number=order_number)


@router.post("/payments/webhook/telegram/{token_suffix}", include_in_schema=False)
async def telegram_webhook(
    token_suffix: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Webhook для Telegram Bot API — pre_checkout_query + successful_payment.

    URL содержит последние 8 символов bot_token как дополнительную защиту.
    Telegram шлёт сюда обновления после настройки setWebhook.
    """
    from app.config import get_settings
    from app.services.payment import _call_telegram

    settings = get_settings()
    bot_token = settings.bot_token.get_secret_value()

    # Проверяем суффикс как простую защиту (последние 8 символов токена)
    if not bot_token or not bot_token.endswith(token_suffix):
        return JSONResponse(status_code=403, content={"ok": False})

    try:
        update = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"ok": False})

    # --- pre_checkout_query ---
    if "pre_checkout_query" in update:
        pcq = update["pre_checkout_query"]
        answer = await handle_pre_checkout(
            session=session,
            query_id=pcq["id"],
            order_number=pcq.get("invoice_payload", ""),
            total_amount=pcq.get("total_amount", 0),
        )
        await _call_telegram("answerPreCheckoutQuery", answer)
        return JSONResponse({"ok": True})

    # --- successful_payment ---
    if "message" in update and "successful_payment" in update.get("message", {}):
        sp = update["message"]["successful_payment"]
        await handle_successful_payment(
            session=session,
            order_number=sp.get("invoice_payload", ""),
            telegram_payment_charge_id=sp.get("telegram_payment_charge_id", ""),
            provider_payment_charge_id=sp.get("provider_payment_charge_id", ""),
            total_amount=sp.get("total_amount", 0),
            raw_payload=update["message"],
        )
        return JSONResponse({"ok": True})

    # Прочие обновления — просто подтверждаем
    return JSONResponse({"ok": True})
