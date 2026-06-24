"""Роутер платежей: webhook T Bank + страницы успеха/ошибки."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.db import get_session_factory
from app.logging import get_logger
from app.models.order import Order
from app.tbank import _verify_token

log = get_logger("app.routers.payments")

router = APIRouter(tags=["payments"])


@router.post("/payments/tbank/webhook", include_in_schema=False)
async def tbank_webhook(request: Request) -> JSONResponse:
    """Получает уведомления от T Bank об изменении статуса платежа."""
    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"ok": False}, status_code=400)

    s = get_settings()
    secret = s.tbank_secret_key.get_secret_value()

    # Проверяем подпись
    if secret and not _verify_token(data, secret):
        log.warning("tbank_webhook_invalid_token", data=data)
        return JSONResponse({"ok": False}, status_code=400)

    status = data.get("Status", "")
    order_number = data.get("OrderId", "")
    payment_id = str(data.get("PaymentId", ""))

    log.info("tbank_webhook", order_number=order_number, status=status, payment_id=payment_id)

    if status not in ("CONFIRMED", "AUTHORIZED"):
        # Нас интересует только подтверждение оплаты
        return JSONResponse({"ok": True})

    async with get_session_factory()() as session:
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.user), selectinload(Order.items), selectinload(Order.delivery_info))
            .where(Order.number == order_number)
        )
        order = result.scalar_one_or_none()
        if not order:
            log.warning("tbank_webhook_order_not_found", order_number=order_number)
            return JSONResponse({"ok": True})

        from datetime import datetime, timezone
        order.paid_at = datetime.now(timezone.utc)
        order.tbank_payment_id = payment_id
        # Для курьера: ждём оплату → переходим в awaiting_payment (уже установлен при создании ссылки)
        # При CONFIRMED оплата подтверждена — помечаем paid_at, дальше менеджер нажимает "В доставку"
        await session.commit()

    # Обновляем карточку у менеджеров в Telegram
    try:
        from app.bot.notify import update_order_notifications
        await update_order_notifications(order.id)
    except Exception as exc:
        log.warning("tbank_webhook_notify_failed", error=str(exc))

    return JSONResponse({"ok": True})


@router.get("/payments/tbank/success", response_class=HTMLResponse, include_in_schema=False)
async def tbank_success(request: Request) -> HTMLResponse:
    return HTMLResponse(_result_page(
        title="Оплата прошла успешно",
        icon="✅",
        color="#1b873f",
        message="Ваш заказ оплачен. Мы уже начали его собирать!",
        sub="Вернитесь в Telegram, чтобы следить за статусом заказа.",
    ))


@router.get("/payments/tbank/fail", response_class=HTMLResponse, include_in_schema=False)
async def tbank_fail(request: Request) -> HTMLResponse:
    return HTMLResponse(_result_page(
        title="Оплата не прошла",
        icon="❌",
        color="#dc3545",
        message="Не удалось провести оплату.",
        sub="Вернитесь в Telegram и попробуйте ещё раз или свяжитесь с нами.",
    ))


def _result_page(*, title: str, icon: str, color: str, message: str, sub: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
  body {{ margin:0; background:#f4f6fb; display:flex; align-items:center; justify-content:center;
         min-height:100vh; font-family:-apple-system,sans-serif; }}
  .card {{ background:#fff; border-radius:20px; padding:40px 32px; text-align:center;
           max-width:360px; box-shadow:0 4px 24px rgba(0,0,0,.08); }}
  .icon {{ font-size:56px; margin-bottom:16px; }}
  h1 {{ font-size:20px; font-weight:700; color:#212529; margin:0 0 10px; }}
  p {{ font-size:14px; color:#6c757d; margin:0 0 6px; line-height:1.5; }}
  .badge {{ display:inline-block; margin-top:20px; padding:10px 24px; border-radius:12px;
            background:{color}; color:#fff; font-size:14px; font-weight:600; text-decoration:none; }}
</style>
</head>
<body>
<div class="card">
  <div class="icon">{icon}</div>
  <h1>{title}</h1>
  <p>{message}</p>
  <p>{sub}</p>
  <a class="badge" href="https://t.me">Вернуться в Telegram</a>
</div>
</body>
</html>"""
