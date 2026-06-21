"""aiogram handlers: /start, FSM-флоу ссылки на оплату."""

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
    waiting_payment_link = State()  # data: order_id, order_number, customer_tg_id


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
# Callback: кнопка «Ссылка на оплату» в уведомлении о заказе
# ──────────────────────────────────────────────────────────────────────────────

async def cb_payment_link(callback: CallbackQuery, state: FSMContext) -> None:
    """Менеджер нажал «Ссылка на оплату» — просим вставить ссылку."""
    order_id = int(callback.data.split(":")[1])

    from sqlalchemy import select
    from app.db import get_session_factory
    from app.models.order import Order

    async with get_session_factory()() as session:
        result = await session.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    customer_tg_id = order.user.telegram_id if order.user else None

    await state.set_state(AdminStates.waiting_payment_link)
    await state.update_data(
        order_id=order_id,
        order_number=order.number,
        customer_tg_id=customer_tg_id,
    )

    await callback.answer()
    await callback.message.answer(
        f"Введите ссылку на оплату для заказа <b>{order.number}</b>:\n\n"
        f"(Или напишите /cancel для отмены)",
        parse_mode="HTML",
    )


# ──────────────────────────────────────────────────────────────────────────────
# FSM: получаем ссылку от менеджера → сохраняем + отправляем клиенту
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

    # Сохраняем ссылку и меняем статус
    from sqlalchemy import select
    from app.db import get_session_factory
    from app.models.order import Order

    async with get_session_factory()() as session:
        result = await session.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        if order:
            order.payment_link = link
            order.status = "awaiting_payment"
            await session.commit()

    # Отправляем клиенту
    if customer_tg_id:
        from app.bot.notify import _send_message
        await _send_message(
            customer_tg_id,
            f"👀 Мы увидели ваш заказ <b>{order_number}</b>!\n\n"
            f"Для оформления перейдите по ссылке на оплату:\n{link}",
        )

    await state.clear()
    await message.answer(
        f"✅ Ссылка отправлена покупателю. Статус заказа {order_number} → «Ожидает оплаты»."
    )


async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Отменяет текущее FSM-действие."""
    current = await state.get_state()
    if current is None:
        await message.answer("Нечего отменять.")
        return
    await state.clear()
    await message.answer("Действие отменено.")


# ──────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ──────────────────────────────────────────────────────────────────────────────

def create_dispatcher() -> Dispatcher:
    router = Router(name="main")

    router.message.register(cmd_start, CommandStart())
    router.message.register(cmd_cancel, F.text == "/cancel")
    router.callback_query.register(cb_payment_link, F.data.startswith("pay_link:"))
    router.message.register(msg_payment_link, AdminStates.waiting_payment_link)

    dp = Dispatcher()
    dp.include_router(router)
    return dp
