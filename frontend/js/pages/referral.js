// ─── Реферальная программа ────────────────────────────────────────────────

let _svgSeq = 0;

function _gaiwanSvg(remaining, total) {
  const id = 'g' + (++_svgSeq);
  const pct = total > 0 ? remaining / total : 0;
  const hasWater = pct > 0;
  // Bowl interior runs y=48..80. waterY = top of water surface.
  const waterY = pct >= 1 ? 50 : pct > 0 ? 65 : 94;

  const steam = hasWater ? `
    <path d="M38,30 C35,24 41,18 38,12" stroke="#a8c8d0" stroke-width="1.8" fill="none" stroke-linecap="round" opacity="0">
      <animate attributeName="opacity" values="0;0.9;0" dur="3s" begin="0s" repeatCount="indefinite"/>
      <animate attributeName="d" values="M38,30 C35,24 41,18 38,12;M38,30 C41,24 35,18 38,12;M38,30 C35,24 41,18 38,12" dur="3s" begin="0s" repeatCount="indefinite"/>
    </path>
    <path d="M50,28 C47,22 53,16 50,10" stroke="#a8c8d0" stroke-width="1.8" fill="none" stroke-linecap="round" opacity="0">
      <animate attributeName="opacity" values="0;0.9;0" dur="3s" begin="1s" repeatCount="indefinite"/>
      <animate attributeName="d" values="M50,28 C47,22 53,16 50,10;M50,28 C53,22 47,16 50,10;M50,28 C47,22 53,16 50,10" dur="3s" begin="1s" repeatCount="indefinite"/>
    </path>
    <path d="M62,30 C59,24 65,18 62,12" stroke="#a8c8d0" stroke-width="1.8" fill="none" stroke-linecap="round" opacity="0">
      <animate attributeName="opacity" values="0;0.9;0" dur="3s" begin="2s" repeatCount="indefinite"/>
      <animate attributeName="d" values="M62,30 C59,24 65,18 62,12;M62,30 C65,24 59,18 62,12;M62,30 C59,24 65,18 62,12" dur="3s" begin="2s" repeatCount="indefinite"/>
    </path>` : '';

  const water = hasWater ? `
    <g clip-path="url(#${id})">
      <rect x="16" y="${waterY}" width="68" height="48" fill="#c8a040" opacity="0.38"/>
      <path d="M-10,${waterY} Q15,${waterY - 4} 40,${waterY} Q65,${waterY + 4} 90,${waterY} Q115,${waterY - 4} 140,${waterY} L140,${waterY + 14} L-10,${waterY + 14} Z" fill="#a07820" opacity="0.26">
        <animateTransform attributeName="transform" type="translate" from="0,0" to="50,0" dur="4s" repeatCount="indefinite"/>
      </path>
    </g>` : '';

  return `<div style="display:flex;flex-direction:column;align-items:center;gap:5px">
<svg viewBox="0 0 100 112" width="84" height="94" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <clipPath id="${id}">
      <path d="M22,48 C20,62 23,74 28,80 L72,80 C77,74 80,62 78,48 Z"/>
    </clipPath>
  </defs>

  ${steam}

  <!-- Ground shadow -->
  <ellipse cx="50" cy="106" rx="34" ry="4" fill="#5060a0" opacity="0.09"/>

  <!-- Saucer -->
  <path d="M12,93 Q13,86 50,84 Q87,86 88,93 Q87,100 50,99 Q13,100 12,93 Z" fill="#e8f0fa" stroke="#5878c0" stroke-width="1.3"/>
  <ellipse cx="50" cy="92" rx="21" ry="3.5" fill="#d4e4f5" stroke="#5878c0" stroke-width="0.7" opacity="0.8"/>

  <!-- Bowl body -->
  <path d="M22,48 C20,62 23,74 28,80 L72,80 C77,74 80,62 78,48 Z" fill="#f0f6ff"/>

  <!-- Water -->
  ${water}

  <!-- === Floral decoration (blue-and-white porcelain) === -->
  <!-- Large chrysanthemum, right -->
  <g transform="translate(65,64)" opacity="0.62">
    <ellipse cx="0" cy="-9" rx="2.6" ry="4.8" fill="#4070c0"/>
    <ellipse cx="0" cy="-9" rx="2.6" ry="4.8" fill="#4070c0" transform="rotate(45)"/>
    <ellipse cx="0" cy="-9" rx="2.6" ry="4.8" fill="#4070c0" transform="rotate(90)"/>
    <ellipse cx="0" cy="-9" rx="2.6" ry="4.8" fill="#4070c0" transform="rotate(135)"/>
    <ellipse cx="0" cy="-9" rx="2.6" ry="4.8" fill="#4070c0" transform="rotate(180)"/>
    <ellipse cx="0" cy="-9" rx="2.6" ry="4.8" fill="#4070c0" transform="rotate(225)"/>
    <ellipse cx="0" cy="-9" rx="2.6" ry="4.8" fill="#4070c0" transform="rotate(270)"/>
    <ellipse cx="0" cy="-9" rx="2.6" ry="4.8" fill="#4070c0" transform="rotate(315)"/>
    <circle cx="0" cy="0" r="4" fill="#2050a0"/>
    <circle cx="0" cy="0" r="2" fill="#3468c0"/>
  </g>
  <!-- Small flower, left -->
  <g transform="translate(34,60)" opacity="0.58">
    <ellipse cx="0" cy="-7" rx="2" ry="3.8" fill="#5080d0" transform="rotate(0)"/>
    <ellipse cx="0" cy="-7" rx="2" ry="3.8" fill="#5080d0" transform="rotate(60)"/>
    <ellipse cx="0" cy="-7" rx="2" ry="3.8" fill="#5080d0" transform="rotate(120)"/>
    <ellipse cx="0" cy="-7" rx="2" ry="3.8" fill="#5080d0" transform="rotate(180)"/>
    <ellipse cx="0" cy="-7" rx="2" ry="3.8" fill="#5080d0" transform="rotate(240)"/>
    <ellipse cx="0" cy="-7" rx="2" ry="3.8" fill="#5080d0" transform="rotate(300)"/>
    <circle cx="0" cy="0" r="3" fill="#2858b0"/>
  </g>
  <!-- Vine -->
  <path d="M40,71 C45,67 53,66 57,69" fill="none" stroke="#4070c0" stroke-width="1" opacity="0.45"/>
  <path d="M47,67 C47,62 51,59 55,62" fill="none" stroke="#4070c0" stroke-width="0.9" opacity="0.45"/>
  <!-- Butterfly -->
  <g transform="translate(49,55)" opacity="0.7">
    <path d="M0,0 C-3,-5 -9,-3 -7,0 C-5,3 -2,2 0,0" fill="#c04828"/>
    <path d="M0,0 C3,-5 9,-3 7,0 C5,3 2,2 0,0" fill="#c04828"/>
    <path d="M0,0 C-2,3 -5,6 -4,8 C-2,9 -1,6 0,0" fill="#9c3820"/>
    <path d="M0,0 C2,3 5,6 4,8 C2,9 1,6 0,0" fill="#9c3820"/>
    <line x1="0" y1="-2" x2="0" y2="9" stroke="#301008" stroke-width="0.7"/>
  </g>
  <!-- Scattered petals -->
  <circle cx="43" cy="74" r="1.5" fill="#5080d0" opacity="0.4"/>
  <circle cx="59" cy="72" r="1.5" fill="#5080d0" opacity="0.4"/>

  <!-- Left wall shine -->
  <path d="M24,52 C22,63 24,72 27,79" fill="none" stroke="white" stroke-width="4.5" stroke-linecap="round" opacity="0.32"/>

  <!-- Bowl outline -->
  <path d="M22,48 C20,62 23,74 28,80 L72,80 C77,74 80,62 78,48 Z" fill="none" stroke="#5878c0" stroke-width="1.8"/>

  <!-- Bowl bottom rim (sits in saucer) -->
  <ellipse cx="50" cy="80" rx="22" ry="3.8" fill="#dce8f5" stroke="#5878c0" stroke-width="1.1"/>

  <!-- Bowl top flared rim -->
  <ellipse cx="50" cy="48" rx="29" ry="5.2" fill="#e4eeff" stroke="#5878c0" stroke-width="1.4"/>
  <ellipse cx="50" cy="47" rx="25" ry="3.8" fill="#f2f8ff"/>

  <!-- Lid collar (overhangs bowl rim) -->
  <ellipse cx="50" cy="44" rx="27" ry="4.8" fill="#dce8f8" stroke="#5878c0" stroke-width="1.3"/>
  <ellipse cx="50" cy="43" rx="23" ry="3.4" fill="#eef5ff"/>

  <!-- Lid dome -->
  <path d="M27,43 Q28,35 50,32 Q72,35 73,43" fill="#eaf3ff" stroke="#5878c0" stroke-width="1.3"/>
  <!-- Lid dome highlight -->
  <path d="M32,41 Q35,36 50,34" fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" opacity="0.52"/>

  <!-- Small flower on lid -->
  <g transform="translate(67,37)" opacity="0.48">
    <ellipse cx="0" cy="-4.8" rx="1.6" ry="2.8" fill="#4070c0" transform="rotate(0)"/>
    <ellipse cx="0" cy="-4.8" rx="1.6" ry="2.8" fill="#4070c0" transform="rotate(60)"/>
    <ellipse cx="0" cy="-4.8" rx="1.6" ry="2.8" fill="#4070c0" transform="rotate(120)"/>
    <ellipse cx="0" cy="-4.8" rx="1.6" ry="2.8" fill="#4070c0" transform="rotate(180)"/>
    <ellipse cx="0" cy="-4.8" rx="1.6" ry="2.8" fill="#4070c0" transform="rotate(240)"/>
    <ellipse cx="0" cy="-4.8" rx="1.6" ry="2.8" fill="#4070c0" transform="rotate(300)"/>
    <circle cx="0" cy="0" r="2" fill="#2858a8"/>
  </g>

  <!-- Jade knob -->
  <ellipse cx="50" cy="32.5" rx="9" ry="6" fill="#50c898" stroke="#30a070" stroke-width="1.3"/>
  <ellipse cx="50" cy="30" rx="7" ry="4.5" fill="#72e0b0" stroke="#30a070" stroke-width="0.9"/>
  <ellipse cx="48.8" cy="28.5" rx="2.8" ry="1.7" fill="#a8f0d8" opacity="0.65"/>
</svg>
<div style="font-size:13px;font-weight:700;color:var(--md-on-surface)">${remaining}/${total}</div>
</div>`;
}

