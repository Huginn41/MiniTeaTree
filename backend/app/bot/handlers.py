"""aiogram handlers: /start, FSM-флоу ссылки на оплату и трек-номера, смена статуса.

Важно: бот работает в групповых чатах с включённым Privacy Mode.
В таком режиме бот получает только:
  - callback queries (кнопки) — всегда
  - команды (/start, /cancel)
  - ОТВЕТЫ на сообщения бота (reply)

Поэтому все промпты отправляются с ForceReply — Telegram автоматически
показывает интерфейс ответа, и бот гарантированно получает reply даже в группе.
"""

from __future__ import annotations

from aiogram import Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, ErrorEvent, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import get_settings
from app.logging import get_logger

log = get_logger("app.bot.handlers")


class AdminStates(StatesGroup):
    waiting_payment_link = State()
    waiting_tracking_link = State()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

async def _load_order(order_id: int):
    """Загружает заказ со всеми связями в отдельной сессии."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.db import get_session_factory
    from app.models.order import Order

    async with get_session_factory()() as session:
        result = await session.execute(
            select(Order).options(selectinload(Order.user)).where(Order.id == order_id)
        )
        return result.scalar_one_or_none()


async def _refresh_card(order_id: int, chat_id: int, message_id: int) -> None:
    """Перегенерирует карточку и редактирует конкретное сообщение напрямую."""
    from app.bot.notify import _order_text, _order_keyboard, _edit_message

    order = await _load_order(order_id)
    if not order:
        log.warning("refresh_card_order_not_found", order_id=order_id)
        return
    ok = await _edit_message(chat_id, message_id, _order_text(order), _order_keyboard(order))
    if not ok:
        log.warning("refresh_card_edit_failed", order_id=order_id, chat_id=chat_id, message_id=message_id)


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
    "in_delivery":      "🚚 В доставке",
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

    try:
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
    except Exception as exc:
        log.error("cb_set_status_db_error", order_id=order_id, error=str(exc))
        await callback.answer("Ошибка при смене статуса", show_alert=True)
        return

    status_label = _STATUS_LABELS.get(new_status, new_status)
    await callback.answer(f"Статус → {status_label}", show_alert=False)

    log.info("order_status_changed", order_id=order_id, old=old_status, new=new_status)

    await _refresh_card(order_id, callback.message.chat.id, callback.message.message_id)

    try:
        from app.bot.notify import update_order_notifications
        await update_order_notifications(order_id)
    except Exception:
        pass

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
    from app.db import get_session_factory
    from app.models.order import Order

    try:
        async with get_session_factory()() as session:
            result = await session.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one_or_none()
            if not order:
                await callback.answer("Заказ не найден", show_alert=True)
                return
            if order.paid_at:
                await callback.answer("Оплата уже подтверждена", show_alert=False)
                return
            order.paid_at = _dt.now(UTC)
            await session.commit()
    except Exception as exc:
        log.error("cb_confirm_payment_db_error", order_id=order_id, error=str(exc))
        await callback.answer("Ошибка при подтверждении оплаты", show_alert=True)
        return

    log.info("payment_confirmed", order_id=order_id)
    await callback.answer("✅ Оплата подтверждена", show_alert=False)

    await _refresh_card(order_id, callback.message.chat.id, callback.message.message_id)

    try:
        from app.bot.notify import update_order_notifications
        await update_order_notifications(order_id)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
# Callback: кнопка «Ссылка на оплату»
# ──────────────────────────────────────────────────────────────────────────────

async def cb_payment_link(callback: CallbackQuery, state: FSMContext) -> None:
    """Менеджер нажал «Ссылка на оплату» — просим ввести ссылку через ForceReply."""
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
    # ForceReply: Telegram показывает интерфейс ответа на это сообщение.
    # Ответ на сообщение бота доходит боту даже в группе с Privacy Mode.
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
        card_chat_id=callback.message.chat.id,
        card_message_id=callback.message.message_id,
    )
    log.info("payment_link_prompt_sent", order_id=order_id, prompt_message_id=prompt.message_id)


# ──────────────────────────────────────────────────────────────────────────────
# FSM: получаем ссылку на оплату
# ──────────────────────────────────────────────────────────────────────────────

async def msg_payment_link(message: Message, state: FSMContext) -> None:
    link = (message.text or "").strip()
    log.info("msg_payment_link_received", chat_id=message.chat.id, user_id=message.from_user.id if message.from_user else None)

    if not link.startswith("http"):
        await message.reply("❌ Это не похоже на ссылку. Введите URL (начинается с http):",
                            reply_markup=ForceReply(selective=True))
        return

    data = await state.get_data()
    if not data or "order_id" not in data:
        log.error("msg_payment_link_no_state_data", chat_id=message.chat.id)
        await message.reply("❌ Сессия устарела. Нажмите кнопку «Ссылка на оплату» ещё раз.")
        await state.clear()
        return

    order_id: int = data["order_id"]
    order_number: str = data["order_number"]
    customer_tg_id: int | None = data.get("customer_tg_id")
    prompt_message_id: int | None = data.get("prompt_message_id")
    card_chat_id: int | None = data.get("card_chat_id")
    card_message_id: int | None = data.get("card_message_id")

    from sqlalchemy import select
    from app.db import get_session_factory
    from app.models.order import Order

    try:
        async with get_session_factory()() as session:
            result = await session.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one_or_none()
            if not order:
                await message.reply(f"❌ Заказ {order_number} не найден в базе.")
                await state.clear()
                return
            order.payment_link = link
            if order.status in {"new", "assembling", "ready"}:
                order.status = "awaiting_payment"
            await session.commit()
    except Exception as exc:
        log.error("msg_payment_link_db_error", order_id=order_id, error=str(exc))
        await message.reply("❌ Ошибка при сохранении ссылки. Попробуйте ещё раз.")
        return

    log.info("payment_link_saved", order_id=order_id, order_number=order_number)
    await state.clear()

    # Удаляем промпт бота и ответ менеджера
    from app.bot.notify import delete_message as _del
    chat_id = message.chat.id
    if prompt_message_id:
        await _del(chat_id, prompt_message_id)
    await _del(chat_id, message.message_id)

    # Обновляем карточку напрямую по сохранённым координатам
    if card_chat_id and card_message_id:
        await _refresh_card(order_id, card_chat_id, card_message_id)
    else:
        log.warning("msg_payment_link_no_card_coords", order_id=order_id)

    try:
        from app.bot.notify import update_order_notifications
        await update_order_notifications(order_id)
    except Exception:
        pass

    # Уведомляем клиента
    if customer_tg_id:
        from app.bot.notify import _send_message
        result = await _send_message(
            customer_tg_id,
            f"👀 Мы увидели ваш заказ <b>{order_number}</b>!\n\n"
            f"Для оплаты перейдите по ссылке:\n{link}",
        )
        if result:
            log.info("client_payment_link_sent", order_id=order_id, customer_tg_id=customer_tg_id)
        else:
            log.warning("client_payment_link_failed", order_id=order_id, customer_tg_id=customer_tg_id)
    else:
        log.warning("msg_payment_link_no_customer_tg_id", order_id=order_id)


# ──────────────────────────────────────────────────────────────────────────────
# Callback: кнопка «Трек-номер»
# ──────────────────────────────────────────────────────────────────────────────

async def cb_tracking_link(callback: CallbackQuery, state: FSMContext) -> None:
    """Менеджер нажал «Трек-номер» — просим ввести трек через ForceReply."""
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
        card_chat_id=callback.message.chat.id,
        card_message_id=callback.message.message_id,
    )
    log.info("tracking_link_prompt_sent", order_id=order_id, prompt_message_id=prompt.message_id)


# ──────────────────────────────────────────────────────────────────────────────
# FSM: получаем трек-номер
# ──────────────────────────────────────────────────────────────────────────────

async def msg_tracking_link(message: Message, state: FSMContext) -> None:
    link = (message.text or "").strip()
    log.info("msg_tracking_link_received", chat_id=message.chat.id)

    if not link.startswith("http"):
        await message.reply("❌ Это не похоже на ссылку. Введите URL (начинается с http):",
                            reply_markup=ForceReply(selective=True))
        return

    data = await state.get_data()
    if not data or "order_id" not in data:
        log.error("msg_tracking_link_no_state_data", chat_id=message.chat.id)
        await message.reply("❌ Сессия устарела. Нажмите кнопку «Трек-номер» ещё раз.")
        await state.clear()
        return

    order_id: int = data["order_id"]
    order_number: str = data["order_number"]
    prompt_message_id: int | None = data.get("prompt_message_id")
    card_chat_id: int | None = data.get("card_chat_id")
    card_message_id: int | None = data.get("card_message_id")

    from sqlalchemy import select
    from app.db import get_session_factory
    from app.models.order import Order

    try:
        async with get_session_factory()() as session:
            result = await session.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one_or_none()
            if not order:
                await message.reply(f"❌ Заказ {order_number} не найден в базе.")
                await state.clear()
                return
            order.tracking_link = link
            await session.commit()
    except Exception as exc:
        log.error("msg_tracking_link_db_error", order_id=order_id, error=str(exc))
        await message.reply("❌ Ошибка при сохранении трека. Попробуйте ещё раз.")
        return

    log.info("tracking_link_saved", order_id=order_id, order_number=order_number)
    await state.clear()

    from app.bot.notify import delete_message as _del
    chat_id = message.chat.id
    if prompt_message_id:
        await _del(chat_id, prompt_message_id)
    await _del(chat_id, message.message_id)

    if card_chat_id and card_message_id:
        await _refresh_card(order_id, card_chat_id, card_message_id)
    else:
        log.warning("msg_tracking_link_no_card_coords", order_id=order_id)

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

    from app.bot.notify import delete_message as _del
    chat_id = message.chat.id
    if prompt_message_id:
        await _del(chat_id, prompt_message_id)
    await _del(chat_id, message.message_id)


# ──────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ──────────────────────────────────────────────────────────────────────────────

async def on_handler_error(event: ErrorEvent) -> None:
    """Ловит все необработанные исключения в handlers и логирует их."""
    exc = event.exception
    update = event.update
    update_type = (
        "message" if update.message else
        "callback_query" if update.callback_query else "other"
    )
    log.error(
        "handler_exception",
        exc_type=type(exc).__name__,
        exc_msg=str(exc),
        update_type=update_type,
        update_id=update.update_id,
        exc_info=exc,
    )


async def on_unhandled_message(message: Message) -> None:
    """Ловит все сообщения, которые не обработал ни один handler.
    Нужен для диагностики: если бот получает сообщение но ни один handler
    не сработал — это видно в логах.
    """
    state_info = "unknown"
    try:
        # Не можем легко получить state здесь без DI, просто логируем факт
        pass
    except Exception:
        pass
    log.warning(
        "unhandled_message",
        chat_id=message.chat.id,
        user_id=message.from_user.id if message.from_user else None,
        text_preview=(message.text or "")[:80],
        is_reply=message.reply_to_message is not None,
    )


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
    # Catch-all для диагностики — должен быть последним
    router.message.register(on_unhandled_message)

    dp = Dispatcher()
    dp.include_router(router)
    # Глобальный обработчик ошибок — ловит исключения из всех handlers
    dp.errors.register(on_handler_error)
    return dp
