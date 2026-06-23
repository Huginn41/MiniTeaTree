App._pickupAddr = function(p) {
  const parts = [];
  if (p.city)     parts.push(p.city);
  if (p.street)   parts.push(p.street);
  if (p.building) parts.push('д. ' + p.building);
  return parts.join(', ') || p.address || '';
};

App.renderCheckout = async function(c) {
  this.setHeader('Оформление заказа');
  c.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;padding:40px 0"><div style="width:28px;height:28px;border:3px solid var(--md-primary);border-top-color:transparent;border-radius:50%;animation:spin .7s linear infinite"></div></div>`;

  let pickupPoints = [];
  let bonusBalance = 0;
  let maxBonusPct = 0;
  let cartTotal = 0;
  try { pickupPoints = await api('/info/pickup-points'); } catch(_) {}
  try {
    const profile = await api('/profile/me');
    bonusBalance = profile.bonus_balance || 0;
  } catch(_) {}
  try {
    const bonusCfg = await api('/info/bonus-config');
    maxBonusPct = bonusCfg.max_payment_pct || 0;
  } catch(_) {}
  try {
    const cart = await api('/cart');
    cartTotal = (cart.items || []).reduce((s, i) => s + i.unit_price * i.quantity, 0);
  } catch(_) {}

  if (pickupPoints.length > 0) this._pickupPoint = pickupPoints[0];
  window._checkoutPickupPoints = pickupPoints;
  window._checkoutBonusBalance = bonusBalance;
  window._checkoutMaxBonusPct = maxBonusPct;
  window._checkoutTotal = cartTotal;

  const pickupCard = (p, checked) => `
    <label class="radio-card" style="flex-direction:column;align-items:flex-start;gap:0;cursor:pointer">
      <div style="display:flex;align-items:center;gap:10px;width:100%">
        <input type="radio" name="pickup_point" value="${p.id}" ${checked?'checked':''} onchange="App._selectPickup(${p.id})"/>
        <span style="font-size:15px;font-weight:600">${esc(p.name)}</span>
      </div>
      <div style="margin-left:28px;margin-top:4px">
        <p style="font-size:12.5px;color:var(--md-on-surface-variant);margin:0;line-height:1.5">${esc(this._pickupAddr(p))}</p>
        ${p.work_hours ? `<p style="font-size:12px;color:var(--md-on-surface-variant);margin:2px 0 0;display:flex;align-items:center;gap:4px"><span>🕐</span>${esc(p.work_hours)}</p>` : ''}
      </div>
    </label>`;

  let pickupSection = '';
  if (pickupPoints.length === 0) {
    pickupSection = `<p style="font-size:13px;color:var(--md-on-surface-variant);padding:8px 0">Адрес уточним после оформления заказа</p>`;
  } else if (pickupPoints.length === 1) {
    pickupSection = pickupCard(pickupPoints[0], true);
  } else {
    pickupSection = pickupPoints.map((p, i) => pickupCard(p, i === 0)).join('');
  }

  c.innerHTML = `
    <form id="checkout-form" onsubmit="App.submitOrder(event)">

      <p style="font-size:12px;font-weight:600;color:var(--md-on-surface-variant);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:10px">СПОСОБ ПОЛУЧЕНИЯ</p>
      <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:20px">
        <label class="radio-card">
          <input type="radio" name="delivery_type" value="pickup" checked/>
          <div>
            <div style="font-size:15px;font-weight:600">Самовывоз</div>
            <div style="font-size:12px;color:var(--md-on-surface-variant);margin-top:2px">Из магазина или пункта выдачи</div>
          </div>
        </label>
        <label class="radio-card">
          <input type="radio" name="delivery_type" value="courier"/>
          <div>
            <div style="font-size:15px;font-weight:600">Курьер</div>
            <div style="font-size:12px;color:var(--md-on-surface-variant);margin-top:2px">Доставка по адресу</div>
          </div>
        </label>
      </div>

      <div id="pickup-section" style="margin-bottom:20px">
        <p style="font-size:12px;font-weight:600;color:var(--md-on-surface-variant);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:10px">ПУНКТ САМОВЫВОЗА</p>
        <div style="display:flex;flex-direction:column;gap:8px">${pickupSection}</div>
      </div>

      <p style="font-size:12px;font-weight:600;color:var(--md-on-surface-variant);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:10px">КОНТАКТЫ</p>
      <div style="display:flex;flex-direction:column;gap:10px;margin-bottom:20px">
        <div>
          <label class="input-label">Телефон</label>
          <input class="md-input" type="tel" name="contact_phone" placeholder="+7 (999) 999-99-99"/>
        </div>
        <div id="address-field" style="display:none">
          <label class="input-label">Адрес доставки</label>
          <input class="md-input" type="text" name="address" placeholder="Город, улица, дом, квартира"/>
        </div>
      </div>

      <p style="font-size:12px;font-weight:600;color:var(--md-on-surface-variant);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:10px">КОММЕНТАРИЙ</p>
      <textarea class="md-input" name="comment" rows="3" placeholder="Пожелания к заказу..." style="resize:none;margin-bottom:20px"></textarea>

      ${bonusBalance > 0 && maxBonusPct > 0 ? `
      <p style="font-size:12px;font-weight:600;color:var(--md-on-surface-variant);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:10px">ОПЛАТА БАЛЛАМИ</p>
      <div class="md-card" style="padding:16px;margin-bottom:20px;background:var(--md-surface-variant)">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
          <span style="font-size:14px;color:var(--md-on-surface-variant)">Доступно баллов</span>
          <span style="font-size:16px;font-weight:700;color:var(--md-primary)">${Math.floor(bonusBalance)}</span>
        </div>
        <div style="display:flex;gap:8px;align-items:center">
          <input
            id="bonus-amount-input"
            type="number"
            min="0"
            max="${Math.floor(bonusBalance)}"
            step="1"
            placeholder="0"
            class="md-input"
            style="flex:1;margin:0"
            oninput="App._updateBonusHint()"
          >
          <button type="button" class="btn btn-tonal" style="white-space:nowrap;padding:10px 14px;font-size:13px" onclick="App._setBonusMax()">Максимум</button>
        </div>
        <div id="bonus-hint" style="display:none;margin-top:10px;font-size:13px;color:#1a6b3c;padding:10px;background:rgba(26,107,60,.08);border-radius:8px;line-height:1.5"></div>
      </div>` : ''}

      <div id="order-summary" style="background:var(--md-surface-container);border-radius:var(--radius-md);padding:14px 16px;margin-bottom:20px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
          <span style="font-size:14px;color:var(--md-on-surface-variant)">Стоимость товаров</span>
          <span style="font-size:14px;font-weight:600" id="summary-items">${fmtPrice(cartTotal)} ₽</span>
        </div>
        <div id="summary-bonus-row" style="display:none;justify-content:space-between;align-items:center;margin-bottom:6px">
          <span style="font-size:14px;color:var(--md-primary)">Списано баллов</span>
          <span style="font-size:14px;font-weight:600;color:var(--md-primary)" id="summary-bonus-val"></span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;padding-top:8px;border-top:1px solid var(--md-outline-variant)">
          <span style="font-size:16px;font-weight:700">К оплате</span>
          <span style="font-size:20px;font-weight:800;color:var(--md-primary)" id="summary-payable">${fmtPrice(cartTotal)} ₽</span>
        </div>
      </div>

      <button type="submit" id="submit-order-btn" class="btn btn-filled ripple-container" style="width:100%">
        Подтвердить заказ
      </button>
    </form>`;

  document.querySelectorAll('input[name="delivery_type"]').forEach(r => {
    r.addEventListener('change', () => {
      const isPickup = r.value === 'pickup';
      document.getElementById('pickup-section').style.display = isPickup ? 'block' : 'none';
      document.getElementById('address-field').style.display = isPickup ? 'none' : 'block';
    });
  });
  c.querySelectorAll('.ripple-container').forEach(addRipple);
};

