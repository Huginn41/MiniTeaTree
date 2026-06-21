"""HTML-шаблон CRM-страницы заказа (пошаговый интерфейс)."""

from __future__ import annotations

from datetime import datetime, timezone


# ── константы ──────────────────────────────────────────────────────────────────

_DELIVERY_STEPS = ["new", "awaiting_payment", "in_delivery", "at_pvz", "delivered"]
_PICKUP_STEPS   = ["new", "assembling", "ready", "delivered"]

_STEP_LABELS_DELIVERY = ["Новый", "Ожидает оплаты", "В доставке", "В ПВЗ", "Доставлен"]
_STEP_LABELS_PICKUP   = ["Новый", "Собираем", "Готов", "Доставлен"]

_ADMIN_LABELS = {
    "new": "Новый", "assembling": "Собираем", "ready": "Готов",
    "awaiting_payment": "Ожидает оплаты", "in_delivery": "Передан в доставку",
    "at_pvz": "В ПВЗ", "delivered": "Доставлен", "cancelled": "Отменён",
}
_DELIVERY_TYPE_LABELS = {"pickup": "Самовывоз", "courier": "Курьер", "pvz": "ПВЗ"}


# ── helpers ────────────────────────────────────────────────────────────────────

def _esc(s: str | None) -> str:
    if not s:
        return ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    import zoneinfo
    msk = zoneinfo.ZoneInfo("Europe/Moscow")
    return dt.replace(tzinfo=timezone.utc).astimezone(msk).strftime("%d.%m.%Y %H:%M")


# ── step card builder ──────────────────────────────────────────────────────────

def _step_card(num: int, title: str, body: str, state: str) -> str:
    """
    state: 'done' | 'active' | 'future'
    """
    icons = {"done": "✓", "active": str(num), "future": str(num)}
    circle_cls = f"sc-circle sc-circle-{state}"
    card_cls = f"step-card step-card-{state}"
    icon = icons[state]

    # future steps: collapse body, show placeholder
    if state == "future":
        body_html = f'<div class="sc-body sc-body-future">{body}</div>'
    elif state == "done":
        body_html = f'<div class="sc-body sc-body-done">{body}</div>'
    else:
        body_html = f'<div class="sc-body sc-body-active">{body}</div>'

    connector = '<div class="sc-connector"></div>'

    return (
        f'<div class="{card_cls}">'
        f'  <div class="sc-left">'
        f'    <div class="{circle_cls}">{icon}</div>'
        f'    {connector}'
        f'  </div>'
        f'  <div class="sc-right">'
        f'    <div class="sc-title">{title}</div>'
        f'    {body_html}'
        f'  </div>'
        f'</div>'
    )


def _btn(label: str, onclick: str, style: str = "primary", disabled: bool = False) -> str:
    dis = "disabled" if disabled else f'onclick="{_esc(onclick)}"'
    return f'<button class="crm-btn crm-btn-{style}" {dis}>{label}</button>'


def _contact_btn(order) -> str:
    user = order.user
    if not user:
        return '<p class="crm-hint">Данные клиента недоступны.</p>'
    href = f"https://t.me/{user.username}" if user.username else f"tg://user?id={user.telegram_id}"
    name = _esc(getattr(user, "display_name", None) or f"ID {user.telegram_id}")
    return (
        f'<a href="{href}" target="_blank" class="crm-btn crm-btn-tg">'
        f'  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">'
        f'    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0z"/>'
        f'    <path fill="white" d="M17.5 7.5l-2.5 11-3.5-3-2 2-1-4.5L5 12l12.5-4.5z"/>'
        f'  </svg>'
        f'  Написать {name}'
        f'</a>'
    )


# ── step bodies (active) ───────────────────────────────────────────────────────

def _body_new_delivery(order) -> str:
    oid = order.id
    if order.payment_link:
        return (
            f'<p class="crm-hint">✅ Ссылка на оплату отправлена клиенту:</p>'
            f'<div class="crm-link-preview">{_esc(order.payment_link)}</div>'
            f'<p class="crm-hint" style="margin-top:10px">Подтвердите переход к следующему шагу:</p>'
            + _btn("💳 К ожиданию оплаты", f"changeStatus({oid},'awaiting_payment')")
        )
    return (
        '<p class="crm-hint">Отправьте клиенту ссылку на оплату.</p>'
        '<input id="pay-link-input" class="crm-input" type="url" placeholder="https://..." />'
        + _btn("💳 Отправить ссылку клиенту", f"sendPaymentLink({oid})")
    )


