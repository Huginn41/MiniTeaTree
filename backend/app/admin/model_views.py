"""SQLAdmin ModelView-классы."""

from __future__ import annotations

from markupsafe import Markup
from sqladmin import ModelView, BaseView, expose
from starlette.requests import Request

from app.admin.upload import delete_upload_file as _delete_upload_file
from datetime import timezone as _tz, timedelta as _td
from sqladmin.fields import SelectField as _AdminSelectField

_MSK = _tz(_td(hours=3))

_STATUS_CHOICES = [
    ("new", "🆕 Новый"),
    ("assembling", "📦 Собираем"),
    ("ready", "✅ Готов"),
    ("awaiting_payment", "💳 Ожидает оплаты"),
    ("in_delivery", "🚚 Передан в доставку"),
    ("at_pvz", "🏪 В ПВЗ"),
    ("delivered", "🎉 Доставлен"),
    ("cancelled", "❌ Отменён"),
]

_SELECT_STYLE = (
    "padding:4px 10px;border-radius:8px;border:1px solid #dee2e6;"
    "cursor:pointer;font-size:13px;background:#fff"
)


def _fmt_dt(dt):
    if dt is None:
        return "—"
    return dt.replace(tzinfo=_tz.utc).astimezone(_MSK).strftime("%d.%m.%Y %H:%M")


def _status_select(order_id: int, field: str, current: str, choices: list) -> Markup:
    options = "".join(
        f'<option value="{v}"{" selected" if v == current else ""}>{label}</option>'
        for v, label in choices
    )
    js = (
        f"fetch('/admin-api/order/{order_id}/status',"
        f"{{method:'POST',credentials:'include',headers:{{'Content-Type':'application/json'}},"
        f"body:JSON.stringify({{field:'{field}',value:this.value}})}}"
        f").then(function(r){{if(r.ok){{location.reload();}}else{{r.text().then(function(t){{alert('Ошибка '+r.status+': '+t);}});}}}}"
        f").catch(function(e){{alert('Сетевая ошибка: '+e);}})"
    )
    return Markup(f'<select onchange="{js}" style="{_SELECT_STYLE}">{options}</select>')


from app.models.admin import AdminUser
from app.models.banner import Banner
from app.models.category import Category
from app.models.content import FaqItem, PickupPoint
from app.models.delivery import DeliveryInfo
from app.models.notification import NotificationTarget
from app.models.order import Order, OrderItem
from app.models.payment import PaymentEvent
from app.models.product import Product, ProductImage, ProductVariant
from app.models.user import User
from app.models.yml_import import YmlImport
from app.seed import DEMO_TG_IDS as _DEMO_TG_IDS


class OrderAdmin(ModelView, model=Order):
    name = "Заказы"
    name_plural = "Заказы"
    icon = "fa-solid fa-box"
    category = "Заказы"
    category_icon = "fa-solid fa-box"

    def list_query(self, request):
        from sqlalchemy import select
        stmt = select(Order)
        if request.session.get("admin_readonly"):
            stmt = stmt.where(Order.number.like("DEMO-%"))
        else:
            stmt = stmt.where(~Order.number.like("DEMO-%"))
        return stmt

    column_list = [
        "number", "user", "total_amount",
        "status", "created_at",
    ]
    column_searchable_list = ["number"]
    column_sortable_list = ["id", "total_amount", "created_at"]
    column_default_sort = [("created_at", True)]

    column_labels = {
        "number": "Номер",
        "user": "Клиент",
        "total_amount": "Сумма",
        "delivery_cost": "Стоимость доставки",
        "status": "Статус",
        "payment_link": "Ссылка на оплату",
        "tracking_link": "Трек / ссылка доставки",
        "comment": "Комментарий",
        "paid_at": "Дата оплаты",
        "delivered_at": "Дата доставки",
        "created_at": "Создан",
        "items": "Позиции",
        "delivery_info": "Доставка",
    }

    column_formatters = {
        "number": lambda m, a: Markup(f'<a href="/crm/order/{m.id}" style="font-weight:600;color:var(--bs-primary)">{m.number}</a>'),
        "user": lambda m, a: m.user.display_name if m.user else "—",
        "total_amount": lambda m, a: Markup(f"<b>{float(m.total_amount):.0f} ₽</b>"),
        "status": lambda m, a: _status_select(m.id, "status", m.status, _STATUS_CHOICES),
        "created_at": lambda m, a: _fmt_dt(m.created_at),
    }

    form_columns = [
        "status", "payment_link", "tracking_link",
        "delivery_cost", "comment", "paid_at", "delivered_at",
    ]
    form_overrides = {
        "status": _AdminSelectField,
    }
    form_args = {
        "status": {"choices": _STATUS_CHOICES},
    }
    page_size = 50

