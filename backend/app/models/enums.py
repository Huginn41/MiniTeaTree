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


class OrderStatus(StrEnum):
    """Единый статус заказа (управляется менеджером в CRM).

    Самовывоз:  new → assembling → ready → delivered
    Доставка:   new → awaiting_payment → in_delivery → at_pvz → delivered
    """

    NEW = "new"                          # новый заказ
    ASSEMBLING = "assembling"            # собираем (самовывоз)
    READY = "ready"                      # готов к выдаче (самовывоз)
    AWAITING_PAYMENT = "awaiting_payment"  # ожидает оплаты (доставка)
    IN_DELIVERY = "in_delivery"          # передан в доставку
    AT_PVZ = "at_pvz"                    # в пункте выдачи
    DELIVERED = "delivered"              # доставлен / выдан
    CANCELLED = "cancelled"              # отменён


# Лейблы для клиентского интерфейса
ORDER_STATUS_CLIENT_LABELS: dict[str, str] = {
    "new": "В обработке",
    "assembling": "Собираем",
    "ready": "Готов к выдаче",
    "awaiting_payment": "Ожидает оплату",
    "in_delivery": "В пути",
    "at_pvz": "В пункте выдачи",
    "delivered": "Получен",
    "cancelled": "Отменён",
}

# Лейблы для администратора
ORDER_STATUS_ADMIN_LABELS: dict[str, str] = {
    "new": "Новый",
    "assembling": "Собираем",
    "ready": "Готов",
    "awaiting_payment": "Ожидает оплаты",
    "in_delivery": "Передан в доставку",
    "at_pvz": "В ПВЗ",
    "delivered": "Доставлен",
    "cancelled": "Отменён",
}


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
ORDER_STATUS_VALUES = tuple(s.value for s in OrderStatus)
DELIVERY_TYPE_VALUES = tuple(s.value for s in DeliveryType)
PROVIDER_VALUES = tuple(s.value for s in PaymentProvider)
NOTIF_ROLE_VALUES = tuple(s.value for s in NotificationRole)
