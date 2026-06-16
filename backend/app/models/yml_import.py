"""Журнал импортов YML-фида.

Каждый запуск импорта (из файла или URL) логируется: источник, статус,
сколько товаров добавлено/обновлено, текстовый лог ошибок.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import PKType, TimestampMixin


class YmlImport(TimestampMixin, Base):
    """Запись об импорте каталога из YML."""

    __tablename__ = "yml_imports"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    # Источник: URL или имя загруженного файла.
    source: Mapped[str] = mapped_column(String(1024), nullable=False)
    # running | success | failed
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    products_added: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False, default=0
    )
    products_updated: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False, default=0
    )
    products_deactivated: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False, default=0
    )
    images_downloaded: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False, default=0
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    log: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<YmlImport id={self.id} source={self.source!r} "
            f"{self.status} +{self.products_added} ~{self.products_updated}>"
        )
