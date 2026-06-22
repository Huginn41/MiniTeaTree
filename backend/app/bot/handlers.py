"""aiogram handlers: /start, FSM-флоу ссылки на оплату и трек-номера, смена статуса."""

from __future__ import annotations

from aiogram import Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import get_settings
from app.logging import get_logger

log = get_logger("app.bot.handlers")


class AdminStates(StatesGroup):
    waiting_payment_link = State()   # data: order_id, order_number, customer_tg_id
    waiting_tracking_link = State()  # data: order_id, order_number


# ──────────────────────────────────────────────────────────────────────────────
# /start
# ──────────────────────────────────────────────────────────────────────────────

async def cmd_start(message: Message) -> None:
    settings = get_settings()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🌿 Открыть магазин", web_app={"url": settings.public_base_url}),
    ]])
    name = message.from_user.first_name if message.from_user else "друг"
    await message.answer(
        f"Привет, {name}! 👋\n\n"
        "🌿 <b>Чайное Дерево</b> — магазин качественного чая.\n\n"
        "Нажми кнопку ниже, чтобы открыть каталог и сделать заказ:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Смена статуса
# ──────────────────────────────────────────────────────────────────────────────

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


async def cb_set_status(callback: CallbackQuery) -> None:
    """Менеджер нажал кнопку смены статуса."""
    _, order_id_str, new_status = callback.data.split(":", 2)
    order_id = int(order_id_str)

    from datetime import UTC, datetime as _dt
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db import get_session_factory
    from app.models.order import Order
    from app.models.enums import ORDER_STATUS_VALUES

    if new_status not in ORDER_STATUS_VALUES:
        await callback.answer("Неверный статус", show_alert=True)
        return

    user_telegram_id = None
    order_number = None
    old_status = None

    async with get_session_factory()() as session:
        result = await session.execute(
            select(Order).options(selectinload(Order.user)).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        old_status = order.status
        order_number = order.number
        order.status = new_status
        if new_status == "delivered" and not order.delivered_at:
            order.delivered_at = _dt.now(UTC)
        if new_status == "in_delivery" and not order.paid_at:
            order.paid_at = _dt.now(UTC)
        if order.user:
            user_telegram_id = order.user.telegram_id
        await session.commit()

    status_label = _STATUS_LABELS.get(new_status, new_status)
    await callback.answer(f"Статус → {status_label}", show_alert=False)

    # Обновить карточки у всех менеджеров
    try:
        from app.bot.notify import update_order_notifications
        await update_order_notifications(order_id)
    except Exception:
        pass

    # Уведомить клиента
    if old_status != new_status and user_telegram_id:
        try:
            import asyncio as _aio
            from app.bot.status_notify import notify_status_changed
            _aio.create_task(notify_status_changed(
                type("O", (), {"id": order_id, "number": order_number, "status": new_status})(),
                new_status,
                user_telegram_id,
            ))
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
# Callback: кнопка «Подтвердить оплату»
# ──────────────────────────────────────────────────────────────────────────────

async def cb_confirm_payment(callback: CallbackQuery) -> None:
    """Менеджер нажал «Подтвердить оплату» — фиксируем paid_at и обновляем карточку."""
    order_id = int(callback.data.split(":")[1])

    from datetime import UTC, datetime as _dt
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db import get_session_factory
    from app.models.order import Order
    from app.bot.notify import _order_text, _order_keyboard, _edit_message, update_order_notifications

    async with get_session_factory()() as session:
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.user), selectinload(Order.items), selectinload(Order.delivery_info))
            .where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            await callback.answer("Заказ не найден", show_alert=True)
            return
        if order.paid_at:
            await callback.answer("Оплата уже подтверждена", show_alert=False)
            return
        order.paid_at = _dt.now(UTC)
        await session.commit()
        text = _order_text(order)
        keyboard = _order_keyboard(order)

    await callback.answer("✅ Оплата подтверждена", show_alert=False)

    # Редактируем карточку напрямую — работает даже если _order_messages пуст
    try:
        await _edit_message(callback.message.chat.id, callback.message.message_id, text, keyboard)
    except Exception:
        pass

    # Обновить карточки у остальных менеджеров
    try:
        await update_order_notifications(order_id)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
# Callback: кнопка «Ссылка на оплату»
# ──────────────────────────────────────────────────────────────────────────────

