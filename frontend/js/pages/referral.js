// ─── Реферальная программа ────────────────────────────────────────────────

// Онбординг-блок для новых пользователей (не подписаны на канал).
App.renderOnboardingBlock = function(ref) {
  if (!ref || ref.is_channel_member) return '';
  return `
    <div class="md-card" id="onboarding-block" style="padding:20px;margin-bottom:16px;background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:1.5px solid #86efac">
      <div style="font-size:16px;font-weight:700;color:#166534;margin-bottom:4px">🎁 Добро пожаловать!</div>
      <div style="font-size:13px;color:#166534;margin-bottom:16px">Выполни шаги и получи <b>250 бонусных баллов</b></div>

      <div style="display:flex;flex-direction:column;gap:10px;margin-bottom:16px">
        <div style="display:flex;align-items:center;gap:10px">
          <div style="width:28px;height:28px;border-radius:50%;background:#22c55e;display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;flex-shrink:0">✓</div>
          <span style="font-size:14px;color:#166534;font-weight:600">Зайти в MiniTeaTree</span>
        </div>
        <div style="display:flex;align-items:center;gap:10px">
          <div style="width:28px;height:28px;border-radius:50%;background:#e5e7eb;display:flex;align-items:center;justify-content:center;color:#6b7280;font-size:13px;font-weight:700;flex-shrink:0">2</div>
          <div style="flex:1">
            <span style="font-size:14px;color:#374151;font-weight:600">Подписаться на канал</span>
            <div style="margin-top:4px">
              <a href="https://t.me/tea_ekb" target="_blank"
                 style="font-size:13px;color:#2563eb;text-decoration:none;font-weight:600">→ Перейти в канал</a>
            </div>
          </div>
        </div>
      </div>

      <button
        id="claim-btn"
        onclick="App.claimReferralBonus()"
        style="width:100%;padding:12px;background:#22c55e;color:#fff;border:none;border-radius:12px;font-size:15px;font-weight:700;cursor:pointer">
        Готово
      </button>
      <div id="claim-msg" style="display:none;margin-top:10px;font-size:13px;text-align:center;color:#166534"></div>
    </div>`;
};

// Реферальная секция для участников (подписаны на канал).
App.renderReferralSection = function(ref) {
  if (!ref || !ref.is_channel_member || !ref.referral_code) return '';

  const link = ref.referral_link || '';
  const slotsTotal = ref.slots_total || 2;
  const slotsUsed = ref.slots_used || 0;

  const slotsHtml = Array.from({ length: slotsTotal }, (_, i) => {
    const used = i < slotsUsed;
    return `
      <div style="display:flex;align-items:center;gap:8px;padding:10px 12px;background:var(--md-surface-container);border-radius:10px">
        <span style="font-size:16px">${used ? '✅' : '🎁'}</span>
        <div style="flex:1">
          <div style="font-size:13px;font-weight:600;color:var(--md-on-surface)">Подарок 250 баллов для друга</div>
          <div style="font-size:12px;color:var(--md-on-surface-variant);margin-top:2px">${used ? 'Использован' : 'Доступен — другу начислится при первой покупке'}</div>
        </div>
        <div style="font-size:12px;font-weight:700;color:${used ? '#6b7280' : 'var(--md-primary)'}">
          ${i + 1}/${slotsTotal}
        </div>
      </div>`;
  }).join('');

  return `
    <div class="md-card" style="padding:20px;margin-bottom:16px">
      <div style="font-size:15px;font-weight:700;margin-bottom:4px">🔗 Пригласи друзей</div>
      <div style="font-size:13px;color:var(--md-on-surface-variant);margin-bottom:14px">
        Друг получит <b>250 баллов</b> при первой покупке · ты получаешь <b>5% с первых 3 покупок</b>
      </div>

      <div style="display:flex;gap:8px;align-items:center;margin-bottom:14px">
        <div style="flex:1;background:var(--md-surface-container);border-radius:10px;padding:10px 14px;font-size:13px;font-weight:600;color:var(--md-on-surface);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
          ${esc(link)}
        </div>
        <button
          onclick="App.copyReferralLink('${esc(link)}')"
          style="padding:10px 14px;background:var(--md-primary);color:var(--md-on-primary);border:none;border-radius:10px;font-size:13px;font-weight:700;cursor:pointer;white-space:nowrap">
          Скопировать
        </button>
      </div>

      <div style="display:flex;flex-direction:column;gap:8px">
        ${slotsHtml}
      </div>
    </div>`;
};

App.copyReferralLink = function(link) {
  if (navigator.clipboard) {
    navigator.clipboard.writeText(link).then(() => showToast('Ссылка скопирована'));
  } else {
    const el = document.createElement('textarea');
    el.value = link;
    document.body.appendChild(el);
    el.select();
    document.execCommand('copy');
    document.body.removeChild(el);
    showToast('Ссылка скопирована');
  }
};

App.claimReferralBonus = async function() {
  const btn = document.getElementById('claim-btn');
  const msg = document.getElementById('claim-msg');
  if (!btn) return;

  btn.disabled = true;
  btn.textContent = 'Проверяем...';

  try {
    const res = await api('/referral/claim', { method: 'POST' });
    if (res.success) {
      if (res.bonus_awarded > 0) {
        showToast(`+${res.bonus_awarded} баллов зачислено!`);
        tg?.HapticFeedback?.notificationOccurred('success');
      }
      App.navigate('profile');
    } else {
      btn.disabled = false;
      btn.textContent = 'Готово';
      msg.style.display = 'block';
      msg.style.color = '#dc2626';
      msg.textContent = 'Подписка не найдена. Подпишись на канал и попробуй ещё раз.';
    }
  } catch (err) {
    btn.disabled = false;
    btn.textContent = 'Готово';
    msg.style.display = 'block';
    msg.style.color = '#dc2626';
    msg.textContent = err.message;
  }
};
