"""HTML-страница CRM — карточка клиента."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone


def _esc(s: str | None) -> str:
    if not s:
        return ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _fmt_dt(dt: datetime | None, date_only: bool = False) -> str:
    if dt is None:
        return "—"
    import zoneinfo
    msk = zoneinfo.ZoneInfo("Europe/Moscow")
    local = dt.replace(tzinfo=timezone.utc).astimezone(msk)
    return local.strftime("%d.%m.%Y") if date_only else local.strftime("%d.%m.%Y %H:%M")


_STATUS_LABELS = {
    "new": "Новый", "assembling": "Собираем", "ready": "Готов",
    "awaiting_payment": "Ожидает оплаты", "in_delivery": "В доставке",
    "at_pvz": "В ПВЗ", "delivered": "Доставлен", "cancelled": "Отменён",
}
_STATUS_COLORS = {
    "new": "#2563eb", "assembling": "#7c3aed", "ready": "#059669",
    "awaiting_payment": "#d97706", "in_delivery": "#0891b2",
    "at_pvz": "#0369a1", "delivered": "#16a34a", "cancelled": "#9ca3af",
}
_STATUS_ICONS = {
    "new": "🆕", "assembling": "📦", "ready": "✅",
    "awaiting_payment": "⏳", "in_delivery": "🚚",
    "at_pvz": "🏪", "delivered": "🎉", "cancelled": "❌",
}


_CSS = """
<style>
:root {
  --c-bg: #f0f2f7;
  --c-card: #ffffff;
  --c-border: #e5e7eb;
  --c-text: #111827;
  --c-muted: #6b7280;
  --c-primary: #1a6b3c;
  --c-primary-light: #e8f5ee;
  --c-bonus: #d97706;
  --c-bonus-light: #fef3c7;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--c-bg); color: var(--c-text); font-size: 14px; line-height: 1.5;
}

.wrap { max-width: 1060px; margin: 0 auto; padding: 24px 16px 72px; }

.back-link {
  display: inline-flex; align-items: center; gap: 6px;
  color: var(--c-primary); font-weight: 600; font-size: 13px;
  text-decoration: none; margin-bottom: 20px;
  padding: 6px 12px; border-radius: 8px; transition: background .15s;
}
.back-link:hover { background: var(--c-primary-light); text-decoration: none; }

