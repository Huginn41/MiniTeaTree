"""Редактор страницы «О нас» и API для FAQ/ПВЗ/контента."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.admin.shared import _render

ABOUT_EDITOR_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>О нас — редактор</title>
{BASE_CSS}
<style>
.ab-card{background:#fff;border-radius:14px;box-shadow:0 2px 10px rgba(0,0,0,.06);padding:24px;margin-bottom:20px}
.ab-label{font-size:12px;font-weight:700;color:#8c9aad;text-transform:uppercase;letter-spacing:.5px;margin-bottom:14px}
.phone-frame{background:#f0f2f5;border-radius:20px;padding:14px;margin-bottom:12px}
.phone-inner{max-width:360px;margin:0 auto;background:#fff;border-radius:32px;padding:14px;
  box-shadow:0 8px 32px rgba(0,0,0,.13)}
.phone-bar{height:6px;background:#e9ecef;border-radius:3px;width:40%;margin:0 auto 12px}
.banner-zone{width:100%;min-height:180px;border-radius:20px;overflow:hidden;position:relative;
  background:linear-gradient(135deg,#1a6b3c,#2d9e5f);cursor:pointer;
  display:flex;align-items:center;justify-content:center;text-align:center}
.banner-zone img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.banner-overlay{position:absolute;inset:0;background:rgba(0,0,0,.15);display:none}
.banner-zone-text{position:relative;z-index:1;color:rgba(255,255,255,.9);font-size:13px}
.banner-zone-emoji{font-size:40px;margin-bottom:6px}
.banner-hover{position:absolute;inset:0;background:rgba(0,0,0,.45);display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:8px;opacity:0;transition:.2s;z-index:3}
.banner-zone:hover .banner-hover{opacity:1}
.banner-hover span{color:#fff;font-size:13px;font-weight:600}
.phone-title{font-size:17px;font-weight:800;color:#212529;padding:10px 4px 2px;letter-spacing:-.3px}
.faq-row{border:1px solid #e9ecef;border-radius:10px;margin-bottom:8px}
.faq-head{display:flex;align-items:center;gap:10px;padding:13px 14px;background:#f8f9fa;border-radius:10px;cursor:pointer;user-select:none}
.faq-head:hover{background:#eef2ff}
.faq-body{display:none;padding:16px;border-top:1px solid #e9ecef}
.faq-body.open{display:block}
.pp-row{display:flex;align-items:center;gap:12px;padding:12px 14px;background:#f8f9fa;
  border:1px solid #e9ecef;border-radius:10px;margin-bottom:8px}
.pp-row.sortable-ghost{opacity:.3;background:#e8f0fe}
.pp-drag,.faq-drag{cursor:grab;color:#adb5bd;font-size:20px;flex-shrink:0;line-height:1;user-select:none}
</style>
</head>
<body>
{TOPNAV}
<div class="container-fluid px-4 py-4" style="max-width:860px">

  <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
    <h5 class="section-title mb-0">✏️ Редактор страницы «О нас»</h5>
    <button id="save-all-btn" class="btn btn-sm btn-primary">
      <i class="fa-solid fa-floppy-disk me-1"></i>Сохранить
    </button>
  </div>

  <!-- 1. Баннер -->
  <div class="ab-card">
    <div class="ab-label">Обложка страницы</div>
    <div style="font-size:11px;color:#8c9aad;margin-bottom:12px;display:flex;align-items:center;gap:5px">
      <i class="fa-solid fa-mobile-screen"></i> Предпросмотр — нажмите на обложку чтобы изменить фото
    </div>
    <div class="phone-frame">
      <div class="phone-inner">
        <div class="phone-bar"></div>
        <div class="banner-zone" id="banner-zone">
          <div class="banner-zone-text" id="banner-text">
            <div class="banner-zone-emoji">🍵</div>
            <div>Нажмите чтобы загрузить фото</div>
            <div style="font-size:11px;opacity:.7;margin-top:4px">JPG, PNG, WebP</div>
          </div>
          <img id="banner-img" style="display:none" alt="">
          <div class="banner-overlay" id="banner-overlay"></div>
          <div class="banner-hover">
            <i class="fa-solid fa-camera fa-2x text-white"></i>
            <span>Изменить фото</span>
          </div>
        </div>
        <div class="phone-title" id="phone-title-preview">Чайное Дерево</div>
      </div>
    </div>
    <input type="file" id="bfile" accept="image/*" style="display:none">
    <div class="d-flex align-items-center gap-3">
      <button class="btn btn-sm btn-outline-danger" id="rm-banner" style="display:none">
        <i class="fa-solid fa-trash me-1"></i>Убрать фото
      </button>
      <span id="banner-status" style="font-size:12px;color:#6c757d"></span>
    </div>
    <div style="font-size:11px;color:#8c9aad;margin-top:8px;line-height:1.5;">📐 Рекомендуется <b>1200×500 px</b> · JPG / PNG / WebP · до 5 МБ</div>
  </div>

  <!-- 2. Заголовок и описание -->
  <div class="ab-card">
    <div class="ab-label">Заголовок и описание</div>
    <label class="form-label">Заголовок</label>
    <input type="text" id="about-title" class="form-control mb-3" placeholder="Чайное Дерево"
      oninput="var v=this.value.trim()||'Чайное Дерево';document.getElementById('phone-title-preview').textContent=v">
    <label class="form-label">Описание</label>
    <textarea id="desc-textarea" class="form-control" rows="7" placeholder="Расскажите о вашем магазине…" style="resize:vertical"></textarea>
  </div>

  <!-- 3. FAQ -->
  <div class="ab-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div class="ab-label mb-0">Часто задаваемые вопросы</div>
      <button id="add-faq-btn" class="btn btn-sm btn-outline-primary">
        <i class="fa-solid fa-plus me-1"></i>Добавить вопрос
      </button>
    </div>
    <div id="faq-list"><p class="text-muted" style="font-size:13px">Загрузка…</p></div>
  </div>

  <!-- 4. Порядок ПВЗ -->
  <div class="ab-card">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div class="ab-label mb-0">Пункты самовывоза</div>
      <a href="/admin/pickup-point/list" class="btn btn-sm btn-outline-secondary">
        <i class="fa-solid fa-pen me-1"></i>Добавить / редактировать
      </a>
    </div>
    <p style="font-size:13px;color:#6c757d;margin-bottom:10px">Перетащите чтобы изменить порядок.</p>
    <div id="pp-list"><p class="text-muted" style="font-size:13px">Загрузка…</p></div>
    <button class="btn btn-sm btn-outline-primary mt-2" id="pp-order-btn" style="display:none">
      <i class="fa-solid fa-arrows-up-down me-1"></i>Сохранить порядок
    </button>
  </div>

</div>

<script src="https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js"></script>
<script>
var bannerPath = null;

function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Баннер ──────────────────────────────────────────────────────────
async function uploadBanner(file) {
  var status = document.getElementById('banner-status');
  status.style.color = '#6c757d';
  status.textContent = 'Загружаем…';
  var fd = new FormData();
  fd.append('file', file);
  try {
    var r = await fetch('/admin-api/upload-image', {method:'POST', credentials:'include', body:fd});
    var text = await r.text();
    if (!r.ok) throw new Error('HTTP ' + r.status + ': ' + text.substring(0,120));
    var d = JSON.parse(text);
    bannerPath = d.path;
    var img = document.getElementById('banner-img');
    img.src = d.path;
    img.style.display = 'block';
    document.getElementById('banner-overlay').style.display = 'block';
    document.getElementById('banner-text').style.display = 'none';
    document.getElementById('rm-banner').style.display = 'inline-flex';
    status.style.color = '#1b873f';
    status.textContent = '✓ Фото загружено. Нажмите «Сохранить».';
  } catch(e) {
    status.style.color = '#dc3545';
    status.textContent = 'Ошибка загрузки: ' + e.message;
  }
}

// ── FAQ ─────────────────────────────────────────────────────────────
function renderFaq(items) {
  var list = document.getElementById('faq-list');
  list.innerHTML = '';
  if (!items.length) {
    list.innerHTML = '<p class="text-muted" style="font-size:13px">Нет вопросов. Нажмите «Добавить вопрос».</p>';
    return;
  }
  items.forEach(function(item) { list.appendChild(makeFaqRow(item)); });
  Sortable.create(list, {
    handle: '.faq-drag', animation: 150, ghostClass: 'sortable-ghost',
    onEnd: function() { saveFaqOrder(); },
  });
}

async function saveFaqOrder() {
  var ids = Array.from(document.querySelectorAll('#faq-list .faq-row'))
    .map(function(r) { return parseInt(r.dataset.id); })
    .filter(Boolean);
  if (!ids.length) return;
  await fetch('/admin-api/faq/reorder', {
    method: 'POST', credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ids: ids}),
  });
}

function makeFaqRow(item) {
  var row = document.createElement('div');
  row.className = 'faq-row';
  row.dataset.id = item.id || '';

  var head = document.createElement('div');
  head.className = 'faq-head';

  var icon = document.createElement('span');
  icon.className = 'faq-drag';
  icon.title = 'Перетащить';
  icon.textContent = '⠿';

  var title = document.createElement('span');
  title.style.cssText = 'flex:1;font-size:14px;font-weight:600;color:#212529';
  title.textContent = item.question || 'Новый вопрос';

  var delBtn = document.createElement('button');
  delBtn.className = 'btn btn-sm btn-outline-danger';
  delBtn.style.cssText = 'padding:2px 8px;font-size:11px;flex-shrink:0';
  delBtn.textContent = '✕ Удалить';
  delBtn.addEventListener('click', function(e) { e.stopPropagation(); delFaq(row); });

  head.appendChild(icon);
  head.appendChild(title);
  head.appendChild(delBtn);
  head.addEventListener('click', function() { toggleFaqBody(body); });

  var body = document.createElement('div');
  body.className = 'faq-body';

  var qLabel = document.createElement('label');
  qLabel.className = 'form-label mt-1';
  qLabel.textContent = 'Вопрос';

  var qInput = document.createElement('input');
  qInput.className = 'form-control mb-3 fq';
  qInput.value = item.question || '';
  qInput.addEventListener('input', function() { title.textContent = qInput.value || 'Новый вопрос'; });

  var aLabel = document.createElement('label');
  aLabel.className = 'form-label';
  aLabel.textContent = 'Ответ';

  var aInput = document.createElement('textarea');
  aInput.className = 'form-control faq-answer';
  aInput.rows = 4;
  aInput.value = (item.answer || '').replace(/<br[^>]*>/gi, '\\n');
  aInput.style.resize = 'vertical';

  var actions = document.createElement('div');
  actions.className = 'd-flex gap-2 mt-3';

  var saveBtn = document.createElement('button');
  saveBtn.className = 'btn btn-sm btn-primary fsb';
  saveBtn.textContent = 'Сохранить';
  saveBtn.addEventListener('click', function() { saveFaqRow(row); });

  var closeBtn = document.createElement('button');
  closeBtn.className = 'btn btn-sm btn-outline-secondary';
  closeBtn.textContent = 'Закрыть';
  closeBtn.addEventListener('click', function() { body.classList.remove('open'); });

  actions.appendChild(saveBtn);
  actions.appendChild(closeBtn);
  body.appendChild(qLabel);
  body.appendChild(qInput);
  body.appendChild(aLabel);
  body.appendChild(aInput);
  body.appendChild(actions);
  row.appendChild(head);
  row.appendChild(body);
  return row;
}

function toggleFaqBody(body) {
  var isOpen = body.classList.contains('open');
  document.querySelectorAll('.faq-body.open').forEach(function(b) { b.classList.remove('open'); });
  if (!isOpen) {
    body.classList.add('open');
    body.querySelector('.fq').focus();
  }
}

function addFaq() {
  var list = document.getElementById('faq-list');
  var empty = list.querySelector('p');
  if (empty) empty.remove();
  var row = makeFaqRow({id: null, question: '', answer: ''});
  list.appendChild(row);
  var body = row.querySelector('.faq-body');
  body.classList.add('open');
  row.querySelector('.fq').focus();
}

async function saveFaqRow(row) {
  var id = row.dataset.id;
  var q = row.querySelector('.fq').value.trim();
  if (!q) { alert('Введите вопрос'); return; }
  var answer = row.querySelector('.faq-answer').value.replace(/\\n/g, '<br>');
  var btn = row.querySelector('.fsb');
  btn.disabled = true; btn.textContent = 'Сохраняем…';
  try {
    var url = id ? '/admin-api/faq/' + id : '/admin-api/faq';
    var r = await fetch(url, {
      method: id ? 'PATCH' : 'POST',
      credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({question: q, answer: answer})
    });
    var text = await r.text();
    if (!r.ok) throw new Error('HTTP ' + r.status + ': ' + text.substring(0, 100));
    var d = JSON.parse(text);
    row.dataset.id = d.id;
    row.querySelector('.faq-body').classList.remove('open');
    btn.disabled = false; btn.textContent = 'Сохранить';
  } catch(e) {
    btn.disabled = false; btn.textContent = 'Сохранить';
    alert('Ошибка: ' + e.message);
  }
}

async function delFaq(row) {
  if (!confirm('Удалить вопрос?')) return;
  var id = row.dataset.id;
  if (id) {
    var r = await fetch('/admin-api/faq/' + id, {method: 'DELETE', credentials: 'include'});
    if (!r.ok) { alert('Ошибка удаления'); return; }
  }
  row.remove();
  if (!document.querySelectorAll('.faq-row').length)
    document.getElementById('faq-list').innerHTML = '<p class="text-muted" style="font-size:13px">Нет вопросов.</p>';
}

// ── ПВЗ drag-and-drop ───────────────────────────────────────────────
function renderPp(items) {
  var list = document.getElementById('pp-list');
  list.innerHTML = '';
  if (!items.length) {
    list.innerHTML = '<p class="text-muted" style="font-size:13px">Нет пунктов. <a href="/admin/pickup-point/list">Добавить →</a></p>';
    return;
  }
  items.forEach(function(p) {
    var addr = [p.city, p.street, p.building ? 'д.' + p.building : ''].filter(Boolean).join(', ') || p.address || '';
    var row = document.createElement('div');
    row.className = 'pp-row';
    row.dataset.id = p.id;
    row.innerHTML = '<span class="pp-drag" title="Перетащить">⠿</span>' +
      '<div style="flex:1;min-width:0">' +
        '<div style="font-size:14px;font-weight:600;color:#212529">' + esc(p.name) + '</div>' +
        (addr ? '<div style="font-size:12px;color:#6c757d">' + esc(addr) + '</div>' : '') +
      '</div>' +
      (!p.is_active ? '<span class="badge bg-secondary">скрыт</span>' : '');
    list.appendChild(row);
  });
  document.getElementById('pp-order-btn').style.display = 'inline-flex';
  if (typeof Sortable !== 'undefined') {
    Sortable.create(list, {handle: '.pp-drag', animation: 150, ghostClass: 'sortable-ghost'});
  }
}

async function savePpOrder() {
  var rows = document.querySelectorAll('#pp-list .pp-row');
  var order = Array.from(rows).map(function(r, i) { return {id: parseInt(r.dataset.id), sort_order: i}; });
  var btn = document.getElementById('pp-order-btn');
  btn.disabled = true; btn.textContent = 'Сохраняем…';
  try {
    var r = await fetch('/admin-api/pickup-points/reorder', {
      method: 'POST', credentials: 'include',
      headers: {'Content-Type': 'application/json'}, body: JSON.stringify(order)
    });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    btn.disabled = false;
    btn.style.cssText = 'background:#1b873f;border-color:#1b873f;color:#fff;display:inline-flex';
    btn.textContent = '✓ Порядок сохранён';
    setTimeout(function() {
      btn.style.cssText = 'display:inline-flex';
      btn.innerHTML = '<i class="fa-solid fa-arrows-up-down me-1"></i>Сохранить порядок';
    }, 2000);
  } catch(e) {
    btn.disabled = false;
    btn.innerHTML = '<i class="fa-solid fa-arrows-up-down me-1"></i>Сохранить порядок';
    alert('Ошибка: ' + e.message);
  }
}

// ── Сохранить заголовок + описание + баннер ─────────────────────────
async function saveAll() {
  var btn = document.getElementById('save-all-btn');
  btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i>Сохраняем…';
  try {
    var r = await fetch('/admin-api/about', {
      method: 'POST', credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        title: document.getElementById('about-title').value.trim() || 'Чайное Дерево',
        description_html: document.getElementById('desc-textarea').value.replace(/\\n/g, '<br>'),
        banner_image_path: bannerPath,
      })
    });
    var text = await r.text();
    if (!r.ok) throw new Error('HTTP ' + r.status + ': ' + text.substring(0, 100));
    btn.disabled = false;
    btn.style.cssText = 'background:#1b873f;border-color:#1b873f';
    btn.innerHTML = '<i class="fa-solid fa-check me-1"></i>Сохранено';
    setTimeout(function() { btn.style.cssText = ''; btn.innerHTML = '<i class="fa-solid fa-floppy-disk me-1"></i>Сохранить'; }, 2000);
  } catch(e) {
    btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-floppy-disk me-1"></i>Сохранить';
    alert('Ошибка сохранения: ' + e.message);
  }
}

// ── Инициализация ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
  // Баннер
  document.getElementById('banner-zone').addEventListener('click', function() {
    document.getElementById('bfile').click();
  });
  document.getElementById('bfile').addEventListener('change', function() {
    if (this.files && this.files[0]) uploadBanner(this.files[0]);
  });
  document.getElementById('rm-banner').addEventListener('click', function(e) {
    e.stopPropagation();
    bannerPath = null;
    document.getElementById('banner-img').style.display = 'none';
    document.getElementById('banner-overlay').style.display = 'none';
    document.getElementById('banner-text').style.display = 'block';
    document.getElementById('rm-banner').style.display = 'none';
    document.getElementById('banner-status').textContent = '';
  });

  // Кнопки
  document.getElementById('save-all-btn').addEventListener('click', saveAll);
  document.getElementById('add-faq-btn').addEventListener('click', addFaq);
  document.getElementById('pp-order-btn').addEventListener('click', savePpOrder);

  // Загружаем данные
  fetch('/admin-api/about', {credentials: 'include'})
    .then(function(r) { return r.json(); })
    .then(function(d) {
      var title = d.title || 'Чайное Дерево';
      document.getElementById('about-title').value = title;
      document.getElementById('phone-title-preview').textContent = title;
      if (d.description_html) {
        document.getElementById('desc-textarea').value = d.description_html.replace(/<br[^>]*>/gi, '\\n');
      }
      if (d.banner_image_path) {
        bannerPath = d.banner_image_path;
        document.getElementById('banner-img').src = d.banner_image_path;
        document.getElementById('banner-img').style.display = 'block';
        document.getElementById('banner-overlay').style.display = 'block';
        document.getElementById('banner-text').style.display = 'none';
        document.getElementById('rm-banner').style.display = 'inline-flex';
      }
    })
    .catch(function(e) { console.error('about load error:', e); });

  fetch('/admin-api/faq', {credentials: 'include'})
    .then(function(r) { return r.json(); })
    .then(renderFaq)
    .catch(function(e) { renderFaq([]); console.error('faq load error:', e); });

  fetch('/admin-api/pickup-points', {credentials: 'include'})
    .then(function(r) { return r.json(); })
    .then(renderPp)
    .catch(function(e) { renderPp([]); console.error('pp load error:', e); });
});
</script>
</body>
</html>"""


