"""Аудит платёжных событий.

Каждый платёж/изменение статуса от провайдера (ЮKassa) логируется сюда.
Сырой payload — JSON-строка, для разбора инцидентов. external_id —
идентификатор платежа на стороне провайдера.
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import PKType, TimestampMixin
from app.models.enums import PROVIDER_VALUES


class PaymentEvent(TimestampMixin, Base):
    """Запись о платёжном событии (webhook от ЮKassa и т.п.)."""

    __tablename__ = "payment_events"
    __table_args__ = (
        CheckConstraint(
            f"provider IN ({','.join(repr(v) for v in PROVIDER_VALUES)})",
            name="provider_valid",
        ),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    # Сырой payload от провайдера (для разбора инцидентов). Никаких секретов.
    raw_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PaymentEvent id={self.id} order={self.order_id} {self.provider}:{self.status}>"
