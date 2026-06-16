"""SQLAdmin — панель администратора Чайного Дерева."""

from __future__ import annotations

import os
import shutil
import uuid as _uuid
from pathlib import Path
from typing import Any, Callable

import bcrypt as _bcrypt
from markupsafe import Markup
from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin import widgets as _sqladmin_widgets

# wtforms 3.2+ добавил validation_attrs, sqladmin 0.27 этого не знает
if not hasattr(_sqladmin_widgets.BooleanInputWidget, "validation_attrs"):
    _sqladmin_widgets.BooleanInputWidget.validation_attrs = []
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy import select
from fastapi import UploadFile, File as _File
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ---------- Варианты статусов ----------

_DELIVERY_CHOICES = [
    ("new", "🆕 Новый"),
    ("manager_contacted", "📞 Связались"),
    ("awaiting_delivery_payment", "💳 Ждёт оплаты"),
    ("delivery_paid", "✅ Доставка OK"),
    ("shipping", "🚚 В пути"),
    ("delivered", "📦 Доставлен"),
    ("cancelled", "❌ Отменён"),
]

_PAYMENT_CHOICES = [
    ("pending", "⏳ Ожидает"),
    ("paid", "✅ Оплачен"),
    ("refunded", "↩️ Возврат"),
    ("failed", "❌ Ошибка"),
    ("cancelled", "🚫 Отменён"),
]

_SELECT_STYLE = (
    "padding:4px 10px;border-radius:8px;border:1px solid #dee2e6;"
    "cursor:pointer;font-size:13px;background:#fff"
)


def _status_select(order_id: int, field: str, current: str, choices: list) -> Markup:
    options = "".join(
        f'<option value="{v}"{"  selected" if v == current else ""}>{label}</option>'
        for v, label in choices
    )
    js = (
        f"fetch('/admin-api/order/{order_id}/status',"
        f"{{method:'POST',headers:{{'Content-Type':'application/json'}},"
        f"body:JSON.stringify({{field:'{field}',value:this.value}})}}"
        f").then(r=>r.ok&&location.reload())"
    )
    return Markup(f'<select onchange="{js}" style="{_SELECT_STYLE}">{options}</select>')


# ---------- Аутентификация ----------

class AdminAuth(AuthenticationBackend):
    async def authenticate(self, request: Request) -> bool:
        return request.session.get("admin_token") == "authenticated"

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
            settings = get_settings()
            if username == settings.admin_username and password == settings.admin_password.get_secret_value():
                request.session["admin_token"] = "authenticated"
                return True
            return False

        if not _bcrypt.checkpw(password.encode(), admin.password_hash.encode()):
            return False

        request.session["admin_token"] = "authenticated"
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True


