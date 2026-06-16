"""Точка входа FastAPI приложения.

Здесь собираются: lifespan (старт/остановка), middleware, маршруты,
healthcheck, обработчики ошибок. Реальные роутеры подключаются по мере
реализации этапов (из app.routers.*).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.config import get_settings
from app.db import dispose_engine
from app.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Жизненный цикл приложения: настройка логов при старте,
    закрытие соединений с БД при остановке."""
    settings = get_settings()
    configure_logging(
        level=settings.log_level,
        json_logs=settings.is_production,
    )
    # Лениво инициализируем подключение к БД.
    from app.db import configure_engine

    configure_engine()
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

    # ---------- CORS ----------
    # Жёстко ограничиваем источники; в проде это URL Mini App.
    origins = settings.cors_origin_list
    if not settings.is_production and not origins:
        # В dev разрешаем localhost для удобства
        origins = ["http://localhost:5173", "http://localhost:8000", "http://127.0.0.1:8000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Telegram-Init-Data"],
    )

    # ---------- Роутеры (подключаются по мере реализации) ----------
    # Импорт внутри функции, чтобы избежать циклических зависимостей при старте
    # и позволить тестам подключать только нужные роутеры.
    _register_routers(app)

    # ---------- Healthcheck ----------
    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        """Liveness-проба. readiness — отдельный эндпоинт с проверкой БД."""
        return {"status": "ok", "version": __version__}

    @app.get("/health/ready", tags=["meta"])
    async def health_ready() -> JSONResponse:
        """Readiness-проба: проверяет соединение с БД."""
        from sqlalchemy import text  # local import — чтобы не тащить в health

        try:
            from app.db import get_session_factory

            async with get_session_factory()() as session:
                await session.execute(text("SELECT 1"))
            return JSONResponse({"status": "ready"})
        except Exception as exc:
            return JSONResponse(
                status_code=503, content={"status": "not_ready", "detail": str(exc)}
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
        # В prod не светим internals наружу.
        detail = "Internal server error" if get_settings().is_production else str(exc)
        return JSONResponse(status_code=500, content={"detail": detail})

    return app


def _register_routers(app: FastAPI) -> None:
    """Регистрирует все роутеры под префиксом /api.

    Роутеры добавляются по мере готовности этапов. Сейчас — заглушка,
    чтобы /api отвечал. Реальные роутеры будут импортированы из app.routers.
    """
    from fastapi import APIRouter

    api = APIRouter(prefix="/api")

    @api.get("/", tags=["meta"])
    async def api_root() -> dict[str, str]:
        return {"name": "MiniTeaTree API", "version": __version__}

    # Здесь позже появятся: catalog, cart, orders, payments, profile, info, admin
    # from app.routers import catalog, cart, orders, payments, profile, info
    # api.include_router(catalog.router)
    # ...

    app.include_router(api)


# Объект, который запускает uvicorn/gunicorn (см. Dockerfile CMD).
app = create_app()
