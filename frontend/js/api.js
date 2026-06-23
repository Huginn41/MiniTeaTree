// ─── Telegram WebApp ───────────────────────────────────────────────────────
const tg = window.Telegram?.WebApp || null;
if (tg) {
  tg.ready();
  tg.expand();
  tg.setHeaderColor('#2D6A4F');
  tg.setBackgroundColor('#FFFDF5');
}

const API_BASE = '/api';

// ─── Auth headers ──────────────────────────────────────────────────────────
const authHeaders = () => {
  const h = { 'Content-Type': 'application/json' };
  if (tg?.initDataUnsafe?.user) {
    h['Authorization'] = `Bearer ${tg.initData}`;
  } else {
    const t = localStorage.getItem('access_token');
    if (t) h['Authorization'] = `Bearer ${t}`;
  }
  return h;
};

async function api(path, opts = {}) {
  const res = await fetch(API_BASE + path, {
    ...opts,
    headers: { ...authHeaders(), ...(opts.headers || {}) },
  });
  if (res.status === 204) return null;
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Ошибка');
  }
  return res.json();
}