async def _about_get() -> dict:
    from sqlalchemy import select
    from app.db import get_session_factory
    from app.models.content import SiteAbout
    async with get_session_factory()() as s:
        r = await s.execute(select(SiteAbout).where(SiteAbout.id == 1))
        a = r.scalar_one_or_none()
        if not a:
            return {"title": "Чайное Дерево", "description_html": "", "banner_image_path": None}
        return {"title": a.title, "description_html": a.description_html or "", "banner_image_path": a.banner_image_path}


async def _about_save(title: str, description_html: str, banner_image_path: str | None) -> None:
    from sqlalchemy import select
    from app.db import get_session_factory
    from app.models.content import SiteAbout
    async with get_session_factory()() as s:
        r = await s.execute(select(SiteAbout).where(SiteAbout.id == 1))
        a = r.scalar_one_or_none()
        if a:
            a.title = title
            a.description_html = description_html
            a.banner_image_path = banner_image_path
        else:
            s.add(SiteAbout(id=1, title=title, description_html=description_html, banner_image_path=banner_image_path))
        await s.commit()


async def _faq_list() -> list[dict]:
    from sqlalchemy import select
    from app.db import get_session_factory
    from app.models.content import FaqItem
    async with get_session_factory()() as s:
        r = await s.execute(select(FaqItem).order_by(FaqItem.sort, FaqItem.id))
        return [{"id": f.id, "question": f.question, "answer": f.answer} for f in r.scalars().all()]


