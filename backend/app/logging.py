"""Структурированное логирование (structlog).

В prod — JSON-логи (удобно собирать в ELK/Loki), в dev — цветная консоль.
Секреты (bot_token, jwt_secret) никогда не должны попадать в логи: для этого
есть процессор-фильтр (см. ниже), который экранирует ключи по списку.
"""

from __future__ import annotations

import logging
import sys

import structlog
from structlog.types import EventDict, Processor

SENSITIVE_KEYS = {
    "bot_token",
    "jwt_secret",
    "password",
    "secret",
    "secret_key",
    "authorization",
    "token",
    "yookassa_secret_key",
}


def _redact_sensitive(_logger: object, _name: str, event_dict: EventDict) -> EventDict:
    """Маскирует значения чувствительных ключей в логах."""
    for key in list(event_dict):
        lk = key.lower()
        if any(s in lk for s in SENSITIVE_KEYS):
            event_dict[key] = "***REDACTED***"
    return event_dict


def configure_logging(level: str = "INFO", json_logs: bool = False) -> None:
    """Настраивает structlog + стандартный logging."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    # Стандартный logging (для uvicorn/gunicorn/sqlalchemy)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        _redact_sensitive,
    ]

    if json_logs:
        renderer: Processor = structlog.processors.JSONRenderer(ensure_ascii=False)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Возвращает подготовленный логгер."""
    return structlog.get_logger(name)  # type: ignore[return-value]
