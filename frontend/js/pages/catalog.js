App.renderCatalog = async function(c, categorySlug) {
  this.setHeader('Каталог');
  const cats = this.categories.length ? this.categories : await api('/catalog/categories');
  this.categories = cats;

  const params = categorySlug ? `?category_slug=${categorySlug}` : '';
  const products = await api(`/catalog/products${params}`);

  const currentCat = cats.find(cat => cat.slug === categorySlug);
  this.setHeader(currentCat ? currentCat.name : 'Каталог');

  let html = `<div class="chips-scroll">
    <span class="chip${!categorySlug ? ' active' : ''}" onclick="App.navigate('catalog')">Все</span>
    ${cats.map(cat => `
      <span class="chip${categorySlug === cat.slug ? ' active' : ''}" onclick="App.navigate('catalog', '${cat.slug}')">
        ${esc(cat.name)}
      </span>
    `).join('')}
  </div>`;

  if (!products.length) {
    html += `<div class="empty-state">
      <div class="empty-icon">🍃</div>
      <h3>Нет товаров</h3>
      <p>В этой категории пока ничего нет</p>
    </div>`;
  } else {
    html += `<div class="products-grid">
      ${products.map(p => this._productCardGrid(p)).join('')}
    </div>`;
  }

  c.innerHTML = html;
};

App.renderProduct = async function(c, slug) {
  c.innerHTML = `<div style="padding:16px"><div class="skeleton" style="height:260px;border-radius:0"></div></div>`;
  const p = await api(`/catalog/products/${slug}`);
  this.setHeader(p.name);

  const minPrice = p.variants.length ? Math.min(...p.variants.map(v => v.price)) : p.base_price;

  let html = '';

  if (p.images.length) {
    const n = p.images.length;
    const dotHtml = n > 1
      ? `<div class="gallery-dots">${p.images.map((_, i) => `<div class="gallery-dot${i===0?' active':''}"></div>`).join('')}</div>`
      : '';
    html += `<div class="product-gallery-wrap">
      <div class="product-gallery" id="pimg-gallery">
        ${p.images.map((img, i) => `<img src="${img.path}" alt="${esc(img.alt || p.name)}" loading="${i===0?'eager':'lazy'}" data-li="${i}"/>`).join('')}
      </div>
      ${dotHtml}
    </div>`;
  } else {
    html += `<div style="height:220px;background:var(--md-surface-container);display:flex;align-items:center;justify-content:center;font-size:64px;margin:-16px -16px 0">🍵</div>`;
  }

  html += `<div class="product-info-sheet">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
      <div>
        <h2 style="font-size:20px;font-weight:700;color:var(--md-on-surface);line-height:1.3">${esc(p.name)}</h2>
        ${p.origin ? `<p style="font-size:13px;color:var(--md-on-surface-variant);margin-top:4px">📍 ${esc(p.origin)}</p>` : ''}
      </div>
      <div style="font-size:18px;font-weight:800;color:var(--md-primary);white-space:nowrap;padding-top:2px">${p.is_unit ? `${fmtPrice(p.variants[0]?.price ?? p.base_price)} ₽ / ${p.unit_label || 'шт'}` : `от ${fmtPrice(minPrice)} ₽`}</div>
    </div>

    ${p.tags.length ? `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:12px">
      ${p.tags.map(t => `<span style="padding:4px 10px;background:var(--md-secondary-container);color:var(--md-on-primary-container);border-radius:100px;font-size:11px;font-weight:600">${esc(t)}</span>`).join('')}
    </div>` : ''}

    ${p.description ? `<p style="font-size:14px;color:var(--md-on-surface-variant);line-height:1.65;margin-top:14px;white-space:pre-wrap">${esc(p.description)}</p>` : ''}

    ${p.variants.length ? `
      <div style="margin-top:20px">
        ${p.is_unit ? `
          <p style="font-size:12px;font-weight:600;color:var(--md-on-surface-variant);letter-spacing:0.5px;text-transform:uppercase">Количество</p>
          <div style="display:flex;align-items:center;gap:12px;margin-top:12px">
            <div style="display:flex;align-items:center;background:var(--md-surface-container);border-radius:12px;overflow:hidden">
              <button id="unit-minus" style="width:44px;height:44px;border:none;background:none;font-size:22px;font-weight:300;color:var(--md-on-surface);cursor:pointer;display:flex;align-items:center;justify-content:center">−</button>
              <span id="unit-qty" style="min-width:32px;text-align:center;font-size:17px;font-weight:700;color:var(--md-on-surface)">1</span>
              <button id="unit-plus" style="width:44px;height:44px;border:none;background:none;font-size:22px;font-weight:300;color:var(--md-on-surface);cursor:pointer;display:flex;align-items:center;justify-content:center">+</button>
            </div>
            <div>
              <div id="unit-total-price" style="font-size:20px;font-weight:800;color:var(--md-primary)">${fmtPrice(p.variants[0].price)} ₽</div>
              <div style="font-size:12px;color:var(--md-on-surface-variant)">${fmtPrice(p.variants[0].price)} ₽ / ${p.unit_label || 'шт'}</div>
            </div>
          </div>
          <div class="variant-actions visible">
            <button class="btn-cart" id="btn-to-cart">В корзину</button>
            <button class="btn-buy" id="btn-buy">Купить</button>
          </div>
        ` : `
          <p style="font-size:12px;font-weight:600;color:var(--md-on-surface-variant);letter-spacing:0.5px;text-transform:uppercase">Выберите вес</p>
          <div class="variant-grid" id="variant-grid">
            ${p.variants.map(v => `
              <button class="variant-btn ${v.in_stock ? 'available' : 'out'}"
                data-variant-id="${v.id}" data-price="${v.price}" data-weight="${v.weight_g}"
                ${!v.in_stock ? 'disabled' : ''}>
                <div class="v-weight">${v.weight_g} г</div>
                <div class="v-price">${fmtPrice(v.price)} ₽</div>
                ${!v.in_stock ? '<div class="v-oos">Нет в наличии</div>' : ''}
              </button>
            `).join('')}
          </div>
          <div class="variant-actions" id="variant-actions">
            <button class="btn-cart" id="btn-to-cart">В корзину</button>
            <button class="btn-buy" id="btn-buy">Купить</button>
          </div>
        `}
      </div>
    ` : ''}
    <div style="height:24px"></div>
  </div>`;

  c.innerHTML = html;
  this._currentProduct = p;
  if (p.images.length) this._initGallery(p.images);
  this._initVariantSelect();
};

