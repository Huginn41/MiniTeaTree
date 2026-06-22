"""Модели бонусной системы."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import PKType, TimestampMixin


class ShopSettings(Base):
    """Синглтон с настройками магазина (всегда id=1)."""

    __tablename__ = "shop_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    bonus_max_payment_pct: Mapped[int] = mapped_column(Integer, default=50, nullable=False)


class BonusTier(Base):
    """Ступень кешбэка: при накопленных покупках от min_amount → cashback_pct%."""

    __tablename__ = "bonus_tiers"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    min_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    cashback_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)


class BonusTransaction(TimestampMixin, Base):
    """Транзакция баланса баллов (delta > 0 — начисление, delta < 0 — списание)."""

    __tablename__ = "bonus_transactions"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    delta: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="bonus_transactions")
