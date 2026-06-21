"""HTML-шаблон CRM-страницы заказа (пошаговый интерфейс)."""

from __future__ import annotations

from datetime import datetime, timezone


# ── константы ──────────────────────────────────────────────────────────────────

_DELIVERY_STEPS = ["new", "awaiting_payment", "in_delivery", "at_pvz", "delivered"]
_PICKUP_STEPS   = ["new", "assembling", "ready", "delivered"]

_STEP_LABELS_DELIVERY = ["Новый", "Ожидает оплаты", "В доставке", "В ПВЗ", "Доставлен"]
_STEP_LABELS_PICKUP   = ["Новый", "Собираем", "Готов", "Доставлен"]

_CLIENT_LABELS = {
    "new": "В обработке", "assembling": "Собираем", "ready": "Готов к выдаче",
    "awaiting_payment": "Ожидает оплату", "in_delivery": "В пути",
    "at_pvz": "В пункте выдачи", "delivered": "Получен", "cancelled": "Отменён",
}
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
    from datetime import timezone as tz
    import zoneinfo
    msk = zoneinfo.ZoneInfo("Europe/Moscow")
    return dt.replace(tzinfo=tz.utc).astimezone(msk).strftime("%d.%m.%Y %H:%M")


# ── steps progress bar ─────────────────────────────────────────────────────────

def _steps_html(steps: list[str], labels: list[str], current: str) -> str:
    try:
        cur_idx = steps.index(current)
    except ValueError:
        cur_idx = -1

    items = []
    for i, (s, lbl) in enumerate(zip(steps, labels)):
        if i < cur_idx:
            cls = "step-done"
            icon = "✓"
        elif i == cur_idx:
            cls = "step-active"
            icon = str(i + 1)
        else:
            cls = "step-future"
            icon = str(i + 1)

        connector = '<div class="step-line"></div>' if i < len(steps) - 1 else ""
        items.append(
            f'<div class="step-item {cls}">'
            f'  <div class="step-circle">{icon}</div>'
            f'  <div class="step-label">{_esc(lbl)}</div>'
            f'</div>'
            f'{connector}'
        )
    return f'<div class="steps-bar">{"".join(items)}</div>'


# ── action cards ───────────────────────────────────────────────────────────────

def _card(title: str, body: str, color: str = "#3d5afe") -> str:
    return (
        f'<div class="action-card" style="--card-accent:{color}">'
        f'  <div class="action-title">{title}</div>'
        f'  {body}'
        f'</div>'
    )


def _btn(label: str, onclick: str, style: str = "primary", disabled: bool = False) -> str:
    dis = 'disabled title="Недоступно"' if disabled else ""
    return f'<button class="crm-btn crm-btn-{style}" onclick="{_esc(onclick)}" {dis}>{label}</button>'


