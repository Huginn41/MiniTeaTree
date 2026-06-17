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


_ADMIN_CSS = ("""
<style>
@font-face { font-family:'Futura'; src:url('/static/fonts/FuturaLightC.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'Futura'; src:url('/static/fonts/FuturaBookC.otf')  format('opentype'); font-weight:400; }
@font-face { font-family:'Futura'; src:url('/static/fonts/FuturaDemiC.otf')  format('opentype'); font-weight:600; }

/* --- Шрифт --- */
body, .navbar, .nav-link, .card, .btn, input, select, textarea, table {
  font-family: 'Futura', 'Century Gothic', -apple-system, sans-serif !important;
}

/* --- Фон --- */
body { background: #f4f6fb !important; }
.page-wrapper { background: #f4f6fb !important; }

/* --- Сайдбар: светлый --- */
aside.navbar-vertical {
  background: #fff !important;
  border-right: 1px solid #e9ecef !important;
  box-shadow: 2px 0 12px rgba(0,0,0,.05) !important;
}
aside.navbar-vertical[data-bs-theme] { --tblr-navbar-color:#495057; }
aside.navbar-vertical .navbar-brand h3 {
  color: #212529 !important;
  font-weight: 700 !important;
  font-size: 16px !important;
}
aside.navbar-vertical .navbar-toggler { border-color: #dee2e6 !important; }
aside.navbar-vertical .navbar-toggler-icon { filter: invert(1) !important; }

/* --- Ссылки сайдбара --- */
aside.navbar-vertical .nav-link {
  color: #495057 !important;
  border-radius: 8px !important;
  margin: 1px 8px !important;
  transition: all .15s !important;
  font-size: 13.5px !important;
}
aside.navbar-vertical .nav-link:hover {
  background: #f0f4ff !important;
  color: #3d5afe !important;
}
aside.navbar-vertical .nav-link.active,
aside.navbar-vertical .nav-item.active > .nav-link {
  background: #3d5afe !important;
  color: #fff !important;
}
aside.navbar-vertical .nav-link.active .nav-link-icon,
aside.navbar-vertical .nav-item.active > .nav-link .nav-link-icon { color: #fff !important; }

/* Подпункты */
.navbar-nav .nav-item .nav-link:not([data-bs-toggle]) {
  padding-left: 2.5rem !important;
  font-size: 0.8rem !important;
  opacity: 0.85;
}
.navbar-nav .nav-item .nav-link:not([data-bs-toggle]):hover { opacity: 1; }

/* Кнопка logout */
aside .btn-secondary {
  background: #f0f4ff !important;
  border-color: #e0e7ff !important;
  color: #3d5afe !important;
  border-radius: 8px !important;
  font-size: 13px !important;
}
aside .btn-secondary:hover { background: #3d5afe !important; color: #fff !important; }

/* Стрелка раскрывающихся разделов */
[data-bs-toggle="collapse"].nav-link::after {
  content: "▾"; float: right; font-size: 12px;
  transition: transform .2s; margin-top: 3px;
}
[data-bs-toggle="collapse"].nav-link.collapsed::after { transform: rotate(-90deg); }

/* --- Заголовок страницы --- */
.page-header { background: transparent !important; padding-top: 20px !important; }
.page-title { font-size: 20px !important; font-weight: 700 !important; color: #212529 !important; }
.page-pretitle { color: #8c9aad !important; font-size: 11px !important; text-transform: uppercase !important; letter-spacing: .5px !important; }

/* --- Карточки --- */
.card {
  border-radius: 14px !important;
  border: none !important;
  box-shadow: 0 2px 10px rgba(0,0,0,.06) !important;
}
.card-header {
  background: #fff !important;
  border-bottom: 1px solid #f0f2f5 !important;
  font-weight: 600 !important;
  border-radius: 14px 14px 0 0 !important;
}
.card-footer { background: #fff !important; border-radius: 0 0 14px 14px !important; }

/* --- Таблицы --- */
.table th {
  font-size: 11.5px !important;
  color: #8c9aad !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: .4px !important;
  border-bottom: 1px solid #f0f2f5 !important;
}
.table td { font-size: 13px !important; border-color: #f5f6fa !important; }
.table-hover tbody tr:hover td { background: #f5f7ff !important; }

/* --- Кнопки --- */
.btn-primary { background: #3d5afe !important; border-color: #3d5afe !important; border-radius: 8px !important; }
.btn-primary:hover { background: #2a3eb1 !important; border-color: #2a3eb1 !important; }
.btn-secondary { border-radius: 8px !important; }
.btn-danger { border-radius: 8px !important; }
.btn-sm { font-size: 12px !important; }

/* --- Формы --- */
.form-control, .form-select {
  border-radius: 8px !important;
  border-color: #dee2e6 !important;
  font-size: 13.5px !important;
}
.form-control:focus, .form-select:focus {
  border-color: #3d5afe !important;
  box-shadow: 0 0 0 3px rgba(61,90,254,.12) !important;
}
.form-label { font-size: 13px !important; font-weight: 600 !important; color: #495057 !important; }

/* --- Бейджи --- */
.badge { border-radius: 6px !important; font-weight: 600 !important; }

/* --- Пагинация --- */
.pagination .page-link { border-radius: 8px !important; color: #3d5afe !important; border-color: #dee2e6 !important; }
.pagination .page-item.active .page-link { background: #3d5afe !important; border-color: #3d5afe !important; color: #fff !important; }
</style>
</head>""").encode("utf-8")

