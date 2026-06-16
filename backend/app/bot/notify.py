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


def _order_text(order: Order) -> str:
    """Форматирует текст уведомления о новом заказе."""
    lines = [
        f"🛒 <b>Новый заказ {order.number}</b>",
        f"💰 Сумма: {float(order.total_amount):.0f} ₽",
    ]

    if order.delivery_info:
        di = order.delivery_info
        type_label = {"pickup": "Самовывоз", "courier": "Курьер", "pvz": "ПВЗ"}.get(di.type, di.type)
        lines.append(f"🚚 Доставка: {type_label}")
        if di.address:
            lines.append(f"📍 Адрес: {di.address}")
        if di.contact_phone:
            lines.append(f"📞 Телефон: {di.contact_phone}")

    if order.items:
        lines.append("")
        lines.append("📦 Состав:")
        for oi in order.items:
            lines.append(f"  • {oi.snapshot_name} {oi.snapshot_weight_g}г × {oi.quantity} шт.")

    if order.comment:
        lines.append(f"\n💬 {order.comment}")

    return "\n".join(lines)


async def _send_message(chat_id: int, text: str) -> bool:
    """Отправляет Telegram-сообщение. Возвращает True при успехе."""
    token = get_settings().bot_token.get_secret_value()
    if not token or token == "0:fake":
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            })
        if not resp.json().get("ok"):
            log.warning("telegram_send_failed", chat_id=chat_id, resp=resp.json())
            return False
        return True
    except Exception as exc:
        log.error("telegram_send_error", chat_id=chat_id, error=str(exc))
        return False


async def notify_new_order(order: Order, session: AsyncSession) -> int:
    """Уведомляет всех активных менеджеров о новом заказе.

    Возвращает количество успешно отправленных сообщений.
    """
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
    sent = 0
    for target in targets:
        if await _send_message(target.telegram_id, text):
            sent += 1

    log.info("order_notifications_sent", order_number=order.number, sent=sent, total=len(targets))
    return sent