def _action_delivery(order, now: datetime) -> str:
    status = order.status
    order_id = order.id

    if status == "cancelled":
        return _card("❌ Заказ отменён", '<p class="crm-hint">Этот заказ был отменён.</p>', "#d32f2f")

    if status == "new":
        if order.payment_link:
            # Ссылка уже отправлена через бота
            body = (
                f'<p class="crm-hint">✅ Ссылка на оплату отправлена клиенту через бота:</p>'
                f'<div class="crm-link-preview">{_esc(order.payment_link)}</div>'
                f'<p class="crm-hint" style="margin-top:12px">Статус обновится автоматически когда вы нажмёте кнопку:</p>'
                + _btn("💳 Перейти к ожиданию оплаты", f"changeStatus({order_id},'awaiting_payment')")
            )
        else:
            body = (
                '<p class="crm-hint">Отправьте клиенту ссылку на оплату. '
                'Можно также отправить через кнопку в уведомлении бота.</p>'
                '<input id="pay-link-input" class="crm-input" type="url" placeholder="https://..." />'
                + _btn("💳 Отправить ссылку клиенту", f"sendPaymentLink({order_id})")
            )
        return _card("💳 Шаг 1 — Ссылка на оплату", body)

    if status == "awaiting_payment":
        link_info = ""
        if order.payment_link:
            link_info = f'<div class="crm-link-preview" style="margin-bottom:16px">{_esc(order.payment_link)}</div>'
        body = (
            f'{link_info}'
            '<p class="crm-hint">Проверьте поступление оплаты от клиента.</p>'
            '<div class="crm-btn-row">'
            + _btn("✅ Да, оплачено", f"confirmPaid({order_id})", "success")
            + _btn("❌ Отменить заказ", f"changeStatus({order_id},'cancelled')", "danger")
            + '</div>'
            '<div id="paid-section" style="display:none;margin-top:20px">'
            f'  <div class="crm-divider"></div>'
            f'  <p class="crm-hint" style="font-weight:600;margin-bottom:12px">📦 Доставка</p>'
            f'  {_contact_btn(order)}'
            f'  <p class="crm-hint" style="margin-top:16px">Вставьте трек-номер или ссылку для отслеживания:</p>'
            f'  <input id="tracking-input" class="crm-input" type="text" '
            f'         placeholder="Номер трека / ссылка" value="{_esc(order.tracking_link or "")}" />'
            + _btn("🚚 Передать в доставку", f"sendToDelivery({order_id})", "primary")
            + '</div>'
        )
        return _card("⏳ Шаг 2 — Ожидание оплаты", body)

    if status == "in_delivery":
        body = (
            f'{_contact_btn(order)}'
            '<p class="crm-hint" style="margin-top:16px">Трек-номер / ссылка для отслеживания:</p>'
            f'<input id="tracking-input" class="crm-input" type="text" '
            f'       placeholder="Трек-номер" value="{_esc(order.tracking_link or "")}" />'
            + _btn("Сохранить трек", f"saveTracking({order_id})", "secondary")
            + '<div class="crm-divider"></div>'
            '<p class="crm-hint">Когда заказ прибыл в пункт выдачи:</p>'
            + _btn("🏪 Отметить: В ПВЗ", f"changeStatus({order_id},'at_pvz')", "primary")
        )
        return _card("🚚 Шаг 3 — В доставке", body)

    if status == "at_pvz":
        body = (
            '<p class="crm-hint">Клиент получил уведомление о том, что заказ в пункте выдачи.</p>'
            + _btn("🎉 Отметить: Доставлен", f"changeStatus({order_id},'delivered')", "success")
        )
        return _card("🏪 Шаг 4 — В пункте выдачи", body, "#1b873f")

    if status == "delivered":
        return _delivered_card(order, now)

    return _card("Статус", f'<p class="crm-hint">{_ADMIN_LABELS.get(status, status)}</p>')


def _action_pickup(order, now: datetime) -> str:
    status = order.status
    order_id = order.id

    if status == "cancelled":
        return _card("❌ Заказ отменён", '<p class="crm-hint">Этот заказ был отменён.</p>', "#d32f2f")

    if status == "new":
        body = (
            '<p class="crm-hint">Начните сборку заказа.</p>'
            + _btn("📦 Начать сборку", f"changeStatus({order_id},'assembling')", "primary")
        )
        return _card("🆕 Шаг 1 — Новый заказ", body)

    if status == "assembling":
        body = (
            '<p class="crm-hint">Когда заказ собран и готов — уведомите клиента.</p>'
            + _btn("✅ Готов к выдаче", f"changeStatus({order_id},'ready')", "success")
        )
        return _card("📦 Шаг 2 — Собираем", body)

    if status == "ready":
        body = (
            f'{_contact_btn(order)}'
            '<div class="crm-divider"></div>'
            '<p class="crm-hint">Когда клиент пришёл, получил заказ и оплатил:</p>'
            + _btn("🎉 Выдан клиенту", f"changeStatus({order_id},'delivered')", "success")
        )
        return _card("✅ Шаг 3 — Готов к выдаче", body, "#1b873f")

    if status == "delivered":
        return _delivered_card(order, now)

    return _card("Статус", f'<p class="crm-hint">{_ADMIN_LABELS.get(status, status)}</p>')


def _contact_btn(order) -> str:
    user = order.user
    if not user:
        return '<p class="crm-hint">Данные клиента недоступны.</p>'
    if user.username:
        href = f"https://t.me/{user.username}"
    else:
        href = f"tg://user?id={user.telegram_id}"
    name = _esc(user.display_name or f"ID {user.telegram_id}")
    return (
        f'<a href="{href}" target="_blank" class="crm-btn crm-btn-tg">'
        f'  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">'
        f'    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0z"/>'
        f'    <path fill="white" d="M17.5 7.5l-2.5 11-3.5-3-2 2-1-4.5L5 12l12.5-4.5z"/>'
        f'  </svg>'
        f'  Написать {name} в Telegram'
        f'</a>'
    )


