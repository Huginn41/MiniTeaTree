"""Заказ и позиции заказа.

Ключевая особенность процесса: у заказа ДВА независимых статуса:
  - status_payment  — оплата ТОВАРОВ (через Telegram Payments / ЮKassa)
  - status_delivery — доставка (управляется менеджером вручную)

Доставка НЕ входит в счёт товаров: менеджер отдельно присылает клиенту
ссылку на оплату доставки (см. DeliveryInfo.ym_payment_link).

OrderItem хранит снапшот цены и названия на момент заказа — чтобы история
не «поплыла» при изменении цен/переименовании товаров позже.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import PKType, TimestampMixin
from app.models.enums import DELIVERY_STATUS_VALUES, PAYMENT_STATUS_VALUES


class Order(TimestampMixin, Base):
    """Заказ пользователя."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            f"status_payment IN ({','.join(repr(v) for v in PAYMENT_STATUS_VALUES)})",
            name="status_payment_valid",
        ),
        CheckConstraint(
            f"status_delivery IN ({','.join(repr(v) for v in DELIVERY_STATUS_VALUES)})",
            name="status_delivery_valid",
        ),
        CheckConstraint("total_amount >= 0", name="total_nonnegative"),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    # Публичный номер заказа (для клиента/менеджера): например "ЧД-000123".
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    # Сумма за ТОВАРЫ (без доставки).
    total_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    # Стоимость доставки (заполняется менеджером позже, может быть 0 при самовывозе).
    delivery_cost: Mapped[float] = mapped_column(
        Numeric(10, 2), server_default=text("0"), nullable=False, default=0
    )

    status_payment: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    status_delivery: Mapped[str] = mapped_column(String(32), nullable=False, default="new")

    # Комментарий клиента к заказу.
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Когда оплачен (товары).
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Когда доставлен/выдан.
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="orders")
    items = relationship(
        "OrderItem",
        back_populates="order",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    delivery_info = relationship(
        "DeliveryInfo",
        back_populates="order",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} number={self.number!r} pay={self.status_payment}>"


class OrderItem(TimestampMixin, Base):
    """Позиция заказа — снапшот варианта/цены/названия на момент оформления."""

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    # Цена за единицу на момент заказа (снапшот).
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    # Название + вес на момент заказа (снапшот, чтобы не зависеть от БД).
    snapshot_name: Mapped[str] = mapped_column(String(256), nullable=False)
    snapshot_weight_g: Mapped[int] = mapped_column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")

    def __repr__(self) -> str:
        return (
            f"<OrderItem id={self.id} order={self.order_id} "
            f"{self.snapshot_name!r} x{self.quantity}>"
        )
