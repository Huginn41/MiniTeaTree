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
try:
    from sqladmin import Link as _AdminLink
    _HAS_LINK = True
except ImportError:
    _HAS_LINK = False
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

from datetime import timezone as _tz, timedelta as _td
from sqladmin.fields import SelectField as _AdminSelectField

_MSK = _tz(_td(hours=3))


def _fmt_dt(dt):
    """UTC datetime → московское время, формат ДД.ММ.ГГГГ ЧЧ:ММ."""
    if dt is None:
        return "—"
    return dt.replace(tzinfo=_tz.utc).astimezone(_MSK).strftime("%d.%m.%Y %H:%M")


# ---------- Варианты статусов ----------

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


def _status_select(order_id: int, field: str, current: str, choices: list) -> Markup:
    options = "".join(
        f'<option value="{v}"{"  selected" if v == current else ""}>{label}</option>'
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
                request.session["admin_username"] = username
                return True
            return False

        if not _bcrypt.checkpw(password.encode(), admin.password_hash.encode()):
            return False

        request.session["admin_token"] = "authenticated"
        request.session["admin_username"] = admin.username
        request.session["admin_readonly"] = not admin.is_superuser
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True


_ADMIN_CSS = ("""
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<style>
/* ── Шрифт Futura ── */
@font-face { font-family:'Futura'; src:url('/static/fonts/FuturaLightC.otf') format('opentype'); font-weight:300; font-display:swap; }
@font-face { font-family:'Futura'; src:url('/static/fonts/FuturaBookC.otf')  format('opentype'); font-weight:400; font-display:swap; }
@font-face { font-family:'Futura'; src:url('/static/fonts/FuturaDemiC.otf')  format('opentype'); font-weight:600; font-display:swap; }
*, body { font-family:'Futura','Century Gothic',-apple-system,sans-serif !important; }
.fa-solid,.fa-regular,.fa-brands,.fas,.far,.fab { font-family:"Font Awesome 6 Free" !important; }
.fa-brands,.fab { font-family:"Font Awesome 6 Brands" !important; }

/* ── Фон ── */
body { background:#f4f6fb !important; }
.page-wrapper { background:#f4f6fb !important; }

/* ── Скрыть дефолтный сайдбар Tabler ── */
.wrapper > aside.navbar-vertical { display:none !important; }
.wrapper { display:block !important; }
.page-wrapper { margin-left:0 !important; }

/* ── Топ-навбар (общие стили для всех страниц) ── */
.ct-topnav {
  background:#fff; border-bottom:1px solid #e9ecef;
  box-shadow:0 1px 8px rgba(0,0,0,.06); height:56px;
  display:flex; align-items:center; padding:0 24px; gap:4px;
  position:sticky; top:0; z-index:1000;
}
.ct-brand {
  font-weight:800; font-size:16px; color:#212529;
  text-decoration:none; margin-right:16px; white-space:nowrap;
  letter-spacing:-.3px;
}
.ct-brand:hover { color:#3d5afe; text-decoration:none; }
.ct-nav-item { position:relative; }
.ct-nav-link {
  display:flex; align-items:center; gap:6px;
  padding:0 12px; height:56px; font-size:13.5px; font-weight:500;
  color:#495057; text-decoration:none;
  border-bottom:2px solid transparent; transition:all .15s;
  white-space:nowrap; cursor:pointer; background:none; border-top:none; border-left:none; border-right:none;
}
.ct-nav-link:hover { color:#3d5afe; border-bottom-color:#3d5afe; text-decoration:none; }
.ct-nav-link.active { color:#3d5afe; border-bottom-color:#3d5afe; font-weight:600; }
.ct-nav-link i { font-size:14px; color:#1a6b3c; }
.ct-sep { width:1px; height:20px; background:#dee2e6; margin:0 8px; flex-shrink:0; }
.ct-logout { margin-left:auto; display:flex; align-items:center; gap:8px; }
.ct-logout a {
  font-size:13px; color:#6c757d; text-decoration:none;
  padding:6px 12px; border-radius:8px; border:1px solid #dee2e6; transition:all .15s;
}
.ct-logout a:hover { color:#3d5afe; border-color:#3d5afe; }

/* Дропдаун меню */
.ct-dropdown { position:relative; }
.ct-dropdown-menu {
  display:none; position:absolute; top:54px; left:0;
  background:#fff; border:1px solid #e9ecef; border-radius:10px;
  box-shadow:0 8px 24px rgba(0,0,0,.1); min-width:200px;
  padding:6px 0; z-index:1001;
}
.ct-dropdown:hover .ct-dropdown-menu { display:block; }
.ct-dropdown-item {
  display:block; padding:9px 16px; font-size:13px;
  color:#495057; text-decoration:none; transition:all .1s;
}
.ct-dropdown-item:hover { background:#f0f4ff; color:#3d5afe; text-decoration:none; }
.ct-dropdown-item.active { color:#3d5afe; font-weight:600; background:#f0f4ff; }
.ct-dropdown-arrow { font-size:10px; opacity:.5; margin-left:2px; }

/* ── Заголовок страницы ── */
.page-header { background:transparent !important; padding-top:20px !important; }
.page-title { font-size:20px !important; font-weight:700 !important; color:#212529 !important; }
.page-pretitle { color:#8c9aad !important; font-size:11px !important; text-transform:uppercase !important; letter-spacing:.5px !important; }

/* ── Карточки ── */
.card { border-radius:14px !important; border:none !important; box-shadow:0 2px 10px rgba(0,0,0,.06) !important; }
.card-header { background:#fff !important; border-bottom:1px solid #f0f2f5 !important; font-weight:600 !important; border-radius:14px 14px 0 0 !important; }
.card-footer { background:#fff !important; border-radius:0 0 14px 14px !important; }

/* ── Таблицы ── */
.table th { font-size:11.5px !important; color:#8c9aad !important; font-weight:600 !important; text-transform:uppercase !important; letter-spacing:.4px !important; border-bottom:1px solid #f0f2f5 !important; }
.table td { font-size:13px !important; border-color:#f5f6fa !important; }
.table-hover tbody tr:hover td { background:#f5f7ff !important; }

/* ── Кнопки ── */
.btn-primary { background:#3d5afe !important; border-color:#3d5afe !important; border-radius:8px !important; }
.btn-primary:hover { background:#2a3eb1 !important; border-color:#2a3eb1 !important; }
.btn { border-radius:8px !important; font-size:13px !important; }

/* ── Формы ── */
.form-control,.form-select { border-radius:8px !important; border-color:#dee2e6 !important; font-size:13.5px !important; }
.form-control:focus,.form-select:focus { border-color:#3d5afe !important; box-shadow:0 0 0 3px rgba(61,90,254,.12) !important; }
.form-label { font-size:13px !important; font-weight:600 !important; color:#495057 !important; }

/* ── Пагинация / бейджи ── */
.pagination .page-link { border-radius:8px !important; color:#3d5afe !important; }
.pagination .page-item.active .page-link { background:#3d5afe !important; border-color:#3d5afe !important; color:#fff !important; }
.badge { border-radius:6px !important; font-weight:600 !important; }
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

    // Подсказка по размеру
    var hint = document.createElement('div');
    hint.style.cssText = 'font-size:11px;color:#8c9aad;margin-top:5px;line-height:1.5;';
    var _p = window.location.pathname;
    if(_p.indexOf('/banner/') !== -1){
      hint.innerHTML = '&#x1F4D0; Рекомендуется <b>1200×500 px</b> (горизонтальный баннер) · JPG / PNG / WebP';
    } else if(_p.indexOf('/category/') !== -1){
      hint.innerHTML = '&#x1F4D0; Рекомендуется <b>600×400 px</b> (обложка категории) · JPG / PNG / WebP';
    } else {
      hint.innerHTML = '&#x1F4D0; JPG / PNG / WebP · до 5 МБ';
    }
    preview.insertAdjacentElement('afterend', hint);

    if(inp.value){ preview.src = inp.value; preview.style.display = 'block'; }

    btn.addEventListener('click', function(){ fi.click(); });
    fi.addEventListener('change', function(){
      var file = fi.files[0]; if(!file) return;
      var localUrl = URL.createObjectURL(file);
      preview.src = localUrl; preview.style.display = 'block'; preview.style.opacity = '0.5';
      var fd = new FormData(); fd.append('file', file);
      btn.textContent = '⏳ Загрузка...'; btn.disabled = true;
      fetch('/admin-api/upload', {method:'POST', body:fd})
        .then(function(r){
          return r.text().then(function(t){
            var d; try { d = JSON.parse(t); } catch(x) { d = {}; }
            if(!r.ok) throw new Error(d.error || ('Ошибка ' + r.status));
            if(!d.path) throw new Error('Нет пути в ответе');
            return d;
          });
        })
        .then(function(d){
          inp.value = d.path;
          preview.src = d.path; preview.style.opacity = '1';
          URL.revokeObjectURL(localUrl);
          btn.textContent = '✅ ' + file.name;
          btn.disabled = false;
        })
        .catch(function(err){
          btn.textContent = '❌ ' + (err.message || 'Ошибка');
          btn.disabled = false; preview.style.opacity = '1';
        });
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
      + '<span id="img-upload-status" style="margin-left:12px;font-size:13px;color:#888"></span>'
      + '<div style="font-size:11px;color:#8c9aad;margin-top:6px;line-height:1.5;">&#x1F4D0; Рекомендуется <b>800×800 px</b> (квадрат) &nbsp;·&nbsp; JPG / PNG / WebP &nbsp;·&nbsp; до 5 МБ на фото</div>';

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

  // ---- 6. Кнопка «Импорт» рядом с «Экспорт» в списке товаров ----
  function initProductImportBtn(){
    if(!/^\/admin\/product\/list/.test(window.location.pathname)) return;

    if(!document.getElementById('ct-import-modal')){
      var m = document.createElement('div');
      m.id = 'ct-import-modal';
      m.className = 'modal fade';
      m.setAttribute('tabindex','-1');
      m.innerHTML =
        '<div class="modal-dialog modal-lg">'
        + '<div class="modal-content" style="border-radius:14px">'
        + '<div class="modal-header" style="border-bottom:1px solid #f0f2f5">'
        +   '<h5 class="modal-title" style="font-weight:700"><i class="fa-solid fa-file-import me-2" style="color:#3d5afe"></i>Импорт товаров</h5>'
        +   '<button type="button" class="btn-close" data-bs-dismiss="modal"></button>'
        + '</div>'
        + '<div class="modal-body" style="padding:24px">'
        +   '<div style="margin-bottom:20px;padding:20px;background:#f8f9fa;border-radius:10px">'
        +     '<h6 style="font-size:14px;font-weight:700;margin-bottom:4px"><i class="fa-solid fa-rss me-1" style="color:#3d5afe"></i>Импорт из YML-фида</h6>'
        +     '<p style="font-size:12px;color:#6c757d;margin-bottom:12px">Формат Яндекс.Маркет. Товары группируются по group_id, изображения скачиваются автоматически.</p>'
        +     '<div style="display:flex;gap:10px">'
        +       '<input type="text" id="ct-yml-url" class="form-control" placeholder="https://example.com/feed.yml" style="flex:1">'
        +       '<button type="button" class="btn btn-primary" onclick="ctStartYmlImport()"><i class="fa-solid fa-play me-1"></i>Запустить</button>'
        +     '</div>'
        +     '<div id="ct-yml-status" style="display:none;margin-top:10px;font-size:13px;color:#212529"></div>'
        +     '<pre id="ct-yml-log" style="display:none;margin-top:10px;background:#f8f9fa;border:1px solid #e9ecef;border-radius:8px;padding:12px;font-size:11px;max-height:180px;overflow-y:auto;white-space:pre-wrap;color:#212529"></pre>'
        +   '</div>'
        +   '<div style="padding:20px;background:#f8f9fa;border-radius:10px">'
        +     '<h6 style="font-size:14px;font-weight:700;margin-bottom:4px"><i class="fa-solid fa-file-excel me-1" style="color:#1a6b3c"></i>Импорт из Excel</h6>'
        +     '<p style="font-size:12px;color:#6c757d;margin-bottom:12px">Загрузите файл .xlsx по шаблону. URL фотографий — через запятую в последней колонке.</p>'
        +     '<div style="margin-bottom:12px">'
        +       '<a href="/admin-api/import/excel/template" download="import_template.xlsx" class="btn btn-sm btn-outline-primary"><i class="fa-solid fa-download me-1"></i>Скачать шаблон</a>'
        +     '</div>'
        +     '<div style="display:flex;gap:10px">'
        +       '<input type="file" id="ct-excel-file" class="form-control" accept=".xlsx" style="flex:1">'
        +       '<button type="button" class="btn btn-primary" onclick="ctStartExcelImport()"><i class="fa-solid fa-upload me-1"></i>Загрузить</button>'
        +     '</div>'
        +     '<div id="ct-excel-status" style="display:none;margin-top:10px;font-size:13px;color:#212529"></div>'
        +     '<pre id="ct-excel-log" style="display:none;margin-top:10px;background:#f8f9fa;border:1px solid #e9ecef;border-radius:8px;padding:12px;font-size:11px;max-height:180px;overflow-y:auto;white-space:pre-wrap;color:#212529"></pre>'
        +   '</div>'
        + '</div>'
        + '</div></div>';
      document.body.appendChild(m);
    }

    // Найти кнопку Export/Экспорт — ищем по href с "export" или по тексту
    var exportBtn = document.querySelector('a[href*="export"]');
    if(!exportBtn){
      document.querySelectorAll('a.btn, button.btn').forEach(function(el){
        var t = el.textContent.replace(/\s+/g,'');
        if(t === 'Export' || t === 'Экспорт') exportBtn = el;
      });
    }

    // Найти обёртку (div.ms-3) чтобы вставить рядом, а не внутрь
    var exportWrap = exportBtn ? (exportBtn.closest('.ms-3') || exportBtn) : null;

    // Кнопка «Импорт» — открывает модал через data-атрибуты Bootstrap
    var wrap = document.createElement('div');
    wrap.className = 'ms-3 d-inline-block';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn btn-outline-primary';
    btn.setAttribute('data-bs-toggle', 'modal');
    btn.setAttribute('data-bs-target', '#ct-import-modal');
    btn.innerHTML = '<i class="fa-solid fa-file-import me-1"></i>Импорт';
    btn.addEventListener('click', function(){
      ['yml','excel'].forEach(function(p){
        var s = document.getElementById('ct-'+p+'-status');
        var l = document.getElementById('ct-'+p+'-log');
        if(s){ s.style.display='none'; s.innerHTML=''; }
        if(l){ l.style.display='none'; l.textContent=''; }
      });
    });
    wrap.appendChild(btn);

    if(exportWrap){
      exportWrap.insertAdjacentElement('afterend', wrap);
    } else {
      // fallback: добавить в .ms-auto заголовка карточки
      var bar = document.querySelector('.card-header .ms-auto');
      if(bar) bar.insertBefore(wrap, bar.firstChild);
    }
  }

  window.ctShowImportStatus = function(prefix, status, data){
    var el = document.getElementById('ct-'+prefix+'-status');
    var log = document.getElementById('ct-'+prefix+'-log');
    if(!el) return;
    el.style.display = 'block';
    if(status === 'running'){
      el.innerHTML = '<span style="color:#e65100"><i class="fa-solid fa-spinner fa-spin me-1"></i>Импорт запущен...</span>';
    } else if(status === 'success'){
      el.innerHTML = '<span style="color:#2e7d32"><i class="fa-solid fa-check-circle me-1"></i>Готово: +'
        +(data.products_added||0)+' товаров, ~'+(data.products_updated||0)+' обновлено, '
        +(data.images_downloaded||0)+' фото</span>';
    } else {
      el.innerHTML = '<span style="color:#c62828"><i class="fa-solid fa-times-circle me-1"></i>Ошибка</span>';
    }
    if(log && data && (data.log || data.error)){
      log.style.display = 'block';
      log.textContent = (data.error ? 'ОШИБКА: '+data.error+'\n\n' : '') + (data.log||'');
    }
  };

  window.ctPollStatus = function(prefix, importId){
    var iv = setInterval(function(){
      fetch('/admin-api/import/'+importId+'/status',{credentials:'include'})
        .then(function(r){ return r.json(); })
        .then(function(d){
          if(d.status !== 'running'){ clearInterval(iv); window.ctShowImportStatus(prefix,d.status,d); }
        });
    },1500);
  };

  window.ctStartYmlImport = function(){
    var url = (document.getElementById('ct-yml-url')||{}).value;
    if(!url || !url.trim()){ alert('Введите URL фида'); return; }
    window.ctShowImportStatus('yml','running',{});
    fetch('/admin-api/import/yml',{
      method:'POST',credentials:'include',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({url:url.trim()}),
    }).then(function(r){ return r.json(); }).then(function(d){
      if(d.import_id) window.ctPollStatus('yml',d.import_id);
      else window.ctShowImportStatus('yml','failed',{error:JSON.stringify(d)});
    }).catch(function(e){ window.ctShowImportStatus('yml','failed',{error:String(e)}); });
  };

  window.ctStartExcelImport = function(){
    var inp = document.getElementById('ct-excel-file');
    if(!inp || !inp.files[0]){ alert('Выберите файл'); return; }
    window.ctShowImportStatus('excel','running',{});
    var fd = new FormData(); fd.append('file',inp.files[0]);
    fetch('/admin-api/import/excel',{method:'POST',credentials:'include',body:fd})
      .then(function(r){ return r.json(); }).then(function(d){
        if(d.import_id) window.ctPollStatus('excel',d.import_id);
        else window.ctShowImportStatus('excel','failed',{error:JSON.stringify(d)});
      }).catch(function(e){ window.ctShowImportStatus('excel','failed',{error:String(e)}); });
  };

  // ---- 7. Drag-and-drop сортировка категорий ----
  function initCategoryDnD(){
    if(!/^\/admin\/category\/list/.test(window.location.pathname)) return;

    var tbody = document.querySelector('table tbody');
    if(!tbody) return;

    // Добавить drag-handle в первую ячейку каждой строки
    Array.from(tbody.querySelectorAll('tr')).forEach(function(tr){
      tr.setAttribute('draggable','true');
      var firstTd = tr.querySelector('td');
      if(firstTd){
        var handle = document.createElement('span');
        handle.innerHTML = '⠿';
        handle.title = 'Перетащить';
        handle.style.cssText = 'cursor:grab;font-size:18px;color:#aaa;margin-right:8px;user-select:none;display:inline-block';
        firstTd.insertBefore(handle, firstTd.firstChild);
      }
    });

    var dragging = null;

    tbody.addEventListener('dragstart', function(e){
      dragging = e.target.closest('tr');
      if(!dragging) return;
      dragging.style.opacity = '0.4';
      e.dataTransfer.effectAllowed = 'move';
    });

    tbody.addEventListener('dragend', function(){
      if(dragging) dragging.style.opacity = '';
      tbody.querySelectorAll('tr').forEach(function(tr){ tr.style.borderTop = ''; });
      dragging = null;
    });

    tbody.addEventListener('dragover', function(e){
      e.preventDefault();
      var target = e.target.closest('tr');
      if(!target || target === dragging) return;
      tbody.querySelectorAll('tr').forEach(function(tr){ tr.style.borderTop = ''; });
      target.style.borderTop = '2px solid #3d5afe';
    });

    tbody.addEventListener('drop', function(e){
      e.preventDefault();
      var target = e.target.closest('tr');
      if(!target || target === dragging || !dragging) return;
      tbody.querySelectorAll('tr').forEach(function(tr){ tr.style.borderTop = ''; });
      tbody.insertBefore(dragging, target);
      dragging.style.opacity = '';

      // Собрать ID в новом порядке
      var ids = Array.from(tbody.querySelectorAll('tr')).map(function(tr){
        var cb = tr.querySelector('input[type="hidden"]');
        return cb ? parseInt(cb.value) : null;
      }).filter(Boolean);

      // Сохранить порядок
      var btn = document.getElementById('ct-cat-save-order');
      if(btn){ btn.style.display = 'inline-flex'; btn.dataset.ids = JSON.stringify(ids); }
    });

    // Кнопка «Сохранить порядок»
    var header = document.querySelector('.card-header');
    if(header){
      var saveBtn = document.createElement('button');
      saveBtn.id = 'ct-cat-save-order';
      saveBtn.type = 'button';
      saveBtn.className = 'btn btn-success btn-sm ms-2';
      saveBtn.style.cssText = 'display:none;align-items:center;gap:6px';
      saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> Сохранить порядок';
      saveBtn.addEventListener('click', function(){
        var ids = JSON.parse(saveBtn.dataset.ids || '[]');
        if(!ids.length) return;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Сохраняю...';
        fetch('/admin-api/categories/reorder',{
          method:'POST', credentials:'include',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({ids: ids}),
        }).then(function(r){ return r.json(); }).then(function(d){
          if(d.ok){
            saveBtn.innerHTML = '<i class="fa-solid fa-check"></i> Сохранено!';
            setTimeout(function(){ saveBtn.style.display='none'; saveBtn.disabled=false; saveBtn.innerHTML='<i class="fa-solid fa-check"></i> Сохранить порядок'; }, 1500);
          } else {
            saveBtn.innerHTML = '❌ Ошибка'; saveBtn.disabled = false;
          }
        });
      });
      header.querySelector('.ms-auto').prepend(saveBtn);
    }
  }

  function init(){
    collapseInactive();
    initProductImages();
    initSlugAuto();
    initPricePreview();
    initFileUploads();
    translateUI();
    initProductImportBtn();
    initCategoryDnD();
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

        # Read-only: блокируем создание/редактирование/удаление
        if (
            request.session.get("admin_readonly")
            and request.url.path.startswith("/admin")
            and request.method in ("POST", "PUT", "DELETE", "PATCH")
            and not request.url.path.startswith("/admin/login")
        ):
            return Response(
                content="<h2>Доступ только для просмотра</h2><a href='/admin/dashboard'>← Назад</a>",
                status_code=403,
                media_type="text/html",
            )
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

    from pathlib import Path as _Path
    settings = get_settings()
    authentication_backend = AdminAuth(secret_key=settings.jwt_secret.get_secret_value())
    _templates_dir = str(_Path(__file__).parent / "templates")
    admin = Admin(
        app=app,
        engine=engine,
        authentication_backend=authentication_backend,
        title="Чайное Дерево",
        base_url="/admin",
        templates_dir=_templates_dir,
    )

    # ===== ЗАКАЗЫ =====

    # Endpoint для смены статуса прямо из списка
    from fastapi.responses import JSONResponse as _JSONResponse

    _UPLOADS_DIR = Path(__file__).parent.parent.parent / "static" / "media" / "uploads"
    _MAX_IMAGE_PX = 1600

    def _to_webp(data: bytes, dest: Path, max_px: int = 1600) -> None:
        from PIL import Image, UnidentifiedImageError
        import io as _bio
        try:
            img = Image.open(_bio.BytesIO(data))
            img.load()  # форсируем загрузку — ловим битые файлы здесь
        except (UnidentifiedImageError, Exception) as exc:
            raise ValueError(f"Не удалось открыть изображение: {exc}") from exc

        # Приводим к RGB через alpha_composite — работает с любым режимом PNG
        if img.mode != "RGB":
            rgba = img.convert("RGBA")
            bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
            img = Image.alpha_composite(bg, rgba).convert("RGB")

        w, h = img.size
        if max(w, h) > max_px:
            r = max_px / max(w, h)
            img = img.resize((int(w * r), int(h * r)), Image.LANCZOS)
        img.save(dest, "WEBP", quality=85, method=4)

    _UPLOAD_MAX_BYTES = 15 * 1024 * 1024  # 15 МБ — совпадает с nginx client_max_body_size

    @app.post("/admin-api/upload")
    async def admin_upload(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        try:
            form = await request.form(max_part_size=_UPLOAD_MAX_BYTES)
        except Exception:
            return _JSONResponse(status_code=413, content={"error": "Файл слишком большой (макс. 15 МБ)"})
        file = form.get("file")
        if file is None:
            return _JSONResponse(status_code=400, content={"error": "Нет файла"})
        _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        name = f"{_uuid.uuid4().hex}.webp"
        try:
            _to_webp(await file.read(), _UPLOADS_DIR / name)
        except ValueError as exc:
            return _JSONResponse(status_code=422, content={"error": str(exc)})
        except Exception as exc:
            import logging as _log
            _log.getLogger(__name__).exception("Upload error: %s", exc)
            return _JSONResponse(status_code=500, content={"error": "Ошибка обработки изображения"})
        return _JSONResponse({"path": f"/static/media/uploads/{name}"})

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
    async def admin_product_image_upload(product_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        try:
            form = await request.form(max_part_size=_UPLOAD_MAX_BYTES)
        except Exception:
            return _JSONResponse(status_code=413, content={"error": "Файл слишком большой (макс. 15 МБ)"})
        file = form.get("file")
        if file is None:
            return _JSONResponse(status_code=400, content={"error": "Нет файла"})
        _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        name = f"{_uuid.uuid4().hex}.webp"
        try:
            _to_webp(await file.read(), _UPLOADS_DIR / name)
        except Exception as exc:
            import logging as _log
            _log.getLogger(__name__).exception("Product image upload error: %s", exc)
            return _JSONResponse(status_code=422, content={"error": "Ошибка обработки изображения"})
        path = f"/static/media/uploads/{name}"
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
                _delete_upload_file(img.path)
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
        if field != "status":
            return _JSONResponse(status_code=400, content={"error": "Invalid field"})
        from app.models.enums import ORDER_STATUS_VALUES
        if value not in ORDER_STATUS_VALUES:
            return _JSONResponse(status_code=400, content={"error": "Invalid status value"})
        from datetime import UTC, datetime as _dt
        from app.db import get_session_factory
        from sqlalchemy.orm import selectinload as _sil
        user_telegram_id = None
        async with get_session_factory()() as session:
            result = await session.execute(
                select(Order).options(_sil(Order.user)).where(Order.id == order_id)
            )
            order = result.scalar_one_or_none()
            if not order:
                return _JSONResponse(status_code=404, content={"error": "Not found"})
            old_status = order.status
            order.status = value
            if value == "delivered" and not order.delivered_at:
                order.delivered_at = _dt.now(UTC)
            if value == "in_delivery" and not order.paid_at:
                order.paid_at = _dt.now(UTC)
            if order.user:
                user_telegram_id = order.user.telegram_id
            order_number = order.number
            await session.commit()
        # Уведомляем клиента и обновляем карточки у менеджеров
        if old_status != value:
            try:
                import asyncio as _aio
                if user_telegram_id:
                    from app.bot.status_notify import notify_status_changed as _notify
                    _aio.create_task(_notify(
                        Order(id=order_id, number=order_number, status=value),
                        value,
                        user_telegram_id,
                    ))
                from app.bot.notify import update_order_notifications as _upd
                _aio.create_task(_upd(order_id))
            except Exception:
                pass
        return _JSONResponse({"ok": True})

    # ===== CRM ЗАКАЗА =====

    @app.get("/crm/order/{order_id}", include_in_schema=False)
    async def admin_crm_order(order_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            from starlette.responses import RedirectResponse
            return RedirectResponse("/admin/login")
        from app.db import get_session_factory
        from sqlalchemy.orm import selectinload
        async with get_session_factory()() as session:
            result = await session.execute(
                select(Order)
                .options(
                    selectinload(Order.items),
                    selectinload(Order.delivery_info),
                    selectinload(Order.user),
                )
                .where(Order.id == order_id)
            )
            order = result.scalar_one_or_none()
        if not order:
            return _JSONResponse(status_code=404, content={"error": "Not found"})
        from fastapi.responses import HTMLResponse as _HTMLResponse
        from app.admin.crm_order import render_crm_order
        admin_username = request.session.get("admin_username", "")
        html = render_crm_order(order, admin_username=admin_username)
        return _HTMLResponse(html)

    @app.get("/admin/crm-customer/{user_id}", include_in_schema=False)
    async def admin_crm_customer(user_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            from starlette.responses import RedirectResponse
            return RedirectResponse("/admin/login")
        from app.db import get_session_factory
        from sqlalchemy.orm import selectinload
        from app.models.user import User as _User
        from app.models.order import Order as _Order, OrderItem as _OrderItem
        from app.models.bonus import BonusTransaction as _BonusTx
        async with get_session_factory()() as session:
            result = await session.execute(
                select(_User)
                .options(
                    selectinload(_User.orders).selectinload(_Order.items),
                    selectinload(_User.bonus_transactions),
                )
                .where(_User.id == user_id)
            )
            user = result.scalar_one_or_none()
        if not user:
            return _JSONResponse(status_code=404, content={"error": "Not found"})
        from fastapi.responses import HTMLResponse as _HTMLResponse
        from app.admin.crm_customer import render_crm_customer
        admin_username = request.session.get("admin_username", "")
        html = render_crm_customer(user, admin_username=admin_username)
        return _HTMLResponse(html)

    @app.patch("/admin-api/customer/{user_id}", include_in_schema=False)
    async def admin_customer_patch(user_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        if request.session.get("admin_readonly"):
            return _JSONResponse(status_code=403, content={"error": "Readonly"})
        data = await request.json()
        from app.db import get_session_factory
        from app.models.user import User as _User
        async with get_session_factory()() as session:
            result = await session.execute(select(_User).where(_User.id == user_id))
            user = result.scalar_one_or_none()
            if not user:
                return _JSONResponse(status_code=404, content={"error": "Not found"})
            if "segment" in data:
                user.segment = data["segment"] or None
            if "notes" in data:
                user.notes = data["notes"] or None
            await session.commit()
        return _JSONResponse({"ok": True})

    # ── Бонусная система ────────────────────────────────────────────────────────

    @app.get("/admin/bonus-settings", include_in_schema=False)
    async def admin_bonus_settings_page(request: Request):
        if request.session.get("admin_token") != "authenticated":
            from starlette.responses import RedirectResponse
            return RedirectResponse("/admin/login")
        from app.db import get_session_factory
        from app.models.bonus import BonusTier as _BonusTier, ShopSettings as _ShopSettings
        from sqlalchemy import select as _sel
        async with get_session_factory()() as session:
            tiers_res = await session.execute(_sel(_BonusTier).order_by(_BonusTier.min_amount))
            tiers = tiers_res.scalars().all()
            settings_res = await session.execute(_sel(_ShopSettings).where(_ShopSettings.id == 1))
            settings = settings_res.scalar_one_or_none()
            max_pct = settings.bonus_max_payment_pct if settings else 50
        from fastapi.responses import HTMLResponse as _HTMLResponse
        from app.admin.bonus_settings import render_bonus_settings
        admin_username = request.session.get("admin_username", "")
        return _HTMLResponse(render_bonus_settings(tiers, max_pct, admin_username=admin_username))

    @app.get("/admin-api/bonus/settings", include_in_schema=False)
    async def admin_bonus_settings_get(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from app.db import get_session_factory
        from app.models.bonus import ShopSettings as _ShopSettings
        from sqlalchemy import select as _sel
        async with get_session_factory()() as session:
            res = await session.execute(_sel(_ShopSettings).where(_ShopSettings.id == 1))
            s = res.scalar_one_or_none()
        return _JSONResponse({"bonus_max_payment_pct": s.bonus_max_payment_pct if s else 50})

    @app.patch("/admin-api/bonus/settings", include_in_schema=False)
    async def admin_bonus_settings_patch(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        data = await request.json()
        pct = int(data.get("bonus_max_payment_pct", 50))
        pct = max(0, min(99, pct))
        from app.db import get_session_factory
        from app.models.bonus import ShopSettings as _ShopSettings
        from sqlalchemy import select as _sel
        async with get_session_factory()() as session:
            res = await session.execute(_sel(_ShopSettings).where(_ShopSettings.id == 1))
            s = res.scalar_one_or_none()
            if s:
                s.bonus_max_payment_pct = pct
            else:
                session.add(_ShopSettings(id=1, bonus_max_payment_pct=pct))
            await session.commit()
        return _JSONResponse({"ok": True, "bonus_max_payment_pct": pct})

    @app.put("/admin-api/bonus/tiers", include_in_schema=False)
    async def admin_bonus_tiers_put(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        data = await request.json()
        from decimal import Decimal as _Dec
        from app.db import get_session_factory
        from app.models.bonus import BonusTier as _BonusTier
        from sqlalchemy import select as _sel, delete as _del
        async with get_session_factory()() as session:
            await session.execute(_del(_BonusTier))
            for item in data:
                session.add(_BonusTier(
                    min_amount=_Dec(str(item["min_amount"])),
                    cashback_pct=_Dec(str(item["cashback_pct"])),
                ))
            await session.commit()
            res = await session.execute(_sel(_BonusTier).order_by(_BonusTier.min_amount))
            tiers = res.scalars().all()
        return _JSONResponse({"tiers": [
            {"id": t.id, "min_amount": float(t.min_amount), "cashback_pct": float(t.cashback_pct)}
            for t in tiers
        ]})

    @app.post("/admin-api/customer/{user_id}/bonus", include_in_schema=False)
    async def admin_customer_bonus(user_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        if request.session.get("admin_readonly"):
            return _JSONResponse(status_code=403, content={"error": "Readonly"})
        data = await request.json()
        delta = float(data.get("delta", 0))
        if delta == 0:
            return _JSONResponse(status_code=400, content={"error": "delta не может быть 0"})
        note = data.get("note") or None
        reason = "manual_add" if delta > 0 else "manual_deduct"
        from decimal import Decimal as _Dec
        from app.db import get_session_factory
        from app.models.user import User as _User
        from app.models.bonus import BonusTransaction as _BonusTx
        from sqlalchemy import select as _sel
        async with get_session_factory()() as session:
            res = await session.execute(_sel(_User).where(_User.id == user_id))
            user = res.scalar_one_or_none()
            if not user:
                return _JSONResponse(status_code=404, content={"error": "Not found"})
            new_balance = float(user.bonus_balance or 0) + delta
            if new_balance < 0:
                return _JSONResponse(status_code=400, content={"error": "Недостаточно баллов"})
            user.bonus_balance = _Dec(str(new_balance))
            session.add(_BonusTx(user_id=user_id, delta=_Dec(str(delta)), reason=reason, note=note))
            await session.commit()
            await session.refresh(user)
        return _JSONResponse({"ok": True, "bonus_balance": float(user.bonus_balance)})

    @app.get("/admin-api/customer/{user_id}/bonus-history", include_in_schema=False)
    async def admin_customer_bonus_history(user_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from app.db import get_session_factory
        from app.models.bonus import BonusTransaction as _BonusTx
        from sqlalchemy import select as _sel
        async with get_session_factory()() as session:
            res = await session.execute(
                _sel(_BonusTx).where(_BonusTx.user_id == user_id)
                .order_by(_BonusTx.created_at.desc()).limit(10)
            )
            txs = res.scalars().all()
        _REASON_LABELS = {
            "order_cashback": "Кешбэк за заказ", "order_payment": "Списание за заказ",
            "manual_add": "Начислено вручную", "manual_deduct": "Списано вручную",
        }
        rows = []
        for tx in txs:
            d = float(tx.delta)
            sign = "+" if d >= 0 else ""
            cls = "pos" if d >= 0 else "neg"
            rl = _REASON_LABELS.get(tx.reason, tx.reason)
            note = f" · {tx.note}" if tx.note else ""
            from datetime import timezone
            import zoneinfo
            msk = zoneinfo.ZoneInfo("Europe/Moscow")
            dt = tx.created_at.replace(tzinfo=timezone.utc).astimezone(msk).strftime("%d.%m.%Y")
            rows.append(
                f'<div class="btx-row">'
                f'<div class="btx-delta {cls}">{sign}{d:.0f} ₽</div>'
                f'<div class="btx-reason">{rl}{note}</div>'
                f'<div class="btx-date">{dt}</div>'
                f'</div>'
            )
        html = "".join(rows) if rows else \
            '<div style="font-size:12px;color:#9ca3af;text-align:center;padding:8px 0">История пуста</div>'
        return _JSONResponse({"html": html})

    @app.post("/admin-api/order/{order_id}/payment-link", include_in_schema=False)
    async def admin_order_payment_link(order_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        if request.session.get("admin_readonly"):
            return _JSONResponse(status_code=403, content={"error": "Readonly"})
        data = await request.json()
        link = (data.get("link") or "").strip()
        if not link.startswith("http"):
            return _JSONResponse(status_code=400, content={"error": "Invalid link"})
        from app.db import get_session_factory
        from sqlalchemy.orm import selectinload
        async with get_session_factory()() as session:
            result = await session.execute(
                select(Order)
                .options(selectinload(Order.user))
                .where(Order.id == order_id)
            )
            order = result.scalar_one_or_none()
            if not order:
                return _JSONResponse(status_code=404, content={"error": "Not found"})
            order.payment_link = link
            order.status = "awaiting_payment"
            await session.commit()
            # Уведомляем клиента
            if order.user:
                try:
                    from app.bot.notify import _send_message
                    import asyncio as _asyncio
                    _asyncio.create_task(_send_message(
                        order.user.telegram_id,
                        f"👀 Мы увидели ваш заказ <b>{order.number}</b>!\n\n"
                        f"Для оформления перейдите по ссылке на оплату:\n{link}",
                    ))
                except Exception:
                    pass
        return _JSONResponse({"ok": True})

    @app.post("/admin-api/order/{order_id}/tracking", include_in_schema=False)
    async def admin_order_tracking(order_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        if request.session.get("admin_readonly"):
            return _JSONResponse(status_code=403, content={"error": "Readonly"})
        data = await request.json()
        link = (data.get("link") or "").strip()
        from app.db import get_session_factory
        async with get_session_factory()() as session:
            result = await session.execute(select(Order).where(Order.id == order_id))
            order = result.scalar_one_or_none()
            if not order:
                return _JSONResponse(status_code=404, content={"error": "Not found"})
            order.tracking_link = link
            await session.commit()
        return _JSONResponse({"ok": True})

    @app.post("/admin-api/order/{order_id}/feedback", include_in_schema=False)
    async def admin_order_feedback(order_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from app.db import get_session_factory
        from sqlalchemy.orm import selectinload
        async with get_session_factory()() as session:
            result = await session.execute(
                select(Order)
                .options(selectinload(Order.items), selectinload(Order.user))
                .where(Order.id == order_id)
            )
            order = result.scalar_one_or_none()
            if not order or not order.user:
                return _JSONResponse(status_code=404, content={"error": "Not found"})
            items_text = ", ".join(
                f"{oi.snapshot_name} {oi.snapshot_weight_g}г" for oi in order.items
            )
            settings = get_settings()
            shop_link = settings.public_base_url.rstrip("/")
            try:
                from app.bot.notify import _send_message
                sent = await _send_message(
                    order.user.telegram_id,
                    f"Здравствуйте! 🌿\n\n"
                    f"Вы заказывали у нас: <b>{items_text}</b>\n\n"
                    f"Понравилось ли вам всё? Будем рады вашему отзыву — "
                    f"напишите нам прямо здесь или зайдите в магазин:\n{shop_link}",
                )
                if sent:
                    from datetime import UTC, datetime as _dt
                    order.feedback_sent_at = _dt.now(UTC)
                    await session.commit()
            except Exception:
                pass
        return _JSONResponse({"ok": True})

    @app.get("/admin-api/me", include_in_schema=False)
    async def admin_me(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        return _JSONResponse({
            "username": request.session.get("admin_username", ""),
            "readonly": bool(request.session.get("admin_readonly")),
        })

    # ===== ИМПОРТ ТОВАРОВ =====

    def _delete_upload_file(path: str | None) -> None:
        """Удаляет файл из static/uploads/ если он там лежит."""
        if not path:
            return
        if not path.startswith("/static/media/uploads/"):
            return
        file = Path(__file__).parent.parent.parent / path.lstrip("/")
        try:
            file.unlink(missing_ok=True)
        except Exception:
            pass

    @app.post("/admin-api/categories/reorder", include_in_schema=False)
    async def admin_categories_reorder(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        if request.session.get("admin_readonly"):
            return _JSONResponse(status_code=403, content={"error": "Readonly"})
        data = await request.json()
        ids = data.get("ids", [])
        if not ids:
            return _JSONResponse(status_code=400, content={"error": "ids required"})
        from app.db import get_session_factory
        from app.models.category import Category
        from sqlalchemy import select
        async with get_session_factory()() as session:
            for order, cat_id in enumerate(ids):
                res = await session.execute(select(Category).where(Category.id == cat_id))
                cat = res.scalar_one_or_none()
                if cat:
                    cat.sort_order = order
            await session.commit()
        return _JSONResponse({"ok": True})

    from fastapi.responses import HTMLResponse as _HTMLResponse, StreamingResponse as _StreamingResponse
    import asyncio as _asyncio
    import io as _io
    from datetime import datetime as _datetime, timezone as _timezone_import

    @app.get("/admin/import", include_in_schema=False)
    async def admin_import_page(request: Request):
        if request.session.get("admin_token") != "authenticated":
            from starlette.responses import RedirectResponse
            return RedirectResponse("/admin/login")
        from app.admin.import_page import IMPORT_PAGE_HTML
        return _HTMLResponse(IMPORT_PAGE_HTML)

    @app.get("/admin-api/import/excel/template", include_in_schema=False)
    async def admin_import_excel_template(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from app.admin.import_worker import make_excel_template
        content = make_excel_template()
        return _StreamingResponse(
            _io.BytesIO(content),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=import_template.xlsx"},
        )

    @app.post("/admin-api/import/yml", include_in_schema=False)
    async def admin_import_yml(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        if request.session.get("admin_readonly"):
            return _JSONResponse(status_code=403, content={"error": "Readonly"})
        data = await request.json()
        url = (data.get("url") or "").strip()
        if not url:
            return _JSONResponse(status_code=400, content={"error": "URL обязателен"})
        from app.db import get_session_factory
        from app.models.yml_import import YmlImport
        from app.admin.import_worker import run_yml_import
        async with get_session_factory()() as session:
            rec = YmlImport(source=url, status="running",
                            started_at=_datetime.now(_timezone_import.utc))
            session.add(rec)
            await session.commit()
            await session.refresh(rec)
            import_id = rec.id
        _asyncio.create_task(run_yml_import(import_id, url))
        return _JSONResponse({"import_id": import_id})

    @app.post("/admin-api/import/excel", include_in_schema=False)
    async def admin_import_excel(request: Request, file: UploadFile = _File(...)):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        if request.session.get("admin_readonly"):
            return _JSONResponse(status_code=403, content={"error": "Readonly"})
        content = await file.read()
        from app.db import get_session_factory
        from app.models.yml_import import YmlImport
        from app.admin.import_worker import run_excel_import
        fname = file.filename or "upload.xlsx"
        async with get_session_factory()() as session:
            rec = YmlImport(source=fname, status="running",
                            started_at=_datetime.now(_timezone_import.utc))
            session.add(rec)
            await session.commit()
            await session.refresh(rec)
            import_id = rec.id
        _asyncio.create_task(run_excel_import(import_id, content))
        return _JSONResponse({"import_id": import_id})

    @app.get("/admin-api/import/{import_id}/status", include_in_schema=False)
    async def admin_import_status(import_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return _JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from app.db import get_session_factory
        from app.models.yml_import import YmlImport
        from sqlalchemy import select
        async with get_session_factory()() as session:
            rec = (await session.execute(select(YmlImport).where(YmlImport.id == import_id))).scalar_one_or_none()
            if not rec:
                return _JSONResponse(status_code=404, content={"error": "Not found"})
            return _JSONResponse({
                "status": rec.status,
                "products_added": rec.products_added,
                "products_updated": rec.products_updated,
                "images_downloaded": rec.images_downloaded,
                "log": rec.log,
                "error": rec.error,
            })

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
                stmt = stmt.where(_User.telegram_id.in_(_DEMO_TG_IDS))
            else:
                stmt = stmt.where(_User.telegram_id.notin_(_DEMO_TG_IDS))
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
    admin.add_view(PickupPointAdmin)
    if _HAS_LINK:
        admin.add_link(_AdminLink(
            label="Бонусная система",
            icon="fa-solid fa-gift",
            url="/admin/bonus-settings",
            category="Настройки магазина",
        ))
    # Система
    admin.add_view(AdminUserAdmin)
    admin.add_view(YmlImportAdmin)
    admin.add_view(PaymentEventAdmin)