def _delivered_card(order, now: datetime) -> str:
    delivered_at = order.delivered_at
    days_since = 0
    if delivered_at:
        delta = now - delivered_at.replace(tzinfo=timezone.utc)
        days_since = delta.days

    feedback_sent = bool(getattr(order, "feedback_sent_at", None))
    feedback_disabled = days_since < 3

    body = (
        '<p class="crm-hint">🎉 Заказ успешно доставлен!</p>'
        '<div class="crm-divider"></div>'
        '<p class="crm-hint" style="font-weight:600">Обратная связь</p>'
    )
    if feedback_sent:
        body += '<p class="crm-hint">✅ Запрос обратной связи уже отправлен клиенту.</p>'
        body += _btn("💬 Запросить обратную связь", "", "secondary", disabled=True)
    elif feedback_disabled:
        days_left = 3 - days_since
        body += (
            f'<p class="crm-hint">Кнопка станет активной через {days_left} д. '
            f'(через 3 дня после доставки)</p>'
            + _btn("💬 Запросить обратную связь", "", "secondary", disabled=True)
        )
    else:
        body += (
            '<p class="crm-hint">Пора запросить обратную связь у клиента!</p>'
            + _btn("💬 Отправить запрос", f"sendFeedback({order.id})", "success")
        )
    return _card("🎉 Заказ доставлен", body, "#1b873f")


# ── JS ─────────────────────────────────────────────────────────────────────────

_JS = """
async function api(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t);
  }
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
  const link = document.getElementById('pay-link-input').value.trim();
  if (!link.startsWith('http')) { toast('Введите корректную ссылку', false); return; }
  try {
    await api(`/admin-api/order/${id}/payment-link`, {link});
    location.reload();
  } catch(e) { toast('Ошибка: ' + e.message, false); }
}

function confirmPaid(id) {
  document.getElementById('paid-section').style.display = 'block';
  // scroll to it
  document.getElementById('paid-section').scrollIntoView({behavior:'smooth', block:'nearest'});
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
    toast('Сообщение с запросом обратной связи отправлено ✓');
  } catch(e) { toast('Ошибка: ' + e.message, false); }
}
"""


# ── CSS ────────────────────────────────────────────────────────────────────────

