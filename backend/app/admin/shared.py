"""Общие компоненты для кастомных страниц админки: навбар, стили, JS-константы."""

from __future__ import annotations


def _topnav(active: str = "") -> str:
    """Возвращает HTML топ-навбара. active: 'dashboard'|'orders'|'crm'|'shop'|'system'"""
    def _cls(key: str) -> str:
        return "ct-nav-link active" if active == key else "ct-nav-link"
    def _item_cls(key: str) -> str:
        return "ct-dropdown-item active" if active == key else "ct-dropdown-item"

    ord_cls = 'ct-nav-link active' if active in ('orders-active', 'orders-history', 'order') else 'ct-nav-link'
    return f"""
<div class="ct-topnav">
  <a class="ct-brand" href="/admin/dashboard">🍵 Чайное Дерево</a>
  <div class="ct-desktop-nav" style="display:flex;align-items:center;gap:4px;flex:1">
    <div class="ct-nav-item">
      <a class="{_cls('dashboard')}" href="/admin/dashboard"><i class="fa-solid fa-chart-line"></i>Дашборд</a>
    </div>
    <div class="ct-sep"></div>
    <div class="ct-nav-item ct-dropdown">
      <span class="{ord_cls}"><i class="fa-solid fa-box"></i>Заказы <span class="ct-dropdown-arrow">▾</span></span>
      <div class="ct-dropdown-menu">
        <a class="{_item_cls('orders-active')}" href="/crm/orders/active">Текущие заказы</a>
        <a class="{_item_cls('orders-history')}" href="/crm/orders/history">История заказов</a>
      </div>
    </div>
    <div class="ct-nav-item ct-dropdown">
      <span class="ct-nav-link"><i class="fa-solid fa-users"></i>CRM <span class="ct-dropdown-arrow">▾</span></span>
      <div class="ct-dropdown-menu">
        <a class="ct-dropdown-item" href="/admin/user/list">Клиенты</a>
      </div>
    </div>
    <div class="ct-nav-item ct-dropdown">
      <span class="ct-nav-link"><i class="fa-solid fa-store"></i>Настройки <span class="ct-dropdown-arrow">▾</span></span>
      <div class="ct-dropdown-menu">
        <a class="ct-dropdown-item" href="/admin/product/list">Товары</a>
        <a class="ct-dropdown-item" href="/admin/category/list">Категории</a>
        <a class="ct-dropdown-item" href="/admin/banner/list">Баннеры</a>
        <a class="{_item_cls('about')}" href="/crm/about">О нас</a>
        <a class="ct-dropdown-item" href="/admin/pickup-point/list">Самовывоз</a>
        <a class="ct-dropdown-item" href="/admin/notification-target/list">Уведомления</a>
        <a class="{_item_cls('bonus')}" href="/admin/bonus-settings">🎁 Бонусная система</a>
      </div>
    </div>
    <div class="ct-nav-item ct-dropdown">
      <span class="ct-nav-link"><i class="fa-solid fa-gear"></i>Система <span class="ct-dropdown-arrow">▾</span></span>
      <div class="ct-dropdown-menu">
        <a class="ct-dropdown-item" href="/admin/admin-user/list">Администраторы</a>
        <a class="ct-dropdown-item" href="/admin/yml-import/list">YML-импорты</a>
        <a class="ct-dropdown-item" href="/admin/payment-event/list">Платежи</a>
      </div>
    </div>
    <div class="ct-logout">
      <span id="dash-user" style="font-size:13px;color:#6c757d;display:flex;align-items:center;gap:6px"></span>
      <a href="/admin/logout" title="Выйти"><i class="fa-solid fa-right-from-bracket me-1"></i>Выйти</a>
    </div>
  </div>
  <button class="ct-burger" id="ct-burger" onclick="ctToggleMobileMenu()" aria-label="Меню">
    <span></span><span></span><span></span>
  </button>
</div>

<div class="ct-mobile-menu" id="ct-mobile-menu">
  <a class="ct-mobile-link{' active' if active == 'dashboard' else ''}" href="/admin/dashboard"><i class="fa-solid fa-chart-line"></i>Дашборд</a>
  <div class="ct-mobile-divider"></div>
  <div class="ct-mobile-section">Заказы</div>
  <a class="ct-mobile-link{' active' if active == 'orders-active' else ''}" href="/crm/orders/active"><i class="fa-solid fa-hourglass-half"></i>Текущие заказы</a>
  <a class="ct-mobile-link{' active' if active == 'orders-history' else ''}" href="/crm/orders/history"><i class="fa-solid fa-clock-rotate-left"></i>История заказов</a>
  <div class="ct-mobile-divider"></div>
  <div class="ct-mobile-section">CRM</div>
  <a class="ct-mobile-link" href="/admin/user/list"><i class="fa-solid fa-users"></i>Клиенты</a>
  <div class="ct-mobile-divider"></div>
  <div class="ct-mobile-section">Настройки</div>
  <a class="ct-mobile-link" href="/admin/product/list"><i class="fa-solid fa-box-open"></i>Товары</a>
  <a class="ct-mobile-link" href="/admin/category/list"><i class="fa-solid fa-tags"></i>Категории</a>
  <a class="ct-mobile-link" href="/admin/banner/list"><i class="fa-solid fa-image"></i>Баннеры</a>
  <a class="ct-mobile-link{' active' if active == 'about' else ''}" href="/crm/about"><i class="fa-solid fa-circle-info"></i>О нас</a>
  <a class="ct-mobile-link" href="/admin/pickup-point/list"><i class="fa-solid fa-location-dot"></i>Самовывоз</a>
  <a class="ct-mobile-link" href="/admin/notification-target/list"><i class="fa-solid fa-bell"></i>Уведомления</a>
  <a class="ct-mobile-link{' active' if active == 'bonus' else ''}" href="/admin/bonus-settings"><i class="fa-solid fa-gift"></i>Бонусная система</a>
  <div class="ct-mobile-divider"></div>
  <div class="ct-mobile-section">Система</div>
  <a class="ct-mobile-link" href="/admin/admin-user/list"><i class="fa-solid fa-shield-halved"></i>Администраторы</a>
  <a class="ct-mobile-link" href="/admin/yml-import/list"><i class="fa-solid fa-file-import"></i>YML-импорты</a>
  <a class="ct-mobile-link" href="/admin/payment-event/list"><i class="fa-solid fa-credit-card"></i>Платежи</a>
  <div class="ct-mobile-divider"></div>
  <a class="ct-mobile-logout" href="/admin/logout"><i class="fa-solid fa-right-from-bracket"></i>Выйти</a>
</div>

<script>
fetch('/admin-api/me',{{credentials:'include'}}).then(function(r){{return r.ok?r.json():null;}}).then(function(d){{
  if(!d) return;
  var el=document.getElementById('dash-user');
  if(el) el.innerHTML='<i class="fa-solid fa-circle-user" style="color:#1a6b3c"></i>'+d.username;
}});
function ctToggleMobileMenu(){{
  var menu=document.getElementById('ct-mobile-menu');
  var burger=document.getElementById('ct-burger');
  var open=menu.classList.toggle('open');
  burger.classList.toggle('open',open);
  document.body.style.overflow=open?'hidden':'';
}}
document.addEventListener('DOMContentLoaded',function(){{
  document.querySelectorAll('.ct-mobile-link,.ct-mobile-logout').forEach(function(a){{
    a.addEventListener('click',function(){{
      document.getElementById('ct-mobile-menu').classList.remove('open');
      document.getElementById('ct-burger').classList.remove('open');
      document.body.style.overflow='';
    }});
  }});
}});
</script>"""


