"""Дашборд администратора — главная страница с аналитикой."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.requests import Request
from starlette.responses import RedirectResponse

# ---------- Общий навбар ----------

def _topnav(active: str = "") -> str:
    """Возвращает HTML топ-навбара. active: 'dashboard'|'orders'|'crm'|'shop'|'system'"""
    def _cls(key: str) -> str:
        return "ct-nav-link active" if active == key else "ct-nav-link"
    def _item_cls(key: str) -> str:
        return "ct-dropdown-item active" if active == key else "ct-dropdown-item"

    return f"""
<div class="ct-topnav">
  <a class="ct-brand" href="/admin/dashboard">🍵 Чайное Дерево</a>
  <div class="ct-nav-item">
    <a class="{_cls('dashboard')}" href="/admin/dashboard"><i class="fa-solid fa-chart-line"></i>Дашборд</a>
  </div>
  <div class="ct-sep"></div>
  <div class="ct-nav-item ct-dropdown">
    <span class="{'ct-nav-link active' if active in ('orders-active','orders-history','order') else 'ct-nav-link'}">
      <i class="fa-solid fa-box"></i>Заказы <span class="ct-dropdown-arrow">▾</span>
    </span>
    <div class="ct-dropdown-menu">
      <a class="{_item_cls('orders-active')}" href="/crm/orders/active">Текущие заказы</a>
      <a class="{_item_cls('orders-history')}" href="/crm/orders/history">История заказов</a>
    </div>
  </div>
  <div class="ct-nav-item ct-dropdown">
    <span class="ct-nav-link"><i class="fa-solid fa-users"></i>CRM <span class="ct-dropdown-arrow">▾</span></span>
    <div class="ct-dropdown-menu">
      <a class="ct-dropdown-item" href="/admin/user/list">Клиенты</a>
      <a class="ct-dropdown-item" href="/admin/notification-target/list">Уведомления</a>
    </div>
  </div>
  <div class="ct-nav-item ct-dropdown">
    <span class="ct-nav-link"><i class="fa-solid fa-store"></i>Настройки <span class="ct-dropdown-arrow">▾</span></span>
    <div class="ct-dropdown-menu">
      <a class="ct-dropdown-item" href="/admin/product/list">Товары</a>
      <a class="ct-dropdown-item" href="/admin/category/list">Категории</a>
      <a class="ct-dropdown-item" href="/admin/banner/list">Баннеры</a>
      <a class="{_item_cls('about')}" href="/crm/about">О нас</a>
      <a class="ct-dropdown-item" href="/admin/faq-item/list">FAQ</a>
      <a class="ct-dropdown-item" href="/admin/pickup-point/list">Самовывоз</a>
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
<script>
fetch('/admin-api/me',{{credentials:'include'}}).then(function(r){{return r.ok?r.json():null;}}).then(function(d){{
  if(!d) return;
  var el=document.getElementById('dash-user');
  if(el) el.innerHTML='<i class="fa-solid fa-circle-user" style="color:#1a6b3c"></i>'+d.username;
}});
</script>"""

# ---------- Общие стили ----------

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

# ---------- ДАШБОРД ----------

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Дашборд — Чайное Дерево</title>
{BASE_CSS}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
</head>
<body>
{TOPNAV}
<div class="container-fluid px-4 py-4" style="max-width:1400px">

  <div class="row g-3 mb-4">
    <div class="col-6 col-sm-3">
      <div class="card stat-card p-3">
        <div class="d-flex align-items-center gap-3">
          <div class="stat-icon" style="background:#fff3e0"><i class="fa-solid fa-hourglass-half" style="color:#ff9800"></i></div>
          <div><div class="stat-value" id="s-pending">—</div><div class="stat-label">Ждут обработки</div></div>
        </div>
      </div>
    </div>
    <div class="col-6 col-sm-3">
      <div class="card stat-card p-3">
        <div class="d-flex align-items-center gap-3">
          <div class="stat-icon" style="background:#e8f5e9"><i class="fa-solid fa-basket-shopping" style="color:#43a047"></i></div>
          <div><div class="stat-value" id="s-today">—</div><div class="stat-label">Заказов сегодня</div></div>
        </div>
      </div>
    </div>
    <div class="col-6 col-sm-3">
      <div class="card stat-card p-3">
        <div class="d-flex align-items-center gap-3">
          <div class="stat-icon" style="background:#e3f2fd"><i class="fa-solid fa-ruble-sign" style="color:#1e88e5"></i></div>
          <div><div class="stat-value" id="s-revenue">—</div><div class="stat-label">Выручка за период</div></div>
        </div>
      </div>
    </div>
    <div class="col-6 col-sm-3">
      <div class="card stat-card p-3">
        <div class="d-flex align-items-center gap-3">
          <div class="stat-icon" style="background:#f3e5f5"><i class="fa-solid fa-circle-check" style="color:#8e24aa"></i></div>
          <div><div class="stat-value" id="s-paid">—</div><div class="stat-label">Выполнено за период</div></div>
        </div>
      </div>
    </div>
  </div>

  <div class="row g-4 mb-4">
    <div class="col-12 col-xl-8">
      <div class="card chart-card p-4">
        <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
          <div class="section-title">📈 Динамика заказов</div>
          <div class="btn-group btn-group-sm" id="period-btns">
            <button class="btn btn-outline-secondary period-btn" onclick="setPeriod(this,7)">7 дней</button>
            <button class="btn btn-outline-secondary period-btn active" onclick="setPeriod(this,30)">30 дней</button>
            <button class="btn btn-outline-secondary period-btn" onclick="setPeriod(this,90)">90 дней</button>
          </div>
        </div>
        <div style="position:relative;height:260px"><canvas id="ordersChart"></canvas></div>
      </div>
    </div>
    <div class="col-12 col-xl-4">
      <div class="card chart-card p-4 h-100">
        <div class="section-title mb-3">🏆 Топ клиентов</div>
        <table class="table mb-0">
          <thead><tr><th></th><th>Клиент</th><th class="text-center">Заказов</th><th class="text-end">Выручка</th></tr></thead>
          <tbody id="top-body"><tr><td colspan="4" class="text-center text-muted py-3">Загрузка...</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="card chart-card p-4">
    <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
      <div class="section-title">⏳ Текущие заказы (требуют обработки)</div>
      <div class="d-flex gap-2">
        <a href="/crm/orders/active" class="btn btn-sm btn-outline-primary">Все текущие →</a>
        <button class="btn btn-sm btn-outline-secondary" onclick="load()"><i class="fa-solid fa-rotate-right me-1"></i>Обновить</button>
      </div>
    </div>
    <div class="table-responsive">
      <table class="table table-hover mb-0">
        <thead><tr><th>Номер</th><th>Клиент</th><th>Сумма</th><th>Статус</th><th>Ожидает</th><th>Создан</th><th></th></tr></thead>
        <tbody id="pending-body"><tr><td colspan="7" class="text-center text-muted py-3">Загрузка...</td></tr></tbody>
      </table>
    </div>
  </div>

</div>
<script>
{STATUS_LABELS}
var chart = null, period = 30;
function setPeriod(btn, p){
  period = p;
  document.querySelectorAll('.period-btn').forEach(function(b){ b.classList.remove('active'); });
  btn.classList.add('active');
  load();
}
function renderChart(rows){
  var labels=rows.map(function(r){return r.day.slice(5).replace('-','/');});
  var counts=rows.map(function(r){return r.count;});
  var revs=rows.map(function(r){return r.revenue;});
  var ctx=document.getElementById('ordersChart').getContext('2d');
  if(chart) chart.destroy();
  chart=new Chart(ctx,{data:{labels:labels,datasets:[
    {type:'bar',label:'Заказов',data:counts,backgroundColor:'rgba(61,90,254,.14)',borderColor:'#3d5afe',borderWidth:2,borderRadius:5,yAxisID:'y'},
    {type:'line',label:'Выручка (₽)',data:revs,borderColor:'#ff9800',backgroundColor:'rgba(255,152,0,.07)',borderWidth:2,pointRadius:3,fill:true,tension:.4,yAxisID:'y1'}
  ]},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
    plugins:{legend:{position:'top',labels:{font:{size:12}}}},
    scales:{y:{position:'left',title:{display:true,text:'Заказов'},beginAtZero:true,ticks:{stepSize:1}},
            y1:{position:'right',title:{display:true,text:'Выручка ₽'},beginAtZero:true,grid:{drawOnChartArea:false}}}}});
}
function renderPending(orders){
  var tb=document.getElementById('pending-body');
  if(!orders.length){tb.innerHTML='<tr><td colspan="7" class="text-center py-4">✅ Нет текущих заказов</td></tr>';return;}
  tb.innerHTML=orders.map(function(o){
    var h=o.age_hours;
    var rc=h>=3?'order-danger':h>=1?'order-warn':'';
    return '<tr class="'+rc+'"><td><a class="order-num" href="/crm/order/'+o.id+'">'+o.number+'</a></td>'
      +'<td>'+o.client+'</td><td><b>'+fmt(o.total)+' ₽</b></td>'
      +'<td>'+statusBadge(o.status)+'</td>'
      +'<td>'+agePill(h)+'</td>'
      +'<td><small class="text-muted">'+fmtDt(o.created_at)+'</small></td>'
      +'<td><a href="/crm/order/'+o.id+'" class="btn btn-sm btn-outline-primary" style="font-size:12px;padding:2px 10px">→</a></td></tr>';
  }).join('');
}
function load(){
  fetch('/admin-api/dashboard/data?period='+period,{credentials:'include'})
    .then(function(r){if(!r.ok) throw new Error('HTTP '+r.status);return r.json();})
    .then(function(d){
      document.getElementById('s-pending').textContent=d.stats.pending_count;
      document.getElementById('s-today').textContent=d.stats.today_count;
      document.getElementById('s-revenue').textContent=fmt(d.stats.period_revenue)+' ₽';
      document.getElementById('s-paid').textContent=d.stats.period_paid_count;
      renderChart(d.chart);
      renderPending(d.pending_orders);
      var tb=document.getElementById('top-body');
      var medals=['🥇','🥈','🥉'];
      tb.innerHTML=d.top_customers.length?d.top_customers.map(function(c,i){
        return '<tr><td class="medal">'+(medals[i]||(i+1)+'.')+'</td>'
          +'<td style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+c.name+'</td>'
          +'<td class="text-center">'+c.order_count+'</td>'
          +'<td class="text-end fw-bold">'+fmt(c.total_spent)+' ₽</td></tr>';
      }).join(''):'<tr><td colspan="4" class="text-center text-muted py-3">Нет данных</td></tr>';
    })
    .catch(function(err){
      document.getElementById('pending-body').innerHTML='<tr><td colspan="7" class="text-center text-danger py-3">Ошибка: '+err.message+'</td></tr>';
    });
}
document.addEventListener('DOMContentLoaded', load);
</script>
</body>
</html>"""

