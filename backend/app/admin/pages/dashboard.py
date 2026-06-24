"""Дашборд — главная страница с аналитикой."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.admin.shared import _render

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Дашборд — Чайное Дерево</title>
{BASE_CSS}
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
</head>
<body>
{TOPNAV}
<div class="container-fluid px-4 py-4" style="max-width:1400px">

  <!-- ⏳ Текущие заказы — вверху -->
  <div class="card chart-card p-4 mb-4">
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
          <div style="display:flex;gap:6px" id="period-btns">
            <button class="btn btn-sm btn-outline-secondary period-btn" onclick="setPeriod(this,7)">7 дней</button>
            <button class="btn btn-sm btn-outline-secondary period-btn active" onclick="setPeriod(this,30)">30 дней</button>
            <button class="btn btn-sm btn-outline-secondary period-btn" onclick="setPeriod(this,90)">90 дней</button>
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


def setup_dashboard_routes(app: FastAPI) -> None:
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