class OrderItemAdmin(ModelView, model=OrderItem):
    name = "↳ Позиции"
    name_plural = "Позиции заказов"
    category = "Заказы"

    column_list = ["order", "snapshot_name", "snapshot_weight_g", "quantity", "unit_price"]
    column_labels = {
        "order": "Заказ",
        "snapshot_name": "Товар",
        "snapshot_weight_g": "Граммовка",
        "quantity": "Кол-во",
        "unit_price": "Цена",
    }
    column_formatters = {
        "snapshot_weight_g": lambda m, a: f"{m.snapshot_weight_g} г",
        "unit_price": lambda m, a: f"{float(m.unit_price):.0f} ₽",
    }
    can_create = False
    can_delete = False
    page_size = 100

class DeliveryInfoAdmin(ModelView, model=DeliveryInfo):
    name = "↳ Доставки"
    name_plural = "Доставки"
    category = "Заказы"

    column_list = ["order", "type", "address", "contact_phone", "ym_payment_link"]
    column_labels = {
        "order": "Заказ",
        "type": "Способ",
        "address": "Адрес",
        "contact_phone": "Телефон",
        "ym_payment_link": "Ссылка на оплату",
    }
    column_formatters = {
        "type": lambda m, a: {"pickup": "Самовывоз", "courier": "Курьер", "pvz": "ПВЗ"}.get(m.type, m.type),
        "ym_payment_link": lambda m, a: Markup(f'<a href="{m.ym_payment_link}" target="_blank">🔗 Ссылка</a>') if m.ym_payment_link else "—",
    }
    form_columns = ["type", "address", "contact_phone", "ym_payment_link"]
    form_choices = {
        "type": [
            ("pickup", "Самовывоз"),
            ("courier", "Курьер"),
            ("pvz", "ПВЗ"),
        ]
    }
    page_size = 50

# ===== CRM =====

