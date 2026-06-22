"""HTML-страница CRM — карточка клиента."""

from __future__ import annotations

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


_SEGMENT_META = {
    "vip":       ("🌟 VIP",        "#7c3aed"),
    "wholesale": ("📦 Оптовик",    "#0369a1"),
    "regular":   ("☕ Постоянный", "#065f46"),
    "at_risk":   ("⚠️ Под риском", "#b45309"),
    "churned":   ("💤 Отток",      "#6b7280"),
}

_STATUS_LABELS = {
    "new": "Новый", "assembling": "Собираем", "ready": "Готов",
    "awaiting_payment": "Ожидает оплаты", "in_delivery": "В доставке",
    "at_pvz": "В ПВЗ", "delivered": "Доставлен", "cancelled": "Отменён",
}
_STATUS_COLORS = {
    "new": "#2563eb", "assembling": "#7c3aed", "ready": "#059669",
    "awaiting_payment": "#d97706", "in_delivery": "#0891b2",
    "at_pvz": "#0369a1", "delivered": "#16a34a", "cancelled": "#6b7280",
}


_CSS = """
<style>
:root {
  --c-bg:    #f4f6fa;
  --c-card:  #ffffff;
  --c-border:#e5e7eb;
  --c-text:  #111827;
  --c-muted: #6b7280;
  --c-green: #16a34a;
  --c-primary: #1a6b3c;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       background: var(--c-bg); color: var(--c-text); font-size: 14px; }

.crm-wrap  { max-width: 1100px; margin: 0 auto; padding: 24px 16px 60px; }
.crm-back  { display:inline-flex;align-items:center;gap:6px;color:var(--c-primary);
             font-weight:600;text-decoration:none;font-size:13px;margin-bottom:20px; }
.crm-back:hover { text-decoration:underline; }

/* ── Profile header ── */
.profile-header {
  background: var(--c-card); border-radius: 16px; border: 1px solid var(--c-border);
  padding: 28px 28px 24px; margin-bottom: 20px;
  display: flex; align-items: flex-start; gap: 20px;
}
.avatar {
  width: 72px; height: 72px; border-radius: 50%; flex-shrink: 0;
  background: var(--c-primary); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-size: 28px; font-weight: 700; letter-spacing: -1px;
}
.profile-info { flex: 1; min-width: 0; }
.profile-name { font-size: 22px; font-weight: 700; line-height: 1.2; margin-bottom: 6px; }
.profile-meta { display: flex; flex-wrap: wrap; gap: 10px 20px; margin-top: 10px; }
.profile-meta-item { display: flex; align-items: center; gap: 5px; color: var(--c-muted); font-size: 13px; }
.profile-meta-item a { color: var(--c-primary); text-decoration: none; font-weight: 600; }
.profile-meta-item a:hover { text-decoration: underline; }
.segment-badge {
  display: inline-flex; align-items: center; padding: 4px 12px;
  border-radius: 100px; font-size: 12px; font-weight: 700;
  margin-top: 10px;
}

/* ── Stats row ── */
.stats-row {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px;
}
.stat-card {
  background: var(--c-card); border-radius: 12px; border: 1px solid var(--c-border);
  padding: 18px 20px;
}
.stat-label { font-size: 11px; font-weight: 600; color: var(--c-muted);
              text-transform: uppercase; letter-spacing: .5px; margin-bottom: 6px; }
.stat-value { font-size: 22px; font-weight: 800; color: var(--c-text); }
.stat-sub   { font-size: 12px; color: var(--c-muted); margin-top: 3px; }

/* ── Grid ── */
.crm-grid { display: grid; grid-template-columns: 1fr 380px; gap: 20px; }
@media (max-width: 768px) { .crm-grid { grid-template-columns: 1fr; } .stats-row { grid-template-columns: repeat(2,1fr); } }

/* ── Card ── */
.crm-card {
  background: var(--c-card); border-radius: 14px; border: 1px solid var(--c-border);
  padding: 20px 20px 16px; margin-bottom: 16px;
}
.crm-card-title {
  font-size: 12px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .5px; color: var(--c-muted); margin-bottom: 14px;
}

/* ── Order history ── */
.order-table { width: 100%; border-collapse: collapse; }
.order-table th {
  text-align: left; padding: 0 10px 10px; font-size: 11px; font-weight: 600;
  color: var(--c-muted); text-transform: uppercase; letter-spacing: .5px;
  border-bottom: 1px solid var(--c-border);
}
.order-table td { padding: 10px; border-bottom: 1px solid var(--c-border); }
.order-table tr:last-child td { border-bottom: none; }
.order-num { font-weight: 700; color: var(--c-primary); text-decoration: none; }
.order-num:hover { text-decoration: underline; }
.status-pill {
  display: inline-block; padding: 2px 8px; border-radius: 100px;
  font-size: 11px; font-weight: 600;
}

/* ── Info rows ── */
.info-row { display: flex; justify-content: space-between; align-items: flex-start;
            padding: 9px 0; border-bottom: 1px solid var(--c-border); }
.info-row:last-child { border-bottom: none; }
.info-label { color: var(--c-muted); font-size: 13px; }
.info-value { font-weight: 600; font-size: 13px; text-align: right; }

/* ── Notes ── */
textarea.notes-area {
  width: 100%; min-height: 100px; padding: 10px 12px;
  border: 1.5px solid var(--c-border); border-radius: 10px;
  font-family: inherit; font-size: 14px; resize: vertical;
  color: var(--c-text); background: #fafafa;
}
textarea.notes-area:focus { outline: none; border-color: var(--c-primary); }

/* ── Segment select ── */
select.seg-select {
  width: 100%; padding: 9px 12px; border: 1.5px solid var(--c-border);
  border-radius: 10px; font-family: inherit; font-size: 14px;
  color: var(--c-text); background: #fafafa; cursor: pointer;
}
select.seg-select:focus { outline: none; border-color: var(--c-primary); }

.save-btn {
  margin-top: 12px; width: 100%; padding: 10px;
  background: var(--c-primary); color: #fff; border: none;
  border-radius: 10px; font-weight: 600; font-size: 14px; cursor: pointer;
}
.save-btn:hover { background: #145530; }
.save-btn:disabled { background: #aaa; cursor: default; }

.crm-toast {
  position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
  background: #1f2937; color: #fff; padding: 10px 22px; border-radius: 100px;
  font-size: 14px; font-weight: 500; opacity: 0; pointer-events: none;
  transition: opacity .3s; z-index: 9999;
}
.crm-toast.show { opacity: 1; }
</style>
"""