_ADMIN_JS = (r"""
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
  function applyFileUpload(inp){
    if(inp._fuDone) return;
    if(!inp.parentNode) return;
    var combined = (inp.id||'') + ' ' + (inp.name||'');
    if(combined.indexOf('path') === -1) return;
    inp._fuDone = true;

    var fi = document.createElement('input');
    fi.type = 'file'; fi.accept = 'image/*'; fi.style.display = 'none';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-sm btn-outline-secondary mt-1';
    btn.style.cssText = 'display:block;';
    btn.textContent = '📁 Загрузить фото';

    inp.insertAdjacentElement('afterend', fi);
    fi.insertAdjacentElement('afterend', btn);

    // Превью
    var preview = document.createElement('img');
    preview.style.cssText = 'display:none;width:120px;height:120px;object-fit:cover;border-radius:8px;margin-top:8px;border:2px solid #dee2e6;';
    btn.insertAdjacentElement('afterend', preview);
    if(inp.value){ preview.src = inp.value; preview.style.display = 'block'; }

    btn.addEventListener('click', function(){ fi.click(); });
    fi.addEventListener('change', function(){
      var file = fi.files[0]; if(!file) return;
      var localUrl = URL.createObjectURL(file);
      preview.src = localUrl; preview.style.display = 'block'; preview.style.opacity = '0.5';
      var fd = new FormData(); fd.append('file', file);
      btn.textContent = '⏳ Загрузка...'; btn.disabled = true;
      fetch('/admin-api/upload', {method:'POST', body:fd})
        .then(function(r){ return r.json(); })
        .then(function(d){
          inp.value = d.path;
          preview.src = d.path; preview.style.opacity = '1';
          URL.revokeObjectURL(localUrl);
          btn.textContent = '✅ ' + file.name;
          btn.disabled = false;
        })
        .catch(function(){ btn.textContent = '❌ Ошибка'; btn.disabled = false; preview.style.opacity = '1'; });
    });
  }

  function initFileUploads(){
    document.querySelectorAll('input[type="text"]').forEach(applyFileUpload);
  }

  // ---- 4. Блок управления фото товара (только на странице edit/create товара) ----
  function initProductImages(){
    var m = window.location.pathname.match(/\/admin\/product\/(edit|create)\/(\d+)/);
    if(!m) return;
    var productId = m[2];

    var container = document.createElement('div');
    container.style.cssText = 'margin-bottom:24px;padding:20px;background:#f8f9fa;border-radius:12px;';
    container.innerHTML = '<h4 style="margin:0 0 16px;font-size:16px;font-weight:700">📸 Фото товара</h4>'
      + '<div id="img-grid" style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:16px"></div>'
      + '<label class="btn btn-outline-primary" style="cursor:pointer">'
      +   '📁 Загрузить фото (можно несколько)'
      +   '<input type="file" accept="image/*" multiple style="display:none" id="img-upload-input">'
      + '</label>'
      + '<span id="img-upload-status" style="margin-left:12px;font-size:13px;color:#888"></span>';

    // Вставляем В НАЧАЛО формы, перед fieldset
    var fieldset = document.querySelector('form fieldset');
    if(fieldset) fieldset.parentNode.insertBefore(container, fieldset);

    function renderImages(imgs){
      var grid = document.getElementById('img-grid');
      grid.innerHTML = '';
      imgs.forEach(function(img){
        var card = document.createElement('div');
        card.style.cssText = 'position:relative;border-radius:8px;overflow:hidden;border:2px solid '+(img.is_main?'#3d5afe':'#dee2e6')+';';
        card.innerHTML = '<img src="'+img.path+'" style="width:100px;height:80px;object-fit:cover;display:block">'
          + '<div style="position:absolute;top:2px;right:2px;display:flex;gap:2px">'
          +   '<button type="button" title="Главное фото" onclick="setMain('+img.id+')" style="background:'+(img.is_main?'#3d5afe':'rgba(0,0,0,0.5)')+';border:none;border-radius:4px;padding:2px 5px;color:#fff;cursor:pointer;font-size:11px">⭐</button>'
          +   '<button type="button" title="Удалить" onclick="delImg('+img.id+')" style="background:rgba(200,0,0,0.75);border:none;border-radius:4px;padding:2px 5px;color:#fff;cursor:pointer;font-size:11px">✕</button>'
          + '</div>';
        grid.appendChild(card);
      });
      if(!imgs.length) grid.innerHTML = '<span style="color:#aaa;font-size:13px">Фото пока нет</span>';
    }

    function loadImages(){
      fetch('/admin-api/product/'+productId+'/images')
        .then(function(r){ return r.json(); })
        .then(renderImages);
    }

    window.delImg = function(id){
      fetch('/admin-api/product-image/'+id, {method:'DELETE'}).then(loadImages);
    };
    window.setMain = function(id){
      fetch('/admin-api/product-image/'+id+'/set-main', {method:'POST'}).then(loadImages);
    };

    document.getElementById('img-upload-input').addEventListener('change', function(){
      var files = Array.from(this.files); if(!files.length) return;
      var status = document.getElementById('img-upload-status');
      var grid = document.getElementById('img-grid');
      status.textContent = '⏳ Загрузка ' + files.length + ' фото...';
      var done = 0; var errors = 0;
      files.forEach(function(file){
        var fd = new FormData(); fd.append('file', file);
        var previewUrl = URL.createObjectURL(file);
        var previewEl = document.createElement('img');
        previewEl.src = previewUrl;
        previewEl.style.cssText = 'width:100px;height:100px;object-fit:cover;border-radius:8px;opacity:0.5;border:2px dashed #aaa;';
        grid.appendChild(previewEl);
        fetch('/admin-api/product/'+productId+'/images', {method:'POST', body:fd})
          .then(function(r){ return r.json(); })
          .then(function(){ done++; URL.revokeObjectURL(previewUrl); if(done+errors===files.length){ status.textContent = errors ? '⚠️ '+done+' загружено, '+errors+' ошибок' : '✅ Загружено '+done+' фото'; loadImages(); }})
          .catch(function(){ errors++; previewEl.remove(); if(done+errors===files.length){ status.textContent = '❌ Ошибок: '+errors; loadImages(); }});
      });
    });

    loadImages();
  }

  // ---- 5. Превью вариантов цен под полем базовой цены ----
  function initPricePreview(){
    var priceEl = document.querySelector('#base_price');
    if(!priceEl) return;

    var preview = document.createElement('div');
    preview.style.cssText = 'display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;';

    var weights = [25, 50, 75, 100];
    var cards = weights.map(function(w){
      var card = document.createElement('div');
      card.style.cssText = [
        'flex:1;min-width:70px;padding:8px 10px;border-radius:8px;',
        'background:#f0f4ff;border:1px solid #d0d9f0;text-align:center;',
        'pointer-events:none;user-select:none;'
      ].join('');
      card.innerHTML = '<div style="font-size:11px;color:#888;margin-bottom:2px">'+w+' г</div>'
                     + '<div class="pv" style="font-size:15px;font-weight:700;color:#3d5afe">—</div>';
      preview.appendChild(card);
      return card.querySelector('.pv');
    });

    function update(){
      var val = parseFloat(priceEl.value);
      weights.forEach(function(w, i){
        cards[i].textContent = isNaN(val) ? '—' : Math.round(val * w) + ' ₽';
      });
    }

    priceEl.addEventListener('input', update);
    update();

    priceEl.parentNode.appendChild(preview);
  }

  // ---- 5. Перевод интерфейса на русский ----
  var _RU = {
    // Кнопки / текст
    'Save':'Сохранить','Cancel':'Отмена','Delete':'Удалить',
    'Create':'Создать','Edit':'Редактировать','Search':'Поиск',
    'Reset':'Сбросить','Export':'Экспорт','Add':'Добавить',
    'Confirm':'Подтвердить','Submit':'Отправить','Go':'Перейти',
    'Back to list':'← К списку',
    'Yes, delete!':'Да, удалить!','No, cancel':'Нет, отмена',
    'Are you sure?':'Вы уверены?',
    'View':'Просмотр',
    'Details':'Подробности',
    'Actions':'Действия',
    'Select all':'Выбрать все',
    'Deselect all':'Снять выбор',
    'Delete selected':'Удалить выбранные',
    'items':'записей','of':'из',
    'per page':'на странице',
    'Previous':'Назад','Next':'Вперёд',
    'Loading...':'Загрузка...',
  };
  // Атрибуты title/placeholder/aria-label
  var _RU_ATTR = {
    'Edit':'Редактировать','Delete':'Удалить','View':'Просмотр',
    'Search':'Поиск...','Go to page':'Перейти к странице',
    'Select row':'Выбрать строку','Select all rows':'Выбрать все строки',
  };

  function _translateNode(el){
    // title / aria-label
    ['title','aria-label','placeholder'].forEach(function(attr){
      var v = el.getAttribute && el.getAttribute(attr);
      if(v && _RU_ATTR[v.trim()]) el.setAttribute(attr, _RU_ATTR[v.trim()]);
    });
    // Текстовые узлы внутри элемента (не трогаем дочерние теги)
    el.childNodes.forEach(function(n){
      if(n.nodeType === 3){
        var t = n.textContent.trim();
        if(_RU[t]) n.textContent = n.textContent.replace(t, _RU[t]);
      }
    });
  }

  function translateUI(){
    // Все элементы с текстом или атрибутами
    document.querySelectorAll(
      'button, a.btn, input[type="submit"], a[title], span, td, th, label, small, p.help-block, .modal-body, .modal-footer'
    ).forEach(_translateNode);

    // placeholder отдельно
    document.querySelectorAll('input[placeholder]').forEach(function(el){
      if(el.placeholder==='Search') el.placeholder='Поиск...';
    });
  }

  // Перехватываем динамически добавляемый контент (модалки, toast-ы)
  var _observer = new MutationObserver(function(mutations){
    mutations.forEach(function(m){
      m.addedNodes.forEach(function(n){
        if(n.nodeType===1){
          _translateNode(n);
          n.querySelectorAll && n.querySelectorAll('button,span,td,th,a,p,small,label').forEach(_translateNode);
          // Кнопки загрузки для динамически добавленных строк инлайн-форм
          n.querySelectorAll && n.querySelectorAll('input[type="text"]').forEach(applyFileUpload);
          if(n.tagName==='INPUT' && n.type==='text') applyFileUpload(n);
        }
      });
    });
  });
  _observer.observe(document.body, {childList:true, subtree:true});

  // ---- 6. Ссылка на дашборд в сайдбаре ----
  function addDashboardLink(){
    var nav = document.querySelector('.navbar-nav');
    if(!nav || document.querySelector('a[href="/admin/dashboard"]')) return;
    var li = document.createElement('li');
    li.className = 'nav-item';
    li.innerHTML = '<a class="nav-link" href="/admin/dashboard" style="font-weight:600;color:#3d5afe">'
      + '<i class="fa-solid fa-chart-line me-2"></i>Дашборд</a>';
    nav.prepend(li);
  }

  function init(){
    collapseInactive();
    addDashboardLink();
    initProductImages();
    initSlugAuto();
    initPricePreview();
    initFileUploads();
    translateUI();
  }

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', init);
  } else { init(); }
})();
</script>
</body>""").encode("utf-8")