def _body_awaiting_payment(order) -> str:
    oid = order.id
    link_preview = ""
    if order.payment_link:
        link_preview = f'<div class="crm-link-preview" style="margin-bottom:12px">{_esc(order.payment_link)}</div>'
    return (
        f'{link_preview}'
        '<p class="crm-hint">Проверьте поступление оплаты.</p>'
        '<div class="crm-btn-row">'
        + _btn("✅ Оплачено", f"confirmPaid({oid})", "success")
        + _btn("❌ Отменить заказ", f"changeStatus({oid},'cancelled')", "danger")
        + '</div>'
        '<div id="paid-section" style="display:none;margin-top:16px">'
        f'  <div class="crm-divider"></div>'
        f'  <p class="crm-hint" style="font-weight:600;margin-bottom:10px">📦 Передать в доставку</p>'
        f'  {_contact_btn(order)}'
        f'  <p class="crm-hint" style="margin-top:12px">Трек-номер / ссылка (необязательно):</p>'
        f'  <input id="tracking-input" class="crm-input" type="text" '
        f'         placeholder="Трек-номер или ссылка" value="{_esc(order.tracking_link or "")}" />'
        + _btn("🚚 Передать в доставку", f"sendToDelivery({oid})", "primary")
        + '</div>'
    )


def _body_in_delivery(order) -> str:
    oid = order.id
    return (
        f'{_contact_btn(order)}'
        '<p class="crm-hint" style="margin-top:12px">Трек-номер / ссылка:</p>'
        f'<input id="tracking-input" class="crm-input" type="text" '
        f'       placeholder="Трек-номер" value="{_esc(order.tracking_link or "")}" />'
        + _btn("💾 Сохранить трек", f"saveTracking({oid})", "secondary")
        + '<div class="crm-divider"></div>'
        '<p class="crm-hint">Заказ прибыл в пункт выдачи:</p>'
        + _btn("🏪 Отметить: В ПВЗ", f"changeStatus({oid},'at_pvz')", "primary")
    )


def _body_at_pvz(order) -> str:
    oid = order.id
    return (
        '<p class="crm-hint">Клиент уведомлён о том, что заказ в ПВЗ.</p>'
        + _btn("🎉 Отметить: Получен", f"changeStatus({oid},'delivered')", "success")
    )


def _body_delivered(order, now: datetime) -> str:
    oid = order.id
    feedback_sent = bool(getattr(order, "feedback_sent_at", None))
    days_since = 0
    if order.delivered_at:
        days_since = (now - order.delivered_at.replace(tzinfo=timezone.utc)).days

    if feedback_sent:
        fb = '<p class="crm-hint">✅ Запрос отзыва уже отправлен.</p>' + _btn("💬 Отзыв отправлен", "", "secondary", disabled=True)
    elif days_since < 3:
        fb = (
            f'<p class="crm-hint">Кнопка станет активной через {3 - days_since} д.</p>'
            + _btn("💬 Запросить отзыв", "", "secondary", disabled=True)
        )
    else:
        fb = (
            '<p class="crm-hint">Пора запросить обратную связь!</p>'
            + _btn("💬 Запросить отзыв", f"sendFeedback({oid})", "success")
        )
    return '<p class="crm-hint">🎉 Заказ успешно доставлен!</p><div class="crm-divider"></div>' + fb


# Pickup bodies
def _body_new_pickup(order) -> str:
    return (
        '<p class="crm-hint">Начните сборку заказа.</p>'
        + _btn("📦 Начать сборку", f"changeStatus({order.id},'assembling')", "primary")
    )


def _body_assembling(order) -> str:
    return (
        '<p class="crm-hint">Когда заказ собран — уведомите клиента.</p>'
        + _btn("✅ Готов к выдаче", f"changeStatus({order.id},'ready')", "success")
    )


def _body_ready(order) -> str:
    return (
        f'{_contact_btn(order)}'
        '<div class="crm-divider"></div>'
        '<p class="crm-hint">Клиент пришёл и забрал заказ:</p>'
        + _btn("🎉 Выдан клиенту", f"changeStatus({order.id},'delivered')", "success")
    )