function _pialaSvg(filled, idx) {
  const id = 'p' + (++_svgSeq);
  // Cup interior: y=23..56. waterY = top of water.
  const waterY = filled ? 25 : 62;
  const hasWater = filled;

  const steam = hasWater ? `
    <path d="M19,18 C16,12 22,7 19,3" stroke="#a8c8d0" stroke-width="1.5" fill="none" stroke-linecap="round" opacity="0">
      <animate attributeName="opacity" values="0;0.85;0" dur="2.8s" begin="${idx * 0.8}s" repeatCount="indefinite"/>
      <animate attributeName="d" values="M19,18 C16,12 22,7 19,3;M19,18 C22,12 16,7 19,3;M19,18 C16,12 22,7 19,3" dur="2.8s" begin="${idx * 0.8}s" repeatCount="indefinite"/>
    </path>
    <path d="M28,16 C25,10 31,5 28,1" stroke="#a8c8d0" stroke-width="1.5" fill="none" stroke-linecap="round" opacity="0">
      <animate attributeName="opacity" values="0;0.85;0" dur="2.8s" begin="${idx * 0.8 + 0.9}s" repeatCount="indefinite"/>
    </path>
    <path d="M37,18 C34,12 40,7 37,3" stroke="#a8c8d0" stroke-width="1.5" fill="none" stroke-linecap="round" opacity="0">
      <animate attributeName="opacity" values="0;0.85;0" dur="2.8s" begin="${idx * 0.8 + 1.8}s" repeatCount="indefinite"/>
    </path>` : '';

  const water = hasWater ? `
    <g clip-path="url(#${id})">
      <rect x="4" y="${waterY}" width="48" height="36" fill="#c8a040" opacity="0.38"/>
      <path d="M-10,${waterY} Q2.5,${waterY - 3} 15,${waterY} Q27.5,${waterY + 3} 40,${waterY} Q52.5,${waterY - 3} 65,${waterY} Q77.5,${waterY + 3} 90,${waterY} L90,${waterY + 9} L-10,${waterY + 9} Z" fill="#a07820" opacity="0.26">
        <animateTransform attributeName="transform" type="translate" from="0,0" to="25,0" dur="3.5s" begin="${idx * 0.35}s" repeatCount="indefinite"/>
      </path>
    </g>` : '';

  // Sunflower enamel decoration (matching reference piala)
  const sunflower = `
    <g transform="translate(37,39)" opacity="${filled ? 0.82 : 0.6}">
      <!-- 12 petals -->
      <ellipse cx="0" cy="-7" rx="2.2" ry="4" fill="#c86838" transform="rotate(0)"/>
      <ellipse cx="0" cy="-7" rx="2.2" ry="4" fill="#c86838" transform="rotate(30)"/>
      <ellipse cx="0" cy="-7" rx="2.2" ry="4" fill="#c86838" transform="rotate(60)"/>
      <ellipse cx="0" cy="-7" rx="2.2" ry="4" fill="#d07840" transform="rotate(90)"/>
      <ellipse cx="0" cy="-7" rx="2.2" ry="4" fill="#c86838" transform="rotate(120)"/>
      <ellipse cx="0" cy="-7" rx="2.2" ry="4" fill="#c86838" transform="rotate(150)"/>
      <ellipse cx="0" cy="-7" rx="2.2" ry="4" fill="#c06030" transform="rotate(180)"/>
      <ellipse cx="0" cy="-7" rx="2.2" ry="4" fill="#c86838" transform="rotate(210)"/>
      <ellipse cx="0" cy="-7" rx="2.2" ry="4" fill="#c86838" transform="rotate(240)"/>
      <ellipse cx="0" cy="-7" rx="2.2" ry="4" fill="#d07840" transform="rotate(270)"/>
      <ellipse cx="0" cy="-7" rx="2.2" ry="4" fill="#c86838" transform="rotate(300)"/>
      <ellipse cx="0" cy="-7" rx="2.2" ry="4" fill="#c86838" transform="rotate(330)"/>
      <!-- Center disc -->
      <circle cx="0" cy="0" r="4.2" fill="#6b2e0e"/>
      <!-- Center texture -->
      <circle cx="0" cy="-1.8" r="0.7" fill="#8b4820"/>
      <circle cx="1.6" cy="0.9" r="0.7" fill="#8b4820"/>
      <circle cx="-1.6" cy="0.9" r="0.7" fill="#8b4820"/>
      <!-- Leaf stem -->
      <path d="M0,4 C-4,6 -9,5 -8,8" fill="none" stroke="#2a6018" stroke-width="1.3" stroke-linecap="round"/>
      <!-- Leaf -->
      <ellipse cx="-6.5" cy="7" rx="3.5" ry="1.8" fill="#3a7828" transform="rotate(-20,-6.5,7)"/>
      <!-- Leaf vein -->
      <path d="M-9,7 C-6.5,6.5 -4,7.5 -3.5,8" fill="none" stroke="#2a6018" stroke-width="0.5"/>
      <!-- Bud -->
      <circle cx="4" cy="-10" r="2" fill="#d4a020"/>
      <ellipse cx="4" cy="-11.5" rx="1" ry="1.5" fill="#4a8028"/>
    </g>`;

  return `<div style="display:flex;flex-direction:column;align-items:center;gap:4px">
<svg viewBox="0 0 56 66" width="50" height="59" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <clipPath id="${id}">
      <path d="M7,23 L14,56 L42,56 L49,23 Z"/>
    </clipPath>
  </defs>

  ${steam}

  <!-- Shadow -->
  <ellipse cx="28" cy="64" rx="16" ry="2.8" fill="#5060a0" opacity="0.09"/>

  <!-- Foot ring -->
  <ellipse cx="28" cy="59" rx="14" ry="2.8" fill="#dce8f5" stroke="#5878c0" stroke-width="1.1"/>
  <ellipse cx="28" cy="58" rx="10.5" ry="2" fill="#eef5ff"/>

  <!-- Cup body (frosted glass look) -->
  <path d="M7,23 L14,56 L42,56 L49,23 Z" fill="#f2f7ff" opacity="0.93"/>

  <!-- Water -->
  ${water}

  <!-- Sunflower decoration -->
  ${sunflower}

  <!-- Left highlight -->
  <path d="M9,26 L15,54" fill="none" stroke="white" stroke-width="4" stroke-linecap="round" opacity="0.38"/>

  <!-- Cup outline -->
  <path d="M7,23 L14,56 L42,56 L49,23 Z" fill="none" stroke="#5878c0" stroke-width="1.6"/>

  <!-- Bottom rim -->
  <ellipse cx="28" cy="56" rx="14" ry="2.6" fill="#dce8f5" stroke="#5878c0" stroke-width="0.9"/>

  <!-- Top rim flare (outer) -->
  <ellipse cx="28" cy="21" rx="23" ry="4.2" fill="#e0eeff" stroke="#5878c0" stroke-width="1.4"/>
  <!-- Top rim inner -->
  <ellipse cx="28" cy="22" rx="20" ry="3.2" fill="#f2f8ff"/>
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
      ? 'Все подарки розданы ✨'
      : `${slotsUsed} из ${slotsTotal} подарков отправлено`;

  const slotsBlock = ref.has_purchased ? `
    <div style="padding-top:14px;margin-top:14px;border-top:1px solid var(--md-outline-variant)">
      <div style="font-size:12px;color:var(--md-on-surface-variant);text-align:center;margin-bottom:16px">
        Первые <b>${slotsTotal}</b> друга получат <b>250 баллов</b> при подписке по твоей ссылке
      </div>
      <div style="display:flex;align-items:flex-end;justify-content:center;gap:18px">
        ${_gaiwanSvg(slotsLeft, slotsTotal)}
        <div style="display:flex;gap:12px">
          ${Array.from({length: slotsTotal}, (_, i) => _pialaSvg(i < slotsUsed, i)).join('')}
        </div>
      </div>
      <div style="font-size:12px;color:var(--md-on-surface-variant);text-align:center;margin-top:8px">${statusText}</div>
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