App._selectPickup = function(id) {
  const radios = document.querySelectorAll('input[name="pickup_point"]');
  radios.forEach(r => {
    if (parseInt(r.value) === id) {
      r.closest('label').style.outline = '2px solid var(--md-primary)';
    } else {
      r.closest('label').style.outline = '';
    }
  });
  if (window._checkoutPickupPoints) {
    this._pickupPoint = window._checkoutPickupPoints.find(p => p.id === id) || this._pickupPoint;
  }
};

App._setBonusMax = function() {
  const inp = document.getElementById('bonus-amount-input');
  if (!inp) return;
  inp.value = Math.floor(window._checkoutBonusBalance || 0);
  this._updateBonusHint();
};

App._updateBonusHint = function() {
  const inp = document.getElementById('bonus-amount-input');
  const hint = document.getElementById('bonus-hint');
  if (!inp || !hint) return;
  const val = Math.max(0, Math.floor(+inp.value || 0));
  const bal = Math.floor(window._checkoutBonusBalance || 0);
  const maxPct = window._checkoutMaxBonusPct || 0;
  const total = window._checkoutTotal || 0;
  if (val > bal) { inp.value = bal; }
  if (val <= 0) {
    hint.style.display = 'none';
    this._updateOrderSummary(0);
    return;
  }
  hint.style.display = 'block';
  hint.innerHTML = `Будет списано <b>${val}</b> баллов (≈ ${val} ₽). Фактическая сумма не превысит ${maxPct}% от итога заказа.`;
  this._updateOrderSummary(val);
};

