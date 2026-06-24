// ─── Реферальная программа ────────────────────────────────────────────────

let _svgSeq = 0;

function _gaiwanSvg(remaining, total) {
  const id = 'g' + (++_svgSeq);
  const pct = total > 0 ? remaining / total : 0;
  const hasWater = pct > 0;
  const waterY = pct >= 1 ? 48 : pct > 0 ? 63 : 86;

  const steam = hasWater ? `
    <path d="M30,31 C27,25 33,20 30,15" stroke="#9aab9a" stroke-width="1.8" fill="none" stroke-linecap="round" opacity="0">
      <animate attributeName="opacity" values="0;0.75;0" dur="3s" begin="0s" repeatCount="indefinite"/>
      <animate attributeName="d" values="M30,31 C27,25 33,20 30,15;M30,31 C33,25 27,20 30,15;M30,31 C27,25 33,20 30,15" dur="3s" begin="0s" repeatCount="indefinite"/>
    </path>
    <path d="M40,28 C37,22 43,17 40,12" stroke="#9aab9a" stroke-width="1.8" fill="none" stroke-linecap="round" opacity="0">
      <animate attributeName="opacity" values="0;0.75;0" dur="3s" begin="1s" repeatCount="indefinite"/>
      <animate attributeName="d" values="M40,28 C37,22 43,17 40,12;M40,28 C43,22 37,17 40,12;M40,28 C37,22 43,17 40,12" dur="3s" begin="1s" repeatCount="indefinite"/>
    </path>
    <path d="M50,31 C47,25 53,20 50,15" stroke="#9aab9a" stroke-width="1.8" fill="none" stroke-linecap="round" opacity="0">
      <animate attributeName="opacity" values="0;0.75;0" dur="3s" begin="2s" repeatCount="indefinite"/>
      <animate attributeName="d" values="M50,31 C47,25 53,20 50,15;M50,31 C53,25 47,20 50,15;M50,31 C47,25 53,20 50,15" dur="3s" begin="2s" repeatCount="indefinite"/>
    </path>` : '';

  const water = hasWater ? `
    <g clip-path="url(#${id})">
      <rect x="14" y="${waterY}" width="52" height="50" fill="#c8843c" opacity="0.5"/>
      <path d="M-40,${waterY} Q-30,${waterY - 3.5} -20,${waterY} Q-10,${waterY + 3.5} 0,${waterY} Q10,${waterY - 3.5} 20,${waterY} Q30,${waterY + 3.5} 40,${waterY} Q50,${waterY - 3.5} 60,${waterY} Q70,${waterY + 3.5} 80,${waterY} Q90,${waterY - 3.5} 100,${waterY} Q110,${waterY + 3.5} 120,${waterY} L120,${waterY + 14} L-40,${waterY + 14} Z" fill="#a06828" opacity="0.32">
        <animateTransform attributeName="transform" type="translate" from="0,0" to="40,0" dur="3s" repeatCount="indefinite"/>
      </path>
    </g>` : '';

  return `<div style="display:flex;flex-direction:column;align-items:center;gap:5px">
<svg viewBox="0 0 80 95" width="72" height="86" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <clipPath id="${id}">
      <path d="M18,46 C16,65 20,77 25,79 L55,79 C60,77 64,65 62,46 Z"/>
    </clipPath>
  </defs>
  ${steam}
  <ellipse cx="40" cy="87" rx="27" ry="3.8" fill="#c09050" opacity="0.2"/>
  <ellipse cx="40" cy="85" rx="24.5" ry="3.2" fill="#d4b27a"/>
  <path d="M18,46 C16,65 20,77 25,79 L55,79 C60,77 64,65 62,46 Z" fill="#f0e5cc"/>
  ${water}
  <path d="M18,46 C16,65 20,77 25,79 L55,79 C60,77 64,65 62,46 Z" fill="none" stroke="#c09050" stroke-width="3.5" stroke-linejoin="round"/>
  <ellipse cx="40" cy="46" rx="22" ry="4" fill="#e8d5b2" stroke="#c09050" stroke-width="1.3"/>
  <ellipse cx="40" cy="43.5" rx="19.5" ry="3.5" fill="#d4aa65" stroke="#b89045" stroke-width="0.7"/>
  <path d="M22.5,43.5 Q23,36 40,33 Q57,36 57.5,43.5" fill="#e8c870" stroke="#c4a050" stroke-width="0.9"/>
  <path d="M28,41 Q30,36.5 40,35 Q50,36.5 52,41" fill="none" stroke="#f2de8a" stroke-width="0.7" opacity="0.5"/>
  <ellipse cx="40" cy="33" rx="5.5" ry="2" fill="#c09050"/>
  <ellipse cx="40" cy="31" rx="3.5" ry="2.5" fill="#a87030"/>
  <ellipse cx="39.2" cy="30.2" rx="1.3" ry="0.9" fill="#d4a060" opacity="0.6"/>
</svg>
<div style="font-size:13px;font-weight:700;color:var(--md-on-surface)">${remaining}/${total}</div>
</div>`;
}