_JS = r"""
function toast(msg) {
  var t = document.getElementById('crm-toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2500);
}

async function saveCrm() {
  var btn = document.getElementById('save-btn');
  btn.disabled = true;
  var uid  = btn.dataset.uid;
  var seg  = document.getElementById('seg-select').value;
  var notes = document.getElementById('notes-area').value;
  var r = await fetch('/admin-api/customer/' + uid, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({segment: seg || null, notes: notes || null})
  });
  btn.disabled = false;
  if (r.ok) { toast('✅ Сохранено'); }
  else       { toast('❌ Ошибка сохранения'); }
}
"""


def render_crm_customer(user, admin_username: str = "") -> str:
    from app.admin.dashboard import _topnav

    # ── initials avatar ──────────────────────────────────────────────────────
    parts = [user.first_name or "", user.last_name or ""]
    words = [p for p in parts if p]
    initials = "".join(w[0].upper() for w in words[:2]) or (user.username or "?")[0].upper()

    # ── username/tg link ─────────────────────────────────────────────────────
    tg_link = f'<a href="https://t.me/{user.username}" target="_blank">@{_esc(user.username)}</a>' \
        if user.username else "—"

    # ── segment ──────────────────────────────────────────────────────────────
    seg_label, seg_color = _SEGMENT_META.get(user.segment or "", ("", "#6b7280"))
    segment_badge = (
        f'<span class="segment-badge" style="background:{seg_color}22;color:{seg_color}">'
        f'{seg_label}</span>'
    ) if user.segment else ""

    # ── stats ─────────────────────────────────────────────────────────────────
    orders = user.orders or []
    total_orders = len(orders)
    total_spent  = sum(float(o.total_amount) for o in orders)
    avg_check    = total_spent / total_orders if total_orders else 0
    last_order   = max((o.created_at for o in orders), default=None)

    # ── order history table ──────────────────────────────────────────────────
    orders_sorted = sorted(orders, key=lambda o: o.created_at, reverse=True)
    if orders_sorted:
        rows = ""
        for o in orders_sorted:
            sc = _STATUS_COLORS.get(o.status, "#6b7280")
            sl = _STATUS_LABELS.get(o.status, o.status)
            rows += (
                f'<tr>'
                f'<td><a class="order-num" href="/crm/order/{o.id}">{_esc(o.number)}</a></td>'
                f'<td style="color:#6b7280">{_fmt_dt(o.created_at, date_only=True)}</td>'
                f'<td style="font-weight:700">{float(o.total_amount):.0f} ₽</td>'
                f'<td><span class="status-pill" style="background:{sc}22;color:{sc}">{sl}</span></td>'
                f'</tr>'
            )
        orders_html = f"""
        <table class="order-table">
          <thead><tr>
            <th>Номер</th><th>Дата</th><th>Сумма</th><th>Статус</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>"""
    else:
        orders_html = '<p style="color:#6b7280;font-size:13px">Заказов пока нет</p>'

    # ── profile meta ─────────────────────────────────────────────────────────
    meta_items = ""
    if user.phone:
        meta_items += f'<div class="profile-meta-item">📱 {_esc(user.phone)}</div>'
    if user.email:
        meta_items += f'<div class="profile-meta-item">✉️ {_esc(user.email)}</div>'
    if user.city:
        meta_items += f'<div class="profile-meta-item">📍 {_esc(user.city)}</div>'
    meta_items += f'<div class="profile-meta-item">🔗 Telegram: {tg_link}</div>'
    meta_items += f'<div class="profile-meta-item">ID: <code>{user.telegram_id}</code></div>'

    # ── info rows (right panel) ───────────────────────────────────────────────
    def info_row(label, value):
        return f'<div class="info-row"><span class="info-label">{label}</span><span class="info-value">{value}</span></div>'

    lang_labels = {"ru": "🇷🇺 Русский", "en": "🇬🇧 English", "uk": "🇺🇦 Украинский"}
    info_rows = (
        info_row("Зарегистрирован", _fmt_dt(user.created_at, date_only=True)) +
        info_row("Последний вход", _fmt_dt(user.last_seen_at)) +
        info_row("Язык", lang_labels.get(user.language_code or "", user.language_code or "—"))
    )

    # ── segment select options ────────────────────────────────────────────────
    seg_options = '<option value="">— без сегмента —</option>'
    for val, (lbl, _) in _SEGMENT_META.items():
        sel = 'selected' if user.segment == val else ''
        seg_options += f'<option value="{val}" {sel}>{lbl}</option>'

    nav = _topnav("crm", admin_username=admin_username)

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
<div class="crm-wrap">

  <a href="/admin/user/list" class="crm-back">← Все клиенты</a>

  <!-- Profile header -->
  <div class="profile-header">
    <div class="avatar">{_esc(initials)}</div>
    <div class="profile-info">
      <div class="profile-name">{_esc(user.display_name)}</div>
      {segment_badge}
      <div class="profile-meta">{meta_items}</div>
    </div>
  </div>

  <!-- Stats -->
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
      <div class="stat-label">Последний заказ</div>
      <div class="stat-value" style="font-size:15px">{_fmt_dt(last_order, date_only=True)}</div>
    </div>
  </div>

  <!-- Main grid -->
  <div class="crm-grid">
    <!-- Left: orders -->
    <div>
      <div class="crm-card">
        <p class="crm-card-title">История заказов</p>
        {orders_html}
      </div>
    </div>

    <!-- Right: info + edit -->
    <div>
      <div class="crm-card">
        <p class="crm-card-title">Информация</p>
        {info_rows}
      </div>

      <div class="crm-card">
        <p class="crm-card-title">Сегмент</p>
        <select id="seg-select" class="seg-select">{seg_options}</select>
      </div>

      <div class="crm-card">
        <p class="crm-card-title">Заметки менеджера</p>
        <textarea id="notes-area" class="notes-area" placeholder="Добавьте заметку о клиенте…">{_esc(user.notes or "")}</textarea>
        <button id="save-btn" class="save-btn" data-uid="{user.id}" onclick="saveCrm()">Сохранить</button>
      </div>
    </div>
  </div>
</div>

<div id="crm-toast" class="crm-toast"></div>
<script>{_JS}</script>
</body>
</html>"""
