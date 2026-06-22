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
    "in_delivery":      "🚚 В доставке",
    "at_pvz":           "🏪 В ПВЗ",
    "delivered":        "🎉 Доставлен",
    "cancelled":        "❌ Отменён",
}

# Цепочки этапов по типу доставки (в порядке отображения)
_STAGE_CHAINS: dict[str, list[tuple[str, str]]] = {
    "pickup": [
        ("new",       "🆕 Новый"),
        ("assembling","📦 Собираем"),
        ("ready",     "✅ Готов"),
        ("delivered", "🎉 Выдан"),
    ],
    "pvz": [
        ("new",       "🆕 Новый"),
        ("assembling","📦 Собираем"),
        ("ready",     "✅ Готов"),
        ("at_pvz",    "🏪 В ПВЗ"),
        ("delivered", "🎉 Доставлен"),
    ],
    "courier": [
        ("new",              "🆕 Принят"),
        ("awaiting_payment", "💳 Оплата"),
        ("in_delivery",      "🚚 В доставке"),
        ("at_pvz",           "🏪 В ПВЗ"),
        ("delivered",        "🎉 Доставлен"),
    ],
}


def _stages_line(delivery_type: str, current_status: str) -> str:
    """Строка прогресса этапов: пройденные · текущий жирный · будущие обычные."""
    chain = _STAGE_CHAINS.get(delivery_type, _STAGE_CHAINS["courier"])
    current_idx = next((i for i, (s, _) in enumerate(chain) if s == current_status), None)

    parts = []
    for i, (_, label) in enumerate(chain):
        if current_idx is None or i > current_idx:
            parts.append(label)          # будущий
        elif i == current_idx:
            parts.append(f"<b>{label}</b>")  # текущий
        else:
            parts.append(f"<s>{label}</s>")  # пройденный
    return " → ".join(parts)

# Следующие статусы — по типу доставки
_NEXT_STATUSES: dict[str, dict[str, list[tuple[str, str]]]] = {
    "pickup": {
        "new":        [("assembling", "📦 Собираем")],
        "assembling": [("ready",      "✅ Готов")],
        "ready":      [("delivered",  "🎉 Выдан")],
        "delivered":  [],
        "cancelled":  [],
    },
    "pvz": {
        "new":        [("assembling", "📦 Собираем")],
        "assembling": [("ready",      "✅ Готов")],
        "ready":      [("at_pvz",     "🏪 Отправлен в ПВЗ")],
        "at_pvz":     [("delivered",  "🎉 Доставлен")],
        "delivered":  [],
        "cancelled":  [],
    },
    "courier": {
        # new: ссылка на оплату отправляется вручную → awaiting_payment
        "new":              [],
        # awaiting_payment: сначала ждём подтверждения оплаты (paid_at)
        # после подтверждения — кнопка "В доставку" (см. _order_keyboard)
        "awaiting_payment": [("in_delivery", "🚚 В доставку")],
        "in_delivery":      [("at_pvz",      "🏪 Пришло в ПВЗ")],
        "at_pvz":           [("delivered",   "🎉 Доставлен")],
        "delivered":        [],
        "cancelled":        [],
    },
}


def _order_text(order: Order) -> str:
    # ── Шапка (неизменная часть) ──
    lines = [f"🛒 <b>Заказ {order.number}</b>"]

    if order.user:
        lines.append(f"👤 {order.user.display_name}")

    if order.delivery_info:
        di = order.delivery_info
        type_label = {"pickup": "Самовывоз", "courier": "Курьер", "pvz": "ПВЗ"}.get(di.type, di.type)
        lines.append(f"💰 <b>{float(order.total_amount):.0f} ₽</b>  ·  {type_label}")
        if di.address:
            lines.append(f"📍 {di.address}")
        if di.contact_phone:
            lines.append(f"📞 {di.contact_phone}")
    else:
        lines.append(f"💰 <b>{float(order.total_amount):.0f} ₽</b>")

    if order.items:
        lines.append("")
        lines.append("📦 <b>Состав:</b>")
        for oi in order.items:
            lines.append(f"  • {oi.snapshot_name} {oi.snapshot_weight_g}г × {oi.quantity}")

    if order.comment:
        lines.append(f"💬 {order.comment}")

    # ── Статус (меняется при каждом обновлении) ──
    lines.append("")
    lines.append("─────────────────")
    delivery_type = (order.delivery_info.type if order.delivery_info else None) or "courier"
    if order.status == "cancelled":
        lines.append("❌ <b>Отменён</b>")
    else:
        lines.append(_stages_line(delivery_type, order.status))

    if order.payment_link:
        lines.append(f"💳 <a href='{order.payment_link}'>Ссылка на оплату</a>")
    if order.tracking_link:
        lines.append(f"🚚 <a href='{order.tracking_link}'>Трек-номер</a>")

    return "\n".join(lines)


def _order_keyboard(order: Order) -> dict:
    settings = get_settings()
    base = settings.public_base_url.rstrip("/")
    current = order.status
    delivery_type = (order.delivery_info.type if order.delivery_info else None) or "courier"
    rows: list[list[dict]] = []

    # Кнопки следующих статусов — по типу доставки
    flow = _NEXT_STATUSES.get(delivery_type, _NEXT_STATUSES["courier"])
    next_statuses = flow.get(current, [])

    # Для курьера awaiting_payment: кнопки статуса показываем только после подтверждения оплаты
    payment_confirmed = order.paid_at is not None
    if delivery_type == "courier" and current == "awaiting_payment" and not payment_confirmed:
        next_statuses = []

    if next_statuses:
        status_btns = [
            {"text": label, "callback_data": f"set_status:{order.id}:{status}"}
            for status, label in next_statuses
        ]
        rows.extend([status_btns[i:i+2] for i in range(0, len(status_btns), 2)])

    # Кнопка «Отменить» — для всех незавершённых статусов
    if current not in ("delivered", "cancelled"):
        rows.append([{"text": "❌ Отменить", "callback_data": f"set_status:{order.id}:cancelled"}])

    # Дополнительные действия — зависят от типа доставки и этапа
    if delivery_type == "courier":
        if current in {"new", "awaiting_payment"}:
            # Ссылка на оплату — всегда доступна пока не оплачено
            rows.append([{"text": "💳 Ссылка на оплату", "callback_data": f"pay_link:{order.id}"}])
        if current == "awaiting_payment" and not payment_confirmed:
            # Оплата ещё не подтверждена — показываем кнопку подтверждения
            rows.append([{"text": "✅ Подтвердить оплату", "callback_data": f"confirm_payment:{order.id}"}])
        if current == "awaiting_payment" and payment_confirmed and order.user:
            # Оплата подтверждена — кнопка связи с клиентом
            rows.append([{"text": "💬 Написать клиенту", "url": f"tg://user?id={order.user.telegram_id}"}])
        if current in {"in_delivery", "at_pvz"}:
            rows.append([{"text": "🚚 Трек-номер", "callback_data": f"tracking:{order.id}"}])
    elif delivery_type == "pvz":
        if current in {"ready", "at_pvz"}:
            rows.append([{"text": "🚚 Трек-номер", "callback_data": f"tracking:{order.id}"}])
    # pickup: никаких дополнительных действий

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


async def delete_message(chat_id: int, message_id: int) -> None:
    """Удаляет сообщение (ошибки игнорирует — сообщение уже могло быть удалено)."""
    await _api_call("deleteMessage", {"chat_id": chat_id, "message_id": message_id})


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
