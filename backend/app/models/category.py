"""Категория чаёв (фильтр каталога)."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import PKType, TimestampMixin


class Category(TimestampMixin, Base):
    """Категория товаров (например: «Зелёный чай», «Улун», «Травяные сборы»).

    slug — для URL и фильтрации; уникален.
    sort_order — порядок отображения (меньше = выше).
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    # Краткое описание (необязательно).
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Иконка-эмодзи или имя SVG-иконки для UI.
    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Фото категории (путь к файлу).
    image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False, default=0
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False, default=True
    )

    products = relationship("Product", back_populates="category", lazy="selectin")

    def __str__(self) -> str:
        prefix = f"{self.icon} " if self.icon else ""
        return f"{prefix}{self.name}"

    def __repr__(self) -> str:
        return f"<Category id={self.id} slug={self.slug!r}>"