class UserAdmin(ModelView, model=User):
    name = "Клиенты"
    name_plural = "Клиенты"
    icon = "fa-solid fa-users"
    category = "CRM"
    category_icon = "fa-solid fa-users"

    def list_query(self, request):
        from sqlalchemy import select
        from app.models.user import User as _User
        stmt = select(_User)
        if request.session.get("admin_readonly"):
            stmt = stmt.where(_User.telegram_id < 0)
        else:
            stmt = stmt.where(_User.telegram_id > 0)
        return stmt

    column_list = [
        "display_name", "segment", "phone", "city",
        "total_orders", "total_spent", "avg_check",
        "last_seen_at", "created_at",
    ]
    column_searchable_list = ["username", "first_name", "phone", "email", "city"]
    column_sortable_list = ["id", "created_at", "last_seen_at"]
    column_default_sort = [("created_at", True)]

    _SEGMENT_LABELS = {
        "vip": ("🌟 VIP", "#7c3aed"),
        "wholesale": ("📦 Оптовик", "#0369a1"),
        "regular": ("☕ Постоянный", "#065f46"),
        "at_risk": ("⚠️ Под риском", "#b45309"),
        "churned": ("💤 Отток", "#6b7280"),
    }

    column_labels = {
        "display_name": "Клиент",
        "segment": "Сегмент",
        "phone": "Телефон",
        "email": "Email",
        "city": "Город",
        "total_orders": "Заказов",
        "total_spent": "Потрачено",
        "avg_check": "Средний чек",
        "last_seen_at": "Был в апп",
        "first_order_date": "Первый заказ",
        "last_order_date": "Последний заказ",
        "created_at": "Зарегистрирован",
        "is_admin": "Администратор",
        "telegram_id": "Telegram ID",
        "first_name": "Имя",
        "last_name": "Фамилия",
        "username": "Username",
        "notes": "Заметки",
        "language_code": "Язык",
    }

    column_formatters = {
        "display_name": lambda m, a: Markup(
            f'<a href="/admin/crm-customer/{m.id}" style="font-weight:600;text-decoration:none">'
            f'{m.display_name}</a>'
        ),
        "segment": lambda m, a: Markup(
            f'<span style="padding:3px 8px;border-radius:100px;font-size:11px;font-weight:600;'
            f'background:{UserAdmin._SEGMENT_LABELS.get(m.segment, ("", "#6b7280"))[1]}22;'
            f'color:{UserAdmin._SEGMENT_LABELS.get(m.segment, ("", "#6b7280"))[1]}">'
            f'{UserAdmin._SEGMENT_LABELS.get(m.segment, (m.segment or "—", ""))[0]}</span>'
        ) if m.segment else "—",
        "total_orders": lambda m, a: Markup(f"<b>{m.total_orders}</b>") if m.total_orders else "0",
        "total_spent": lambda m, a: f"{m.total_spent:.0f} ₽" if m.total_spent else "—",
        "avg_check": lambda m, a: f"{m.avg_check:.0f} ₽" if m.avg_check else "—",
        "last_seen_at": lambda m, a: _fmt_dt(m.last_seen_at) if m.last_seen_at else "—",
        "created_at": lambda m, a: _fmt_dt(m.created_at),
    }

    form_columns = ["phone", "email", "city", "segment", "notes", "is_admin"]
    form_choices = {
        "segment": [
            ("", "— без сегмента —"),
            ("vip", "🌟 VIP"),
            ("wholesale", "📦 Оптовик"),
            ("regular", "☕ Постоянный"),
            ("at_risk", "⚠️ Под риском"),
            ("churned", "💤 Отток"),
        ]
    }
    can_delete = False
    page_size = 50

class NotificationTargetAdmin(ModelView, model=NotificationTarget):
    name = "Уведомления"
    name_plural = "Уведомления (кому слать)"
    category = "Система"

    column_list = ["telegram_id", "name", "role", "is_active"]
    column_labels = {
        "telegram_id": "Telegram ID",
        "name": "Имя",
        "role": "Роль",
        "is_active": "Активен",
    }
    column_formatters = {
        "role": lambda m, a: {
            "shop": "🏪 Магазин",
            "owner": "👑 Владелец",
            "manager": "👨‍💼 Менеджер",
            "logistics": "🚚 Логист",
        }.get(m.role, m.role),
        "is_active": lambda m, a: Markup("✅") if m.is_active else Markup("❌"),
    }
    form_choices = {
        "role": [
            ("shop", "Магазин"),
            ("owner", "Владелец"),
            ("manager", "Менеджер"),
            ("logistics", "Логист"),
        ]
    }
    page_size = 50

class PickupPointAdmin(ModelView, model=PickupPoint):
    name = "↳ Самовывоз"
    name_plural = "Пункты самовывоза"
    category = "Настройки магазина"

    column_list = ["name", "city", "street", "building", "work_hours", "is_active"]
    column_labels = {
        "name": "Название",
        "city": "Город",
        "street": "Улица",
        "building": "Дом",
        "address": "Адрес",
        "work_hours": "Режим работы",
        "comment": "Комментарий",
        "phone": "Телефон",
        "map_embed_src": "Ссылка Яндекс Карт (src iframe)",
        "is_active": "Активен",
        "sort_order": "Порядок",
    }
    form_columns = [
        "name", "city", "street", "building",
        "work_hours", "comment", "phone",
        "map_embed_src", "sort_order", "is_active",
    ]
    page_size = 50

