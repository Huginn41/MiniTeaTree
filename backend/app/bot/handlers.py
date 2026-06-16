"""aiogram handlers: /start, помощь, кнопка Mini App.

Диспетчер регистрируется в setup_bot() и монтируется как FastAPI-роутер
через SimpleRequestHandler (aiogram.webhook.aiohttp → здесь через starlette).
"""

from __future__ import annotations

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.config import get_settings
from app.logging import get_logger

log = get_logger("app.bot.handlers")


async def cmd_start(message: Message) -> None:
    """Отвечает на /start кнопкой открытия Mini App."""
    settings = get_settings()

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🌿 Открыть магазин",
            web_app={"url": settings.public_base_url},
        )
    ]])

    name = message.from_user.first_name if message.from_user else "друг"
    await message.answer(
        f"Привет, {name}! 👋\n\n"
        "🌿 <b>Чайное Дерево</b> — магазин качественного чая.\n\n"
        "Нажми кнопку ниже, чтобы открыть каталог и сделать заказ:",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


def create_dispatcher() -> Dispatcher:
    router = Router(name="main")
    router.message.register(cmd_start, CommandStart())
    dp = Dispatcher()
    dp.include_router(router)
    return dp
