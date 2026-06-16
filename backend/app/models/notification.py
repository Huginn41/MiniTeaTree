"""Получатели уведомлений о заказах (Telegram-аккаунты менеджеров).

При новом заказе / смене статуса бот шлёт красивое сообщение всем активным
целям с подходящей ролью. Редактируется в админке.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, CheckConstraint, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import PKType, TimestampMixin
from app.models.enums import NOTIF_ROLE_VALUES


class NotificationTarget(TimestampMixin, Base):
    """Куда слать уведомления о заказах (chat_id в Telegram)."""

    __tablename__ = "notification_targets"
    __table_args__ = (
        # роль должна быть из допустимого набора
        CheckConstraint(
            f"role IN ({','.join(repr(v) for v in NOTIF_ROLE_VALUES)})",
            name="role_valid",
        ),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    # Telegram chat_id / user_id менеджера.
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="manager")
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("1"), nullable=False, default=True
    )

    def __repr__(self) -> str:
        return f"<NotificationTarget id={self.id} tg={self.telegram_id} role={self.role!r}>"