# ===== КАТАЛОГ =====

class CategoryAdmin(ModelView, model=Category):
    name = "↳ Категории"
    name_plural = "Категории"
    category = "Настройки магазина"

    column_list = ["sort_order", "name", "slug", "image_path", "created_at"]
    column_searchable_list = ["name", "slug"]
    column_sortable_list = ["sort_order", "name"]
    column_default_sort = [("sort_order", False)]
    column_labels = {
        "sort_order": "Порядок",
        "name": "Название",
        "slug": "API тег",
        "image_path": "Фото",
        "icon": "Иконка (эмодзи)",
        "description": "Описание",
        "created_at": "Создана",
    }
    column_formatters = {
        "image_path": lambda m, a: Markup(
            f'<img src="{m.image_path}" style="width:48px;height:48px;object-fit:cover;border-radius:6px">'
        ) if m.image_path else "—",
    }
    form_columns = ["name", "slug", "image_path", "icon", "description", "sort_order", "is_active"]
    page_size = 50

class ProductAdmin(ModelView, model=Product):
    name = "Товары"
    name_plural = "Товары"
    icon = "fa-solid fa-leaf"
    category = "Настройки магазина"
    category_icon = "fa-solid fa-store"

    column_list = ["sort_order", "name", "category", "base_price", "slug"]
    column_searchable_list = ["name", "slug"]
    column_sortable_list = ["sort_order", "base_price", "name"]
    column_default_sort = [("sort_order", False)]
    column_labels = {
        "sort_order": "Порядок",
        "name": "Название",
        "category": "Категория",
        "base_price": "Цена (₽/г или ₽/шт)",
        "slug": "API тег",
        "description": "Описание",
        "origin": "Происхождение",
        "tags": "Теги",
        "is_active": "Активен",
        "is_unit": "Штучный товар",
        "unit_label": "Единица (шт / блин / упак)",
    }
    column_formatters = {
        "base_price": lambda m, a: (
            f"{float(m.base_price):.0f} ₽/шт" if m.is_unit else f"{float(m.base_price):.2f} ₽/г"
        ),
    }
    form_columns = [
        "category", "name", "slug", "base_price",
        "is_unit", "unit_label",
        "description", "origin", "tags", "sort_order", "is_active",
    ]
    page_size = 50

    async def after_model_change(self, data, model, is_created, request):
        from app.db import get_session_factory
        from app.models.product import ProductVariant
        from sqlalchemy import select, delete

        async with get_session_factory()() as session:
            if model.is_unit:
                # Штучный товар: один вариант weight_g=0, цена = base_price
                await session.execute(
                    delete(ProductVariant).where(
                        ProductVariant.product_id == model.id,
                        ProductVariant.weight_g != 0,
                    )
                )
                res = await session.execute(
                    select(ProductVariant).where(
                        ProductVariant.product_id == model.id,
                        ProductVariant.weight_g == 0,
                    )
                )
                variant = res.scalar_one_or_none()
                price = float(model.base_price)
                if variant:
                    variant.price = price
                else:
                    session.add(ProductVariant(
                        product_id=model.id, weight_g=0, price=price, in_stock=True,
                    ))
            else:
                # Весовой товар: 4 варианта 25/50/75/100 г
                await session.execute(
                    delete(ProductVariant).where(
                        ProductVariant.product_id == model.id,
                        ProductVariant.weight_g == 0,
                    )
                )
                price_per_gram = float(model.base_price)
                for weight in (25, 50, 75, 100):
                    res = await session.execute(
                        select(ProductVariant).where(
                            ProductVariant.product_id == model.id,
                            ProductVariant.weight_g == weight,
                        )
                    )
                    variant = res.scalar_one_or_none()
                    price = round(price_per_gram * weight, 2)
                    if variant:
                        variant.price = price
                    else:
                        session.add(ProductVariant(
                            product_id=model.id, weight_g=weight, price=price, in_stock=True,
                        ))
            await session.commit()

    async def after_model_delete(self, model, request):
        from app.db import get_session_factory
        from app.models.product import ProductImage
        from sqlalchemy import select
        async with get_session_factory()() as session:
            imgs = (await session.execute(
                select(ProductImage).where(ProductImage.product_id == model.id)
            )).scalars().all()
            for img in imgs:
                _delete_upload_file(img.path)

