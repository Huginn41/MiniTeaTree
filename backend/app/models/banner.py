"""Баннер для слайдера на главной странице Mini App."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import PKType, TimestampMixin


class Banner(TimestampMixin, Base):
    """Баннер карусели на главной.

    image_path — путь к картинке в /static/media/banners.
    link — куда ведёт баннер (slug категории, URL товара или внешний URL).
    """

    __tablename__ = "banners"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    subtitle: Mapped[str | None] = mapped_column(String(256), nullable=True)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    # Куда ведёт: "catalog:green-tea", "product:sencha", или URL.
    link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False, default=True
    )
    is_demo: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False, default=False
    )

    def __repr__(self) -> str:
        return f"<Banner id={self.id} title={self.title!r}>"
