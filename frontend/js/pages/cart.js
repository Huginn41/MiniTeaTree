App.renderCart = async function(c) {
  this.setHeader('Корзина');
  let html = '';
  try {
    const cart = await api('/cart');
    if (!cart.items.length) {
      html = `<div class="empty-state">
        <div class="empty-icon">🛒</div>
        <h3>Корзина пуста</h3>
        <p>Выберите чай из каталога</p>
        <button class="btn btn-filled" onclick="App.navigate('catalog')" style="margin-top:8px">Перейти в каталог</button>
      </div>`;
    } else {
      html += `<div id="cart-items">`;
      cart.items.forEach(item => {
        html += `
          <div class="cart-item">
            <div class="cart-item-img">
              ${item.main_image ? `<img src="${item.main_image}" alt="${esc(item.product_name)}" loading="lazy"/>` : '🍵'}
            </div>
            <div style="flex:1;min-width:0">
              <p style="font-size:14px;font-weight:600;color:var(--md-on-surface);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(item.product_name)}</p>
              <p style="font-size:12px;color:var(--md-on-surface-variant);margin-top:2px">${item.variant.weight_g === 0 ? (item.unit_label || 'шт') : item.variant.weight_g + ' г'}</p>
              <p style="font-size:14px;font-weight:700;color:var(--md-primary);margin-top:4px">${fmtPrice(item.variant.price * item.quantity)} ₽</p>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px">
              <button class="btn-icon" onclick="App.removeCartItem(${item.id})" style="width:32px;height:32px;background:var(--md-error-container);color:var(--md-error)">
                <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
              </button>
              <div class="qty-control">
                <button class="qty-btn" onclick="App.updateCartItem(${item.id}, ${item.quantity - 1})">−</button>
                <span class="qty-value">${item.quantity}</span>
                <button class="qty-btn" onclick="App.updateCartItem(${item.id}, ${item.quantity + 1})">+</button>
              </div>
            </div>
          </div>`;
      });
      html += `</div>`;

      html += `
        <div class="md-card" style="padding:16px;margin-top:8px">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
            <span style="font-size:15px;color:var(--md-on-surface-variant)">Итого</span>
            <span style="font-size:22px;font-weight:800;color:var(--md-primary)">${fmtPrice(cart.total_amount)} ₽</span>
          </div>
          <button class="btn btn-filled ripple-container" style="width:100%" onclick="App.checkout()">
            Оформить заказ
          </button>
        </div>`;
    }
  } catch (e) {
    html = `<div class="empty-state">
      <div class="empty-icon">🔒</div>
      <h3>Нужна авторизация</h3>
      <p>Откройте приложение через Telegram</p>
    </div>`;
  }
  c.innerHTML = html;
  c.querySelectorAll('.ripple-container').forEach(addRipple);
};