# ---------- ТЕКУЩИЕ ЗАКАЗЫ ----------

ACTIVE_ORDERS_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Текущие заказы — Чайное Дерево</title>
{BASE_CSS}
</head>
<body>
{TOPNAV}
<div class="container-fluid px-4 py-4" style="max-width:1400px">

  <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
    <h5 class="section-title mb-0">⏳ Текущие заказы</h5>
    <button class="btn btn-sm btn-outline-secondary" onclick="load()"><i class="fa-solid fa-rotate-right me-1"></i>Обновить</button>
  </div>

  <div class="card chart-card p-4">
    <div class="table-responsive">
      <table class="table table-hover mb-0">
        <thead>
          <tr>
            <th>Номер</th><th>Клиент</th><th>Состав</th><th>Тип</th>
            <th>Статус</th><th>Ожидает</th><th>Создан</th><th></th>
          </tr>
        </thead>
        <tbody id="orders-body">
          <tr><td colspan="8" class="text-center text-muted py-4">Загрузка...</td></tr>
        </tbody>
      </table>
    </div>
    <div id="empty-msg" style="display:none" class="text-center py-5 text-muted">
      <i class="fa-solid fa-circle-check fa-2x mb-3" style="color:#1b873f"></i>
      <p class="mb-0">Все заказы обработаны!</p>
    </div>
  </div>

