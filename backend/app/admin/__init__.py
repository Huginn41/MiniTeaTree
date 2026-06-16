"""SQLAdmin — панель администратора.

Авторизация: username/password из таблицы admin_users (bcrypt).
Маршрут: /admin (регистрируется в main.py).

Представления сгруппированы по разделам:
  - Каталог: продукты, варианты, категории, изображения, баннеры
  - Заказы: заказы, позиции, доставка
  - CRM: пользователи, FAQ, ПВЗ
  - Система: админы, уведомления, импорты YML, платёжные события
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from passlib.context import CryptContext
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from starlette.requests import Request

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminAuth(AuthenticationBackend):
    """Аутентификация через AdminUser (username + bcrypt-пароль)."""

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("admin_token")
        return token == "authenticated"

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))

        from app.config import get_settings
        from app.db import get_session_factory
        from app.models.admin import AdminUser

        async with get_session_factory()() as session:
            result = await session.execute(
                select(AdminUser).where(AdminUser.username == username)
            )
            admin = result.scalar_one_or_none()

        if admin is None:
            # Фоллбек: проверяем статичный пароль из .env (для первого входа).
            settings = get_settings()
            if username == settings.admin_username and password == settings.admin_password.get_secret_value():
                request.session["admin_token"] = "authenticated"
                return True
            return False

        if not _pwd_ctx.verify(password, admin.password_hash):
            return False

        request.session["admin_token"] = "authenticated"
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True


# ---------- ModelView helpers ----------

def _money(col: str) -> dict[str, Any]:
    return {"form_columns": [col]}


# ---------- Каталог ----------

class CategoryAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "Категория"
    name_plural = "Категории"
    icon = "fa-solid fa-tag"
    category = "Каталог"
    column_list = ["id", "name", "slug", "sort_order", "created_at"]
    column_searchable_list = ["name", "slug"]
    column_sortable_list = ["id", "sort_order", "name"]
    column_default_sort = [("sort_order", False)]
    form_excluded_columns = ["products", "created_at", "updated_at"]
    page_size = 50


class ProductAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "Товар"
    name_plural = "Товары"
    icon = "fa-solid fa-leaf"
    category = "Каталог"
    column_list = ["id", "name", "slug", "category", "base_price", "sort_order", "created_at"]
    column_searchable_list = ["name", "slug"]
    column_sortable_list = ["id", "sort_order", "base_price", "name"]
    column_default_sort = [("sort_order", False)]
    form_excluded_columns = ["variants", "images", "cart_items", "order_items", "created_at", "updated_at"]
    page_size = 50


class ProductVariantAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "Вариант товара"
    name_plural = "Варианты товаров"
    icon = "fa-solid fa-weight-hanging"
    category = "Каталог"
    column_list = ["id", "product", "weight_g", "price", "sku", "in_stock"]
    column_searchable_list = ["sku"]
    column_sortable_list = ["id", "weight_g", "price", "in_stock"]
    column_default_sort = [("id", True)]
    form_excluded_columns = ["cart_items", "order_items", "created_at", "updated_at"]
    page_size = 100


class ProductImageAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "Фото товара"
    name_plural = "Фото товаров"
    icon = "fa-solid fa-image"
    category = "Каталог"
    column_list = ["id", "product", "is_main", "sort_order", "path"]
    column_sortable_list = ["id", "sort_order", "is_main"]
    form_excluded_columns = ["created_at", "updated_at"]
    page_size = 100


class BannerAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "Баннер"
    name_plural = "Баннеры"
    icon = "fa-solid fa-images"
    category = "Каталог"
    column_list = ["id", "title", "sort_order", "is_active", "image_path", "link"]
    column_sortable_list = ["id", "sort_order"]
    form_excluded_columns = ["created_at", "updated_at"]
    page_size = 50


# ---------- Заказы ----------

class OrderAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "Заказ"
    name_plural = "Заказы"
    icon = "fa-solid fa-box"
    category = "Заказы"
    column_list = [
        "id", "number", "user", "total_amount", "delivery_cost",
        "status_payment", "status_delivery", "created_at",
    ]
    column_searchable_list = ["number"]
    column_sortable_list = ["id", "total_amount", "status_payment", "status_delivery", "created_at"]
    column_default_sort = [("created_at", True)]
    # Менеджер может менять только статусы и стоимость доставки
    form_columns = [
        "status_payment", "status_delivery", "delivery_cost", "comment",
        "paid_at", "delivered_at",
    ]
    page_size = 50


class OrderItemAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "Позиция заказа"
    name_plural = "Позиции заказов"
    icon = "fa-solid fa-list"
    category = "Заказы"
    column_list = ["id", "order", "snapshot_name", "snapshot_weight_g", "quantity", "unit_price"]
    column_sortable_list = ["id"]
    form_excluded_columns = ["created_at", "updated_at"]
    can_create = False
    can_delete = False
    page_size = 100


class DeliveryInfoAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "Доставка"
    name_plural = "Доставки"
    icon = "fa-solid fa-truck"
    category = "Заказы"
    column_list = ["id", "order", "type", "address", "contact_phone", "ym_payment_link"]
    column_searchable_list = ["address", "contact_phone"]
    column_sortable_list = ["id", "type"]
    # Менеджер заполняет ссылку на оплату доставки
    form_columns = ["type", "address", "contact_phone", "ym_payment_link"]
    page_size = 50


# ---------- CRM ----------

class UserAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-users"
    category = "CRM"
    column_list = ["id", "telegram_id", "first_name", "last_name", "username", "phone", "created_at"]
    column_searchable_list = ["telegram_id", "username", "first_name", "phone"]
    column_sortable_list = ["id", "created_at"]
    column_default_sort = [("created_at", True)]
    form_columns = ["phone", "is_admin"]
    can_delete = False
    page_size = 50


class FaqItemAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "FAQ"
    name_plural = "FAQ"
    icon = "fa-solid fa-circle-question"
    category = "CRM"
    column_list = ["id", "question", "sort_order", "is_active"]
    column_sortable_list = ["id", "sort_order"]
    form_excluded_columns = ["created_at", "updated_at"]
    page_size = 50


class PickupPointAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "Пункт самовывоза"
    name_plural = "Пункты самовывоза"
    icon = "fa-solid fa-location-dot"
    category = "CRM"
    column_list = ["id", "name", "address", "work_hours", "is_active"]
    column_searchable_list = ["name", "address"]
    form_excluded_columns = ["created_at", "updated_at"]
    page_size = 50


class NotificationTargetAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "Уведомление"
    name_plural = "Уведомления (кому слать)"
    icon = "fa-solid fa-bell"
    category = "CRM"
    column_list = ["id", "telegram_id", "role", "is_active"]
    form_excluded_columns = ["created_at", "updated_at"]
    page_size = 50


# ---------- Система ----------

class AdminUserAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "Администратор"
    name_plural = "Администраторы"
    icon = "fa-solid fa-user-shield"
    category = "Система"
    column_list = ["id", "username", "is_superuser", "created_at"]
    form_columns = ["username", "is_superuser", "telegram_id"]
    can_delete = True
    page_size = 50


class YmlImportAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "YML-импорт"
    name_plural = "YML-импорты"
    icon = "fa-solid fa-file-import"
    category = "Система"
    column_list = ["id", "source", "status", "products_added", "products_updated", "products_deactivated", "started_at"]
    column_sortable_list = ["id", "status", "started_at"]
    column_default_sort = [("started_at", True)]
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 50


class PaymentEventAdmin(ModelView, model=None):  # type: ignore[call-arg]
    name = "Платёж"
    name_plural = "Платёжные события"
    icon = "fa-solid fa-credit-card"
    category = "Система"
    column_list = ["id", "order_id", "provider", "status", "external_id", "created_at"]
    column_sortable_list = ["id", "created_at"]
    column_default_sort = [("created_at", True)]
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 50


# ---------- Регистрация ----------

def setup_admin(app: FastAPI, engine: Any) -> None:
    """Подключает SQLAdmin к FastAPI-приложению.

    Вызывается из main.py после инициализации движка БД.
    Использует синхронный движок (sqladmin не поддерживает async engine напрямую
    с некоторыми версиями, но sqladmin >= 0.18 работает с async engine).
    """
    from app.config import get_settings
    from app.models.admin import AdminUser
    from app.models.banner import Banner
    from app.models.cart import CartItem
    from app.models.category import Category
    from app.models.content import FaqItem, PickupPoint
    from app.models.delivery import DeliveryInfo
    from app.models.notification import NotificationTarget
    from app.models.order import Order, OrderItem
    from app.models.payment import PaymentEvent
    from app.models.product import Product, ProductImage, ProductVariant
    from app.models.user import User
    from app.models.yml_import import YmlImport

    settings = get_settings()

    authentication_backend = AdminAuth(secret_key=settings.jwt_secret.get_secret_value())
    admin = Admin(
        app=app,
        engine=engine,
        authentication_backend=authentication_backend,
        title="Чайное Дерево — CRM",
        base_url="/admin",
        templates_dir=None,
    )

    # Привязываем модели к view-классам
    CategoryAdmin.model = Category
    ProductAdmin.model = Product
    ProductVariantAdmin.model = ProductVariant
    ProductImageAdmin.model = ProductImage
    BannerAdmin.model = Banner
    OrderAdmin.model = Order
    OrderItemAdmin.model = OrderItem
    DeliveryInfoAdmin.model = DeliveryInfo
    UserAdmin.model = User
    FaqItemAdmin.model = FaqItem
    PickupPointAdmin.model = PickupPoint
    NotificationTargetAdmin.model = NotificationTarget
    AdminUserAdmin.model = AdminUser
    YmlImportAdmin.model = YmlImport
    PaymentEventAdmin.model = PaymentEvent

    admin.add_view(CategoryAdmin)
    admin.add_view(ProductAdmin)
    admin.add_view(ProductVariantAdmin)
    admin.add_view(ProductImageAdmin)
    admin.add_view(BannerAdmin)
    admin.add_view(OrderAdmin)
    admin.add_view(OrderItemAdmin)
    admin.add_view(DeliveryInfoAdmin)
    admin.add_view(UserAdmin)
    admin.add_view(FaqItemAdmin)
    admin.add_view(PickupPointAdmin)
    admin.add_view(NotificationTargetAdmin)
    admin.add_view(AdminUserAdmin)
    admin.add_view(YmlImportAdmin)
    admin.add_view(PaymentEventAdmin)