# Placeholder bodies for done/future steps
_DONE_BODY = '<p class="crm-hint done-text">Этот шаг выполнен.</p>'

def _future_delivery_body(step: str) -> str:
    hints = {
        "awaiting_payment": "Ожидание подтверждения оплаты от клиента.",
        "in_delivery":      "Передача заказа в службу доставки.",
        "at_pvz":           "Заказ прибудет в пункт выдачи.",
        "delivered":        "Клиент получит заказ.",
    }
    return f'<p class="crm-hint future-text">{hints.get(step, "")}</p>'


def _future_pickup_body(step: str) -> str:
    hints = {
        "assembling": "Сборка позиций заказа.",
        "ready":      "Уведомление клиента о готовности.",
        "delivered":  "Клиент заберёт заказ из магазина.",
    }
    return f'<p class="crm-hint future-text">{hints.get(step, "")}</p>'


# ── pipeline renderers ─────────────────────────────────────────────────────────

def _pipeline_delivery(order, now: datetime) -> str:
    status = order.status
    oid = order.id

    steps = [
        ("new",              "💳 Ссылка на оплату"),
        ("awaiting_payment", "⏳ Ожидание оплаты"),
        ("in_delivery",      "🚚 В доставке"),
        ("at_pvz",           "🏪 В пункте выдачи"),
        ("delivered",        "🎉 Доставлен"),
    ]

    if status == "cancelled":
        return '<div class="crm-cancelled">❌ Заказ отменён</div>'

    try:
        cur = [s for s, _ in steps].index(status)
    except ValueError:
        cur = 0

    bodies = {
        "new":              _body_new_delivery(order),
        "awaiting_payment": _body_awaiting_payment(order),
        "in_delivery":      _body_in_delivery(order),
        "at_pvz":           _body_at_pvz(order),
        "delivered":        _body_delivered(order, now),
    }

    html = []
    for i, (step, title) in enumerate(steps):
        if i < cur:
            html.append(_step_card(i + 1, title, _DONE_BODY, "done"))
        elif i == cur:
            html.append(_step_card(i + 1, title, bodies[step], "active"))
        else:
            html.append(_step_card(i + 1, title, _future_delivery_body(step), "future"))

    return "".join(html)


def _pipeline_pickup(order, now: datetime) -> str:
    status = order.status
    oid = order.id

    steps = [
        ("new",        "🆕 Новый заказ"),
        ("assembling", "📦 Собираем"),
        ("ready",      "✅ Готов к выдаче"),
        ("delivered",  "🎉 Выдан клиенту"),
    ]

    if status == "cancelled":
        return '<div class="crm-cancelled">❌ Заказ отменён</div>'

    try:
        cur = [s for s, _ in steps].index(status)
    except ValueError:
        cur = 0

    bodies = {
        "new":        _body_new_pickup(order),
        "assembling": _body_assembling(order),
        "ready":      _body_ready(order),
        "delivered":  _body_delivered(order, now),
    }

    html = []
    for i, (step, title) in enumerate(steps):
        if i < cur:
            html.append(_step_card(i + 1, title, _DONE_BODY, "done"))
        elif i == cur:
            html.append(_step_card(i + 1, title, bodies[step], "active"))
        else:
            html.append(_step_card(i + 1, title, _future_pickup_body(step), "future"))

    return "".join(html)


# ── JS ─────────────────────────────────────────────────────────────────────────

