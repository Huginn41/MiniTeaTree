"""Пункт самовывоза (ПВЗ) и FAQ — справочный контент.

По процессу доставки: после заказа менеджер связывается с клиентом и
присылает ссылку на оплату доставки. Список ПВЗ и адрес самовывоза —
статичный, редактируется в админке.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import PKType, TimestampMixin


class PickupPoint(TimestampMixin, Base):
    """Пункт выдачи / адрес самовывоза."""

    __tablename__ = "pickup_points"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    address: Mapped[str] = mapped_column(String(256), nullable=False)
    work_hours: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Координаты для карты (если потом понадобится).
    lat: Mapped[float | None] = mapped_column(nullable=True)
    lon: Mapped[float | None] = mapped_column(nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False, default=0
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False, default=True
    )

    def __repr__(self) -> str:
        return f"<PickupPoint id={self.id} name={self.name!r}>"


class FaqItem(TimestampMixin, Base):
    """Вопрос-ответ для раздела FAQ."""

    __tablename__ = "faq_items"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(String(256), nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    sort: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False, default=True
    )

    def __repr__(self) -> str:
        return f"<FaqItem id={self.id} q={self.question!r}>"