_ADMIN_JS = ("""
<script>
(function(){

  // ---- 1. Свернуть неактивные разделы меню ----
  function collapseInactive(){
    document.querySelectorAll('[data-bs-toggle="collapse"]').forEach(function(t){
      var sel = t.getAttribute('data-bs-target') || t.getAttribute('href');
      if(!sel) return;
      var el = document.querySelector(sel);
      if(!el || !el.classList.contains('show')) return;
      if(!el.querySelector('.active')){
        el.classList.remove('show');
        t.classList.add('collapsed');
        t.setAttribute('aria-expanded','false');
      }
    });
  }

  // ---- 2. Автогенерация slug (API тег) из названия ----
  var _tr = {
    'а':'a','б':'b','в':'v','г':'g','д':'d',
    'е':'e','ё':'yo','ж':'zh','з':'z','и':'i',
    'й':'j','к':'k','л':'l','м':'m','н':'n',
    'о':'o','п':'p','р':'r','с':'s','т':'t',
    'у':'u','ф':'f','х':'kh','ц':'ts','ч':'ch',
    'ш':'sh','щ':'shch','ъ':'','ы':'y','ь':'',
    'э':'e','ю':'yu','я':'ya'
  };
  function toSlug(s){
    return s.toLowerCase().split('').map(function(c){ return _tr[c]||c; }).join('')
      .replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
  }
  function initSlugAuto(){
    var nameEl = document.querySelector('#name');
    var slugEl = document.querySelector('#slug');
    if(!nameEl || !slugEl) return;
    slugEl.placeholder = 'авто из названия';
    slugEl.style.background = '#f8f9fa';
    slugEl.title = 'Генерируется автоматически. Можно редактировать вручную.';
    nameEl.addEventListener('input', function(){
      if(!slugEl._manual){ slugEl.value = toSlug(nameEl.value); }
    });
    slugEl.addEventListener('input', function(){ slugEl._manual = true; });
    slugEl.addEventListener('dblclick', function(){ slugEl._manual = false; slugEl.value = toSlug(nameEl.value||''); });
  }

  // ---- 3. Кнопки загрузки файлов ----
  function initFileUploads(){
    document.querySelectorAll('input[type="text"]').forEach(function(inp){
      var id = inp.id||''; var nm = inp.name||'';
      if(id.indexOf('path')===-1 && nm.indexOf('path')===-1) return;

      // Скрываем оригинальный input, он будет хранить путь и отправляться в форме
      inp.style.display = 'none';

      // Видимое поле — только для отображения имени файла
      var display = document.createElement('input');
      display.type = 'text';
      display.readOnly = true;
      display.className = inp.className;
      display.style.cssText = 'background:#f8f9fa;cursor:default;flex:1;';
      display.placeholder = 'Файл не выбран';
      // Показываем имя уже загруженного файла (если путь есть)
      if(inp.value){ display.value = inp.value.split('/').pop(); }

      var fileInput = document.createElement('input');
      fileInput.type = 'file'; fileInput.accept = 'image/*'; fileInput.style.display = 'none';

      var btn = document.createElement('button');
      btn.type = 'button'; btn.textContent = '📁 Выбрать файл';
      btn.className = 'btn btn-sm btn-outline-secondary';

      var wrap = document.createElement('div');
      wrap.style.cssText = 'display:flex;align-items:center;gap:8px;';
      inp.parentNode.insertBefore(wrap, inp);
      wrap.appendChild(inp);
      wrap.appendChild(display);
      wrap.appendChild(fileInput);
      wrap.appendChild(btn);

      btn.onclick = function(){ fileInput.click(); };
      fileInput.onchange = function(){
        var file = fileInput.files[0]; if(!file) return;
        var fd = new FormData(); fd.append('file', file);
        btn.textContent = '⏳ ...'; btn.disabled = true;
        fetch('/admin-api/upload',{method:'POST',body:fd})
          .then(function(r){return r.json();})
          .then(function(d){
            inp.value = d.path;
            display.value = file.name;
            btn.textContent = '📁 Выбрать файл'; btn.disabled = false;
          })
          .catch(function(){ btn.textContent = '❌ Ошибка'; btn.disabled = false; });
      };
    });
  }

  function init(){
    collapseInactive();
    initSlugAuto();
    initFileUploads();
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else { init(); }
})();
</script>
</body>""").encode("utf-8")


class _AdminCollapseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        ct = response.headers.get("content-type", "")
        if request.url.path.startswith("/admin") and "text/html" in ct:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            body = body.replace(b"</body>", _ADMIN_JS)
            headers = dict(response.headers)
            headers["content-length"] = str(len(body))
            return Response(content=body, status_code=response.status_code,
                            headers=headers, media_type="text/html")
        return response


# ---------- Регистрация ----------