class _AdminCollapseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in ("/admin", "/admin/") and request.session.get("admin_token") == "authenticated":
            return Response(status_code=302, headers={"location": "/admin/dashboard"})
        response = await call_next(request)
        ct = response.headers.get("content-type", "")
        if request.url.path.startswith("/admin") and "text/html" in ct:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            body = body.replace(b"</head>", _ADMIN_CSS)
            body = body.replace(b"</body>", _ADMIN_JS)
            headers = dict(response.headers)
            headers["content-length"] = str(len(body))
            return Response(content=body, status_code=response.status_code,
                            headers=headers, media_type="text/html")
        return response


# ---------- Регистрация ----------

def setup_admin(app: FastAPI, engine: Any) -> None:
    from app.admin.dashboard import setup_dashboard
    setup_dashboard(app)
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

    @app.get("/admin-api/product/{product_id}/images")
    async def admin_product_images(product_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from app.db import get_session_factory
        from app.models.product import ProductImage
        from sqlalchemy import select
        async with get_session_factory()() as session:
            res = await session.execute(
                select(ProductImage).where(ProductImage.product_id == product_id).order_by(ProductImage.sort)
            )
            imgs = res.scalars().all()
            return _JSONResponse([{"id": i.id, "path": i.path, "is_main": i.is_main, "alt": i.alt or "", "sort": i.sort} for i in imgs])

    @app.post("/admin-api/product/{product_id}/images")
    async def admin_product_image_upload(product_id: int, request: Request, file: UploadFile = _File(...)):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            ext = ".jpg"
        name = f"{_uuid.uuid4().hex}{ext}"
        with open(_UPLOADS_DIR / name, "wb") as f:
            shutil.copyfileobj(file.file, f)
        path = f"/static/uploads/{name}"
        from app.db import get_session_factory
        from app.models.product import ProductImage
        from sqlalchemy import select, func
        async with get_session_factory()() as session:
            count_res = await session.execute(
                select(func.count()).where(ProductImage.product_id == product_id)
            )
            count = count_res.scalar() or 0
            img = ProductImage(product_id=product_id, path=path, is_main=(count == 0), sort=count)
            session.add(img)
            await session.commit()
            await session.refresh(img)
            return _JSONResponse({"id": img.id, "path": img.path, "is_main": img.is_main})

    @app.delete("/admin-api/product-image/{image_id}")
    async def admin_delete_product_image(image_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from app.db import get_session_factory
        from app.models.product import ProductImage
        from sqlalchemy import select
        async with get_session_factory()() as session:
            res = await session.execute(select(ProductImage).where(ProductImage.id == image_id))
            img = res.scalar_one_or_none()
            if img:
                await session.delete(img)
                await session.commit()
        return _JSONResponse({"ok": True})

    @app.post("/admin-api/product-image/{image_id}/set-main")
    async def admin_set_main_image(image_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from app.db import get_session_factory
        from app.models.product import ProductImage
        from sqlalchemy import select
        async with get_session_factory()() as session:
            res = await session.execute(select(ProductImage).where(ProductImage.id == image_id))
            img = res.scalar_one_or_none()
            if not img:
                return _JSONResponse(status_code=404, content={"error": "Not found"})
            all_res = await session.execute(
                select(ProductImage).where(ProductImage.product_id == img.product_id)
            )
            for i in all_res.scalars().all():
                i.is_main = (i.id == image_id)
            await session.commit()
        return _JSONResponse({"ok": True})

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
            "base_price": "Цена за 1 г. (₽)",
            "slug": "API тег",
            "description": "Описание",
            "origin": "Происхождение",
            "tags": "Теги",
            "is_active": "Активен",
        }
        column_formatters = {
            "base_price": lambda m, a: f"{float(m.base_price):.2f} ₽/г",
        }
        form_columns = [
            "category", "name", "slug", "base_price",
            "description", "origin", "tags", "sort_order", "is_active",
        ]
        page_size = 50

        async def after_model_change(self, data, model, is_created, request):
            from app.db import get_session_factory
            from app.models.product import ProductVariant
            from sqlalchemy import select

            price_per_gram = float(model.base_price)
            async with get_session_factory()() as session:
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
                            product_id=model.id,
                            weight_g=weight,
                            price=price,
                            in_stock=True,
                        ))
                await session.commit()

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
