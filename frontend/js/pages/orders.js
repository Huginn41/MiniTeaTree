App.renderOrderDetail = async function(c, orderNumber) {
  this.setHeader(orderNumber);
  const o = await api(`/orders/${orderNumber}`);

  const delivLabel = { pickup: 'Самовывоз', courier: 'Курьер', pvz: 'Пункт выдачи' };
  const isPickup = o.delivery_info?.type === 'pickup';

  if (isPickup && !this._pickupPoint) {
    try {
      const pts = await api('/info/pickup-points');
      if (pts.length) {
        this._pickupPoint = pts.find(p => o.delivery_info?.address && this._pickupAddr(p) === o.delivery_info.address) || pts[0];
      }
    } catch(_) {}
  }

  const stepsDelivery = [
    { key: 'new',              label: 'Заказ принят' },
    { key: 'awaiting_payment', label: 'Ожидает оплату' },
    { key: 'in_delivery',      label: 'В пути' },
    { key: 'at_pvz',           label: 'В пункте выдачи' },
    { key: 'delivered',        label: 'Доставлен' },
  ];
  const stepsPickup = [
    { key: 'new',        label: 'Заказ принят' },
    { key: 'assembling', label: 'Собираем' },
    { key: 'ready',      label: 'Готов к выдаче' },
    { key: 'delivered',  label: 'Получен' },
  ];
  const steps = isPickup ? stepsPickup : stepsDelivery;
  const stepKeys = steps.map(s => s.key);
  const isDelivered = o.status === 'delivered';
  const currentStepIdx = Math.max(0, stepKeys.indexOf(o.status));
  const isCancelled = o.status === 'cancelled';

  let progressHtml = '';
  if (isCancelled) {
    progressHtml = `<div style="padding:12px 14px;background:var(--md-error-container);border-radius:var(--radius-sm);text-align:center">
      <p style="font-size:14px;font-weight:600;color:var(--md-error)">Заказ отменён</p>
    </div>`;
  } else {
    progressHtml = `<div style="display:flex;flex-direction:column;gap:0">
      ${steps.map((step, i) => {
        const done = isDelivered || i < currentStepIdx;
        const active = !isDelivered && i === currentStepIdx;
        const color = done || active ? 'var(--md-primary)' : 'var(--md-outline)';
        const bgDot = done ? 'var(--md-primary)' : active ? 'var(--md-primary-container)' : 'var(--md-surface-container)';
        const borderDot = done || active ? 'var(--md-primary)' : 'var(--md-outline)';
        return `<div style="display:flex;align-items:flex-start;gap:12px">
          <div style="display:flex;flex-direction:column;align-items:center;flex-shrink:0">
            <div style="width:20px;height:20px;border-radius:50%;background:${bgDot};border:2px solid ${borderDot};display:flex;align-items:center;justify-content:center;margin-top:2px">
              ${done ? `<svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 5l2.5 2.5L8 3" stroke="white" stroke-width="1.5" stroke-linecap="round"/></svg>` : ''}
            </div>
            ${i < steps.length - 1 ? `<div style="width:2px;height:24px;background:${done ? 'var(--md-primary)' : 'var(--md-outline-variant)'};margin-top:2px"></div>` : ''}
          </div>
          <p style="font-size:14px;font-weight:${active ? '700' : '400'};color:${active ? 'var(--md-on-surface)' : done ? 'var(--md-primary)' : 'var(--md-on-surface-variant)'};padding-top:1px;padding-bottom:${i < steps.length - 1 ? '20px' : '0'}">${step.label}</p>
        </div>`;
      }).join('')}
    </div>`;
  }

  const paymentLinkHtml = (o.payment_link && o.status === 'awaiting_payment') ? `
    <div style="background:var(--md-primary-container);border-radius:var(--radius-md);padding:16px;margin-bottom:12px">
      <p style="font-size:12px;font-weight:600;color:var(--md-on-primary-container);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:8px">ССЫЛКА НА ОПЛАТУ</p>
      <p style="font-size:13px;color:var(--md-on-primary-container);margin-bottom:12px;line-height:1.5">Менеджер прислал ссылку для оплаты. Нажмите кнопку ниже:</p>
      <a href="${esc(o.payment_link)}" target="_blank"
        style="display:flex;align-items:center;justify-content:center;gap:8px;background:var(--md-primary);color:white;padding:14px 20px;border-radius:100px;font-size:15px;font-weight:600;text-decoration:none">
        <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2z"/>
        </svg>
        Перейти к оплате
      </a>
    </div>` : '';

  const newOrderBanner = o.status === 'new' ? `
    <div style="background:#FFF8E1;border-radius:var(--radius-md);padding:14px 16px;margin-bottom:12px;display:flex;gap:12px;align-items:flex-start">
      <span style="font-size:22px;flex-shrink:0">⏳</span>
      <div>
        <p style="font-size:14px;font-weight:600;color:#E65100">Заказ принят</p>
        <p style="font-size:13px;color:#BF360C;margin-top:4px;line-height:1.5">Мы обрабатываем ваш заказ и скоро свяжемся с вами.</p>
      </div>
    </div>` : '';

  let html = `
    <div class="md-card" style="padding:16px;margin-bottom:12px">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
        <div>
          <p style="font-size:20px;font-weight:800;color:var(--md-primary)">${o.number}</p>
          <p style="font-size:12px;color:var(--md-on-surface-variant);margin-top:2px">${fmtDate(o.created_at)}</p>
        </div>
        <span class="status-badge ${o.status}">${_statusLabel(o.status)}</span>
      </div>
      ${o.delivery_info ? `
        <div style="background:var(--md-surface-container);border-radius:var(--radius-sm);padding:10px 12px">
          <p style="font-size:13px;font-weight:600;color:var(--md-on-surface)">${delivLabel[o.delivery_info.type] || o.delivery_info.type}</p>
          ${o.delivery_info.address ? `<p style="font-size:12px;color:var(--md-on-surface-variant);margin-top:2px">${esc(o.delivery_info.address)}</p>` : ''}
        </div>
      ` : ''}
      ${isPickup && App._pickupPoint ? (() => {
        const p = App._pickupPoint;
        const addr = App._pickupAddr(p);
        const mapSrc = p.map_embed_src || '';
        return `
        <div style="margin-top:10px;border-radius:var(--radius-sm);overflow:hidden;background:var(--md-surface-container)">
          <div style="padding:12px 14px;display:flex;align-items:flex-start;gap:10px">
            <span style="font-size:20px;flex-shrink:0">📍</span>
            <div>
              <p style="font-size:13px;font-weight:700;color:var(--md-on-surface);margin:0 0 2px">Можете забрать заказ здесь:</p>
              <p style="font-size:13px;color:var(--md-on-surface);margin:0 0 2px">${esc(p.name)}</p>
              ${addr ? `<p style="font-size:12px;color:var(--md-on-surface-variant);margin:0 0 4px">${esc(addr)}</p>` : ''}
              ${p.work_hours ? `<p style="font-size:12px;color:var(--md-on-surface-variant);margin:0">🕐 ${esc(p.work_hours)}</p>` : ''}
            </div>
          </div>
          ${mapSrc ? `
          <div style="position:relative;width:100%;height:220px;overflow:hidden">
            <iframe src="${mapSrc}" width="100%" height="220" frameborder="0" allowfullscreen style="border:0;display:block"></iframe>
          </div>
          <a href="https://yandex.ru/maps/?text=${encodeURIComponent(addr)}" target="_blank"
            style="display:flex;align-items:center;justify-content:center;gap:6px;padding:11px;font-size:13px;font-weight:600;color:var(--md-primary);text-decoration:none;border-top:1px solid var(--md-outline-variant)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
            Открыть в Яндекс Картах
          </a>` : (addr ? `
          <a href="https://yandex.ru/maps/?text=${encodeURIComponent(addr)}" target="_blank"
            style="display:flex;align-items:center;justify-content:center;gap:6px;padding:11px;font-size:13px;font-weight:600;color:var(--md-primary);text-decoration:none;border-top:1px solid var(--md-outline-variant)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
            Открыть в Яндекс Картах
          </a>` : '')}
        </div>`;
      })() : ''}
    </div>

    ${newOrderBanner}
    ${paymentLinkHtml}

    <p style="font-size:12px;font-weight:600;color:var(--md-on-surface-variant);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:10px">СТАТУС</p>
    <div class="md-card" style="padding:16px;margin-bottom:12px">
      ${progressHtml}
    </div>

    <p style="font-size:12px;font-weight:600;color:var(--md-on-surface-variant);letter-spacing:0.5px;text-transform:uppercase;margin-bottom:10px">СОСТАВ ЗАКАЗА</p>
    <div class="md-card" style="padding:0 16px;margin-bottom:12px">
      ${o.items.map(item => `
        <div class="detail-row">
          <div>
            <p style="font-size:14px;font-weight:600;color:var(--md-on-surface)">${esc(item.snapshot_name)}</p>
            <p style="font-size:12px;color:var(--md-on-surface-variant)">${item.snapshot_weight_g === 0 ? `${item.quantity} шт.` : `${item.snapshot_weight_g} г · ${item.quantity} шт.`}</p>
          </div>
          <span style="font-size:14px;font-weight:700;color:var(--md-primary)">${fmtPrice(item.unit_price * item.quantity)} ₽</span>
        </div>
      `).join('')}
      <div style="display:flex;justify-content:space-between;padding:14px 0 12px">
        <span style="font-size:15px;font-weight:700">Итого</span>
        <span style="font-size:18px;font-weight:800;color:var(--md-primary)">${fmtPrice(o.total_amount)} ₽</span>
      </div>
    </div>

    ${o.comment ? `
      <div class="md-card-filled" style="padding:12px 14px;margin-bottom:12px">
        <p style="font-size:12px;font-weight:600;color:var(--md-on-surface-variant);margin-bottom:4px">КОММЕНТАРИЙ</p>
        <p style="font-size:14px;color:var(--md-on-surface)">${esc(o.comment)}</p>
      </div>` : ''}

    <button class="btn btn-outlined" style="width:100%;margin-top:4px" onclick="App.navigate('profile')">
      ← К списку заказов
    </button>`;

  c.innerHTML = html;
};