_JS = """
async function api(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });
  if (!r.ok) { const t = await r.text(); throw new Error(t); }
  return r.json();
}

function toast(msg, ok=true) {
  const el = document.getElementById('crm-toast');
  el.textContent = msg;
  el.className = 'crm-toast show ' + (ok ? 'ok' : 'err');
  setTimeout(() => el.className = 'crm-toast', 3000);
}

async function changeStatus(id, status) {
  try {
    await api(`/admin-api/order/${id}/status`, {field:'status', value:status});
    location.reload();
  } catch(e) { toast('Ошибка: ' + e.message, false); }
}

async function sendPaymentLink(id) {
  const link = (document.getElementById('pay-link-input')?.value || '').trim();
  if (!link.startsWith('http')) { toast('Введите корректную ссылку', false); return; }
  try {
    await api(`/admin-api/order/${id}/payment-link`, {link});
    toast('Ссылка отправлена клиенту ✓');
    setTimeout(() => location.reload(), 1200);
  } catch(e) { toast('Ошибка: ' + e.message, false); }
}

function confirmPaid(id) {
  const sec = document.getElementById('paid-section');
  if (sec) { sec.style.display = 'block'; sec.scrollIntoView({behavior:'smooth', block:'nearest'}); }
}

async function sendToDelivery(id) {
  const tracking = (document.getElementById('tracking-input')?.value || '').trim();
  try {
    if (tracking) await api(`/admin-api/order/${id}/tracking`, {link: tracking});
    await api(`/admin-api/order/${id}/status`, {field:'status', value:'in_delivery'});
    location.reload();
  } catch(e) { toast('Ошибка: ' + e.message, false); }
}

async function saveTracking(id) {
  const link = (document.getElementById('tracking-input')?.value || '').trim();
  try {
    await api(`/admin-api/order/${id}/tracking`, {link});
    toast('Трек сохранён ✓');
  } catch(e) { toast('Ошибка: ' + e.message, false); }
}

async function sendFeedback(id) {
  try {
    await api(`/admin-api/order/${id}/feedback`, {});
    toast('Запрос отзыва отправлен ✓');
    setTimeout(() => location.reload(), 1200);
  } catch(e) { toast('Ошибка: ' + e.message, false); }
}
"""


# ── CSS ────────────────────────────────────────────────────────────────────────