async def cb_payment_link(callback: CallbackQuery, state: FSMContext) -> None:
    """Менеджер нажал «Ссылка на оплату»."""
    order_id = int(callback.data.split(":")[1])

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db import get_session_factory
    from app.models.order import Order

    async with get_session_factory()() as session:
        result = await session.execute(
            select(Order).options(selectinload(Order.user)).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    await callback.answer()
    prompt = await callback.message.answer(
        f"Введите ссылку на оплату для заказа <b>{order.number}</b>:\n"
        "(или /cancel для отмены)",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_payment_link)
    await state.update_data(
        order_id=order_id,
        order_number=order.number,
        customer_tg_id=order.user.telegram_id if order.user else None,
        prompt_message_id=prompt.message_id,
    )


# ──────────────────────────────────────────────────────────────────────────────
# FSM: получаем ссылку на оплату
# ──────────────────────────────────────────────────────────────────────────────

async def msg_payment_link(message: Message, state: FSMContext) -> None:
    link = (message.text or "").strip()
    if not link.startswith("http"):
        await message.answer("❌ Это не похоже на ссылку. Введите URL (начинается с http):")
        return

    data = await state.get_data()
    order_id: int = data["order_id"]
    order_number: str = data["order_number"]
    customer_tg_id: int | None = data.get("customer_tg_id")
    prompt_message_id: int | None = data.get("prompt_message_id")

    from sqlalchemy import select
    from app.db import get_session_factory
    from app.models.order import Order

    async with get_session_factory()() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if order:
            order.payment_link = link
            # Переводим в awaiting_payment только если заказ ещё не отправлен
            if order.status in {"new", "assembling", "ready"}:
                order.status = "awaiting_payment"
            await session.commit()

    await state.clear()

    # Удаляем промпт и ответ менеджера — ссылка сохранится в карточке заказа
    from app.bot.notify import delete_message as _del
    chat_id = message.chat.id
    if prompt_message_id:
        await _del(chat_id, prompt_message_id)
    await _del(chat_id, message.message_id)

    # Обновить карточку заказа у всех менеджеров (ссылка появится в тексте)
    try:
        from app.bot.notify import update_order_notifications
        await update_order_notifications(order_id)
    except Exception:
        pass

    # Уведомить клиента
    if customer_tg_id:
        from app.bot.notify import _send_message
        await _send_message(
            customer_tg_id,
            f"👀 Мы увидели ваш заказ <b>{order_number}</b>!\n\n"
            f"Для оформления перейдите по ссылке на оплату:\n{link}",
        )


# ──────────────────────────────────────────────────────────────────────────────
# Callback: кнопка «Трек-номер»
# ──────────────────────────────────────────────────────────────────────────────

async def cb_tracking_link(callback: CallbackQuery, state: FSMContext) -> None:
    """Менеджер нажал «Трек-номер»."""
    order_id = int(callback.data.split(":")[1])

    from sqlalchemy import select
    from app.db import get_session_factory
    from app.models.order import Order

    async with get_session_factory()() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()

    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    await callback.answer()
    prompt = await callback.message.answer(
        f"Введите ссылку для отслеживания заказа <b>{order.number}</b>:\n"
        "(или /cancel для отмены)",
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_tracking_link)
    await state.update_data(
        order_id=order_id,
        order_number=order.number,
        prompt_message_id=prompt.message_id,
    )


# ──────────────────────────────────────────────────────────────────────────────
# FSM: получаем трек-номер
# ──────────────────────────────────────────────────────────────────────────────

async def msg_tracking_link(message: Message, state: FSMContext) -> None:
    link = (message.text or "").strip()
    if not link.startswith("http"):
        await message.answer("❌ Это не похоже на ссылку. Введите URL (начинается с http):")
        return

    data = await state.get_data()
    order_id: int = data["order_id"]
    prompt_message_id: int | None = data.get("prompt_message_id")

    from sqlalchemy import select
    from app.db import get_session_factory
    from app.models.order import Order

    async with get_session_factory()() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if order:
            order.tracking_link = link
            await session.commit()

    await state.clear()

    # Удаляем промпт и ответ менеджера — трек появится в карточке заказа
    from app.bot.notify import delete_message as _del
    chat_id = message.chat.id
    if prompt_message_id:
        await _del(chat_id, prompt_message_id)
    await _del(chat_id, message.message_id)

    try:
        from app.bot.notify import update_order_notifications
        await update_order_notifications(order_id)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
# /cancel
# ──────────────────────────────────────────────────────────────────────────────

async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer("Нечего отменять.")
        return

    data = await state.get_data()
    prompt_message_id: int | None = data.get("prompt_message_id")
    await state.clear()

    # Удаляем промпт бота и сообщение /cancel менеджера
    from app.bot.notify import delete_message as _del
    chat_id = message.chat.id
    if prompt_message_id:
        await _del(chat_id, prompt_message_id)
    await _del(chat_id, message.message_id)


# ──────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ──────────────────────────────────────────────────────────────────────────────

def create_dispatcher() -> Dispatcher:
    router = Router(name="main")

    router.message.register(cmd_start, CommandStart())
    router.message.register(cmd_cancel, F.text == "/cancel")
    router.callback_query.register(cb_set_status,       F.data.startswith("set_status:"))
    router.callback_query.register(cb_confirm_payment,  F.data.startswith("confirm_payment:"))
    router.callback_query.register(cb_payment_link,     F.data.startswith("pay_link:"))
    router.callback_query.register(cb_tracking_link,    F.data.startswith("tracking:"))
    router.message.register(msg_payment_link,  AdminStates.waiting_payment_link)
    router.message.register(msg_tracking_link, AdminStates.waiting_tracking_link)

    dp = Dispatcher()
    dp.include_router(router)
    return dp