def setup_admin(app: FastAPI, engine: Any) -> None:
    from app.config import get_settings
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

    settings = get_settings()
    authentication_backend = AdminAuth(secret_key=settings.jwt_secret.get_secret_value())
    admin = Admin(
        app=app,
        engine=engine,
        authentication_backend=authentication_backend,
        title="Чайное Дерево — CRM",
        base_url="/admin",
    )

    # ===== ЗАКАЗЫ =====

    # Endpoint для смены статуса прямо из списка
    from fastapi.responses import JSONResponse as _JSONResponse

    _UPLOADS_DIR = Path(__file__).parent.parent.parent / "static" / "uploads"

    @app.post("/admin-api/upload")
    async def admin_upload(request: Request, file: UploadFile = _File(...)):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            ext = ".jpg"
        name = f"{_uuid.uuid4().hex}{ext}"
        with open(_UPLOADS_DIR / name, "wb") as f:
            shutil.copyfileobj(file.file, f)
        return _JSONResponse({"path": f"/static/uploads/{name}"})

    @app.post("/admin-api/order/{order_id}/status")
    async def admin_update_order_status(order_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        data = await request.json()
        field = data.get("field")
        value = data.get("value")
        allowed_fields = {"status_delivery", "status_payment"}
        if field not in allowed_fields:
            return _JSONResponse(status_code=400, content={"error": "Invalid field"})
        from app.db import get_session_factory
        async with get_session_factory()() as session:
            result = await session.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one_or_none()
            if not order:
                return _JSONResponse(status_code=404, content={"error": "Not found"})
            setattr(order, field, value)
            await session.commit()
        return _JSONResponse({"ok": True})

    class OrderAdmin(ModelView, model=Order):
        name = "Заказы"
        name_plural = "Заказы"
        icon = "fa-solid fa-box"
        category = "Заказы"

        column_list = [
            "number", "user", "total_amount",
            "status_payment", "status_delivery", "created_at",
        ]
        column_searchable_list = ["number"]
        column_sortable_list = ["id", "total_amount", "created_at"]
        column_default_sort = [("created_at", True)]

        column_labels = {
            "number": "Номер",
            "user": "Клиент",
            "total_amount": "Сумма",
            "delivery_cost": "Стоимость доставки",
            "status_payment": "Оплата",
            "status_delivery": "Статус доставки",
            "comment": "Комментарий",
            "paid_at": "Дата оплаты",
            "delivered_at": "Дата доставки",
            "created_at": "Создан",
            "items": "Позиции",
            "delivery_info": "Доставка",
        }

        column_formatters = {
            "number": lambda m, a: Markup(f'<a href="/admin/order/edit/{m.id}" style="font-weight:600;color:var(--bs-primary)">{m.number}</a>'),
            "user": lambda m, a: m.user.display_name if m.user else "—",
            "total_amount": lambda m, a: Markup(f"<b>{float(m.total_amount):.0f} ₽</b>"),
            "status_delivery": lambda m, a: _status_select(m.id, "status_delivery", m.status_delivery, _DELIVERY_CHOICES),
            "status_payment": lambda m, a: _status_select(m.id, "status_payment", m.status_payment, _PAYMENT_CHOICES),
            "created_at": lambda m, a: m.created_at.strftime("%d.%m.%Y %H:%M") if m.created_at else "—",
        }

        form_columns = [
            "status_payment", "status_delivery", "delivery_cost",
            "comment", "paid_at", "delivered_at",
        ]
        form_choices = {
            "status_delivery": _DELIVERY_CHOICES,
            "status_payment": _PAYMENT_CHOICES,
        }
        form_overrides = {
            "status_delivery": __import__("wtforms").SelectField,
            "status_payment": __import__("wtforms").SelectField,
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

        column_list = [
            "display_name", "phone",
            "total_orders", "total_spent", "avg_check", "first_order_date",
            "created_at",
        ]
        column_searchable_list = ["username", "first_name", "phone"]
        column_sortable_list = ["id", "created_at"]
        column_default_sort = [("created_at", True)]

        column_labels = {
            "display_name": "Имя",
            "phone": "Телефон",
            "total_orders": "Заказов",
            "total_spent": "Потрачено",
            "avg_check": "Средний чек",
            "first_order_date": "Первый заказ",
            "created_at": "Зарегистрирован",
            "is_admin": "Администратор",
            "telegram_id": "Telegram ID",
            "first_name": "Имя",
            "last_name": "Фамилия",
            "username": "Username",
        }

        column_formatters = {
            "display_name": lambda m, a: m.display_name,
            "total_orders": lambda m, a: Markup(f"<b>{m.total_orders}</b>") if m.total_orders else "0",
            "total_spent": lambda m, a: f"{m.total_spent:.0f} ₽" if m.total_spent else "—",
            "avg_check": lambda m, a: f"{m.avg_check:.0f} ₽" if m.avg_check else "—",
            "first_order_date": lambda m, a: m.first_order_date.strftime("%d.%m.%Y") if m.first_order_date else "—",
            "created_at": lambda m, a: m.created_at.strftime("%d.%m.%Y") if m.created_at else "—",
        }

        form_columns = ["phone", "is_admin"]
        can_delete = False
        page_size = 50

    class NotificationTargetAdmin(ModelView, model=NotificationTarget):
        name = "↳ Уведомления"
        name_plural = "Уведомления (кому слать)"
        category = "CRM"

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

    class FaqItemAdmin(ModelView, model=FaqItem):
        name = "↳ FAQ"
        name_plural = "FAQ"
        category = "Настройки магазина"

        column_list = ["sort", "question", "is_active"]
        column_labels = {
            "sort": "Порядок",
            "question": "Вопрос",
            "answer": "Ответ",
            "is_active": "Активен",
        }
        column_sortable_list = ["sort"]
        form_excluded_columns = ["created_at", "updated_at"]
        page_size = 50

    class PickupPointAdmin(ModelView, model=PickupPoint):
        name = "↳ Самовывоз"
        name_plural = "Пункты самовывоза"
        category = "Настройки магазина"

        column_list = ["name", "address", "work_hours", "is_active"]
        column_labels = {
            "name": "Название",
            "address": "Адрес",
            "work_hours": "Часы работы",
            "is_active": "Активен",
        }
        form_excluded_columns = ["created_at", "updated_at"]
        page_size = 50

    # ===== КАТАЛОГ =====

    class CategoryAdmin(ModelView, model=Category):
        name = "↳ Категории"
        name_plural = "Категории"
        category = "Настройки магазина"

        column_list = ["sort_order", "name", "slug", "created_at"]
        column_searchable_list = ["name", "slug"]
        column_sortable_list = ["sort_order", "name"]
        column_default_sort = [("sort_order", False)]
        column_labels = {
            "sort_order": "Порядок",
            "name": "Название",
            "slug": "API тег",
            "created_at": "Создана",
        }
        form_excluded_columns = ["products", "created_at", "updated_at"]
        page_size = 50

    class ProductAdmin(ModelView, model=Product):
        name = "Товары"
        name_plural = "Товары"
        icon = "fa-solid fa-leaf"
        category = "Настройки магазина"

        column_list = ["sort_order", "name", "category", "base_price", "slug"]
        column_searchable_list = ["name", "slug"]
        column_sortable_list = ["sort_order", "base_price", "name"]
        column_default_sort = [("sort_order", False)]
        column_labels = {
            "sort_order": "Порядок",
            "name": "Название",
            "category": "Категория",
            "base_price": "Базовая цена",
            "slug": "API тег",
            "description": "Описание",
            "origin": "Происхождение",
            "tags": "Теги",
            "is_active": "Активен",
        }
        column_formatters = {
            "base_price": lambda m, a: f"{float(m.base_price):.0f} ₽",
        }
        form_columns = [
            "category", "name", "slug", "base_price",
            "description", "origin", "tags", "sort_order", "is_active",
        ]
        inline_models = [
            (ProductVariant, {"form_columns": ["weight_g", "price", "sku", "in_stock"]}),
            (ProductImage, {"form_columns": ["path", "is_main", "sort", "alt"]}),
        ]
        page_size = 50

    class BannerAdmin(ModelView, model=Banner):
        name = "↳ Баннеры"
        name_plural = "Баннеры"
        category = "Настройки магазина"

        column_list = ["sort", "title", "is_active", "link"]
        column_sortable_list = ["sort"]
        column_labels = {
            "sort": "Порядок",
            "title": "Заголовок",
            "subtitle": "Подзаголовок",
            "is_active": "Активен",
            "image_path": "Путь к картинке",
            "link": "Ссылка",
        }
        column_formatters = {
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

        column_list = ["username", "is_superuser", "created_at"]
        column_labels = {
            "username": "Логин",
            "is_superuser": "Суперадмин",
            "telegram_id": "Telegram ID",
            "created_at": "Создан",
        }
        column_formatters = {
            "is_superuser": lambda m, a: Markup("👑") if m.is_superuser else "",
            "created_at": lambda m, a: m.created_at.strftime("%d.%m.%Y") if m.created_at else "—",
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
            "started_at": lambda m, a: m.started_at.strftime("%d.%m.%Y %H:%M") if m.started_at else "—",
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
            "created_at": lambda m, a: m.created_at.strftime("%d.%m.%Y %H:%M") if m.created_at else "—",
        }
        can_create = False
        can_edit = False
        can_delete = False
        page_size = 50

    # ---------- Порядок регистрации ----------

    # Заказы
    admin.add_view(OrderAdmin)
    admin.add_view(OrderItemAdmin)
    admin.add_view(DeliveryInfoAdmin)
    # CRM
    admin.add_view(UserAdmin)
    admin.add_view(NotificationTargetAdmin)
    # Настройки магазина
    admin.add_view(ProductAdmin)
    admin.add_view(CategoryAdmin)
    admin.add_view(BannerAdmin)
    admin.add_view(FaqItemAdmin)
    admin.add_view(PickupPointAdmin)
    # Система
    admin.add_view(AdminUserAdmin)
    admin.add_view(YmlImportAdmin)
    admin.add_view(PaymentEventAdmin)
