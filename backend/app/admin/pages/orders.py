"""Страницы текущих заказов и истории заказов."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.admin.shared import _render

ACTIVE_ORDERS_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
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

HISTORY_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
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
      <div style="display:flex;gap:6px" id="period-btns">
        <button class="btn btn-sm btn-outline-secondary period-btn" onclick="setPeriod(this,7)">7 дней</button>
        <button class="btn btn-sm btn-outline-secondary period-btn active" onclick="setPeriod(this,30)">30 дней</button>
        <button class="btn btn-sm btn-outline-secondary period-btn" onclick="setPeriod(this,90)">90 дней</button>
        <button class="btn btn-sm btn-outline-secondary period-btn" onclick="setPeriod(this,365)">Год</button>
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


async def _get_active_orders(demo: bool = False) -> dict:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.db import get_session_factory
    from app.models.delivery import DeliveryInfo
    from app.models.order import Order, OrderItem

    now = datetime.now(timezone.utc)

    async with get_session_factory()() as s:
        stmt = (
            select(Order)
            .options(selectinload(Order.user), selectinload(Order.items), selectinload(Order.delivery_info))
            .where(Order.status.notin_(["delivered", "cancelled"]))
            .order_by(Order.created_at.asc())
        )
        if demo:
            stmt = stmt.where(Order.number.like("DEMO-%"))
        else:
            stmt = stmt.where(~Order.number.like("DEMO-%"))
        result = await s.execute(stmt)
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


async def _get_history(period_days: int, demo: bool = False) -> dict:
    from sqlalchemy import func, select
    from sqlalchemy.orm import selectinload

    from app.db import get_session_factory
    from app.models.order import Order

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=period_days)

    async with get_session_factory()() as s:
        stmt = (
            select(Order)
            .options(selectinload(Order.user), selectinload(Order.items))
            .where(Order.status.in_(["delivered", "cancelled"]), Order.created_at >= since)
            .order_by(Order.created_at.desc())
        )
        if demo:
            stmt = stmt.where(Order.number.like("DEMO-%"))
        else:
            stmt = stmt.where(~Order.number.like("DEMO-%"))
        result = await s.execute(stmt)
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


def setup_orders_routes(app: FastAPI) -> None:
    @app.get("/crm/orders/active", response_class=HTMLResponse, include_in_schema=False)
    async def active_orders_page(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return RedirectResponse("/admin/login")
        return HTMLResponse(_render(ACTIVE_ORDERS_HTML, "orders-active"))

    @app.get("/admin-api/orders/active", include_in_schema=False)
    async def active_orders_data(request: Request):
        if request.session.get("admin_token") != "authenticated":
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        demo = request.session.get("admin_username") == "demo"
        return JSONResponse(await _get_active_orders(demo=demo))

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
        demo = request.session.get("admin_username") == "demo"
        return JSONResponse(await _get_history(period, demo=demo))
