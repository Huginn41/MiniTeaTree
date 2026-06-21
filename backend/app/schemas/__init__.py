"""Pydantic-схемы (request/response) для API эндпоинтов.

Используются в роутерах для валидации и сериализации.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# ===================== Категории =====================

class CategoryBrief(BaseModel):
    """Краткое представление категории для списка."""

    id: int
    name: str
    slug: str
    icon: str | None = None
    image_path: str | None = None

    model_config = {"from_attributes": True}


# ===================== Товары =====================

class VariantOut(BaseModel):
    """Вариант товара (граммовка + цена)."""

    id: int
    weight_g: int
    price: float
    sku: str | None = None
    in_stock: bool = True

    model_config = {"from_attributes": True}


class ProductImageOut(BaseModel):
    """Фото товара."""

    id: int
    path: str
    is_main: bool = False
    alt: str | None = None

    model_config = {"from_attributes": True}


class ProductListItem(BaseModel):
    """Товар для каталога (кратко)."""

    id: int
    name: str
    slug: str
    base_price: float
    origin: str | None = None
    category: CategoryBrief
    main_image: str | None = None
    variants: list[VariantOut] = []

    model_config = {"from_attributes": True}


class ProductDetail(BaseModel):
    """Товар для страницы деталей."""

    id: int
    name: str
    slug: str
    description: str | None = None
    base_price: float
    origin: str | None = None
    tags: list[str] = []
    category: CategoryBrief
    variants: list[VariantOut] = []
    images: list[ProductImageOut] = []

    model_config = {"from_attributes": True}


# ===================== Баннеры =====================

class BannerOut(BaseModel):
    """Баннер для главной."""

    id: int
    title: str | None = None
    subtitle: str | None = None
    image_path: str
    link: str | None = None

    model_config = {"from_attributes": True}


# ===================== FAQ / ПВЗ =====================

class FaqItemOut(BaseModel):
    """FAQ-элемент."""

    id: int
    question: str
    answer: str

    model_config = {"from_attributes": True}


class PickupPointOut(BaseModel):
    """Пункт самовывоза."""

    id: int
    name: str
    address: str
    work_hours: str | None = None
    phone: str | None = None

    model_config = {"from_attributes": True}


# ===================== Корзина =====================

class CartItemOut(BaseModel):
    """Позиция корзины для ответа."""

    id: int
    variant: VariantOut
    quantity: int
    # Информация о товаре для отображения (denormalised).
    product_name: str = ""
    product_slug: str = ""
    main_image: str | None = None

    model_config = {"from_attributes": True}


class CartOut(BaseModel):
    """Корзина целиком."""

    items: list[CartItemOut] = []
    total_amount: float = 0

    model_config = {"from_attributes": True}


class CartItemAdd(BaseModel):
    """Добавить вариант в корзину."""

    variant_id: int
    quantity: int = Field(default=1, ge=1, le=99)


class CartItemUpdate(BaseModel):
    """Обновить количество позиции."""

    quantity: int = Field(ge=0, le=99)


# ===================== Заказы =====================

class OrderItemSnapshot(BaseModel):
    """Позиция заказа (снапшот)."""

    id: int
    product_id: int | None = None
    variant_id: int | None = None
    quantity: int
    unit_price: float
    snapshot_name: str
    snapshot_weight_g: int

    model_config = {"from_attributes": True}


class DeliveryInfoOut(BaseModel):
    """Информация о доставке заказа."""

    type: str
    address: str = ""
    contact_phone: str | None = None
    ym_payment_link: str | None = None

    model_config = {"from_attributes": True}


class OrderBrief(BaseModel):
    """Краткое представление заказа в списке."""

    id: int
    number: str
    total_amount: float
    status: str
    created_at: datetime
    items_count: int = 0

    model_config = {"from_attributes": True}


class OrderDetail(BaseModel):
    """Детали заказа."""

    id: int
    number: str
    total_amount: float
    delivery_cost: float
    status: str
    payment_link: str | None = None
    tracking_link: str | None = None
    comment: str | None = None
    paid_at: datetime | None = None
    delivered_at: datetime | None = None
    created_at: datetime
    items: list[OrderItemSnapshot] = []
    delivery_info: DeliveryInfoOut | None = None

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    """Создание заказа."""

    comment: str | None = None
    delivery_type: str = "pickup"
    address: str = ""
    contact_phone: str | None = None


class OrderStatusUpdate(BaseModel):
    """Обновление статуса заказа менеджером."""

    status: str


# ===================== Профиль =====================

class ProfileOut(BaseModel):
    """Профиль пользователя."""

    telegram_id: int
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    phone: str | None = None

    model_config = {"from_attributes": True}