_BASE_CSS = """
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<style>
body { background:#f4f6fb; min-height:100vh; }
.stat-card { border-radius:14px; border:none; box-shadow:0 2px 10px rgba(0,0,0,.06); transition:transform .15s,box-shadow .15s; }
.stat-card:hover { transform:translateY(-2px); box-shadow:0 6px 20px rgba(0,0,0,.1); }
.stat-icon { width:46px; height:46px; border-radius:12px; display:flex; align-items:center; justify-content:center; font-size:19px; flex-shrink:0; }
.stat-value { font-size:1.85rem; font-weight:800; line-height:1.1; letter-spacing:-.5px; }
.stat-label { font-size:.79rem; color:#6c757d; margin-top:3px; }
.section-title { font-size:14.5px; font-weight:700; color:#212529; margin-bottom:0; }
.chart-card { border-radius:14px; border:none; box-shadow:0 2px 10px rgba(0,0,0,.06); }
.period-btn { border-radius:8px !important; font-size:12.5px; padding:4px 12px; }
.period-btn.active { background:#3d5afe !important; border-color:#3d5afe !important; color:#fff !important; }
.order-warn { background:#fffbf0 !important; }
.order-danger { background:#fff5f5 !important; }
.age-pill { font-size:11px; border-radius:20px; padding:2px 9px; font-weight:600; display:inline-block; }
.age-ok { background:#e8f5e9; color:#2e7d32; }
.age-warn { background:#fff8e1; color:#e65100; }
.age-danger { background:#ffebee; color:#c62828; }
.order-num { font-weight:700; color:#3d5afe; text-decoration:none; }
.order-num:hover { text-decoration:underline; }
.medal { font-size:16px; }
.status-badge { font-size:11px; border-radius:20px; padding:2px 10px; font-weight:600; display:inline-block; }
.status-new        { background:#e3f2fd; color:#1565c0; }
.status-assembling { background:#fff3e0; color:#e65100; }
.status-ready      { background:#e8f5e9; color:#2e7d32; }
.status-awaiting_payment { background:#fff8e1; color:#f57f17; }
.status-in_delivery { background:#e0f7fa; color:#00695c; }
.status-at_pvz     { background:#f3e5f5; color:#6a1b9a; }
.status-delivered  { background:#e8f5e9; color:#1b5e20; }
.status-cancelled  { background:#fdecea; color:#b71c1c; }

/* Navbar */
.ct-topnav { background:#fff; border-bottom:1px solid #e9ecef; box-shadow:0 1px 8px rgba(0,0,0,.06);
  height:56px; display:flex; align-items:center; padding:0 24px; gap:4px; position:sticky; top:0; z-index:1000; }
.ct-brand { font-weight:800; font-size:16px; color:#212529; text-decoration:none; margin-right:16px; white-space:nowrap; }
.ct-brand:hover { color:#3d5afe; text-decoration:none; }
.ct-nav-item { position:relative; }
.ct-nav-link { display:flex; align-items:center; gap:6px; padding:0 12px; height:56px; font-size:13.5px;
  font-weight:500; color:#495057; text-decoration:none; border-bottom:2px solid transparent;
  transition:all .15s; white-space:nowrap; cursor:pointer; background:none; border-top:none; border-left:none; border-right:none; }
.ct-nav-link:hover,.ct-nav-link.active { color:#3d5afe; border-bottom-color:#3d5afe; text-decoration:none; }
.ct-nav-link.active { font-weight:600; }
.ct-nav-link i { font-size:14px; color:#1a6b3c; }
.ct-sep { width:1px; height:20px; background:#dee2e6; margin:0 8px; flex-shrink:0; }
.ct-logout { margin-left:auto; display:flex; align-items:center; gap:8px; }
.ct-logout a { font-size:13px; color:#6c757d; text-decoration:none; padding:6px 12px;
  border-radius:8px; border:1px solid #dee2e6; transition:all .15s; }
.ct-logout a:hover { color:#3d5afe; border-color:#3d5afe; }
.ct-dropdown { position:relative; }
.ct-dropdown-menu { display:none; position:absolute; top:54px; left:0; background:#fff;
  border:1px solid #e9ecef; border-radius:10px; box-shadow:0 8px 24px rgba(0,0,0,.1);
  min-width:200px; padding:6px 0; z-index:1001; }
.ct-dropdown:hover .ct-dropdown-menu { display:block; }
.ct-dropdown-item { display:block; padding:9px 16px; font-size:13px; color:#495057; text-decoration:none; transition:all .1s; }
.ct-dropdown-item:hover,.ct-dropdown-item.active { background:#f0f4ff; color:#3d5afe; text-decoration:none; }
.ct-dropdown-arrow { font-size:10px; opacity:.5; margin-left:2px; }

/* Бургер */
.ct-burger { display:none; margin-left:auto; background:none; border:none; cursor:pointer;
  padding:8px; flex-direction:column; gap:5px; border-radius:8px; transition:background .15s; }
.ct-burger:hover { background:#f0f4ff; }
.ct-burger span { display:block; width:22px; height:2px; background:#495057; border-radius:2px; transition:all .25s; }
.ct-burger.open span:nth-child(1) { transform:translateY(7px) rotate(45deg); }
.ct-burger.open span:nth-child(2) { opacity:0; }
.ct-burger.open span:nth-child(3) { transform:translateY(-7px) rotate(-45deg); }
/* Мобильное меню */
.ct-mobile-menu { display:none; position:fixed; top:56px; left:0; right:0; bottom:0;
  background:#fff; z-index:999; overflow-y:auto; padding:8px 0 24px;
  border-top:1px solid #e9ecef; box-shadow:0 8px 24px rgba(0,0,0,.1); }
.ct-mobile-menu.open { display:block; }
.ct-mobile-link { display:flex; align-items:center; gap:12px; padding:14px 20px;
  font-size:15px; font-weight:500; color:#212529; text-decoration:none;
  border-bottom:1px solid #f5f6fa; transition:background .1s; }
.ct-mobile-link:hover,.ct-mobile-link.active { background:#f0f4ff; color:#3d5afe; text-decoration:none; }
.ct-mobile-link i { width:20px; text-align:center; color:#1a6b3c; font-size:15px; }
.ct-mobile-link.active i { color:#3d5afe; }
.ct-mobile-section { padding:16px 20px 6px; font-size:10px; font-weight:700;
  color:#8c9aad; text-transform:uppercase; letter-spacing:.6px; }
.ct-mobile-divider { height:1px; background:#f0f2f5; margin:8px 0; }
.ct-mobile-logout { display:flex; align-items:center; gap:12px; padding:14px 20px;
  font-size:15px; color:#dc3545; text-decoration:none; font-weight:500; }
.ct-mobile-logout i { width:20px; text-align:center; }
@media (max-width: 768px) {
  .ct-topnav { padding:0 16px; height:56px; }
  .ct-desktop-nav { display:none !important; }
  .ct-sep { display:none !important; }
  .ct-logout { display:none !important; }
  .ct-burger { display:flex !important; }
  .container-fluid { padding-left:12px !important; padding-right:12px !important; }
  .stat-value { font-size:1.4rem !important; }
  .table th, .table td { font-size:11px !important; padding:6px 8px !important; }
  .card { border-radius:10px !important; }
}
</style>
"""

