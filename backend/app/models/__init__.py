"""Пакет ORM-моделей.

Импортирует все модели, чтобы Alembic (через alembic/env.py) и SQLAlchemy
видели их в Base.metadata, а SQLAdmin мог их регистрировать.
"""

from app.models.admin import AdminUser
from app.models.banner import Banner
from app.models.bonus import BonusTransaction, BonusTier, ShopSettings
from app.models.cart import Cart, CartItem
from app.models.category import Category
from app.models.content import FaqItem, PickupPoint
from app.models.delivery import DeliveryInfo
from app.models.notification import NotificationTarget
from app.models.order import Order, OrderItem
from app.models.payment import PaymentEvent
from app.models.product import Product, ProductImage, ProductVariant
from app.models.referral import ReferralLink
from app.models.user import User
from app.models.yml_import import YmlImport

__all__ = [
    "AdminUser",
    "Banner",
    "BonusTransaction",
    "BonusTier",
    "ShopSettings",
    "Cart",
    "CartItem",
    "Category",
    "DeliveryInfo",
    "FaqItem",
    "NotificationTarget",
    "Order",
    "OrderItem",
    "PaymentEvent",
    "PickupPoint",
    "Product",
    "ProductImage",
    "ProductVariant",
    "ReferralLink",
    "User",
    "YmlImport",
]
