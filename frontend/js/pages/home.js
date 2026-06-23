App.renderHome = async function(c) {
  this.setHeader('Чайное Дерево');
  const [banners, cats] = await Promise.all([
    api('/info/banners'),
    api('/catalog/categories'),
  ]);
  this.categories = cats;

  let html = '';

  if (banners.length) {
    html += `<div class="banner-scroll">
      ${banners.map(b => `
        <div class="banner-card">
          <img src="${imgUrl(b.image_path)}" alt="${esc(b.title || '')}" loading="lazy"/>
          ${b.title ? `<div class="banner-overlay"><h3>${esc(b.title)}</h3>${b.subtitle ? `<p>${esc(b.subtitle)}</p>` : ''}</div>` : ''}
        </div>
      `).join('')}
    </div>`;
  }

  html += `<div class="section-header" style="margin-top:16px">
    <h2>Категории</h2>
    <a onclick="App.navigate('catalog')">Все →</a>
  </div>`;

  const catTile = cat => `
    <button class="category-tile" onclick="App.navigate('catalog', '${cat.slug}')">
      <div class="category-tile-img">
        ${cat.image_path
          ? `<img class="cat-bg" src="${cat.image_path}" alt="${esc(cat.name)}" loading="lazy"/>`
          : `<div class="cat-emoji">${cat.icon || '🍃'}</div>`}
      </div>
      <span>${esc(cat.name)}</span>
    </button>`;

  html += `<div class="category-grid">
    ${cats.slice(0, 3).map(catTile).join('')}
    ${cats.length > 3 ? `
      <div class="cat-extra-grid">${cats.slice(3).map(catTile).join('')}</div>
      <button class="cat-show-more" onclick="
        const extra = this.closest('.category-grid').querySelector('.cat-extra-grid');
        const isOpen = extra.classList.toggle('open');
        this.querySelector('.cat-more-text').textContent = isOpen ? 'Скрыть' : 'Показать ещё';
        this.querySelector('.cat-more-arrow').classList.toggle('up', isOpen);
      "><span class="cat-more-text">Показать ещё</span><span class="cat-more-arrow">›</span></button>
    ` : ''}
  </div>`;

  try {
    const products = await api('/catalog/products');
    if (products.length) {
      html += `<div class="section-header">
        <h2>Популярное</h2>
        <a onclick="App.navigate('catalog')">Все →</a>
      </div>`;
      html += `<div class="products-scroll">
        ${products.slice(0, 8).map(p => this._productCardSmall(p)).join('')}
      </div>`;
    }
  } catch (_) {}

  c.innerHTML = html;
};