App._updateOrderSummary = function(bonusVal) {
  const total = window._checkoutTotal || 0;
  const payable = Math.max(0, total - bonusVal);
  const bonusRow = document.getElementById('summary-bonus-row');
  const bonusValEl = document.getElementById('summary-bonus-val');
  const payableEl = document.getElementById('summary-payable');
  if (!payableEl) return;
  if (bonusVal > 0 && bonusRow && bonusValEl) {
    bonusRow.style.display = 'flex';
    bonusValEl.textContent = `−${fmtPrice(bonusVal)} ₽`;
  } else if (bonusRow) {
    bonusRow.style.display = 'none';
  }
  payableEl.textContent = `${fmtPrice(payable)} ₽`;
};

App.submitOrder = async function(e) {
  e.preventDefault();
  const btn = document.getElementById('submit-order-btn');
  btn.disabled = true;
  btn.textContent = 'Отправляем…';
  try {
    const form = e.target;
    const delivery_type = form.querySelector('input[name="delivery_type"]:checked').value;
    const pickupAddr = delivery_type === 'pickup' && this._pickupPoint
      ? this._pickupAddr(this._pickupPoint) : '';
    const bonusInp = document.getElementById('bonus-amount-input');
    const useBonusAmount = bonusInp ? Math.max(0, Math.floor(+bonusInp.value || 0)) : 0;
    const order = await api('/orders', {
      method: 'POST',
      body: JSON.stringify({
        delivery_type,
        contact_phone: form.contact_phone.value || null,
        address: delivery_type === 'courier' ? (form.address?.value || '') : pickupAddr,
        comment: form.comment.value || null,
        use_bonus_amount: useBonusAmount,
      }),
    });
    this.cartCount = 0;
    this.updateCartBadge();
    tg?.HapticFeedback?.notificationOccurred('success');
    this.navigate('order-detail', order.number);
  } catch (err) {
    btn.disabled = false;
    btn.textContent = 'Подтвердить заказ';
    if (tg) tg.showPopup({ title: 'Ошибка', message: err.message, buttons: [{ type: 'ok' }] });
    else showToast(err.message);
  }
};