_CSS = """
.crm-wrap { max-width: 1100px; margin: 0 auto; padding: 0 0 40px; }
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

.crm-grid { display:grid; grid-template-columns:320px 1fr; gap:20px; align-items:start; }
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

/* Steps */
.steps-bar { display:flex; align-items:center; margin-bottom:20px; }
.step-item { display:flex; flex-direction:column; align-items:center; gap:6px; }
.step-circle { width:32px; height:32px; border-radius:50%; display:flex; align-items:center;
               justify-content:center; font-size:13px; font-weight:700; flex-shrink:0; }
.step-label { font-size:11px; font-weight:600; text-align:center; max-width:70px; line-height:1.2; }
.step-done .step-circle { background:#3d5afe; color:#fff; }
.step-done .step-label { color:#3d5afe; }
.step-active .step-circle { background:#3d5afe; color:#fff;
                             box-shadow:0 0 0 4px rgba(61,90,254,.2); }
.step-active .step-label { color:#3d5afe; font-weight:800; }
.step-future .step-circle { background:#eef1ff; color:#8c9aad; }
.step-future .step-label { color:#8c9aad; }
.step-line { flex:1; height:2px; background:#eef1ff; min-width:16px; margin-bottom:20px; }
.step-done + .step-line { background:#3d5afe; }

/* Action card */
.action-card { background:#fff; border-radius:14px; padding:24px;
               box-shadow:0 2px 10px rgba(0,0,0,.06);
               border-top:4px solid var(--card-accent,#3d5afe); }
.action-title { font-size:16px; font-weight:800; color:#1a1d2e; margin-bottom:16px; }
.crm-hint { font-size:13px; color:#5a6478; margin:0 0 12px; line-height:1.5; }
.crm-input { width:100%; box-sizing:border-box; padding:10px 14px; border-radius:10px;
             border:1.5px solid #dee2e6; font-size:13.5px; outline:none; margin-bottom:12px; }
.crm-input:focus { border-color:#3d5afe; box-shadow:0 0 0 3px rgba(61,90,254,.12); }
.crm-link-preview { background:#f4f6fb; border-radius:8px; padding:10px 14px;
                    font-size:12px; color:#3d5afe; word-break:break-all; }
.crm-btn-row { display:flex; gap:10px; flex-wrap:wrap; }
.crm-divider { border:none; border-top:1px solid #f0f2f5; margin:16px 0; }
.crm-btn { display:inline-flex; align-items:center; gap:6px; padding:10px 20px;
           border-radius:10px; font-size:13.5px; font-weight:700; cursor:pointer;
           border:none; transition:opacity .15s, transform .12s; margin-right:8px; margin-bottom:8px; }
.crm-btn:active { transform:scale(.97); }
.crm-btn:disabled { opacity:.45; cursor:not-allowed; }
.crm-btn-primary { background:#3d5afe; color:#fff; }
.crm-btn-success { background:#1b873f; color:#fff; }
.crm-btn-danger  { background:#d32f2f; color:#fff; }
.crm-btn-secondary { background:#eef1ff; color:#3d5afe; }
.crm-btn-tg { background:#29b6f6; color:#fff; text-decoration:none; margin-bottom:0; }
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
    """Рендерит полную HTML-страницу CRM для заказа."""
    now = datetime.now(timezone.utc)
    is_pickup = order.delivery_info and order.delivery_info.type == "pickup"

    status = order.status
    status_label = _ADMIN_LABELS.get(status, status)

    badge_cls = "crm-status-badge"
    if status == "cancelled":
        badge_cls += " cancelled"
    elif status == "delivered":
        badge_cls += " delivered"

    # Steps
    if status == "cancelled":
        steps_html = '<p style="color:#d32f2f;font-weight:600;font-size:13px">❌ Заказ отменён</p>'
    elif is_pickup:
        steps_html = _steps_html(_PICKUP_STEPS, _STEP_LABELS_PICKUP, status)
    else:
        steps_html = _steps_html(_DELIVERY_STEPS, _STEP_LABELS_DELIVERY, status)

    # Action card
    if is_pickup:
        action_html = _action_pickup(order, now)
    else:
        action_html = _action_delivery(order, now)

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
        client_rows += f'<div class="crm-info-row"><span class="crm-info-label">Имя</span><span class="crm-info-value">{_esc(user.display_name or "—")}</span></div>'
        if user.username:
            client_rows += f'<div class="crm-info-row"><span class="crm-info-label">Username</span><span class="crm-info-value"><a href="https://t.me/{_esc(user.username)}" target="_blank">@{_esc(user.username)}</a></span></div>'
        client_rows += f'<div class="crm-info-row"><span class="crm-info-label">Telegram ID</span><span class="crm-info-value">{user.telegram_id}</span></div>'
        if user.phone:
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
        delivery_rows += f'<div class="crm-info-row"><span class="crm-info-label">Ссылка оплаты</span><span class="crm-info-value"><a href="{_esc(order.payment_link)}" target="_blank">Ссылка</a></span></div>'

    if order.tracking_link:
        delivery_rows += f'<div class="crm-info-row"><span class="crm-info-label">Трек</span><span class="crm-info-value"><a href="{_esc(order.tracking_link)}" target="_blank">{_esc(order.tracking_link)}</a></span></div>'

    if order.paid_at:
        delivery_rows += f'<div class="crm-info-row"><span class="crm-info-label">Оплачен</span><span class="crm-info-value">{_fmt_dt(order.paid_at)}</span></div>'
    if order.delivered_at:
        delivery_rows += f'<div class="crm-info-row"><span class="crm-info-label">Доставлен</span><span class="crm-info-value">{_fmt_dt(order.delivered_at)}</span></div>'

    readonly_banner = ""
    if not admin_username:
        readonly_banner = '<div style="background:#fff8e1;border-radius:10px;padding:10px 16px;font-size:13px;color:#795548;margin-bottom:16px">⚠️ Режим просмотра — только чтение</div>'

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
    <a href="/admin/order/list" class="crm-back">← Заказы</a>
    <h1 class="crm-title">{_esc(order.number)}</h1>
    <span class="{badge_cls}">{_esc(status_label)}</span>
    <span class="crm-date">{_fmt_dt(order.created_at)}</span>
  </div>

  <div class="crm-grid">
    <!-- Left: info -->
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
        <p class="crm-card-title">Доставка</p>
        {delivery_rows or '<p class="crm-hint">Нет данных</p>'}
      </div>
    </div>

    <!-- Right: steps + action -->
    <div>
      {steps_html}
      {action_html}
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
