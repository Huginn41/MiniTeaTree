"""Информация о доставке конкретного заказа.

По процессу: после создания заказа менеджер связывается с клиентом,
уточняет способ доставки и присылает ссылку на оплату доставки.
ym_payment_link — та самая ссылка (например, на оплату ПВЗ/курьера).
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import PKType, TimestampMixin
from app.models.enums import DELIVERY_TYPE_VALUES


class DeliveryInfo(TimestampMixin, Base):
    """Доставка заказа (1:1 с заказом)."""

    __tablename__ = "delivery_info"
    __table_args__ = (
        CheckConstraint(
            f"type IN ({','.join(repr(v) for v in DELIVERY_TYPE_VALUES)})",
            name="type_valid",
        ),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False, default="pickup")
    # Адрес доставки / ПВЗ / адрес самовывоза (заполняется после уточнения).
    address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Контактный телефон клиента (уточняется менеджером).
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Ссылка на оплату доставки (присылает менеджер).
    ym_payment_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    # Комментарий логиста/менеджера.
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    order = relationship("Order", back_populates="delivery_info")

    def __repr__(self) -> str:
        return f"<DeliveryInfo id={self.id} order={self.order_id} type={self.type!r}>"
