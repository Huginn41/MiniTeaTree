// ─── Реферальная программа ────────────────────────────────────────────────

// Онбординг-блок для новых пользователей (не подписаны на канал).
App.renderOnboardingBlock = function(ref) {
  if (!ref || ref.is_channel_member) return '';
  return `
    <div class="md-card" id="onboarding-block" style="padding:20px;margin-bottom:16px;background:linear-gradient(135deg,#f0fdf4,#dcfce7);border:1.5px solid #86efac">
      <div style="font-size:16px;font-weight:700;color:#166534;margin-bottom:4px">🎁 Добро пожаловать!</div>
      <div style="font-size:13px;color:#166534;margin-bottom:16px">Выполни шаги и стань участником бонусной программы</div>

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

// Карточка с реферальной ссылкой (для участников).
App.renderReferralSection = function(ref) {
  if (!ref || !ref.is_channel_member || !ref.referral_code) return '';

  const link = ref.referral_link || '';
  const slotsTotal = ref.slots_total || 2;
  const slotsUsed = ref.slots_used || 0;

  // Слоты и описание показываем только если есть хотя бы одна покупка
  const slotsBlock = ref.has_purchased ? `
    <div style="font-size:13px;color:var(--md-on-surface-variant);margin:12px 0 10px">
      Первые <b>${slotsTotal} человека</b> по ссылке получат <b>250 бонусных баллов</b> при первой покупке
    </div>
    <div style="display:flex;flex-direction:column;gap:8px">
      ${Array.from({ length: slotsTotal }, (_, i) => {
        const used = i < slotsUsed;
        return `
          <div style="display:flex;align-items:center;gap:8px;padding:10px 12px;background:var(--md-surface-container);border-radius:10px">
            <span style="font-size:16px">${used ? '✅' : '🎁'}</span>
            <div style="flex:1">
              <div style="font-size:13px;font-weight:600;color:var(--md-on-surface)">Подарок для друга</div>
              <div style="font-size:12px;color:var(--md-on-surface-variant);margin-top:2px">${used ? 'Использован' : 'Доступен'}</div>
            </div>
            <div style="font-size:12px;font-weight:700;color:${used ? '#9ca3af' : 'var(--md-primary)'}">
              ${i + 1}/${slotsTotal}
            </div>
          </div>`;
      }).join('')}
    </div>` : '';

  return `
    <div class="md-card" style="padding:20px;margin-bottom:16px">
      <div style="font-size:15px;font-weight:700;margin-bottom:12px">🔗 Реферальная ссылка</div>
      <div style="display:flex;gap:8px;align-items:center">
        <div style="flex:1;background:var(--md-surface-container);border-radius:10px;padding:10px 14px;font-size:13px;font-weight:600;color:var(--md-on-surface);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
          ${esc(link)}
        </div>
        <button
          onclick="App.copyReferralLink('${esc(link)}')"
          style="padding:10px 14px;background:var(--md-primary);color:var(--md-on-primary);border:none;border-radius:10px;font-size:13px;font-weight:700;cursor:pointer;white-space:nowrap">
          Скопировать
        </button>
      </div>
      ${slotsBlock}
    </div>`;
};

// Бонусный чеклист (под карточкой с ссылкой).
App.renderBonusChecklist = function(ref) {
  if (!ref || !ref.is_channel_member || !ref.referral_code) return '';

  const done = ref.has_purchased;
  return `
    <div class="md-card" style="padding:20px;margin-bottom:16px">
      <div style="font-size:15px;font-weight:700;margin-bottom:12px">📋 Бонусный чеклист</div>
      <div style="display:flex;align-items:flex-start;gap:10px">
        <div style="width:22px;height:22px;border-radius:6px;flex-shrink:0;margin-top:1px;
             background:${done ? '#22c55e' : 'var(--md-surface-container)'};
             border:${done ? 'none' : '2px solid #d1d5db'};
             display:flex;align-items:center;justify-content:center;color:#fff;font-size:13px">
          ${done ? '✓' : ''}
        </div>
        <div>
          <div style="font-size:14px;font-weight:600;color:var(--md-on-surface)">
            Соверши покупку и подари 250 баллов друзьям, которые ещё не с нами
          </div>
          ${done
            ? `<div style="font-size:12px;color:#22c55e;margin-top:3px;font-weight:600">Выполнено ✓</div>`
            : `<div style="font-size:12px;color:var(--md-on-surface-variant);margin-top:3px">После покупки активируются подарки для друзей</div>`}
        </div>
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
      tg?.HapticFeedback?.notificationOccurred('success');
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
