"""Уведомления клиентам при смене статуса заказа.

Вызывается из PATCH /api/orders/{number}/status (endpoint для менеджера).
Некоторые статусы не шлют авто-уведомление (awaiting_payment, assembling, new)
— они обрабатываются отдельной логикой в handlers.py.
"""

from __future__ import annotations

import httpx

from app.logging import get_logger
from app.models.order import Order

log = get_logger("app.bot.status_notify")

# Авто-уведомления для статусов. None = не слать клиенту (обрабатывается вручную).
_STATUS_MESSAGES: dict[str, str | None] = {
    "new": None,
    "assembling": None,
    "awaiting_payment": None,  # клиент получает сообщение с ссылкой через FSM-флоу
    "ready": (
        "✅ <b>Ваш заказ {number} готов!</b>\n\n"
        "Приходите забрать в наш магазин 🍵\n"
        "Если будут вопросы — напишите нам."
    ),
    "in_delivery": (
        "🚚 <b>Заказ {number} передан в доставку!</b>\n\n"
        "Скоро он будет у вас. Мы сообщим, когда заказ прибудет в пункт выдачи."
    ),
    "at_pvz": (
        "📦 <b>Ваш заказ {number} в пункте выдачи!</b>\n\n"
        "Поторопитесь забрать — заказ ждёт вас 🏪"
    ),
    "delivered": (
        "🎉 <b>Заказ {number} доставлен!</b>\n\n"
        "Спасибо, что выбрали Чайное Дерево 🌿\n"
        "Приятного чаепития!"
    ),
    "cancelled": "❌ Заказ {number} отменён. Если есть вопросы — напишите нам.",
}


async def notify_status_changed(order: Order, new_status: str, user_telegram_id: int) -> bool:
    """Отправляет клиенту уведомление о смене статуса.

    Возвращает True если сообщение отправлено, False если статус без авто-уведомления.
    """
    from app.config import get_settings

    template = _STATUS_MESSAGES.get(new_status)
    if not template:
        return False

    settings = get_settings()
    token = settings.bot_token.get_secret_value()
    if not token or token == "0:fake":
        return False

    text = template.format(number=order.number)
    base = settings.telegram_api_base_url.rstrip("/") if settings.telegram_api_base_url else "https://api.telegram.org"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{base}/bot{token}/sendMessage",
                json={"chat_id": user_telegram_id, "text": text, "parse_mode": "HTML"},
            )
        ok = resp.json().get("ok", False)
        if not ok:
            log.warning("status_notify_failed", order=order.number, status=new_status, resp=resp.json())
        return ok
    except Exception as exc:
        log.error("status_notify_error", order=order.number, error=str(exc))
        return False
