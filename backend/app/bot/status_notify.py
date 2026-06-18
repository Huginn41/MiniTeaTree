"""Уведомления клиентам при смене статуса доставки.

Вызывается из PATCH /api/orders/{number}/status (endpoint для менеджера).
Шлёт сообщение напрямую клиенту (telegram_id из users) через Bot API.
"""

from __future__ import annotations

import httpx

from app.logging import get_logger
from app.models.order import Order

log = get_logger("app.bot.status_notify")

# Текстовые метки и эмодзи для каждого статуса доставки
_STATUS_MESSAGES: dict[str, str] = {
    "new": "📋 Ваш заказ {number} получен и ждёт обработки.",
    "manager_contacted": "👋 Менеджер принял заказ {number} и скоро свяжется с вами.",
    "awaiting_delivery_payment": (
        "💳 Для завершения заказа {number} оплатите доставку по ссылке от менеджера."
    ),
    "delivery_paid": "✅ Оплата доставки по заказу {number} подтверждена. Готовим к отправке.",
    "shipping": "🚚 Заказ {number} отправлен и уже в пути!",
    "delivered": "🎉 Заказ {number} доставлен. Спасибо, что выбрали Чайное Дерево! 🌿",
    "cancelled": "❌ Заказ {number} отменён. Если есть вопросы — напишите менеджеру.",
}


async def notify_status_changed(order: Order, new_status: str, user_telegram_id: int) -> bool:
    """Отправляет клиенту уведомление о смене статуса доставки.

    Возвращает True если сообщение отправлено, False при ошибке или отсутствии токена.
    """
    from app.config import get_settings

    settings = get_settings()
    token = settings.bot_token.get_secret_value()
    if not token or token == "0:fake":
        return False

    template = _STATUS_MESSAGES.get(new_status)
    if not template:
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
