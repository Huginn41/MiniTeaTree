App.renderProfile = async function(c) {
  this.setHeader('Профиль');
  let html = '';
  try {
    const [user, ref] = await Promise.all([
      api('/profile/me'),
      api('/referral/info').catch(() => null),
    ]);
    const name = [user.first_name, user.last_name].filter(Boolean).join(' ');
    html = `
      <div class="md-card" style="padding:20px;margin-bottom:16px">
        <div style="display:flex;align-items:center;gap:16px;margin-bottom:${user.bonus_balance > 0 || user.cashback_pct > 0 ? '16' : '0'}px">
          <div class="avatar-circle">${initials(user.first_name, user.last_name)}</div>
          <div>
            <h2 style="font-size:18px;font-weight:700">${esc(name || 'Пользователь')}</h2>
            ${user.username ? `<p style="font-size:13px;color:var(--md-on-surface-variant);margin-top:2px">@${esc(user.username)}</p>` : ''}
            ${user.phone ? `<p style="font-size:13px;color:var(--md-on-surface-variant);margin-top:2px">${esc(user.phone)}</p>` : ''}
          </div>
        </div>
        ${(user.bonus_balance > 0 || user.cashback_pct > 0) ? `
        <div style="display:flex;gap:10px">
          <div style="flex:1;background:linear-gradient(135deg,#1a6b3c,#2d9c5d);border-radius:12px;padding:14px 16px;color:#fff">
            <div style="font-size:11px;opacity:.8;font-weight:600;letter-spacing:.5px;text-transform:uppercase">Баллы</div>
            <div style="font-size:24px;font-weight:700;margin-top:4px">${Math.floor(user.bonus_balance)}</div>
            <div style="font-size:11px;opacity:.7;margin-top:2px">≈ ${Math.floor(user.bonus_balance)} ₽</div>
          </div>
          ${user.cashback_pct > 0 ? `
          <div style="flex:1;background:linear-gradient(135deg,#7c3aed,#a855f7);border-radius:12px;padding:14px 16px;color:#fff">
            <div style="font-size:11px;opacity:.8;font-weight:600;letter-spacing:.5px;text-transform:uppercase">Кешбэк</div>
            <div style="font-size:24px;font-weight:700;margin-top:4px">${user.cashback_pct}%</div>
            <div style="font-size:11px;opacity:.7;margin-top:2px">с каждого заказа</div>
          </div>` : ''}
        </div>` : ''}
      </div>`;

    // Реферальные блоки — онбординг для новых, ссылка для участников
    if (ref) {
      html += App.renderOnboardingBlock(ref);
      html += App.renderReferralSection(ref);
      html += App.renderBonusChecklist(ref);
    }

    try {
      const orders = await api('/orders');
      html += `<p style="font-size:12px;font-weight:600;color:var(--md-on-surface-variant);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:10px">МОИ ЗАКАЗЫ</p>`;
      if (!orders.length) {
        html += `<div class="md-card-filled" style="padding:24px;text-align:center">
          <p style="color:var(--md-on-surface-variant);font-size:14px">Заказов пока нет</p>
          <button class="btn btn-tonal" onclick="App.navigate('catalog')" style="margin-top:12px">Перейти в каталог</button>
        </div>`;
      } else {
        html += `<div style="display:flex;flex-direction:column;gap:8px">
          ${orders.map(o => `
            <button class="order-row" onclick="App.navigate('order-detail', '${o.number}')">
              <div class="order-num-dot">
                <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--md-primary)">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
              </div>
              <div style="flex:1;min-width:0">
                <p style="font-size:14px;font-weight:700;color:var(--md-on-surface)">${o.number}</p>
                <p style="font-size:12px;color:var(--md-on-surface-variant);margin-top:2px">${fmtDate(o.created_at)} · ${o.items_count} шт. · ${fmtPrice(o.total_amount)} ₽</p>
              </div>
              <span class="status-badge ${o.status}">${_statusLabel(o.status)}</span>
              <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" style="color:var(--md-outline);flex-shrink:0">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/>
              </svg>
            </button>
          `).join('')}
        </div>`;
      }
    } catch (_) {}
  } catch (_) {
    html = `<div class="empty-state">
      <div class="empty-icon">🔒</div>
      <h3>Нужна авторизация</h3>
      <p>Откройте приложение через Telegram</p>
    </div>`;
  }
  c.innerHTML = html;
};
