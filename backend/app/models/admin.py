"""Администратор панели (SQLAdmin) — отдельная учётка с паролем.

Отличается от User: авторизация по логину/паролю (для веб-админки),
а не по Telegram. Связан с Optional[telegram_id] для дополнительной
привязки. Пароли — bcrypt (через passlib), никогда не хранятся в открытом виде.
"""

from __future__ import annotations

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import PKType, TimestampMixin


class AdminUser(TimestampMixin, Base):
    """Учётная запись администратора для входа в /admin (SQLAdmin)."""

    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # bcrypt-хэш. Поле называется password_hash, чтобы случайно не залогировать.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_superuser: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False, default=True
    )
    # Необязательная привязка к Telegram (для 2FA/уведомлений в будущем).
    telegram_id: Mapped[int | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<AdminUser id={self.id} username={self.username!r}>"
