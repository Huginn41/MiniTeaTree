"""Пакет ORM-моделей.

Импортирует все модели, чтобы Alembic (через alembic/env.py) и SQLAlchemy
видели их в Base.metadata. По мере добавления моделей — добавляем импорт.
Сейчас пакет пустой (модели появятся на этапе 2), но он нужен, чтобы
`import app.models` не падал.
"""

# Модели будут добавлены на этапе 2:
# from app.models.user import User
# from app.models.category import Category
# from app.models.product import Product, ProductVariant, ProductImage
# from app.models.cart import Cart, CartItem
# from app.models.order import Order, OrderItem
# from app.models.delivery import DeliveryInfo
# from app.models.banner import Banner
# from app.models.pickup_point import PickupPoint
# from app.models.faq import FaqItem
# from app.models.payment import PaymentEvent
# from app.models.yml_import import YmlImport
# from app.models.notification import NotificationTarget
# from app.models.admin import AdminUser

__all__: list[str] = []