function _pialaSvg(filled, idx) {
  const id = 'p' + (++_svgSeq);
  const waterY = filled ? 28 : 56;
  const hasWater = filled;

  const steam = hasWater ? `
    <path d="M18,22 C15,16 21,11 18,7" stroke="#9aab9a" stroke-width="1.4" fill="none" stroke-linecap="round" opacity="0">
      <animate attributeName="opacity" values="0;0.7;0" dur="2.5s" begin="${idx * 0.6}s" repeatCount="indefinite"/>
      <animate attributeName="d" values="M18,22 C15,16 21,11 18,7;M18,22 C21,16 15,11 18,7;M18,22 C15,16 21,11 18,7" dur="2.5s" begin="${idx * 0.6}s" repeatCount="indefinite"/>
    </path>
    <path d="M25,20 C22,14 28,9 25,5" stroke="#9aab9a" stroke-width="1.4" fill="none" stroke-linecap="round" opacity="0">
      <animate attributeName="opacity" values="0;0.7;0" dur="2.5s" begin="${idx * 0.6 + 0.8}s" repeatCount="indefinite"/>
    </path>
    <path d="M32,22 C29,16 35,11 32,7" stroke="#9aab9a" stroke-width="1.4" fill="none" stroke-linecap="round" opacity="0">
      <animate attributeName="opacity" values="0;0.7;0" dur="2.5s" begin="${idx * 0.6 + 1.6}s" repeatCount="indefinite"/>
    </path>` : '';

  const water = hasWater ? `
    <g clip-path="url(#${id})">
      <rect x="5" y="${waterY}" width="40" height="30" fill="#c8843c" opacity="0.5"/>
      <path d="M-20,${waterY} Q-12,${waterY - 2.5} -5,${waterY} Q3,${waterY + 2.5} 10,${waterY} Q18,${waterY - 2.5} 25,${waterY} Q33,${waterY + 2.5} 40,${waterY} Q48,${waterY - 2.5} 55,${waterY} Q63,${waterY + 2.5} 70,${waterY} L70,${waterY + 8} L-20,${waterY + 8} Z" fill="#a06828" opacity="0.32">
        <animateTransform attributeName="transform" type="translate" from="0,0" to="30,0" dur="2.8s" begin="${idx * 0.25}s" repeatCount="indefinite"/>
      </path>
    </g>` : '';

  return `<div style="display:flex;flex-direction:column;align-items:center;gap:4px">
<svg viewBox="0 0 50 58" width="46" height="54" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <clipPath id="${id}">
      <path d="M10,26 C8,43 12,49 16,51 L34,51 C38,49 42,43 40,26 Z"/>
    </clipPath>
  </defs>
  ${steam}
  <ellipse cx="25" cy="55.5" rx="17" ry="2.5" fill="#c09050" opacity="0.18"/>
  <ellipse cx="25" cy="54" rx="15" ry="2.2" fill="#d4b27a"/>
  <path d="M10,26 C8,43 12,49 16,51 L34,51 C38,49 42,43 40,26 Z" fill="#f0e5cc"/>
  ${water}
  <path d="M10,26 C8,43 12,49 16,51 L34,51 C38,49 42,43 40,26 Z" fill="none" stroke="#c09050" stroke-width="2.5" stroke-linejoin="round"/>
  <ellipse cx="25" cy="26" rx="15" ry="2.8" fill="#e8d5b2" stroke="#c09050" stroke-width="1"/>
</svg>
<div style="font-size:11px;font-weight:${filled ? '600' : '400'};color:${filled ? '#22c55e' : 'var(--md-on-surface-variant)'}">
  ${filled ? '✅ Получен' : '🎁 Доступен'}
</div>
</div>`;
}

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
  const slotsLeft = slotsTotal - slotsUsed;

  const statusText = slotsUsed === 0
    ? 'Подарки ждут твоих друзей'
    : slotsUsed >= slotsTotal
      ? 'Все подарки розданы!'
      : `${slotsUsed} из ${slotsTotal} подарков отправлено`;

  const slotsBlock = ref.has_purchased ? `
    <div style="padding-top:14px;margin-top:14px;border-top:1px solid var(--md-outline-variant)">
      <div style="font-size:12px;color:var(--md-on-surface-variant);text-align:center;margin-bottom:14px">
        Первые <b>${slotsTotal}</b> друга получат <b>250 баллов</b> при подписке по твоей ссылке
      </div>
      <div style="display:flex;align-items:flex-end;justify-content:center;gap:20px">
        ${_gaiwanSvg(slotsLeft, slotsTotal)}
        <div style="display:flex;gap:12px;padding-bottom:24px">
          ${Array.from({length: slotsTotal}, (_, i) => _pialaSvg(i < slotsUsed, i)).join('')}
        </div>
      </div>
      <div style="font-size:12px;color:var(--md-on-surface-variant);text-align:center;margin-top:4px">${statusText}</div>
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
            Соверши покупку — разблокируй подарки для друзей
          </div>
          ${done
            ? `<div style="font-size:12px;color:#22c55e;margin-top:3px;font-weight:600">Выполнено ✓</div>`
            : `<div style="font-size:12px;color:var(--md-on-surface-variant);margin-top:3px">После покупки появится счётчик подарков</div>`}
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
