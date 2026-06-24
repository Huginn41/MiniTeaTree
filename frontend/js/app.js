// ─── App State ─────────────────────────────────────────────────────────────
const App = {
  currentView: 'home',
  viewStack: [],
  categories: [],
  cartCount: 0,
  _pickupPoint: null,

  navigate(view, data) {
    if (this.currentView !== view) this.viewStack.push(this.currentView);
    this.currentView = view;
    this.render(view, data);
    this.syncNav(view);
    this.syncBackBtn();
    window.scrollTo({ top: 0 });
  },

  goBack() {
    if (!this.viewStack.length) return;
    this.currentView = this.viewStack.pop();
    this.render(this.currentView);
    this.syncNav(this.currentView);
    this.syncBackBtn();
    window.scrollTo({ top: 0 });
  },

  syncNav(view) {
    document.querySelectorAll('.nav-item').forEach(el => {
      el.classList.toggle('active', el.dataset.view === view);
    });
  },

  syncBackBtn() {
    const btn = document.getElementById('back-btn');
    const show = !['home', 'catalog'].includes(this.currentView);
    btn.classList.toggle('visible', show);
  },

  setHeader(title) {
    document.getElementById('header-title').textContent = title;
  },

  async render(view, data) {
    const c = document.getElementById('app-content');
    c.innerHTML = '';
    const wrapper = document.createElement('div');
    wrapper.className = 'page-enter';
    c.appendChild(wrapper);
    try {
      switch (view) {
        case 'home':         await this.renderHome(wrapper); break;
        case 'catalog':      await this.renderCatalog(wrapper, data); break;
        case 'product':      await this.renderProduct(wrapper, data); break;
        case 'cart':         await this.renderCart(wrapper); break;
        case 'checkout':     await this.renderCheckout(wrapper); break;
        case 'order-detail': await this.renderOrderDetail(wrapper, data); break;
        case 'profile':      await this.renderProfile(wrapper); break;
        case 'about':        await this.renderAbout(wrapper); break;
        default:
          wrapper.innerHTML = `<div class="empty-state"><div class="empty-icon">🔍</div><h3>Страница не найдена</h3></div>`;
      }
    } catch (e) {
      wrapper.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">⚠️</div>
          <h3>Что-то пошло не так</h3>
          <p>${esc(e.message)}</p>
          <button class="btn btn-tonal" onclick="App.navigate('home')" style="margin-top:8px">На главную</button>
        </div>`;
    }
  },

  checkout() { this.navigate('checkout'); },

  updateCartBadge() {
    const el = document.getElementById('cart-badge');
    if (this.cartCount > 0) {
      el.textContent = this.cartCount;
      el.style.display = 'flex';
    } else {
      el.style.display = 'none';
    }
  },

  // ─── Cart Actions ─────────────────────────────────────────────────────────
  async addToCart(variantId, quantity = 1) {
    try {
      await api('/cart/items', {
        method: 'POST',
        body: JSON.stringify({ variant_id: variantId, quantity }),
      });
      this.cartCount++;
      this.updateCartBadge();
      tg?.HapticFeedback?.impactOccurred('light');
      showToast('Добавлено в корзину');
    } catch (err) {
      showToast(err.message);
    }
  },

  async updateCartItem(itemId, qty) {
    if (qty <= 0) return this.removeCartItem(itemId);
    await api(`/cart/items/${itemId}`, { method: 'PATCH', body: JSON.stringify({ quantity: qty }) });
    this.render('cart');
  },

  async removeCartItem(itemId) {
    await api(`/cart/items/${itemId}`, { method: 'DELETE' });
    this.cartCount = Math.max(0, this.cartCount - 1);
    this.updateCartBadge();
    this.render('cart');
  },

  // ─── Component Helpers ────────────────────────────────────────────────────
  _productCardSmall(p) {
    const minPrice = p.variants.length ? Math.min(...p.variants.map(v => v.price)) : p.base_price;
    const priceLabel = p.is_unit
      ? `${fmtPrice(p.variants[0]?.price ?? minPrice)} ₽ / ${p.unit_label || 'шт'}`
      : `от ${fmtPrice(minPrice)} ₽`;
    return `
      <div class="product-card-small" onclick="App.navigate('product', '${p.slug}')">
        <div class="pcard-img">
          ${p.main_image ? `<img src="${p.main_image}" alt="${esc(p.name)}" loading="lazy"/>` : '🍵'}
        </div>
        <div class="pcard-body">
          <div class="pcard-name">${esc(p.name)}</div>
          <div class="pcard-cat">${esc(p.category.name)}</div>
          <div class="pcard-price">${priceLabel}</div>
        </div>
      </div>`;
  },

  _productCardGrid(p) {
    const minPrice = p.variants.length ? Math.min(...p.variants.map(v => v.price)) : p.base_price;
    const priceLabel = p.is_unit
      ? `${fmtPrice(p.variants[0]?.price ?? minPrice)} ₽ / ${p.unit_label || 'шт'}`
      : `от ${fmtPrice(minPrice)} ₽`;
    return `
      <div class="product-card-grid" onclick="App.navigate('product', '${p.slug}')">
        <div class="pcard-img">
          ${p.main_image ? `<img src="${p.main_image}" alt="${esc(p.name)}" loading="lazy"/>` : '🍵'}
        </div>
        <div class="pcard-body">
          <div class="pcard-name" style="font-size:14px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:1.3;max-height:2.6em">${esc(p.name)}</div>
          <div class="pcard-cat" style="font-size:11px;margin-top:3px">${esc(p.category.name)}</div>
          <div class="pcard-price" style="font-size:15px;margin-top:8px">${priceLabel}</div>
        </div>
      </div>`;
  },
};

// ─── Init ──────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  App.navigate('home');
  try {
    const cart = await api('/cart');
    App.cartCount = cart.items?.reduce((s, i) => s + i.quantity, 0) || 0;
    App.updateCartBadge();
  } catch (_) {}

  // Реферальная ссылка: считываем ref из URL (?ref=REF_xxxx) и регистрируем донора.
  const refParam = new URLSearchParams(location.search).get('ref')
    || tg?.initDataUnsafe?.start_param;
  if (refParam && refParam.startsWith('REF_')) {
    api('/referral/register?ref_code=' + encodeURIComponent(refParam), { method: 'POST' })
      .catch(() => {});
  }
});
