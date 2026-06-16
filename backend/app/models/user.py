"""Модель пользователя (клиента Mini App)."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, String, text
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
        Boolean, server_default=text("0"), nullable=False, default=False
    )

    # Связи (lazy — загружаются по запросу, чтобы не тащить всё подряд).
    cart = relationship("Cart", back_populates="user", uselist=False, lazy="selectin")
    orders = relationship("Order", back_populates="user", lazy="selectin")

    def __repr__(self) -> str:
        return f"<User id={self.id} tg={self.telegram_id}>"
