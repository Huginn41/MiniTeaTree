"""Модель реферальной программы."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import PKType, TimestampMixin


class ReferralLink(TimestampMixin, Base):
    """Связь донор → реципиент.

    Создаётся когда реципиент открывает мини-апп по реферальной ссылке
    и подтверждает подписку на канал.
    Один реципиент может быть приглашён только одним донором (unique recipient_id).
    """

    __tablename__ = "referral_links"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)

    donor_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # True после того как реципиент подписался и получил 250 баллов.
    welcome_paid: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Сколько покупок реципиента уже принесли донору 5% (лимит: 3).
    purchases_rewarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    donor = relationship("User", foreign_keys=[donor_id])
    recipient = relationship("User", foreign_keys=[recipient_id])
