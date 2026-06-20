"""HTML-страница импорта товаров для SQLAdmin."""

IMPORT_PAGE_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Импорт товаров — Чайное Дерево</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
@font-face { font-family:'Futura'; src:url('/static/fonts/FuturaLightC.otf') format('opentype'); font-weight:300; }
@font-face { font-family:'Futura'; src:url('/static/fonts/FuturaBookC.otf') format('opentype'); font-weight:400; }
@font-face { font-family:'Futura'; src:url('/static/fonts/FuturaDemiC.otf') format('opentype'); font-weight:600; }
*, body { font-family:'Futura','Century Gothic',-apple-system,sans-serif !important; }
.fa-solid,.fa-regular,.fa-brands,.fas,.far,.fab { font-family:"Font Awesome 6 Free" !important; }
.fa-brands,.fab { font-family:"Font Awesome 6 Brands" !important; }

body { background:#f4f6fb; min-height:100vh; }

/* ── Навбар (те же классы что в layout.html) ── */
.ct-topnav { background:#fff; border-bottom:1px solid #e9ecef; box-shadow:0 1px 8px rgba(0,0,0,.06);
  height:56px; display:flex; align-items:center; padding:0 24px; gap:4px; position:sticky; top:0; z-index:1000; }
.ct-brand { font-weight:800; font-size:16px; color:#212529; text-decoration:none; margin-right:16px; }
.ct-brand:hover { color:#3d5afe; text-decoration:none; }
.ct-nav-link { display:flex; align-items:center; gap:6px; padding:0 12px; height:56px; font-size:13.5px;
  font-weight:500; color:#495057; text-decoration:none; border-bottom:2px solid transparent; transition:all .15s; cursor:pointer; }
.ct-nav-link:hover { color:#3d5afe; border-bottom-color:#3d5afe; text-decoration:none; }
.ct-nav-link.active { color:#3d5afe; border-bottom-color:#3d5afe; font-weight:600; }
.ct-nav-link i { font-size:14px; color:#1a6b3c; }
.ct-nav-link.active i { color:#3d5afe; }
.ct-sep { width:1px; height:20px; background:#dee2e6; margin:0 8px; }
.ct-dropdown { position:relative; }
.ct-dropdown-menu { display:none; position:absolute; top:52px; left:0; background:#fff;
  border:1px solid #e9ecef; border-radius:10px; box-shadow:0 8px 24px rgba(0,0,0,.1);
  min-width:200px; padding:6px 0; z-index:1001; }
.ct-dropdown:hover .ct-dropdown-menu,.ct-dropdown-menu:hover { display:block; }
.ct-dropdown-item { display:block; padding:8px 16px; font-size:13px; color:#495057; text-decoration:none; transition:all .1s; }
.ct-dropdown-item:hover { background:#f0f4ff; color:#3d5afe; text-decoration:none; }
.ct-dropdown-arrow { font-size:10px; opacity:.5; margin-left:2px; }
.ct-logout { margin-left:auto; display:flex; align-items:center; gap:8px; }
.ct-logout a { font-size:13px; color:#6c757d; text-decoration:none; padding:6px 12px;
  border-radius:8px; border:1px solid #dee2e6; transition:all .15s; }
.ct-logout a:hover { color:#3d5afe; border-color:#3d5afe; }

/* ── Контент ── */
.import-card { background:#fff; border-radius:14px; box-shadow:0 2px 10px rgba(0,0,0,.06); padding:28px; margin-bottom:20px; }
.import-card h5 { font-size:15px; font-weight:700; margin-bottom:4px; color:#212529; }
.import-card .subtitle { font-size:12.5px; color:#6c757d; margin-bottom:20px; }
.btn-import { background:#3d5afe; color:#fff; border:none; border-radius:8px; padding:10px 24px;
  font-size:14px; font-weight:600; cursor:pointer; transition:background .15s; }
.btn-import:hover { background:#2a3eb1; }
.btn-import:disabled { background:#aaa; cursor:not-allowed; }
.btn-template { background:#f0f4ff; color:#3d5afe; border:1px solid #c0ccff; border-radius:8px;
  padding:8px 18px; font-size:13px; font-weight:600; cursor:pointer; text-decoration:none;
  display:inline-flex; align-items:center; gap:6px; transition:all .15s; }
.btn-template:hover { background:#e0e8ff; color:#2a3eb1; text-decoration:none; }
.form-control { border-radius:8px !important; border-color:#dee2e6 !important; font-size:14px !important; }
.form-control:focus { border-color:#3d5afe !important; box-shadow:0 0 0 3px rgba(61,90,254,.12) !important; }
.form-label { font-size:13px; font-weight:600; color:#495057; margin-bottom:6px; }
.log-box { background:#f8f9fa; border:1px solid #e9ecef; border-radius:8px; padding:14px;
  font-size:12px; font-family:monospace; white-space:pre-wrap; max-height:300px; overflow-y:auto;
  display:none; margin-top:16px; }
.status-badge { display:inline-flex; align-items:center; gap:6px; padding:6px 14px;
  border-radius:20px; font-size:13px; font-weight:600; margin-top:12px; display:none; }
.status-running { background:#fff8e1; color:#e65100; }
.status-success { background:#e8f5e9; color:#2e7d32; }
.status-failed { background:#ffebee; color:#c62828; }
.hint-box { background:#f0f4ff; border-left:3px solid #3d5afe; border-radius:0 8px 8px 0;
  padding:12px 16px; font-size:12.5px; color:#3d5afe; margin-bottom:18px; }
</style>
</head>
<body>

<!-- ── Навбар ── -->
<div class="ct-topnav">
  <a class="ct-brand" href="/admin/dashboard">🍵 Чайное Дерево</a>
  <a class="ct-nav-link" href="/admin/dashboard"><i class="fa-solid fa-chart-line"></i> Дашборд</a>
  <div class="ct-sep"></div>
  <a class="ct-nav-link active" href="/admin/import"><i class="fa-solid fa-file-import"></i> Импорт</a>
  <div class="ct-sep"></div>
  <div class="ct-dropdown">
    <span class="ct-nav-link"><i class="fa-solid fa-box"></i> Заказы <span class="ct-dropdown-arrow">▾</span></span>
    <div class="ct-dropdown-menu">
      <a class="ct-dropdown-item" href="/admin/order/list">Заказы</a>
      <a class="ct-dropdown-item" href="/admin/orderitem/list">Позиции заказов</a>
      <a class="ct-dropdown-item" href="/admin/deliveryinfo/list">Доставки</a>
    </div>
  </div>
  <div class="ct-dropdown">
    <span class="ct-nav-link"><i class="fa-solid fa-users"></i> CRM <span class="ct-dropdown-arrow">▾</span></span>
    <div class="ct-dropdown-menu">
      <a class="ct-dropdown-item" href="/admin/user/list">Клиенты</a>
      <a class="ct-dropdown-item" href="/admin/notificationtarget/list">Уведомления</a>
    </div>
  </div>
  <div class="ct-dropdown">
    <span class="ct-nav-link"><i class="fa-solid fa-store"></i> Каталог <span class="ct-dropdown-arrow">▾</span></span>
    <div class="ct-dropdown-menu">
      <a class="ct-dropdown-item" href="/admin/product/list">Товары</a>
      <a class="ct-dropdown-item" href="/admin/category/list">Категории</a>
      <a class="ct-dropdown-item" href="/admin/banner/list">Баннеры</a>
      <a class="ct-dropdown-item" href="/admin/faqitem/list">FAQ</a>
      <a class="ct-dropdown-item" href="/admin/pickuppoint/list">Самовывоз</a>
    </div>
  </div>
  <div class="ct-logout">
    <span id="nav-username" style="font-size:13px;color:#6c757d;display:none;align-items:center;gap:6px">
      <i class="fa-solid fa-circle-user" style="color:#1a6b3c"></i><span id="nav-uname"></span>
    </span>
    <a href="/admin/logout"><i class="fa-solid fa-right-from-bracket me-1"></i>Выйти</a>
  </div>
</div>

<!-- ── Контент ── -->
<div class="container" style="max-width:800px;padding:32px 16px">
  <h2 style="font-size:22px;font-weight:800;margin-bottom:6px">Импорт товаров</h2>
  <p style="color:#6c757d;font-size:14px;margin-bottom:28px">Добавление и обновление товаров из YML-фида или Excel-файла</p>

  <!-- ── YML ── -->
  <div class="import-card">
    <h5><i class="fa-solid fa-rss" style="color:#3d5afe;margin-right:6px"></i>Импорт из YML-фида</h5>
    <p class="subtitle">Поддерживается формат Яндекс.Маркет. Товары группируются по group_id, изображения скачиваются автоматически.</p>

    <div class="hint-box">
      Изображения скачиваются только для <b>новых</b> товаров. При повторном импорте цены и категории обновляются.
    </div>

    <label class="form-label">URL фида</label>
    <div style="display:flex;gap:10px;margin-bottom:14px">
      <input type="text" id="yml-url" class="form-control"
             placeholder="https://example.com/feed.yml" style="flex:1">
      <button class="btn-import" onclick="startYmlImport()">
        <i class="fa-solid fa-play me-1"></i>Запустить
      </button>
    </div>

    <div id="yml-status" class="status-badge"></div>
    <div id="yml-log" class="log-box"></div>
  </div>

  <!-- ── Excel ── -->
  <div class="import-card">
    <h5><i class="fa-solid fa-file-excel" style="color:#1a6b3c;margin-right:6px"></i>Импорт из Excel</h5>
    <p class="subtitle">Загрузите файл .xlsx в формате шаблона. Скачайте шаблон и заполните его перед загрузкой.</p>

    <div class="hint-box">
      Скачайте шаблон, заполните данные и загрузите обратно. URL фотографий указываются в последней колонке через запятую.
    </div>

    <div style="display:flex;align-items:center;gap:12px;margin-bottom:18px;flex-wrap:wrap">
      <a class="btn-template" href="/admin-api/import/excel/template" download="import_template.xlsx">
        <i class="fa-solid fa-download"></i> Скачать шаблон
      </a>
      <span style="font-size:12.5px;color:#6c757d">Заполните и загрузите обратно →</span>
    </div>

    <label class="form-label">Excel-файл (.xlsx)</label>
    <div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap">
      <input type="file" id="excel-file" class="form-control" accept=".xlsx" style="flex:1;min-width:200px">
      <button class="btn-import" onclick="startExcelImport()">
        <i class="fa-solid fa-upload me-1"></i>Загрузить
      </button>
    </div>

    <div id="excel-status" class="status-badge"></div>
    <div id="excel-log" class="log-box"></div>
  </div>
</div>

<script>
// Загрузить username
fetch('/admin-api/me', {credentials:'include'}).then(r => r.ok ? r.json() : null).then(d => {
  if (d && d.username) {
    document.getElementById('nav-username').style.display = 'flex';
    document.getElementById('nav-uname').textContent = d.username;
  }
});

function showStatus(prefix, status, data) {
  const el = document.getElementById(prefix + '-status');
  const log = document.getElementById(prefix + '-log');
  el.style.display = 'inline-flex';
  el.className = 'status-badge status-' + status;
  if (status === 'running') {
    el.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Импорт запущен...';
  } else if (status === 'success') {
    el.innerHTML = '<i class="fa-solid fa-check-circle"></i> Готово: +'
      + data.products_added + ' товаров, ~' + data.products_updated + ' обновлено, '
      + data.images_downloaded + ' фото';
  } else {
    el.innerHTML = '<i class="fa-solid fa-times-circle"></i> Ошибка';
  }
  if (data && (data.log || data.error)) {
    log.style.display = 'block';
    log.textContent = (data.error ? 'ОШИБКА: ' + data.error + '\\n\\n' : '') + (data.log || '');
  }
}

function pollStatus(prefix, importId) {
  const interval = setInterval(async () => {
    const r = await fetch('/admin-api/import/' + importId + '/status', {credentials:'include'});
    if (!r.ok) return;
    const d = await r.json();
    if (d.status !== 'running') {
      clearInterval(interval);
      showStatus(prefix, d.status, d);
    }
  }, 1500);
}

async function startYmlImport() {
  const url = document.getElementById('yml-url').value.trim();
  if (!url) { alert('Введите URL фида'); return; }
  showStatus('yml', 'running', {});
  const r = await fetch('/admin-api/import/yml', {
    method: 'POST',
    credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({url}),
  });
  if (!r.ok) { showStatus('yml', 'failed', {error: await r.text()}); return; }
  const d = await r.json();
  pollStatus('yml', d.import_id);
}

async function startExcelImport() {
  const file = document.getElementById('excel-file').files[0];
  if (!file) { alert('Выберите файл'); return; }
  showStatus('excel', 'running', {});
  const fd = new FormData();
  fd.append('file', file);
  const r = await fetch('/admin-api/import/excel', {
    method: 'POST',
    credentials: 'include',
    body: fd,
  });
  if (!r.ok) { showStatus('excel', 'failed', {error: await r.text()}); return; }
  const d = await r.json();
  pollStatus('excel', d.import_id);
}
</script>
</body>
</html>"""