</div>
<script>
{STATUS_LABELS}
function load(){
  fetch('/admin-api/orders/active',{credentials:'include'})
    .then(function(r){if(!r.ok) throw new Error('HTTP '+r.status);return r.json();})
    .then(function(d){
      var tb=document.getElementById('orders-body');
      var em=document.getElementById('empty-msg');
      if(!d.orders.length){
        tb.innerHTML='';
        em.style.display='block';
        return;
      }
      em.style.display='none';
      tb.innerHTML=d.orders.map(function(o){
        var h=o.age_hours;
        var rc=h>=3?'order-danger':h>=1?'order-warn':'';
        return '<tr class="'+rc+'"><td><a class="order-num" href="/crm/order/'+o.id+'">'+o.number+'</a></td>'
          +'<td style="max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+o.client+'</td>'
          +'<td style="max-width:200px;font-size:12px;color:#5a6478">'+o.items_short+'</td>'
          +'<td><small>'+(DL[o.delivery_type]||'—')+'</small></td>'
          +'<td>'+statusBadge(o.status)+'</td>'
          +'<td>'+agePill(h)+'</td>'
          +'<td><small class="text-muted">'+fmtDt(o.created_at)+'</small></td>'
          +'<td><a href="/crm/order/'+o.id+'" class="btn btn-sm btn-outline-primary" style="font-size:12px;padding:2px 10px">→</a></td></tr>';
      }).join('');
    })
    .catch(function(err){
      document.getElementById('orders-body').innerHTML='<tr><td colspan="8" class="text-center text-danger py-3">Ошибка: '+err.message+'</td></tr>';
    });
}
document.addEventListener('DOMContentLoaded', load);
</script>
</body>
</html>"""

# ---------- ИСТОРИЯ ЗАКАЗОВ ----------

HISTORY_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>История заказов — Чайное Дерево</title>
{BASE_CSS}
</head>
<body>
{TOPNAV}
<div class="container-fluid px-4 py-4" style="max-width:1400px">

  <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
    <h5 class="section-title mb-0">📦 История заказов</h5>
    <div class="d-flex gap-2 align-items-center">
      <div class="btn-group btn-group-sm" id="period-btns">
        <button class="btn btn-outline-secondary period-btn" onclick="setPeriod(this,7)">7 дней</button>
        <button class="btn btn-outline-secondary period-btn active" onclick="setPeriod(this,30)">30 дней</button>
        <button class="btn btn-outline-secondary period-btn" onclick="setPeriod(this,90)">90 дней</button>
        <button class="btn btn-outline-secondary period-btn" onclick="setPeriod(this,365)">Год</button>
      </div>
      <button class="btn btn-sm btn-outline-secondary" onclick="load()"><i class="fa-solid fa-rotate-right me-1"></i>Обновить</button>
    </div>
  </div>

  <div class="row g-3 mb-4">
    <div class="col-6 col-sm-3">
      <div class="card stat-card p-3">
        <div class="d-flex align-items-center gap-3">
          <div class="stat-icon" style="background:#e8f5e9"><i class="fa-solid fa-circle-check" style="color:#1b873f"></i></div>
          <div><div class="stat-value" id="s-count">—</div><div class="stat-label">Завершено</div></div>
        </div>
      </div>
    </div>
    <div class="col-6 col-sm-3">
      <div class="card stat-card p-3">
        <div class="d-flex align-items-center gap-3">
          <div class="stat-icon" style="background:#e3f2fd"><i class="fa-solid fa-ruble-sign" style="color:#1e88e5"></i></div>
          <div><div class="stat-value" id="s-revenue">—</div><div class="stat-label">Выручка</div></div>
        </div>
      </div>
    </div>
    <div class="col-6 col-sm-3">
      <div class="card stat-card p-3">
        <div class="d-flex align-items-center gap-3">
          <div class="stat-icon" style="background:#fdecea"><i class="fa-solid fa-ban" style="color:#d32f2f"></i></div>
          <div><div class="stat-value" id="s-cancelled">—</div><div class="stat-label">Отменено</div></div>
        </div>
      </div>
    </div>
    <div class="col-6 col-sm-3">
      <div class="card stat-card p-3">
        <div class="d-flex align-items-center gap-3">
          <div class="stat-icon" style="background:#f3e5f5"><i class="fa-solid fa-chart-simple" style="color:#8e24aa"></i></div>
          <div><div class="stat-value" id="s-avg">—</div><div class="stat-label">Средний чек</div></div>
        </div>
      </div>
    </div>
  </div>

  <div class="card chart-card p-4">
    <div class="table-responsive">
      <table class="table table-hover mb-0">
        <thead>
          <tr>
            <th>Номер</th><th>Клиент</th><th>Состав заказа</th>
            <th>Дата</th><th>Сумма</th><th>Статус</th><th>Трек / оплата</th>
          </tr>
        </thead>
        <tbody id="history-body">
          <tr><td colspan="7" class="text-center text-muted py-4">Загрузка...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

</div>
<script>
{STATUS_LABELS}
var period = 30;
function setPeriod(btn, p){
  period = p;
  document.querySelectorAll('.period-btn').forEach(function(b){ b.classList.remove('active'); });
  btn.classList.add('active');
  load();
}
function load(){
  fetch('/admin-api/orders/history?period='+period,{credentials:'include'})
    .then(function(r){if(!r.ok) throw new Error('HTTP '+r.status);return r.json();})
    .then(function(d){
      document.getElementById('s-count').textContent=d.stats.delivered_count;
      document.getElementById('s-revenue').textContent=fmt(d.stats.revenue)+' ₽';
      document.getElementById('s-cancelled').textContent=d.stats.cancelled_count;
      document.getElementById('s-avg').textContent=d.stats.avg_order?fmt(d.stats.avg_order)+' ₽':'—';
      var tb=document.getElementById('history-body');
      if(!d.orders.length){
        tb.innerHTML='<tr><td colspan="7" class="text-center py-5 text-muted">Нет заказов за период</td></tr>';
        return;
      }
      tb.innerHTML=d.orders.map(function(o){
        var link='';
        if(o.tracking_link) link='<a href="'+o.tracking_link+'" target="_blank" class="btn btn-xs btn-outline-secondary" style="font-size:11px;padding:1px 8px">🚚 Трек</a>';
        else if(o.payment_link) link='<a href="'+o.payment_link+'" target="_blank" class="btn btn-xs btn-outline-secondary" style="font-size:11px;padding:1px 8px">💳 Оплата</a>';
        return '<tr><td><a class="order-num" href="/crm/order/'+o.id+'">'+o.number+'</a></td>'
          +'<td style="max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+o.client+'</td>'
          +'<td style="font-size:12px;color:#5a6478;max-width:220px">'+o.items_text+'</td>'
          +'<td><small>'+fmtDate(o.created_at)+'</small></td>'
          +'<td><b>'+fmt(o.total)+' ₽</b></td>'
          +'<td>'+statusBadge(o.status)+'</td>'
          +'<td>'+link+'</td></tr>';
      }).join('');
    })
    .catch(function(err){
      document.getElementById('history-body').innerHTML='<tr><td colspan="7" class="text-center text-danger py-3">Ошибка: '+err.message+'</td></tr>';
    });
}
document.addEventListener('DOMContentLoaded', load);
</script>
</body>
</html>"""


