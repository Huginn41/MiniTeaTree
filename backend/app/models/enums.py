"""Доменные перечисления (статусы, типы).

Используем Python str-enum + SQLAlchemy String(со значением enum), а НЕ
нативый PostgreSQL ENUM. Причины:
1. PG ENUM тяжело менять (миграции добавления/удаления значений громоздкие).
2. Хотим совместимость с SQLite для тестов.
3. Строки в CHECK-констрейнте дают ту же целостность, но гибче.

Каждый enum = набор допустимых строковых значений + констрейнт на колонку.
"""

from __future__ import annotations

from enum import Enum, IntEnum, StrEnum


class OrderPaymentStatus(StrEnum):
    """Статус оплаты заказа (товары, через Telegram Payments / ЮKassa)."""

    PENDING = "pending"  # создан, ждёт оплаты
    PAID = "paid"  # оплачен
    REFUNDED = "refunded"  # возврат
    FAILED = "failed"  # платёж не прошёл
    CANCELLED = "cancelled"  # отменён до оплаты


class OrderDeliveryStatus(StrEnum):
    """Статус доставки (управляется менеджером вручную в CRM).

    Особенность процесса: доставка НЕ входит в платёж товаров — менеджер
    отдельно присылает клиенту ссылку на оплату доставки.
    """

    NEW = "new"  # новый заказ, ждёт менеджера
    MANAGER_CONTACTED = "manager_contacted"  # менеджер вышел на связь
    AWAITING_DELIVERY_PAYMENT = "awaiting_delivery_payment"  # ждём оплату доставки
    DELIVERY_PAID = "delivery_paid"  # доставка оплачена
    SHIPPING = "shipping"  # в пути
    DELIVERED = "delivered"  # доставлено/выдано
    CANCELLED = "cancelled"  # отменён


class DeliveryType(StrEnum):
    """Способ получения заказа."""

    PICKUP = "pickup"  # самовывоз
    COURIER = "courier"  # курьер
    PVZ = "pvz"  # пункт выдачи (Яндекс Маркет и т.п.)


class PaymentProvider(StrEnum):
    """Платёжный провайдер."""

    TELEGRAM_YOOKASSA = "telegram_yookassa"
    TBANK = "tbank"  # зарезервировано на будущее


class NotificationRole(StrEnum):
    """Роль получателя уведомлений о заказах."""

    SHOP = "shop"  # основной аккаунт магазина
    OWNER = "owner"  # владелец
    MANAGER = "manager"  # менеджер заказов
    LOGISTICS = "logistics"  # логист


class ProductWeight(IntEnum):
    """Стандартные граммовки чая (граммы)."""

    G25 = 25
    G50 = 50
    G75 = 75
    G100 = 100


# Обратная совместимость: Enum оставлен в импорте на случай использования
# в будущем (например, для нетипизированных наборов).
_ = Enum


# Списки значений для CHECK-констрейнтов (через запятую для SQL IN).
PAYMENT_STATUS_VALUES = tuple(s.value for s in OrderPaymentStatus)
DELIVERY_STATUS_VALUES = tuple(s.value for s in OrderDeliveryStatus)
DELIVERY_TYPE_VALUES = tuple(s.value for s in DeliveryType)
PROVIDER_VALUES = tuple(s.value for s in PaymentProvider)
NOTIF_ROLE_VALUES = tuple(s.value for s in NotificationRole)
