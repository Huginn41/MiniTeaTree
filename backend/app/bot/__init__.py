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
    from aiogram.client.session.aiohttp import AiohttpSession

    from app.bot.handlers import create_dispatcher

    session_kwargs = {}
    if settings.telegram_api_base_url:
        session_kwargs["api"] = __import__(
            "aiogram.client.telegram", fromlist=["TelegramAPIServer"]
        ).TelegramAPIServer(
            base=settings.telegram_api_base_url + "/bot{token}/{method}",
            file=settings.telegram_api_base_url + "/file/bot{token}/{path}",
        )

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode="HTML"),
        session=AiohttpSession(**session_kwargs) if session_kwargs else None,
    )
    dp = create_dispatcher()

    @app.post("/bot/webhook", include_in_schema=False)
    async def bot_webhook(request: Request) -> JSONResponse:
        """Принимает Update от Telegram, сразу отвечает 200, обрабатывает в фоне."""
        import asyncio
        from aiogram.types import Update

        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"ok": False})

        try:
            update = Update.model_validate(body)
        except Exception:
            return JSONResponse(status_code=400, content={"ok": False})

        async def process() -> None:
            try:
                await dp.feed_update(bot=bot, update=update)
            except Exception as e:
                log.error("bot_update_error", error=str(e), update_id=update.update_id)

        asyncio.create_task(process())
        return JSONResponse({"ok": True})

    log.info("bot_webhook_registered", path="/bot/webhook")