def _pp_dict(p) -> dict:
    return {"id": p.id, "name": p.name, "city": p.city, "street": p.street,
            "building": p.building, "address": p.address, "work_hours": p.work_hours,
            "comment": p.comment, "phone": p.phone, "map_embed_src": p.map_embed_src,
            "is_active": p.is_active, "sort_order": p.sort_order}


def setup_about_routes(app: FastAPI) -> None:
    @app.get("/crm/about", response_class=HTMLResponse, include_in_schema=False)
    async def about_editor_page(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return RedirectResponse("/admin/login")
        return HTMLResponse(_render(ABOUT_EDITOR_HTML, "about"))

    @app.get("/admin-api/about", include_in_schema=False)
    async def about_get(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        return JSONResponse(await _about_get())

    @app.post("/admin-api/about", include_in_schema=False)
    async def about_save(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        body = await request.json()
        await _about_save(
            title=body.get("title", "Чайное Дерево"),
            description_html=body.get("description_html", ""),
            banner_image_path=body.get("banner_image_path"),
        )
        return JSONResponse({"ok": True})

    @app.post("/admin-api/upload-image", include_in_schema=False)
    async def upload_image(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        import uuid
        from pathlib import Path
        from fastapi import UploadFile
        from app.admin.upload import to_webp, UPLOADS_DIR
        form = await request.form()
        file: UploadFile = form.get("file")
        if not file:
            return JSONResponse(status_code=400, content={"error": "no file"})
        data = await file.read(16 * 1024 * 1024)
        fname = f"{uuid.uuid4().hex}.webp"
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        dest = UPLOADS_DIR / fname
        try:
            to_webp(data, dest)
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        return JSONResponse({"path": f"/static/media/uploads/{fname}"})

    @app.get("/admin-api/faq", include_in_schema=False)
    async def faq_list_api(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        return JSONResponse(await _faq_list())

    @app.post("/admin-api/faq", include_in_schema=False)
    async def faq_create(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from app.db import get_session_factory
        from app.models.content import FaqItem
        body = await request.json()
        async with get_session_factory()() as s:
            item = FaqItem(question=body.get("question", ""), answer=body.get("answer", ""), sort=0, is_active=True)
            s.add(item)
            await s.commit()
            await s.refresh(item)
            return JSONResponse({"id": item.id, "question": item.question, "answer": item.answer})

    @app.patch("/admin-api/faq/{faq_id}", include_in_schema=False)
    async def faq_update(faq_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from sqlalchemy import select
        from app.db import get_session_factory
        from app.models.content import FaqItem
        body = await request.json()
        async with get_session_factory()() as s:
            r = await s.execute(select(FaqItem).where(FaqItem.id == faq_id))
            item = r.scalar_one_or_none()
            if not item:
                return JSONResponse(status_code=404, content={"error": "not found"})
            if "question" in body:
                item.question = body["question"]
            if "answer" in body:
                item.answer = body["answer"]
            await s.commit()
            return JSONResponse({"id": item.id, "question": item.question, "answer": item.answer})

    @app.delete("/admin-api/faq/{faq_id}", include_in_schema=False)
    async def faq_delete(faq_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from sqlalchemy import delete
        from app.db import get_session_factory
        from app.models.content import FaqItem
        async with get_session_factory()() as s:
            await s.execute(delete(FaqItem).where(FaqItem.id == faq_id))
            await s.commit()
        return JSONResponse({"ok": True})

    @app.post("/admin-api/faq/reorder", include_in_schema=False)
    async def faq_reorder(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        data = await request.json()
        ids = data.get("ids", [])
        from sqlalchemy import select as _select
        from app.db import get_session_factory
        from app.models.content import FaqItem
        async with get_session_factory()() as s:
            for sort, faq_id in enumerate(ids):
                res = await s.execute(_select(FaqItem).where(FaqItem.id == faq_id))
                item = res.scalar_one_or_none()
                if item:
                    item.sort = sort
            await s.commit()
        return JSONResponse({"ok": True})

    @app.get("/admin-api/pickup-points", include_in_schema=False)
    async def pp_list(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from sqlalchemy import select
        from app.db import get_session_factory
        from app.models.content import PickupPoint
        async with get_session_factory()() as s:
            r = await s.execute(select(PickupPoint).order_by(PickupPoint.sort_order, PickupPoint.id))
            return JSONResponse([_pp_dict(p) for p in r.scalars().all()])

    @app.post("/admin-api/pickup-points", include_in_schema=False)
    async def pp_create(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from app.db import get_session_factory
        from app.models.content import PickupPoint
        body = await request.json()
        async with get_session_factory()() as s:
            city = body.get("city", "")
            street = body.get("street", "")
            building = body.get("building", "")
            parts = [x for x in [city, street, ("д. "+building if building else "")] if x]
            address = ", ".join(parts) if parts else ""
            p = PickupPoint(
                name=body.get("name", ""),
                city=city, street=street, building=building, address=address,
                work_hours=body.get("work_hours") or None,
                comment=body.get("comment") or None,
                phone=body.get("phone") or None,
                map_embed_src=body.get("map_embed_src") or None,
                is_active=True, sort_order=0,
            )
            s.add(p)
            await s.commit()
            await s.refresh(p)
            return JSONResponse(_pp_dict(p))

    @app.patch("/admin-api/pickup-points/{pp_id}", include_in_schema=False)
    async def pp_update(pp_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from sqlalchemy import select
        from app.db import get_session_factory
        from app.models.content import PickupPoint
        body = await request.json()
        async with get_session_factory()() as s:
            r = await s.execute(select(PickupPoint).where(PickupPoint.id == pp_id))
            p = r.scalar_one_or_none()
            if not p:
                return JSONResponse(status_code=404, content={"error": "not found"})
            for field in ("name", "city", "street", "building", "work_hours", "comment", "phone", "map_embed_src"):
                if field in body:
                    setattr(p, field, body[field] or None if field != "name" else body[field])
            city = p.city or ""
            street = p.street or ""
            building = p.building or ""
            parts = [x for x in [city, street, ("д. "+building if building else "")] if x]
            p.address = ", ".join(parts) if parts else p.address
            await s.commit()
            return JSONResponse(_pp_dict(p))

    @app.post("/admin-api/pickup-points/reorder", include_in_schema=False)
    async def pp_reorder(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from sqlalchemy import select
        from app.db import get_session_factory
        from app.models.content import PickupPoint
        body = await request.json()
        async with get_session_factory()() as s:
            for item in body:
                r = await s.execute(select(PickupPoint).where(PickupPoint.id == item["id"]))
                p = r.scalar_one_or_none()
                if p:
                    p.sort_order = item["sort_order"]
            await s.commit()
        return JSONResponse({"ok": True})

    @app.delete("/admin-api/pickup-points/{pp_id}", include_in_schema=False)
    async def pp_delete(pp_id: int, request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        from sqlalchemy import delete
        from app.db import get_session_factory
        from app.models.content import PickupPoint
        async with get_session_factory()() as s:
            await s.execute(delete(PickupPoint).where(PickupPoint.id == pp_id))
            await s.commit()
        return JSONResponse({"ok": True})