_STATUS_LABELS_JS = """
var SL = {
  'new':'🆕 Новый','assembling':'📦 Собираем','ready':'✅ Готов',
  'awaiting_payment':'💳 Ожидает оплаты','in_delivery':'🚚 В доставке',
  'at_pvz':'🏪 В ПВЗ','delivered':'🎉 Доставлен','cancelled':'❌ Отменён'
};
var DL = {'pickup':'Самовывоз','courier':'Курьер','pvz':'ПВЗ'};
function fmt(n){ return new Intl.NumberFormat('ru-RU').format(Math.round(n||0)); }
function fmtDt(s){ var d=new Date(s); return d.toLocaleDateString('ru-RU',{day:'2-digit',month:'2-digit',year:'2-digit'})+' '+d.toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'}); }
function fmtDate(s){ var d=new Date(s); return d.toLocaleDateString('ru-RU',{day:'2-digit',month:'2-digit',year:'numeric'}); }
function agePill(h){ return h>=3?'<span class="age-pill age-danger"><i class="fa-solid fa-triangle-exclamation me-1"></i>'+Math.round(h)+' ч</span>':h>=1?'<span class="age-pill age-warn">'+Math.round(h)+' ч</span>':'<span class="age-pill age-ok">< 1 ч</span>'; }
function statusBadge(s){ return '<span class="status-badge status-'+s+'">'+(SL[s]||s)+'</span>'; }
"""


def _render(template: str, active: str) -> str:
    return (
        template
        .replace("{BASE_CSS}", _BASE_CSS)
        .replace("{TOPNAV}", _topnav(active))
        .replace("{STATUS_LABELS}", _STATUS_LABELS_JS)
    )
