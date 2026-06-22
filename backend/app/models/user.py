"""Модель пользователя (клиента Mini App)."""

from __future__ import annotations

from datetime import datetime

from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import PKType, TimestampMixin


class User(TimestampMixin, Base):
    """Пользователь Mini App.

    Один пользователь = один Telegram-аккаунт (telegram_id уникален).
    Профильные поля (имя, телефон) заполняются из Telegram initData и/или
    при оформлении заказа.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)

    # Telegram ID пользователя (bigint — Telegram ID может превышать 2^31).
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    # Имя/фамилия из Telegram (на момент первого входа).
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Телефон запрашивается отдельно (через Telegram или вручную).
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Является ли админом (определяется по ADMIN_TELEGRAM_IDS в настройках).
    is_admin: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False, default=False
    )

    # ── Дополнительные контакты ──────────────────────────────────────────────
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Язык интерфейса из Telegram (ru, en, …).
    language_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    # Город — заполняется из адреса первого заказа или вручную.
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # ── CRM / маркетинг ──────────────────────────────────────────────────────
    # Сегмент: vip / wholesale / regular / at_risk / churned
    segment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Заметки менеджера о клиенте.
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Время последнего входа в мини-апп (обновляется при авторизации).
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Бонусный баланс (в рублях).
    bonus_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"), server_default="0"
    )

    # Связи (lazy — загружаются по запросу, чтобы не тащить всё подряд).
    cart = relationship("Cart", back_populates="user", uselist=False, lazy="selectin")
    orders = relationship("Order", back_populates="user", lazy="selectin")
    bonus_transactions = relationship(
        "BonusTransaction", back_populates="user", lazy="select", order_by="BonusTransaction.created_at.desc()"
    )

    @property
    def display_name(self) -> str:
        parts = [self.first_name or "", self.last_name or ""]
        name = " ".join(p for p in parts if p).strip()
        if self.username:
            name = f"{name} (@{self.username})" if name else f"@{self.username}"
        return name or f"tg:{self.telegram_id}"

    @property
    def total_orders(self) -> int:
        return len(self.orders) if self.orders else 0

    @property
    def total_spent(self) -> float:
        return sum(float(o.total_amount) for o in self.orders) if self.orders else 0.0

    @property
    def avg_check(self) -> float:
        if not self.orders:
            return 0.0
        return self.total_spent / len(self.orders)

    @property
    def first_order_date(self):
        if not self.orders:
            return None
        return min(o.created_at for o in self.orders)

    @property
    def last_order_date(self):
        if not self.orders:
            return None
        return max(o.created_at for o in self.orders)

    def __repr__(self) -> str:
        return f"<User id={self.id} tg={self.telegram_id}>"
