"""Уведомления через Telegram Bot API.

notify_new_order() вызывается из orders router сразу после создания заказа.
Шлёт сообщение всем активным NotificationTarget с ролью shop/owner/manager.

Используем прямые вызовы Bot API через httpx, без aiogram, чтобы не зависеть
от polling/webhook — вызов чисто outbound.
"""

from __future__ import annotations

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.logging import get_logger
from app.models.notification import NotificationTarget
from app.models.order import Order

log = get_logger("app.bot.notify")

_NOTIFY_ROLES = {"shop", "owner", "manager"}

# order_id → [(chat_id, message_id)] — для редактирования карточек при смене статуса
_order_messages: dict[int, list[tuple[int, int]]] = {}

_STATUS_LABELS = {
    "new":              "🆕 Новый",
    "assembling":       "📦 Собираем",
    "ready":            "✅ Готов",
    "awaiting_payment": "💳 Ожидает оплаты",
    "in_delivery":      "🚚 В доставку",
    "at_pvz":           "🏪 В ПВЗ",
    "delivered":        "🎉 Доставлен",
    "cancelled":        "❌ Отменён",
}

# Следующие статусы для каждого текущего — логика пошаговой обработки
_NEXT_STATUSES: dict[str, list[tuple[str, str]]] = {
    "new":              [("assembling",       "📦 Собираем")],
    "assembling":       [("ready",            "✅ Готов")],
    "ready":            [("awaiting_payment", "💳 Ожид. оплаты"),
                         ("in_delivery",      "🚚 В доставку"),
                         ("at_pvz",           "🏪 В ПВЗ")],
    "awaiting_payment": [("in_delivery",      "🚚 В доставку"),
                         ("at_pvz",           "🏪 В ПВЗ")],
    "in_delivery":      [("delivered",        "🎉 Доставлен")],
    "at_pvz":           [("delivered",        "🎉 Доставлен")],
    "delivered":        [],
    "cancelled":        [],
}

_PRE_DELIVERY = {"new", "assembling", "ready", "awaiting_payment"}
_IN_DELIVERY  = {"in_delivery", "at_pvz"}


def _order_text(order: Order) -> str:
    status_label = _STATUS_LABELS.get(order.status, order.status)
    lines = [f"🛒 <b>Заказ {order.number}</b>  |  {status_label}"]

    if order.user:
        lines.append(f"👤 {order.user.display_name}")

    lines.append(f"💰 Сумма: <b>{float(order.total_amount):.0f} ₽</b>")

    if order.delivery_info:
        di = order.delivery_info
        type_label = {"pickup": "Самовывоз", "courier": "Курьер", "pvz": "ПВЗ"}.get(di.type, di.type)
        lines.append(f"🚚 {type_label}")
        if di.address:
            lines.append(f"📍 {di.address}")
        if di.contact_phone:
            lines.append(f"📞 {di.contact_phone}")

    if order.items:
        lines.append("")
        lines.append("📦 <b>Состав:</b>")
        for oi in order.items:
            lines.append(f"  • {oi.snapshot_name} {oi.snapshot_weight_g}г × {oi.quantity}")

    if order.comment:
        lines.append(f"\n💬 {order.comment}")

    if order.payment_link:
        lines.append(f"\n💳 <a href='{order.payment_link}'>Ссылка на оплату</a>")
    if order.tracking_link:
        lines.append(f"🚚 <a href='{order.tracking_link}'>Трек-номер</a>")

    return "\n".join(lines)


def _order_keyboard(order: Order) -> dict:
    settings = get_settings()
    base = settings.public_base_url.rstrip("/")
    current = order.status
    rows: list[list[dict]] = []

    # Кнопки следующих статусов по логике флоу
    next_statuses = _NEXT_STATUSES.get(current, [])
    if next_statuses:
        status_btns = [
            {"text": label, "callback_data": f"set_status:{order.id}:{status}"}
            for status, label in next_statuses
        ]
        rows.extend([status_btns[i:i+2] for i in range(0, len(status_btns), 2)])

    # Кнопка «Отменить» — для всех незавершённых статусов
    if current not in ("delivered", "cancelled"):
        rows.append([{"text": "❌ Отменить", "callback_data": f"set_status:{order.id}:cancelled"}])

    # Действия — зависят от этапа
    action_row = []
    if current in _PRE_DELIVERY:
        action_row.append({"text": "💳 Ссылка на оплату", "callback_data": f"pay_link:{order.id}"})
    if current in _IN_DELIVERY:
        action_row.append({"text": "🚚 Трек-номер", "callback_data": f"tracking:{order.id}"})
    if action_row:
        rows.append(action_row)

    # CRM
    rows.append([{"text": "🔍 Открыть в CRM", "url": f"{base}/crm/order/{order.id}"}])

    return {"inline_keyboard": rows}


async def _api_call(method: str, payload: dict) -> dict:
    """Вызов Telegram Bot API. Возвращает response dict."""
    settings = get_settings()
    token = settings.bot_token.get_secret_value()
    if not token or token == "0:fake":
        return {"ok": False}
    base = (settings.telegram_api_base_url or "https://api.telegram.org").rstrip("/")
    url = f"{base}/bot{token}/{method}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
        return resp.json()
    except Exception as exc:
        log.error("telegram_api_error", method=method, error=str(exc))
        return {"ok": False}


async def _send_message(chat_id: int, text: str, reply_markup: dict | None = None) -> int | None:
    """Отправляет сообщение. Возвращает message_id при успехе, None при ошибке."""
    payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    result = await _api_call("sendMessage", payload)
    if not result.get("ok"):
        log.warning("telegram_send_failed", chat_id=chat_id, resp=result)
        return None
    return result.get("result", {}).get("message_id")


async def _edit_message(chat_id: int, message_id: int, text: str, reply_markup: dict | None = None) -> bool:
    """Редактирует существующее сообщение."""
    payload: dict = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    result = await _api_call("editMessageText", payload)
    return bool(result.get("ok"))


async def notify_new_order(order: Order, session: AsyncSession) -> int:
    """Уведомляет всех активных менеджеров о новом заказе с кнопками."""
    stmt = select(NotificationTarget).where(
        NotificationTarget.is_active.is_(True),
        NotificationTarget.role.in_(_NOTIFY_ROLES),
    )
    result = await session.execute(stmt)
    targets = result.scalars().all()

    if not targets:
        log.info("no_notification_targets", order_number=order.number)
        return 0

    text = _order_text(order)
    keyboard = _order_keyboard(order)
    sent = 0
    _order_messages[order.id] = []
    for target in targets:
        msg_id = await _send_message(target.telegram_id, text, reply_markup=keyboard)
        if msg_id:
            _order_messages[order.id].append((target.telegram_id, msg_id))
            sent += 1

    log.info("order_notifications_sent", order_number=order.number, sent=sent, total=len(targets))
    return sent


async def update_order_notifications(order_id: int) -> None:
    """Обновляет карточки заказа у всех менеджеров после смены статуса."""
    msgs = _order_messages.get(order_id)
    if not msgs:
        return

    from sqlalchemy.orm import selectinload
    from app.db import get_session_factory

    async with get_session_factory()() as s:
        result = await s.execute(
            select(Order)
            .options(
                selectinload(Order.user),
                selectinload(Order.items),
                selectinload(Order.delivery_info),
            )
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

    if not order:
        return

    text = _order_text(order)
    keyboard = _order_keyboard(order)
    for chat_id, message_id in msgs:
        await _edit_message(chat_id, message_id, text, keyboard)
