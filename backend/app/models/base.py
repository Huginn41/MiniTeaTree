"""Общие примеси и типы для всех моделей.

- TimestampMixin: created_at / updated_at (серверные default'ы).
- PKType: тип первичного ключа (BigInteger → BIGINT на Postgres, INTEGER на SQLite).

Время храним в UTC (timezone-aware). server_default=func.now() — на стороне БД.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

# Общий тип первичного ключа. На Postgres — BIGINT (Telegram ID и т.п.
# могут превышать 2^31). На SQLite — INTEGER PRIMARY KEY, чтобы работал
# autoincrement (BIGINT на SQLite autoincrement не даёт).
PKType = BigInteger().with_variant(Integer, "sqlite")


class TimestampMixin:
    """created_at проставляется一次, updated_at обновляется автоматически."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
