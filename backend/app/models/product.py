"""Товар и его варианты (граммовки).

Product — сам чай (название, описание, категория).
ProductVariant — конкретная граммовка (25/50/75/100 г) со своей ценой и SKU.
  Цена привязана к варианту, а не к продукту — потому что у каждой
  граммовки своя цена (по требованию заказчика).

Это даёт гибкость: разные граммовки, разные SKU для склада/YML.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import PKType, TimestampMixin


class Product(TimestampMixin, Base):
    """Товар (чай)."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Базовая цена за 100 г (для отображения «от»). Реальные цены — в вариантах.
    base_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    # Происхождение/страна (информационное).
    origin: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Теги через запятую (для быстрого фильтра без отдельной таблицы).
    tags: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False, default=True
    )
    # Порядок сортировки в каталоге.
    sort_order: Mapped[int] = mapped_column(
        Integer, server_default=text("0"), nullable=False, default=0
    )

    category = relationship("Category", back_populates="products", lazy="selectin")
    variants = relationship(
        "ProductVariant",
        back_populates="product",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    images = relationship(
        "ProductImage",
        back_populates="product",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort",
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} slug={self.slug!r}>"


class ProductVariant(TimestampMixin, Base):
    """Вариант товара — конкретная граммовка с ценой.

    Уникальность (product_id, weight_g) — нельзя иметь два варианта 50 г
    у одного товара.
    """

    __tablename__ = "product_variants"
    __table_args__ = (UniqueConstraint("product_id", "weight_g", name="uq_product_weight"),)

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Вес в граммах (25/50/75/100). int, без enum — гибче.
    weight_g: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    # Артикул для склада/YML/1C. Может быть null (для ручных товаров).
    sku: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    # Доступность (наличие). Если False — нет в продаже.
    in_stock: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False, default=True
    )

    product = relationship("Product", back_populates="variants")

    def __repr__(self) -> str:
        return f"<ProductVariant id={self.id} product={self.product_id} {self.weight_g}g>"


class ProductImage(TimestampMixin, Base):
    """Фото товара. Может быть несколько; одно — главное (is_main)."""

    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Путь относительно /static/media (например, "products/abc123.jpg").
    # НЕ внешний URL — храним на нашем сервере (требование заказчика).
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    # Главное фото для карточки/каталога. У товара должно быть ≤1 главного.
    is_main: Mapped[bool] = mapped_column(
        Boolean, server_default=text("0"), nullable=False, default=False
    )
    sort: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False, default=0)
    # alt-текст для доступности.
    alt: Mapped[str | None] = mapped_column(String(256), nullable=True)

    product = relationship("Product", back_populates="images")

    def __repr__(self) -> str:
        return f"<ProductImage id={self.id} product={self.product_id} main={self.is_main}>"