App._initVariantSelect = function() {
  const btnCart = document.getElementById('btn-to-cart');
  const btnBuy  = document.getElementById('btn-buy');

  // Штучный товар — кнопки − / +
  const unitMinus = document.getElementById('unit-minus');
  const unitPlus  = document.getElementById('unit-plus');
  const unitQty   = document.getElementById('unit-qty');
  if (unitMinus && unitPlus && unitQty && btnCart && btnBuy) {
    let qty = 1;
    const variantId  = this._currentProduct?.variants?.[0]?.id;
    const unitPrice  = parseFloat(this._currentProduct?.variants?.[0]?.price ?? 0);
    const totalPriceEl = document.getElementById('unit-total-price');
    const updatePrice = () => {
      if (totalPriceEl) totalPriceEl.textContent = fmtPrice(unitPrice * qty) + ' ₽';
    };
    unitMinus.addEventListener('click', () => {
      if (qty > 1) { qty--; unitQty.textContent = qty; updatePrice(); }
      tg?.HapticFeedback?.selectionChanged?.();
    });
    unitPlus.addEventListener('click', () => {
      qty++; unitQty.textContent = qty; updatePrice();
      tg?.HapticFeedback?.selectionChanged?.();
    });
    btnCart.addEventListener('click', async () => {
      if (!variantId) return;
      await App.addToCart(variantId, qty);
      qty = 1; unitQty.textContent = 1; updatePrice();
      tg?.HapticFeedback?.notificationOccurred?.('success');
    });
    btnBuy.addEventListener('click', async () => {
      if (!variantId) return;
      await App.addToCart(variantId, qty);
      App.navigate('cart');
    });
    return;
  }

  // Весовой товар — выбор граммовки
  const grid    = document.getElementById('variant-grid');
  const actions = document.getElementById('variant-actions');
  if (!grid || !actions || !btnCart || !btnBuy) return;

  let selectedId = null;

  grid.querySelectorAll('.variant-btn.available').forEach(btn => {
    btn.addEventListener('click', () => {
      grid.querySelectorAll('.variant-btn').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      selectedId = parseInt(btn.dataset.variantId);
      actions.classList.add('visible');
      tg?.HapticFeedback?.selectionChanged?.();
      setTimeout(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }), 50);
    });
  });

  btnCart.addEventListener('click', async () => {
    if (!selectedId) return;
    await App.addToCart(selectedId);
    actions.classList.remove('visible');
    grid.querySelectorAll('.variant-btn').forEach(b => b.classList.remove('selected'));
    selectedId = null;
  });

  btnBuy.addEventListener('click', async () => {
    if (!selectedId) return;
    await App.addToCart(selectedId);
    App.navigate('cart');
  });
};

