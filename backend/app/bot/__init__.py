"""Telegram-бот: инициализация и webhook-endpoint для FastAPI.

setup_bot() вызывается из lifespan после configure_engine().
Регистрирует маршрут /bot/webhook в FastAPI для приёма обновлений от Telegram.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.logging import get_logger

log = get_logger("app.bot")


def setup_bot(app: FastAPI) -> None:
    """Подключает Telegram-бот к FastAPI.

    В dev (BOT_TOKEN=0:fake) — маршрут регистрируется, но реальных вызовов нет.
    В проде — нужно вызвать setWebhook вручную или через make webhook.
    """
    from app.config import get_settings

    settings = get_settings()
    token = settings.bot_token.get_secret_value()

    if not token:
        log.warning("bot_token_missing_bot_disabled")
        return

    from aiogram import Bot
    from aiogram.client.default import DefaultBotProperties

    from app.bot.handlers import create_dispatcher

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = create_dispatcher()

    @app.post("/bot/webhook", include_in_schema=False)
    async def bot_webhook(request: Request) -> JSONResponse:
        """Принимает Update от Telegram и прогоняет через aiogram Dispatcher."""
        from aiogram.types import Update

        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"ok": False})

        try:
            update = Update.model_validate(body)
        except Exception:
            return JSONResponse(status_code=400, content={"ok": False})

        try:
            await dp.feed_update(bot=bot, update=update)
        except Exception:
            pass  # ошибки обработки не ломают ответ Telegram
        return JSONResponse({"ok": True})

    log.info("bot_webhook_registered", path="/bot/webhook")