def _render(template: str, active: str) -> str:
    return template.replace("{BASE_CSS}", _BASE_CSS).replace("{TOPNAV}", _topnav(active)).replace("{STATUS_LABELS}", _STATUS_LABELS_JS)


# ---------- Данные ----------

async def _get_dashboard_data(period_days: int, demo: bool = False) -> dict:
    from sqlalchemy import func, select
    from sqlalchemy.orm import selectinload

    from app.db import get_session_factory
    from app.models.order import Order
    from app.models.user import User

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=period_days)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    def _demo(stmt):
        return stmt.where(Order.number.like("DEMO-%")) if demo else stmt

    async with get_session_factory()() as s:
        pr = await s.execute(_demo(
            select(Order).where(Order.status.notin_(["delivered", "cancelled"]))
            .options(selectinload(Order.user)).order_by(Order.created_at.asc())
        ))
        pending = pr.scalars().all()

        today_count = (await s.execute(_demo(select(func.count(Order.id)).where(Order.created_at >= today_start)))).scalar() or 0
        period_revenue = float((await s.execute(_demo(select(func.coalesce(func.sum(Order.total_amount), 0)).where(Order.created_at >= since, Order.status == "delivered")))).scalar() or 0)
        period_paid = (await s.execute(_demo(select(func.count(Order.id)).where(Order.created_at >= since, Order.status == "delivered")))).scalar() or 0

        chart_r = await s.execute(_demo(
            select(func.date(Order.created_at).label("day"), func.count(Order.id).label("count"), func.coalesce(func.sum(Order.total_amount), 0).label("revenue"))
            .where(Order.created_at >= since).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at))
        ))
        chart_rows = chart_r.all()

        top_r = await s.execute(
            select(User.first_name, User.last_name, User.username, func.count(Order.id).label("order_count"), func.coalesce(func.sum(Order.total_amount), 0).label("total_spent"))
            .join(Order, Order.user_id == User.id)
            .where(Order.status == "delivered", *([] if not demo else [Order.number.like("DEMO-%")]))
            .group_by(User.id, User.first_name, User.last_name, User.username)
            .order_by(func.sum(Order.total_amount).desc()).limit(10)
        )
        top_rows = top_r.all()

    def _name(f, l, u):
        full = f"{f or ''} {l or ''}".strip()
        return full or (f"@{u}" if u else "—")

    return {
        "stats": {"pending_count": len(pending), "today_count": today_count, "period_revenue": period_revenue, "period_paid_count": period_paid},
        "chart": [{"day": str(r.day), "count": r.count, "revenue": float(r.revenue)} for r in chart_rows],
        "pending_orders": [
            {"id": o.id, "number": o.number, "client": o.user.display_name if o.user else "—",
             "total": float(o.total_amount), "status": o.status,
             "created_at": o.created_at.isoformat(),
             "age_hours": (now - o.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600}
            for o in pending
        ],
        "top_customers": [{"name": _name(r.first_name, r.last_name, r.username), "order_count": r.order_count, "total_spent": float(r.total_spent)} for r in top_rows],
    }


async def _get_active_orders() -> dict:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.db import get_session_factory
    from app.models.delivery import DeliveryInfo
    from app.models.order import Order, OrderItem

    now = datetime.now(timezone.utc)

    async with get_session_factory()() as s:
        result = await s.execute(
            select(Order)
            .options(selectinload(Order.user), selectinload(Order.items), selectinload(Order.delivery_info))
            .where(Order.status.notin_(["delivered", "cancelled"]))
            .order_by(Order.created_at.asc())
        )
        orders = result.scalars().all()

    def _items_short(items):
        parts = [f"{oi.snapshot_name} {oi.snapshot_weight_g}г×{oi.quantity}" for oi in items]
        return ", ".join(parts[:3]) + ("…" if len(parts) > 3 else "")

    return {"orders": [
        {"id": o.id, "number": o.number,
         "client": o.user.display_name if o.user else "—",
         "items_short": _items_short(o.items),
         "delivery_type": o.delivery_info.type if o.delivery_info else "",
         "total": float(o.total_amount), "status": o.status,
         "created_at": o.created_at.isoformat(),
         "age_hours": (now - o.created_at.replace(tzinfo=timezone.utc)).total_seconds() / 3600}
        for o in orders
    ]}


async def _get_history(period_days: int) -> dict:
    from sqlalchemy import func, select
    from sqlalchemy.orm import selectinload

    from app.db import get_session_factory
    from app.models.order import Order

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=period_days)

    async with get_session_factory()() as s:
        result = await s.execute(
            select(Order)
            .options(selectinload(Order.user), selectinload(Order.items))
            .where(Order.status.in_(["delivered", "cancelled"]), Order.created_at >= since)
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()

        delivered = [o for o in orders if o.status == "delivered"]
        cancelled = [o for o in orders if o.status == "cancelled"]
        revenue = sum(float(o.total_amount) for o in delivered)
        avg = revenue / len(delivered) if delivered else 0

    def _items_text(items):
        return ", ".join(f"{oi.snapshot_name} {oi.snapshot_weight_g}г × {oi.quantity}" for oi in items)

    return {
        "stats": {
            "delivered_count": len(delivered),
            "cancelled_count": len(cancelled),
            "revenue": revenue,
            "avg_order": avg,
        },
        "orders": [
            {"id": o.id, "number": o.number,
             "client": o.user.display_name if o.user else "—",
             "items_text": _items_text(o.items),
             "total": float(o.total_amount), "status": o.status,
             "created_at": o.created_at.isoformat(),
             "tracking_link": o.tracking_link,
             "payment_link": o.payment_link}
            for o in orders
        ],
    }


# ---------- РЕДАКТОР «О НАС» ----------

ABOUT_EDITOR_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>О нас — редактор</title>
{BASE_CSS}
<link href="https://cdn.quilljs.com/1.3.7/quill.snow.css" rel="stylesheet">
<style>
.ql-toolbar.ql-snow { border-radius:8px 8px 0 0 !important; border-color:#dee2e6 !important; background:#f8f9fa; }
.ql-container.ql-snow { border-radius:0 0 8px 8px !important; border-color:#dee2e6 !important; font-size:14px; min-height:120px; }
.ql-editor { min-height:100px; }
.about-section { background:#fff; border-radius:14px; box-shadow:0 2px 10px rgba(0,0,0,.06); padding:24px; margin-bottom:20px; }
.about-section-title { font-size:13px; font-weight:700; color:#8c9aad; text-transform:uppercase; letter-spacing:.5px; margin-bottom:16px; }
.banner-wrap { position:relative; width:100%; height:180px; border-radius:12px; overflow:hidden; cursor:pointer;
  background:linear-gradient(135deg,#1a6b3c 0%,#2d9e5f 100%); display:flex; align-items:center; justify-content:center; }
.banner-wrap img { width:100%; height:100%; object-fit:cover; }
.banner-overlay { position:absolute; inset:0; background:rgba(0,0,0,.35); display:flex; flex-direction:column;
  align-items:center; justify-content:center; gap:8px; opacity:0; transition:opacity .2s; }
.banner-wrap:hover .banner-overlay { opacity:1; }
.banner-placeholder { font-size:48px; }
.faq-item-row { border:1px solid #e9ecef; border-radius:10px; margin-bottom:10px; overflow:hidden; }
.faq-item-header { display:flex; align-items:center; gap:10px; padding:12px 14px; background:#f8f9fa; cursor:pointer; }
.faq-item-header:hover { background:#f0f4ff; }
.faq-question-text { flex:1; font-size:14px; font-weight:600; color:#212529; }
.faq-item-body { padding:14px; display:none; border-top:1px solid #e9ecef; }
.faq-item-body.open { display:block; }
.drag-handle { color:#ced4da; cursor:grab; font-size:16px; }
</style>
</head>
<body>
{TOPNAV}
<div class="container-fluid px-4 py-4" style="max-width:900px">

  <div class="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
    <h5 class="section-title mb-0">✏️ Редактор страницы «О нас»</h5>
    <button class="btn btn-sm btn-primary" onclick="saveAll()">
      <i class="fa-solid fa-floppy-disk me-1"></i>Сохранить
    </button>
  </div>

  <!-- Баннер -->
  <div class="about-section">
    <div class="about-section-title">Баннер</div>
    <div class="banner-wrap" id="banner-wrap" onclick="document.getElementById('banner-file').click()">
      <div class="banner-placeholder" id="banner-placeholder">🍵</div>
      <img id="banner-img" style="display:none">
      <div class="banner-overlay">
        <i class="fa-solid fa-camera fa-2x text-white"></i>
        <span style="color:#fff;font-size:13px;font-weight:600">Нажмите чтобы изменить фото</span>
      </div>
    </div>
    <input type="file" id="banner-file" accept="image/*" style="display:none" onchange="uploadBanner(this)">
    <div id="banner-path" style="display:none"></div>
    <button class="btn btn-sm btn-outline-danger mt-2" onclick="removeBanner()" id="remove-banner-btn" style="display:none">
      <i class="fa-solid fa-trash me-1"></i>Убрать фото
    </button>
  </div>

  <!-- Заголовок и описание -->
  <div class="about-section">
    <div class="about-section-title">Заголовок и описание</div>
    <label class="form-label">Заголовок</label>
    <input type="text" id="about-title" class="form-control mb-3" placeholder="Чайное Дерево">
    <label class="form-label">Описание</label>
    <div id="desc-editor"></div>
  </div>

  <!-- FAQ -->
  <div class="about-section">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div class="about-section-title mb-0">Часто задаваемые вопросы</div>
      <button class="btn btn-sm btn-outline-primary" onclick="addFaqItem()">
        <i class="fa-solid fa-plus me-1"></i>Добавить вопрос
      </button>
    </div>
    <div id="faq-list"></div>
  </div>

  <!-- Пункты самовывоза -->
  <div class="about-section">
    <div class="about-section-title">Пункты самовывоза</div>
    <p style="font-size:13px;color:#6c757d;margin-bottom:12px">Пункты самовывоза редактируются в отдельном разделе:</p>
    <a href="/admin/pickup-point/list" class="btn btn-outline-secondary btn-sm">
      <i class="fa-solid fa-location-dot me-1"></i>Управление пунктами самовывоза →
    </a>
  </div>

</div>
<script src="https://cdn.quilljs.com/1.3.7/quill.js"></script>
<script>
var descEditor, faqEditors = {}, faqData = [], bannerPath = null;

var TOOLBAR = [['bold','italic','underline'],[{'list':'bullet'}],['link'],['clean']];

function initDescEditor(html) {
  descEditor = new Quill('#desc-editor', { theme:'snow', modules:{toolbar:TOOLBAR} });
  if (html) descEditor.root.innerHTML = html;
}

function makeQuill(id, html) {
  var q = new Quill('#'+id, { theme:'snow', modules:{toolbar:TOOLBAR} });
  if (html) q.root.innerHTML = html;
  faqEditors[id] = q;
  return q;
}

function renderFaq(items) {
  faqData = items.slice();
  var list = document.getElementById('faq-list');
  list.innerHTML = '';
  if (!items.length) {
    list.innerHTML = '<p class="text-muted" style="font-size:13px">Нет вопросов. Нажмите «Добавить вопрос».</p>';
    return;
  }
  items.forEach(function(item, idx) {
    var edId = 'faq-ed-' + (item.id || 'new' + idx);
    var div = document.createElement('div');
    div.className = 'faq-item-row';
    div.dataset.id = item.id || '';
    div.innerHTML =
      '<div class="faq-item-header" onclick="toggleFaq(this)">' +
        '<span class="drag-handle">⠿</span>' +
        '<span class="faq-question-text">' + (item.question || 'Новый вопрос') + '</span>' +
        '<button class="btn btn-sm btn-outline-danger ms-auto" style="padding:2px 8px;font-size:11px" onclick="event.stopPropagation();deleteFaq(' + (item.id||0) + ',this.closest(\'.faq-item-row\'))">Удалить</button>' +
      '</div>' +
      '<div class="faq-item-body">' +
        '<label class="form-label">Вопрос</label>' +
        '<input type="text" class="form-control mb-3 faq-q-input" value="' + (item.question||'').replace(/"/g,'&quot;') + '" oninput="this.closest(\'.faq-item-row\').querySelector(\'.faq-question-text\').textContent=this.value||\'Новый вопрос\'">' +
        '<label class="form-label">Ответ</label>' +
        '<div id="' + edId + '"></div>' +
        '<div class="d-flex gap-2 mt-3">' +
          '<button class="btn btn-sm btn-primary" onclick="saveFaq(this.closest(\'.faq-item-row\'))">Сохранить</button>' +
          '<button class="btn btn-sm btn-outline-secondary" onclick="toggleFaq(this.closest(\'.faq-item-row\').querySelector(\'.faq-item-header\'))">Отмена</button>' +
        '</div>' +
      '</div>';
    list.appendChild(div);
    setTimeout(function() { makeQuill(edId, item.answer || ''); }, 0);
  });
}

function toggleFaq(header) {
  var body = header.nextElementSibling;
  var isOpen = body.classList.contains('open');
  document.querySelectorAll('.faq-item-body.open').forEach(function(b){ b.classList.remove('open'); });
  if (!isOpen) body.classList.add('open');
}

function addFaqItem() {
  var tempId = 'temp_' + Date.now();
  faqData.push({ id: null, question: '', answer: '', _temp: tempId });
  renderFaq(faqData);
  // Открываем последний
  var rows = document.querySelectorAll('.faq-item-row');
  if (rows.length) {
    var last = rows[rows.length-1];
    last.querySelector('.faq-item-body').classList.add('open');
    last.querySelector('.faq-q-input').focus();
  }
}

async function saveFaq(row) {
  var id = row.dataset.id;
  var q = row.querySelector('.faq-q-input').value.trim();
  if (!q) { alert('Введите вопрос'); return; }
  var edId = row.querySelector('[id^="faq-ed-"]').id;
  var answer = faqEditors[edId] ? faqEditors[edId].root.innerHTML : '';
  var btn = row.querySelector('.btn-primary');
  btn.disabled = true; btn.textContent = 'Сохраняем…';
  try {
    var resp, data;
    if (id) {
      resp = await fetch('/admin-api/faq/'+id, {method:'PATCH', credentials:'include', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question:q, answer:answer})});
    } else {
      resp = await fetch('/admin-api/faq', {method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question:q, answer:answer})});
    }
    if (!resp.ok) throw new Error('Ошибка сервера');
    data = await resp.json();
    row.dataset.id = data.id;
    row.querySelector('.faq-question-text').textContent = q;
    row.querySelector('.faq-item-body').classList.remove('open');
    btn.disabled = false; btn.textContent = 'Сохранить';
  } catch(e) {
    btn.disabled = false; btn.textContent = 'Сохранить';
    alert('Ошибка: ' + e.message);
  }
}

async function deleteFaq(id, row) {
  if (!confirm('Удалить вопрос?')) return;
  if (id) {
    var r = await fetch('/admin-api/faq/'+id, {method:'DELETE', credentials:'include'});
    if (!r.ok) { alert('Ошибка удаления'); return; }
  }
  row.remove();
}

async function uploadBanner(input) {
  if (!input.files[0]) return;
  var fd = new FormData(); fd.append('file', input.files[0]);
  var r = await fetch('/admin-api/upload-image', {method:'POST', credentials:'include', body:fd});
  if (!r.ok) { alert('Ошибка загрузки'); return; }
  var d = await r.json();
  bannerPath = d.path;
  document.getElementById('banner-placeholder').style.display = 'none';
  var img = document.getElementById('banner-img');
  img.src = d.path; img.style.display = 'block';
  document.getElementById('remove-banner-btn').style.display = 'inline-flex';
}

function removeBanner() {
  bannerPath = null;
  document.getElementById('banner-placeholder').style.display = 'block';
  document.getElementById('banner-img').style.display = 'none';
  document.getElementById('remove-banner-btn').style.display = 'none';
}

async function saveAll() {
  var btn = document.querySelector('[onclick="saveAll()"]');
  btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i>Сохраняем…';
  try {
    var r = await fetch('/admin-api/about', {
      method:'POST', credentials:'include',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        title: document.getElementById('about-title').value || 'Чайное Дерево',
        description_html: descEditor ? descEditor.root.innerHTML : '',
        banner_image_path: bannerPath,
      })
    });
    if (!r.ok) throw new Error('Ошибка сервера');
    btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-floppy-disk me-1"></i>Сохранить';
    btn.style.background = '#1b873f'; btn.style.borderColor = '#1b873f';
    setTimeout(function(){ btn.style.background = ''; btn.style.borderColor = ''; }, 1500);
  } catch(e) {
    btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-floppy-disk me-1"></i>Сохранить';
    alert('Ошибка: ' + e.message);
  }
}

document.addEventListener('DOMContentLoaded', function() {
  fetch('/admin-api/about', {credentials:'include'})
    .then(function(r){ return r.json(); })
    .then(function(d) {
      document.getElementById('about-title').value = d.title || 'Чайное Дерево';
      initDescEditor(d.description_html || '');
      if (d.banner_image_path) {
        bannerPath = d.banner_image_path;
        document.getElementById('banner-placeholder').style.display = 'none';
        var img = document.getElementById('banner-img');
        img.src = d.banner_image_path; img.style.display = 'block';
        document.getElementById('remove-banner-btn').style.display = 'inline-flex';
      } else {
        initDescEditor('');
      }
    });
  fetch('/admin-api/faq', {credentials:'include'})
    .then(function(r){ return r.json(); })
    .then(function(d){ renderFaq(d); });
});
</script>
</body>
</html>"""


# ---------- Данные для «О нас» и FAQ ----------

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


# ---------- Регистрация маршрутов ----------

def setup_dashboard(app: FastAPI) -> None:
    @app.get("/admin/dashboard", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard_page(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return RedirectResponse("/admin/login")
        return HTMLResponse(_render(DASHBOARD_HTML, "dashboard"))

    @app.get("/admin-api/dashboard/data", include_in_schema=False)
    async def dashboard_data(request: Request, period: int = 30):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        period = period if period in (7, 30, 90) else 30
        demo = bool(request.session.get("admin_readonly"))
        return JSONResponse(await _get_dashboard_data(period, demo=demo))

    @app.get("/crm/orders/active", response_class=HTMLResponse, include_in_schema=False)
    async def active_orders_page(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return RedirectResponse("/admin/login")
        return HTMLResponse(_render(ACTIVE_ORDERS_HTML, "orders-active"))

    @app.get("/admin-api/orders/active", include_in_schema=False)
    async def active_orders_data(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        return JSONResponse(await _get_active_orders())

    @app.get("/crm/orders/history", response_class=HTMLResponse, include_in_schema=False)
    async def history_page(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return RedirectResponse("/admin/login")
        return HTMLResponse(_render(HISTORY_HTML, "orders-history"))

    @app.get("/admin-api/orders/history", include_in_schema=False)
    async def history_data(request: Request, period: int = 30):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        period = period if period in (7, 30, 90, 365) else 30
        return JSONResponse(await _get_history(period))

    # ---- «О нас» редактор ----

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
        import shutil, uuid
        from pathlib import Path
        from fastapi import UploadFile
        form = await request.form()
        file: UploadFile = form.get("file")
        if not file:
            return JSONResponse(status_code=400, content={"error": "no file"})
        ext = Path(file.filename).suffix.lower() or ".jpg"
        media_dir = Path("/app/app/static/media")
        media_dir.mkdir(parents=True, exist_ok=True)
        fname = f"{uuid.uuid4().hex}{ext}"
        dest = media_dir / fname
        with dest.open("wb") as out:
            shutil.copyfileobj(file.file, out)
        return JSONResponse({"path": f"/static/media/{fname}"})

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
        from sqlalchemy import select, delete
        from app.db import get_session_factory
        from app.models.content import FaqItem
        async with get_session_factory()() as s:
            await s.execute(delete(FaqItem).where(FaqItem.id == faq_id))
            await s.commit()
        return JSONResponse({"ok": True})