App._initGallery = function(images) {
  const gallery = document.getElementById('pimg-gallery');
  if (!gallery) return;

  const n = images.length;
  let lbIdx = 0;

  const dots = gallery.parentNode.querySelectorAll('.gallery-dot');
  function updateDots() {
    const idx = Math.round(gallery.scrollLeft / window.innerWidth);
    dots.forEach((d, i) => d.classList.toggle('active', i === idx));
  }
  if (dots.length) gallery.addEventListener('scroll', updateDots, { passive: true });

  document.getElementById('lb-overlay')?.remove();
  const lb = document.createElement('div');
  lb.id = 'lb-overlay';
  lb.className = 'lb-overlay';
  const navHide = n <= 1 ? ' style="display:none"' : '';
  lb.innerHTML = `
    <div class="lb-track">
      ${images.map((img, i) => `<img src="${img.path}" alt="" draggable="false" loading="${i===0?'eager':'lazy'}"/>`).join('')}
    </div>
    <button class="lb-close" aria-label="Закрыть">
      <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
    </button>
    <button class="lb-prev"${navHide} aria-label="Назад">
      <svg viewBox="0 0 24 24"><path d="M15.41 16.59L10.83 12l4.58-4.59L14 6l-6 6 6 6z"/></svg>
    </button>
    <button class="lb-next"${navHide} aria-label="Вперёд">
      <svg viewBox="0 0 24 24"><path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6z"/></svg>
    </button>
    <div class="lb-counter"></div>`;
  document.body.appendChild(lb);

  const lbTrack = lb.querySelector('.lb-track');
  const lbCtr   = lb.querySelector('.lb-counter');
  const VW = () => window.innerWidth;

  function lbGo(idx, animate = true) {
    lbIdx = Math.max(0, Math.min(n - 1, idx));
    lbTrack.style.transition = animate
      ? 'transform 0.32s cubic-bezier(0.25,0.46,0.45,0.94)' : 'none';
    lbTrack.style.transform = `translateX(${-lbIdx * VW()}px)`;
    lbCtr.textContent = n > 1 ? `${lbIdx + 1} / ${n}` : '';
  }

  function openLb(idx) {
    lbGo(idx, false);
    lb.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function closeLb() {
    lb.classList.remove('open');
    document.body.style.overflow = '';
    gallery.scrollTo({ left: lbIdx * VW(), behavior: 'instant' });
    updateDots();
  }

  gallery.querySelectorAll('img').forEach(img =>
    img.addEventListener('click', () => openLb(parseInt(img.dataset.li)))
  );
  lb.querySelector('.lb-close').addEventListener('click', closeLb);
  lb.querySelector('.lb-prev')?.addEventListener('click', e => { e.stopPropagation(); lbGo(lbIdx - 1); });
  lb.querySelector('.lb-next')?.addEventListener('click', e => { e.stopPropagation(); lbGo(lbIdx + 1); });

  let lbX = null;
  lb.addEventListener('touchstart', e => {
    if (e.target.closest('button')) return;
    lbX = e.touches[0].clientX;
    lbTrack.style.transition = 'none';
  }, { passive: true });
  lb.addEventListener('touchmove', e => {
    if (lbX === null) return;
    const dx = e.touches[0].clientX - lbX;
    const base = -lbIdx * VW();
    const atEdge = (dx > 0 && lbIdx === 0) || (dx < 0 && lbIdx === n - 1);
    lbTrack.style.transform = `translateX(${base + (atEdge ? dx * 0.2 : dx)}px)`;
  }, { passive: true });
  lb.addEventListener('touchend', e => {
    if (lbX === null) return;
    const dx = e.changedTouches[0].clientX - lbX;
    lbX = null;
    if (Math.abs(dx) > 50) lbGo(lbIdx + (dx < 0 ? 1 : -1));
    else lbGo(lbIdx);
  });
};
