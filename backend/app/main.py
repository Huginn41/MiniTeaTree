"""Точка входа FastAPI приложения.

Здесь собираются: lifespan (старт/остановка), middleware, маршруты,
healthcheck, обработчики ошибок. Реальные роутеры подключаются по мере
реализации этапов (из app.routers.*).
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app import __version__
from app.config import get_settings
from app.db import dispose_engine
from app.logging import configure_logging, get_logger

# ---------- Rate Limiter (slowapi) ----------
# Ограничения можно настраивать по-умолчанию и per-endpoint через @limiter.limit().
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Жизненный цикл приложения: настройка логов при старте,
    закрытие соединений с БД при остановке."""
    settings = get_settings()
    configure_logging(
        level=settings.log_level,
        json_logs=settings.is_production,
    )
    from app.db import configure_engine

    configure_engine()

    from app.admin import setup_admin
    from app.db import get_engine

    setup_admin(app, get_engine())

    log = get_logger("app.lifespan")
    log.info(
        "startup",
        env=settings.app_env,
        version=__version__,
        public_base_url=settings.public_base_url,
    )

    try:
        yield
    finally:
        log.info("shutdown")
        await dispose_engine()


def create_app() -> FastAPI:
    """Фабрика приложения — используется и в runtime, и в тестах."""
    settings = get_settings()

    app = FastAPI(
        title="Чайное Дерево — Mini App API",
        version=__version__,
        description="Backend for Telegram Mini App tea shop",
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # Rate limiter state (slowapi)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ---------- Middleware ----------
    # SessionMiddleware нужна для SQLAdmin (хранение состояния аутентификации).
    from starlette.middleware.sessions import SessionMiddleware

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.jwt_secret.get_secret_value(),
        https_only=settings.is_production,
        max_age=86400 * 7,  # 7 дней
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    origins = settings.cors_origin_list
    if not settings.is_production and not origins:
        origins = [
            "http://localhost:5173",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Telegram-Init-Data",
            "X-Request-ID",
        ],
    )

    # ---------- Роутеры ----------
    _register_routers(app)

    # ---------- Telegram-бот (webhook endpoint) ----------
    from app.bot import setup_bot
    setup_bot(app)

    # ---------- Healthcheck ----------
    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/health/ready", tags=["meta"])
    async def health_ready() -> JSONResponse:
        from sqlalchemy import text

        try:
            from app.db import get_session_factory

            async with get_session_factory()() as session:
                await session.execute(text("SELECT 1"))
            return JSONResponse({"status": "ready"})
        except Exception as exc:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "detail": str(exc)},
            )

    # ---------- Глобальный обработчик ошибок ----------
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        log = get_logger("app.errors")
        log.error(
            "unhandled_exception",
            error=str(exc),
            path=request.url.path,
            exc_info=exc,
        )
        detail = "Internal server error" if get_settings().is_production else str(exc)
        return JSONResponse(status_code=500, content={"detail": detail})

    return app


def _register_routers(app: FastAPI) -> None:
    """Регистрирует все роутеры под префиксом /api."""
    from fastapi import APIRouter

    api = APIRouter(prefix="/api")

    @api.get("/", tags=["meta"])
    async def api_root() -> dict[str, str]:
        return {"name": "MiniTeaTree API", "version": __version__}

    # --- Auth endpoints (этап 3) ---
    @api.post("/auth/refresh", tags=["auth"])
    async def auth_refresh(request: Request) -> JSONResponse:
        """Обновляет access-токен по refresh-токен.

        Body: {"refresh_token": "..."}
        Returns: {"access_token": "...", "refresh_token": "..."}
        """
        from app.deps import _get_user_by_telegram_id
        from app.security import create_token_pair, verify_token

        try:
            body = await request.json()
        except Exception:
            return JSONResponse(status_code=400, content={"detail": "Invalid JSON body"})

        refresh_token = body.get("refresh_token")
        if not refresh_token:
            return JSONResponse(status_code=400, content={"detail": "Missing refresh_token"})

        try:
            telegram_id = verify_token(refresh_token, expected_type="refresh")
        except ValueError as exc:
            return JSONResponse(status_code=401, content={"detail": str(exc)})

        from app.db import get_session_factory

        async with get_session_factory()() as session:
            user = await _get_user_by_telegram_id(session, telegram_id)
            if user is None:
                return JSONResponse(status_code=401, content={"detail": "User not found"})

        access, refresh = create_token_pair(telegram_id)
        return JSONResponse(content={"access_token": access, "refresh_token": refresh})

    # --- Catalog + Info + Cart (этап 4) ---
    from app.routers import cart, catalog, info, orders, payments

    api.include_router(catalog.router)
    api.include_router(info.router)
    api.include_router(cart.router)
    api.include_router(orders.router)
    api.include_router(payments.router)

    app.include_router(api)


# Объект, который запускает uvicorn/gunicorn.
app = create_app()