/* ── Profile header ── */
.profile-header {
  background: linear-gradient(135deg, #1a6b3c 0%, #2d9a5c 100%);
  border-radius: 18px; padding: 28px 28px 24px;
  display: flex; align-items: center; gap: 20px;
  margin-bottom: 16px; color: #fff;
}
.avatar {
  width: 76px; height: 76px; border-radius: 50%; flex-shrink: 0;
  background: rgba(255,255,255,.2); backdrop-filter: blur(4px);
  border: 2.5px solid rgba(255,255,255,.4);
  display: flex; align-items: center; justify-content: center;
  font-size: 28px; font-weight: 700; color: #fff; letter-spacing: -1px;
}
.profile-name { font-size: 22px; font-weight: 700; line-height: 1.2; }
.profile-sub { display: flex; flex-wrap: wrap; gap: 6px 18px; margin-top: 8px; }
.profile-sub-item { display: flex; align-items: center; gap: 5px; font-size: 13px; color: rgba(255,255,255,.85); }
.profile-sub-item a { color: #fff; font-weight: 600; text-decoration: none; border-bottom: 1px solid rgba(255,255,255,.4); }
.profile-sub-item a:hover { border-color: #fff; }

/* ── Stats row ── */
.stats-row {
  display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px;
  margin-bottom: 20px;
}
@media (max-width: 960px) { .stats-row { grid-template-columns: repeat(3,1fr); } }
@media (max-width: 560px) { .stats-row { grid-template-columns: repeat(2,1fr); } }

.stat-card {
  background: var(--c-card); border-radius: 14px; border: 1px solid var(--c-border);
  padding: 16px 18px; position: relative; overflow: hidden;
}
.stat-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--c-primary); border-radius: 14px 14px 0 0;
}
.stat-card.bonus-card::before { background: var(--c-bonus); }
.stat-label { font-size: 10px; font-weight: 700; color: var(--c-muted); text-transform: uppercase; letter-spacing: .6px; margin-bottom: 8px; }
.stat-value { font-size: 20px; font-weight: 800; color: var(--c-text); }
.stat-sub { font-size: 11px; color: var(--c-muted); margin-top: 3px; }

/* ── Main grid ── */
.main-grid { display: grid; grid-template-columns: 1fr 300px; gap: 16px; align-items: start; }
@media (max-width: 760px) { .main-grid { grid-template-columns: 1fr; } }

/* ── Card ── */
.card { background: var(--c-card); border-radius: 14px; border: 1px solid var(--c-border); overflow: hidden; margin-bottom: 16px; }
.card-header {
  padding: 14px 20px; border-bottom: 1px solid var(--c-border);
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .6px; color: var(--c-muted);
  display: flex; align-items: center; justify-content: space-between;
}
.card-header-count { background: var(--c-primary-light); color: var(--c-primary); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 100px; }
.card-body { padding: 8px 0; }
.card-empty { padding: 24px 20px; color: var(--c-muted); font-size: 13px; text-align: center; }

/* ── Order cards ── */
.order-card {
  display: flex; align-items: flex-start; gap: 14px;
  padding: 14px 20px; border-bottom: 1px solid var(--c-border);
  text-decoration: none; color: inherit; transition: background .12s;
}
.order-card:last-child { border-bottom: none; }
.order-card:hover { background: #fafbff; }
.order-icon { width: 38px; height: 38px; border-radius: 10px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 18px; }
.order-main { flex: 1; min-width: 0; }
.order-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.order-num { font-weight: 700; font-size: 14px; color: var(--c-primary); }
.order-amount { font-weight: 800; font-size: 15px; white-space: nowrap; }
.order-meta { display: flex; align-items: center; gap: 10px; margin-top: 4px; }
.order-date { font-size: 12px; color: var(--c-muted); }
.status-pill { display: inline-flex; align-items: center; gap: 3px; padding: 2px 9px; border-radius: 100px; font-size: 11px; font-weight: 600; white-space: nowrap; }
.order-items-preview { margin-top: 5px; font-size: 12px; color: var(--c-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ── Top products ── */
.top-product { display: flex; align-items: center; gap: 12px; padding: 12px 20px; border-bottom: 1px solid var(--c-border); }
.top-product:last-child { border-bottom: none; }
.top-rank { width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 800; }
.rank-1 { background: #fef3c7; color: #92400e; }
.rank-2 { background: #f1f5f9; color: #475569; }
.rank-3 { background: #fef2ef; color: #9a3412; }
.top-product-name { flex: 1; font-size: 13px; font-weight: 600; min-width: 0; }
.top-product-count { font-size: 12px; font-weight: 700; color: var(--c-muted); background: var(--c-bg); padding: 2px 8px; border-radius: 100px; white-space: nowrap; }

/* ── Bonus widget ── */
.bonus-widget { padding: 20px; }
.bonus-balance-display { text-align: center; padding: 16px; background: var(--c-bonus-light); border-radius: 12px; margin-bottom: 16px; }
.bonus-balance-display .val { font-size: 32px; font-weight: 800; color: var(--c-bonus); }
.bonus-balance-display .lbl { font-size: 12px; color: #92400e; font-weight: 600; margin-top: 2px; }
.bonus-actions { display: flex; flex-direction: column; gap: 8px; }
.bonus-inp-row { display: flex; gap: 8px; }
.bonus-inp { flex: 1; border: 1px solid var(--c-border); border-radius: 8px; padding: 8px 12px; font-size: 14px; }
.bonus-inp:focus { outline: none; border-color: var(--c-primary); }
.bonus-note { width: 100%; border: 1px solid var(--c-border); border-radius: 8px; padding: 8px 12px; font-size: 13px; resize: none; height: 52px; }
.bonus-note:focus { outline: none; border-color: var(--c-primary); }
.btn-bonus-add { flex: 1; background: #065f46; color: #fff; border: none; border-radius: 8px; padding: 9px 0; font-weight: 600; font-size: 13px; cursor: pointer; }
.btn-bonus-add:hover { background: #047857; }
.btn-bonus-sub { flex: 1; background: #991b1b; color: #fff; border: none; border-radius: 8px; padding: 9px 0; font-weight: 600; font-size: 13px; cursor: pointer; }
.btn-bonus-sub:hover { background: #7f1d1d; }
.bonus-history { margin-top: 12px; }
.btx-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid var(--c-border); font-size: 12px; }
.btx-row:last-child { border-bottom: none; }
.btx-delta { font-weight: 700; min-width: 60px; text-align: right; }
.btx-delta.pos { color: #065f46; }
.btx-delta.neg { color: #991b1b; }
.btx-reason { flex: 1; color: var(--c-muted); }
.btx-date { color: #9ca3af; white-space: nowrap; }
.toast { position: fixed; bottom: 24px; right: 24px; background: #1a6b3c; color: #fff; padding: 12px 20px; border-radius: 10px; font-weight: 600; font-size: 14px; display: none; z-index: 9999; }
.toast.err { background: #dc2626; }
</style>
"""


def render_crm_customer(user, admin_username: str = "") -> str:
    from app.admin.dashboard import _topnav

    parts = [user.first_name or "", user.last_name or ""]
    words = [p for p in parts if p]
    initials = "".join(w[0].upper() for w in words[:2]) or (user.username or "?")[0].upper()

    orders = user.orders or []
    total_orders = len(orders)
    total_spent = sum(float(o.total_amount) for o in orders)
    avg_check = total_spent / total_orders if total_orders else 0
    last_order_dt = max((o.created_at for o in orders), default=None)
    bonus_balance = float(user.bonus_balance) if user.bonus_balance else 0.0

    # Top-3 products
    product_counter: Counter = Counter()
    for o in orders:
        if hasattr(o, "items") and o.items:
            for item in o.items:
                product_counter[item.snapshot_name] += item.quantity
    top_products = product_counter.most_common(3)

    orders_sorted = sorted(orders, key=lambda o: o.created_at, reverse=True)

    def order_card_html(o) -> str:
        sc = _STATUS_COLORS.get(o.status, "#9ca3af")
        sl = _STATUS_LABELS.get(o.status, o.status)
        si = _STATUS_ICONS.get(o.status, "📋")
        items_preview = ""
        if hasattr(o, "items") and o.items:
            parts_list = []
            for it in sorted(o.items, key=lambda x: x.snapshot_name):
                label = f"{_esc(it.snapshot_name)}"
                if it.snapshot_weight_g:
                    label += f" {it.snapshot_weight_g} г"
                if it.quantity > 1:
                    label += f" × {it.quantity}"
                parts_list.append(label)
            items_preview = ", ".join(parts_list)
        return (
            f'<a class="order-card" href="/crm/order/{o.id}">'
            f'  <div class="order-icon" style="background:{sc}18">{si}</div>'
            f'  <div class="order-main">'
            f'    <div class="order-top">'
            f'      <span class="order-num">{_esc(o.number)}</span>'
            f'      <span class="order-amount">{float(o.total_amount):.0f} ₽</span>'
            f'    </div>'
            f'    <div class="order-meta">'
            f'      <span class="order-date">{_fmt_dt(o.created_at)}</span>'
            f'      <span class="status-pill" style="background:{sc}18;color:{sc}">{sl}</span>'
            f'    </div>'
            f'    {f"<div class=order-items-preview>{items_preview}</div>" if items_preview else ""}'
            f'  </div>'
            f'</a>'
        )

    orders_html = "".join(order_card_html(o) for o in orders_sorted) if orders_sorted else \
        '<div class="card-empty">Заказов пока нет</div>'

    rank_classes = ["rank-1", "rank-2", "rank-3"]
    rank_emojis = ["🥇", "🥈", "🥉"]
    if top_products:
        top_html = ""
        for i, (name, qty) in enumerate(top_products):
            rc = rank_classes[i] if i < 3 else "rank-3"
            re = rank_emojis[i] if i < 3 else str(i + 1)
            top_html += (
                f'<div class="top-product">'
                f'  <div class="top-rank {rc}">{re}</div>'
                f'  <div class="top-product-name">{_esc(name)}</div>'
                f'  <div class="top-product-count">{qty} шт</div>'
                f'</div>'
            )
    else:
        top_html = '<div class="card-empty">Нет данных</div>'

    # Bonus transaction history (last 10)
    btx_list = []
    if hasattr(user, "bonus_transactions") and user.bonus_transactions:
        btx_list = list(user.bonus_transactions)[:10]

    _REASON_LABELS = {
        "order_cashback": "Кешбэк за заказ",
        "order_payment": "Списание за заказ",
        "manual_add": "Начисление (вручную)",
        "manual_deduct": "Списание (вручную)",
    }

    def btx_html(tx) -> str:
        delta = float(tx.delta)
        sign = "+" if delta >= 0 else ""
        cls = "pos" if delta >= 0 else "neg"
        reason_label = _REASON_LABELS.get(tx.reason, tx.reason)
        note_part = f" · {_esc(tx.note)}" if tx.note else ""
        return (
            f'<div class="btx-row">'
            f'  <div class="btx-delta {cls}">{sign}{delta:.0f} ₽</div>'
            f'  <div class="btx-reason">{reason_label}{note_part}</div>'
            f'  <div class="btx-date">{_fmt_dt(tx.created_at, date_only=True)}</div>'
            f'</div>'
        )

    btx_section = "".join(btx_html(tx) for tx in btx_list) if btx_list else \
        '<div style="font-size:12px;color:#9ca3af;text-align:center;padding:8px 0">История пуста</div>'

    sub_items = ""
    if user.username:
        sub_items += (
            f'<div class="profile-sub-item">'
            f'<a href="https://t.me/{_esc(user.username)}" target="_blank">@{_esc(user.username)}</a>'
            f'</div>'
        )
    if user.phone:
        sub_items += f'<div class="profile-sub-item">📱 {_esc(user.phone)}</div>'
    sub_items += f'<div class="profile-sub-item" style="opacity:.7">ID {user.telegram_id}</div>'

    nav = _topnav("crm")

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(user.display_name)} — CRM</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
{_CSS}
</head>
<body>
{nav}
<div class="wrap">

  <a href="/admin/user/list" class="back-link">← Все клиенты</a>

  <div class="profile-header">
    <div class="avatar">{_esc(initials)}</div>
    <div>
      <div class="profile-name">{_esc(user.display_name)}</div>
      <div class="profile-sub">{sub_items}</div>
    </div>
  </div>

  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-label">Заказов</div>
      <div class="stat-value">{total_orders}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Потрачено</div>
      <div class="stat-value">{total_spent:.0f} ₽</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Средний чек</div>
      <div class="stat-value">{avg_check:.0f} ₽</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Последняя покупка</div>
      <div class="stat-value" style="font-size:15px;line-height:1.3">{_fmt_dt(last_order_dt, date_only=True)}</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Был в апп</div>
      <div class="stat-value" style="font-size:13px;line-height:1.3;padding-top:3px">{_fmt_dt(user.last_seen_at)}</div>
      <div class="stat-sub">Зарег. {_fmt_dt(user.created_at, date_only=True)}</div>
    </div>
    <div class="stat-card bonus-card">
      <div class="stat-label">🎁 Баллы</div>
      <div class="stat-value" style="color:#d97706">{bonus_balance:.0f}</div>
    </div>
  </div>

  <div class="main-grid">
    <div>
      <div class="card">
        <div class="card-header">
          История заказов
          <span class="card-header-count">{total_orders}</span>
        </div>
        <div class="card-body">{orders_html}</div>
      </div>
    </div>

    <div>
      <div class="card">
        <div class="card-header">Топ товары</div>
        <div class="card-body">{top_html}</div>
      </div>

      <div class="card">
        <div class="card-header">🎁 Бонусные баллы</div>
        <div class="bonus-widget">
          <div class="bonus-balance-display">
            <div class="val" id="bonus-val">{bonus_balance:.0f}</div>
            <div class="lbl">текущий баланс</div>
          </div>
          <div class="bonus-actions">
            <div class="bonus-inp-row">
              <input class="bonus-inp" type="number" min="1" step="1" id="bonus-amount" placeholder="Сумма баллов">
            </div>
            <textarea class="bonus-note" id="bonus-note" placeholder="Комментарий (необязательно)"></textarea>
            <div class="bonus-inp-row">
              <button class="btn-bonus-add" onclick="adjustBonus(1)">+ Начислить</button>
              <button class="btn-bonus-sub" onclick="adjustBonus(-1)">− Списать</button>
            </div>
          </div>
          <div class="bonus-history" id="bonus-history">
            {btx_section}
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
async function adjustBonus(sign) {{
  var amt = parseFloat(document.getElementById('bonus-amount').value);
  if (!amt || amt <= 0) {{ showToast('Введите сумму', true); return; }}
  var note = document.getElementById('bonus-note').value.trim();
  try {{
    var r = await fetch('/admin-api/customer/{user.id}/bonus', {{
      method: 'POST',
      headers: {{'Content-Type':'application/json'}},
      body: JSON.stringify({{delta: sign * amt, note: note || null}})
    }});
    var d = await r.json();
    if (!r.ok) throw new Error(d.error || 'Ошибка');
    document.getElementById('bonus-val').textContent = parseFloat(d.bonus_balance).toFixed(0);
    document.getElementById('bonus-amount').value = '';
    document.getElementById('bonus-note').value = '';
    showToast(sign > 0 ? '+ ' + amt.toFixed(0) + ' баллов начислено' : '− ' + amt.toFixed(0) + ' баллов списано');
    // reload history
    var hr = await fetch('/admin-api/customer/{user.id}/bonus-history');
    var hd = await hr.json();
    document.getElementById('bonus-history').innerHTML = hd.html || '';
  }} catch(e) {{
    showToast(e.message||'Ошибка', true);
  }}
}}

function showToast(msg, err) {{
  var t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast' + (err?' err':'');
  t.style.display = 'block';
  setTimeout(function(){{t.style.display='none';}}, 3000);
}}
</script>
</body>
</html>"""
