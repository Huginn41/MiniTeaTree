"""Корзина пользователя.

У одного User — одна Cart (uselist=False). CartItem ссылается на
ProductVariant (конкретную граммовку) + количество.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.base import PKType, TimestampMixin


class Cart(TimestampMixin, Base):
    """Корзина пользователя (одна на пользователя)."""

    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    user = relationship("User", back_populates="cart")
    items = relationship(
        "CartItem",
        back_populates="cart",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Cart id={self.id} user={self.user_id}>"


class CartItem(TimestampMixin, Base):
    """Позиция в корзине: вариант + количество."""

    __tablename__ = "cart_items"
    __table_args__ = (
        # один вариант — одна строка в корзине (кол-во суммируется)
        UniqueConstraint("cart_id", "variant_id", name="uq_cart_variant"),
    )

    id: Mapped[int] = mapped_column(PKType, primary_key=True, autoincrement=True)
    cart_id: Mapped[int] = mapped_column(
        ForeignKey("carts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    cart = relationship("Cart", back_populates="items")
    variant = relationship("ProductVariant", lazy="selectin")

    def __repr__(self) -> str:
        return f"<CartItem id={self.id} variant={self.variant_id} qty={self.quantity}>"
