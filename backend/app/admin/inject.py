"""CSS/JS-инжекция и middleware для SQLAdmin."""

from __future__ import annotations

from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

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

/* ── Toggle switch для чекбоксов ── */
.form-group.row input[type="checkbox"],
.form-check-input[type="checkbox"] {
  -webkit-appearance:none !important; appearance:none !important;
  width:44px !important; height:24px !important;
  background:#dee2e6 !important; border:none !important;
  border-radius:12px !important; position:relative !important;
  cursor:pointer !important; transition:background .2s !important;
  margin-top:4px !important; flex-shrink:0 !important; padding:0 !important;
  display:inline-block !important; vertical-align:middle !important;
}
.form-group.row input[type="checkbox"]::before,
.form-check-input[type="checkbox"]::before {
  content:'' !important; position:absolute !important;
  width:18px !important; height:18px !important;
  background:#fff !important; border-radius:50% !important;
  top:3px !important; left:3px !important;
  transition:left .2s !important; box-shadow:0 1px 4px rgba(0,0,0,.25) !important;
}
.form-group.row input[type="checkbox"]:checked,
.form-check-input[type="checkbox"]:checked { background:#3d5afe !important; }
.form-group.row input[type="checkbox"]:checked::before,
.form-check-input[type="checkbox"]:checked::before { left:23px !important; }
.form-group.row input[type="checkbox"]:focus,
.form-check-input[type="checkbox"]:focus { box-shadow:0 0 0 3px rgba(61,90,254,.2) !important; outline:none !important; }

/* ── Пагинация / бейджи ── */
.pagination .page-link { border-radius:8px !important; color:#3d5afe !important; }
.pagination .page-item.active .page-link { background:#3d5afe !important; border-color:#3d5afe !important; color:#fff !important; }
.badge { border-radius:6px !important; font-weight:600 !important; }

/* ── Мобильная адаптивность ── */
@media (max-width: 768px) {
  .ct-topnav { padding:0 12px !important; gap:0 !important; flex-wrap:wrap !important; height:auto !important; min-height:48px !important; }
  .ct-brand { font-size:14px !important; margin-right:8px !important; }
  .ct-nav-link { padding:0 8px !important; font-size:12px !important; height:48px !important; }
  .ct-nav-link i { display:none !important; }
  .ct-sep { display:none !important; }
  .ct-logout a { font-size:11px !important; padding:4px 8px !important; }
  .ct-dropdown-menu { min-width:160px !important; }
  .page-wrapper { padding:0 !important; }
  .container-fluid { padding-left:12px !important; padding-right:12px !important; }
  .table th, .table td { font-size:11px !important; padding:6px 6px !important; }
  .card { border-radius:10px !important; }
  .col-sm-2, .col-sm-10 { padding-left:0 !important; padding-right:0 !important; }
}
@media (max-width: 576px) {
  .card-header { padding:12px 16px !important; }
  .card-body { padding:14px 16px !important; }
  .table .d-none-xs { display:none !important; }
}
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

  // ---- N. Добавить «Бонусная система» в сайдбар SQLAdmin ----
  function injectBonusLink(){
    if(document.querySelector('a[href="/admin/bonus-settings"]')) return;
    // Находим любую ссылку категории «Настройки магазина» по href
    var anchor = document.querySelector('a[href="/admin/banner/list"]');
    if(!anchor) return;
    var isActive = window.location.pathname === '/admin/bonus-settings';
    // Клонируем структуру соседнего элемента (li или просто a)
    var li = anchor.closest('li');
    var newLink = document.createElement('a');
    newLink.href = '/admin/bonus-settings';
    newLink.className = anchor.className.replace(/\bactive\b/g, '').trim() + (isActive ? ' active' : '');
    newLink.innerHTML = '<i class="fa-solid fa-gift me-2"></i><span>Бонусная система</span>';
    if(li){
      var newLi = document.createElement('li');
      newLi.appendChild(newLink);
      li.parentElement.appendChild(newLi);
      if(isActive){
        // раскрыть collapse-секцию
        var collapse = li.closest('.collapse');
        if(collapse) collapse.classList.add('show');
      }
    } else {
      anchor.parentElement.appendChild(newLink);
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
    injectBonusLink();
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