_CSS = """
.crm-wrap { max-width: 1100px; margin: 0 auto; padding: 0 0 60px; }
.crm-header { display:flex; align-items:center; gap:14px; margin-bottom:24px; flex-wrap:wrap; }
.crm-back { color:#3d5afe; text-decoration:none; font-size:13px; font-weight:600;
            background:#eef1ff; padding:6px 14px; border-radius:8px; }
.crm-back:hover { background:#dde2ff; }
.crm-title { font-size:22px; font-weight:800; color:#1a1d2e; margin:0; }
.crm-status-badge { padding:4px 12px; border-radius:20px; font-size:12px; font-weight:700;
                    background:#eef1ff; color:#3d5afe; }
.crm-status-badge.cancelled { background:#fdecea; color:#d32f2f; }
.crm-status-badge.delivered { background:#e8f5e9; color:#1b873f; }
.crm-date { font-size:13px; color:#8c9aad; margin-left:auto; }

.crm-grid { display:grid; grid-template-columns:320px 1fr; gap:24px; align-items:start; }
@media(max-width:768px){ .crm-grid { grid-template-columns:1fr; } }

.crm-card { background:#fff; border-radius:14px; padding:20px;
            box-shadow:0 2px 10px rgba(0,0,0,.06); margin-bottom:16px; }
.crm-card-title { font-size:12px; font-weight:700; color:#8c9aad; text-transform:uppercase;
                  letter-spacing:.5px; margin:0 0 14px; }
.crm-items { list-style:none; margin:0; padding:0; }
.crm-items li { display:flex; justify-content:space-between; align-items:center;
                padding:8px 0; border-bottom:1px solid #f5f6fa; font-size:13px; }
.crm-items li:last-child { border-bottom:none; }
.crm-items .item-name { color:#1a1d2e; font-weight:500; }
.crm-items .item-price { color:#3d5afe; font-weight:600; }
.crm-total { display:flex; justify-content:space-between; font-size:15px; font-weight:700;
             margin-top:14px; padding-top:14px; border-top:2px solid #f0f2f5; }
.crm-info-row { display:flex; gap:8px; padding:7px 0; font-size:13px;
                border-bottom:1px solid #f5f6fa; }
.crm-info-row:last-child { border-bottom:none; }
.crm-info-label { color:#8c9aad; min-width:90px; }
.crm-info-value { color:#1a1d2e; font-weight:500; word-break:break-all; }

/* Pipeline steps */
.step-card { display:flex; gap:0; margin-bottom:0; }
.sc-left { display:flex; flex-direction:column; align-items:center; width:48px; flex-shrink:0; }
.sc-circle { width:36px; height:36px; border-radius:50%; display:flex; align-items:center;
             justify-content:center; font-size:13px; font-weight:800; flex-shrink:0; z-index:1; }
.sc-connector { flex:1; width:2px; background:#e9ecef; margin:4px 0; min-height:20px; }
.step-card:last-child .sc-connector { display:none; }

.sc-circle-done   { background:#3d5afe; color:#fff; }
.sc-circle-active { background:#3d5afe; color:#fff; box-shadow:0 0 0 5px rgba(61,90,254,.18); }
.sc-circle-future { background:#e9ecef; color:#adb5bd; }

.sc-right { flex:1; padding:0 0 24px 16px; min-width:0; }
.sc-title { font-size:15px; font-weight:700; color:#1a1d2e; margin:4px 0 10px; line-height:1.2; }
.step-card-done   .sc-title { color:#3d5afe; }
.step-card-future .sc-title { color:#adb5bd; }

.sc-body { }
.sc-body-done   { opacity:.7; }
.sc-body-future { opacity:.5; pointer-events:none; }
.done-text   { color:#3d5afe !important; font-size:12px !important; }
.future-text { color:#adb5bd !important; font-size:12px !important; }

.crm-cancelled { background:#fdecea; border-radius:12px; padding:16px 20px;
                 color:#d32f2f; font-weight:600; font-size:15px; }

.crm-hint { font-size:13px; color:#5a6478; margin:0 0 10px; line-height:1.5; }
.crm-input { width:100%; box-sizing:border-box; padding:10px 14px; border-radius:10px;
             border:1.5px solid #dee2e6; font-size:13.5px; outline:none; margin-bottom:10px; }
.crm-input:focus { border-color:#3d5afe; box-shadow:0 0 0 3px rgba(61,90,254,.12); }
.crm-link-preview { background:#f4f6fb; border-radius:8px; padding:10px 14px;
                    font-size:12px; color:#3d5afe; word-break:break-all; margin-bottom:10px; }
.crm-btn-row { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:4px; }
.crm-divider { border:none; border-top:1px solid #f0f2f5; margin:12px 0; }
.crm-btn { display:inline-flex; align-items:center; gap:6px; padding:10px 20px;
           border-radius:10px; font-size:13.5px; font-weight:700; cursor:pointer;
           border:none; transition:opacity .15s, transform .12s; margin-right:8px; margin-bottom:8px; }
.crm-btn:active { transform:scale(.97); }
.crm-btn:disabled { opacity:.4; cursor:not-allowed; }
.crm-btn-primary   { background:#3d5afe; color:#fff; }
.crm-btn-success   { background:#1b873f; color:#fff; }
.crm-btn-danger    { background:#d32f2f; color:#fff; }
.crm-btn-secondary { background:#eef1ff; color:#3d5afe; }
.crm-btn-tg { background:#29b6f6; color:#fff; text-decoration:none; }
.crm-btn-tg:hover { opacity:.88; }

/* Toast */
.crm-toast { position:fixed; bottom:32px; left:50%; transform:translateX(-50%) translateY(20px);
             padding:12px 24px; border-radius:12px; font-size:14px; font-weight:600;
             opacity:0; transition:all .3s; pointer-events:none; z-index:9999; }
.crm-toast.show { opacity:1; transform:translateX(-50%) translateY(0); }
.crm-toast.ok  { background:#1b873f; color:#fff; }
.crm-toast.err { background:#d32f2f; color:#fff; }
"""


# ── main render ────────────────────────────────────────────────────────────────

