// ─── Utils ─────────────────────────────────────────────────────────────────
function esc(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function imgUrl(path) {
  if (!path) return '';
  if (path.startsWith('http') || path.startsWith('/')) return path;
  return '/static/' + path;
}

function fmtPrice(n) {
  const num = Number(n);
  if (isNaN(num)) return '0';
  return num.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function fmtDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
}

function initials(first, last) {
  return ((first?.[0] || '') + (last?.[0] || '')).toUpperCase() || '?';
}

// ─── Toast ─────────────────────────────────────────────────────────────────
let _toastTimer;
function showToast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove('show'), 2600);
}

// ─── Ripple ────────────────────────────────────────────────────────────────
function addRipple(el) {
  el.addEventListener('click', e => {
    const r = document.createElement('span');
    r.className = 'ripple';
    const rect = el.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    r.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX-rect.left-size/2}px;top:${e.clientY-rect.top-size/2}px`;
    el.appendChild(r);
    setTimeout(() => r.remove(), 500);
  });
}

// ─── Labels ────────────────────────────────────────────────────────────────
function _statusLabel(s) {
  return {
    new: 'В обработке', assembling: 'Собираем', ready: 'Готов к выдаче',
    awaiting_payment: 'Ожидает оплату', in_delivery: 'В пути',
    at_pvz: 'В пункте выдачи', delivered: 'Получен', cancelled: 'Отменён',
  }[s] || s;
}