class BannerAdmin(ModelView, model=Banner):
    name = "↳ Баннеры"
    name_plural = "Баннеры"
    category = "Настройки магазина"

    column_list = ["sort", "image_path", "title", "is_active", "link"]
    column_sortable_list = ["sort"]
    column_labels = {
        "sort": "Порядок",
        "image_path": "Фото",
        "title": "Заголовок",
        "subtitle": "Подзаголовок",
        "is_active": "Активен",
        "link": "Ссылка",
    }
    column_formatters = {
        "image_path": lambda m, a: Markup(
            f'<img src="{m.image_path}" style="height:48px;border-radius:6px;object-fit:cover;max-width:120px" '
            f'onerror="this.style.display=\'none\';this.nextSibling.style.display=\'inline\'">'
            f'<span style="display:none;color:#dc3545;font-size:12px">⚠️ нет файла</span>'
        ) if m.image_path else Markup('<span style="color:#aaa">—</span>'),
        "is_active": lambda m, a: Markup("✅") if m.is_active else Markup("❌"),
    }
    form_columns = ["title", "subtitle", "image_path", "link", "sort", "is_active"]
    page_size = 50

# ===== СИСТЕМА =====

class AdminUserAdmin(ModelView, model=AdminUser):
    name = "Администраторы"
    name_plural = "Администраторы"
    icon = "fa-solid fa-shield"
    category = "Система"
    category_icon = "fa-solid fa-gear"

    column_list = ["username", "is_superuser", "created_at"]
    column_labels = {
        "username": "Логин",
        "is_superuser": "Суперадмин",
        "telegram_id": "Telegram ID",
        "created_at": "Создан",
    }
    column_formatters = {
        "is_superuser": lambda m, a: Markup("👑") if m.is_superuser else "",
        "created_at": lambda m, a: _fmt_dt(m.created_at),
    }
    form_columns = ["username", "is_superuser", "telegram_id"]
    page_size = 50

class YmlImportAdmin(ModelView, model=YmlImport):
    name = "↳ YML-импорты"
    name_plural = "YML-импорты"
    category = "Система"

    column_list = ["source", "status", "products_added", "products_updated", "started_at"]
    column_labels = {
        "source": "Источник",
        "status": "Статус",
        "products_added": "Добавлено",
        "products_updated": "Обновлено",
        "products_deactivated": "Деактивировано",
        "started_at": "Запущен",
    }
    column_formatters = {
        "started_at": lambda m, a: _fmt_dt(m.started_at),
    }
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 50

class PaymentEventAdmin(ModelView, model=PaymentEvent):
    name = "↳ Платежи"
    name_plural = "Платёжные события"
    category = "Система"

    column_list = ["order_id", "provider", "status", "external_id", "created_at"]
    column_labels = {
        "order_id": "Заказ",
        "provider": "Провайдер",
        "status": "Статус",
        "external_id": "Внешний ID",
        "created_at": "Дата",
    }
    column_formatters = {
        "created_at": lambda m, a: _fmt_dt(m.created_at),
    }
    can_create = False
    can_edit = False
    can_delete = False
    page_size = 50


class BonusSettingsView(BaseView):
    name = "Бонусная система"
    icon = "fa-solid fa-gift"
    category = "Настройки магазина"

    @expose("/bonus-settings", methods=["GET"])
    async def bonus_settings(self, request: Request):
        from starlette.responses import RedirectResponse
        return RedirectResponse("/admin/bonus-settings")