def render_crm_order(order, admin_username: str = "") -> str:
    now = datetime.now(timezone.utc)
    is_pickup = order.delivery_info and order.delivery_info.type == "pickup"

    status = order.status
    status_label = _ADMIN_LABELS.get(status, status)

    badge_cls = "crm-status-badge"
    if status == "cancelled":
        badge_cls += " cancelled"
    elif status == "delivered":
        badge_cls += " delivered"

    pipeline = _pipeline_pickup(order, now) if is_pickup else _pipeline_delivery(order, now)

    # Items
    items_rows = "".join(
        f'<li><span class="item-name">{_esc(oi.snapshot_name)} {oi.snapshot_weight_g}г × {oi.quantity}</span>'
        f'<span class="item-price">{float(oi.unit_price) * oi.quantity:.0f} ₽</span></li>'
        for oi in (order.items or [])
    )

    # Client info
    user = order.user
    client_rows = ""
    if user:
        client_rows += f'<div class="crm-info-row"><span class="crm-info-label">Имя</span><span class="crm-info-value">{_esc(getattr(user, "display_name", None) or "—")}</span></div>'
        if user.username:
            client_rows += f'<div class="crm-info-row"><span class="crm-info-label">Username</span><span class="crm-info-value"><a href="https://t.me/{_esc(user.username)}" target="_blank">@{_esc(user.username)}</a></span></div>'
        client_rows += f'<div class="crm-info-row"><span class="crm-info-label">Telegram ID</span><span class="crm-info-value">{user.telegram_id}</span></div>'
        if getattr(user, "phone", None):
            client_rows += f'<div class="crm-info-row"><span class="crm-info-label">Телефон</span><span class="crm-info-value">{_esc(user.phone)}</span></div>'

    # Delivery info
    delivery_rows = ""
    if order.delivery_info:
        di = order.delivery_info
        delivery_rows += f'<div class="crm-info-row"><span class="crm-info-label">Тип</span><span class="crm-info-value">{_DELIVERY_TYPE_LABELS.get(di.type, di.type)}</span></div>'
        if di.address:
            delivery_rows += f'<div class="crm-info-row"><span class="crm-info-label">Адрес</span><span class="crm-info-value">{_esc(di.address)}</span></div>'
        if di.contact_phone:
            delivery_rows += f'<div class="crm-info-row"><span class="crm-info-label">Телефон</span><span class="crm-info-value">{_esc(di.contact_phone)}</span></div>'

    if order.comment:
        delivery_rows += f'<div class="crm-info-row"><span class="crm-info-label">Комментарий</span><span class="crm-info-value">{_esc(order.comment)}</span></div>'
    if order.payment_link:
        delivery_rows += f'<div class="crm-info-row"><span class="crm-info-label">Ссылка оплаты</span><span class="crm-info-value"><a href="{_esc(order.payment_link)}" target="_blank">Открыть ↗</a></span></div>'
    if order.tracking_link:
        delivery_rows += f'<div class="crm-info-row"><span class="crm-info-label">Трек</span><span class="crm-info-value"><a href="{_esc(order.tracking_link)}" target="_blank">{_esc(order.tracking_link)}</a></span></div>'
    if order.paid_at:
        delivery_rows += f'<div class="crm-info-row"><span class="crm-info-label">Оплачен</span><span class="crm-info-value">{_fmt_dt(order.paid_at)}</span></div>'
    if order.delivered_at:
        delivery_rows += f'<div class="crm-info-row"><span class="crm-info-label">Доставлен</span><span class="crm-info-value">{_fmt_dt(order.delivered_at)}</span></div>'

    readonly_banner = ""
    if not admin_username:
        readonly_banner = '<div style="background:#fff8e1;border-radius:10px;padding:10px 16px;font-size:13px;color:#795548;margin-bottom:16px">⚠️ Режим просмотра</div>'

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Заказ {_esc(order.number)} — CRM</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"/>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"/>
<style>
body {{ background:#f4f6fb; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }}
{_CSS}
</style>
</head>
<body>
<div class="container-fluid py-4 px-4">
<div class="crm-wrap">
  {readonly_banner}

  <!-- Header -->
  <div class="crm-header">
    <a href="/admin/order/list" class="crm-back">← Все заказы</a>
    <h1 class="crm-title">{_esc(order.number)}</h1>
    <span class="{badge_cls}">{_esc(status_label)}</span>
    <span class="crm-date">{_fmt_dt(order.created_at)}</span>
  </div>

  <div class="crm-grid">
    <!-- Left: info cards -->
    <div>
      <div class="crm-card">
        <p class="crm-card-title">Состав заказа</p>
        <ul class="crm-items">{items_rows}</ul>
        <div class="crm-total">
          <span>Итого</span>
          <span>{float(order.total_amount):.0f} ₽</span>
        </div>
      </div>

      <div class="crm-card">
        <p class="crm-card-title">Клиент</p>
        {client_rows or '<p class="crm-hint">Нет данных</p>'}
      </div>

      <div class="crm-card">
        <p class="crm-card-title">Доставка и детали</p>
        {delivery_rows or '<p class="crm-hint">Нет данных</p>'}
      </div>
    </div>

    <!-- Right: pipeline -->
    <div class="crm-card" style="padding:24px 20px">
      <p class="crm-card-title">Этапы обработки</p>
      {pipeline}
    </div>
  </div>
</div>
</div>

<div id="crm-toast" class="crm-toast"></div>

<script>
{_JS}
</script>
</body>
</html>"""
