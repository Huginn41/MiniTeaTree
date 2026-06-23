App.renderAbout = async function(c) {
  this.setHeader('О нас');
  c.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;padding:40px 0"><div style="width:32px;height:32px;border:3px solid var(--md-primary);border-top-color:transparent;border-radius:50%;animation:spin .7s linear infinite"></div></div>`;

  let points = [], faq = [], about = {};
  try { about  = await api('/info/about'); } catch(_) {}
  try { points = await api('/info/pickup-points'); } catch(_) {}
  try { faq    = await api('/info/faq'); } catch(_) {}

  const fullAddr = p => {
    const parts = [];
    if (p.city)     parts.push(p.city);
    if (p.street)   parts.push(p.street);
    if (p.building) parts.push('д. ' + p.building);
    return parts.length ? parts.join(', ') : (p.address || '');
  };

  const pointCard = p => `
    <div style="background:var(--md-surface-container-low);border-radius:16px;padding:18px 16px;margin-bottom:12px">
      <div style="display:flex;align-items:flex-start;gap:12px">
        <div style="width:40px;height:40px;border-radius:12px;background:var(--md-primary-container);display:flex;align-items:center;justify-content:center;flex-shrink:0">
          <svg width="20" height="20" fill="none" stroke="var(--md-primary)" stroke-width="2" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/>
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
        </div>
        <div style="flex:1;min-width:0">
          <p style="font-size:15px;font-weight:700;color:var(--md-on-surface);margin:0 0 4px">${esc(p.name)}</p>
          <p style="font-size:13px;color:var(--md-on-surface-variant);margin:0 0 10px;line-height:1.4">${esc(fullAddr(p))}</p>
          ${p.work_hours ? `
          <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:8px">
            <svg width="15" height="15" fill="none" stroke="var(--md-on-surface-variant)" stroke-width="2" viewBox="0 0 24 24" style="flex-shrink:0;margin-top:1px">
              <circle cx="12" cy="12" r="10"/><path stroke-linecap="round" d="M12 6v6l4 2"/>
            </svg>
            <p style="font-size:12.5px;color:var(--md-on-surface-variant);margin:0;line-height:1.5">${esc(p.work_hours)}</p>
          </div>` : ''}
          ${p.comment ? `
          <div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:8px">
            <svg width="15" height="15" fill="none" stroke="var(--md-on-surface-variant)" stroke-width="2" viewBox="0 0 24 24" style="flex-shrink:0;margin-top:1px">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
            <p style="font-size:12.5px;color:var(--md-on-surface-variant);margin:0;line-height:1.5">${esc(p.comment)}</p>
          </div>` : ''}
          ${p.phone ? `
          <a href="tel:${esc(p.phone)}" style="display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--md-primary);font-weight:600;text-decoration:none;margin-top:4px">
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/>
            </svg>
            ${esc(p.phone)}
          </a>` : ''}
        </div>
      </div>
      ${p.map_embed_src ? `
      <div style="margin-top:12px;border-radius:12px;overflow:hidden">
        <iframe src="${p.map_embed_src}" width="100%" height="260" frameborder="0" allowfullscreen style="border:0;display:block"></iframe>
        <a href="https://yandex.ru/maps/?text=${encodeURIComponent(fullAddr(p))}" target="_blank"
          style="display:flex;align-items:center;justify-content:center;gap:6px;padding:11px;font-size:13px;font-weight:600;color:var(--md-primary);text-decoration:none;border-top:1px solid var(--md-outline-variant);background:var(--md-surface)">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
          Открыть в Яндекс Картах
        </a>
      </div>` : ''}
    </div>`;

  const bannerStyle = about.banner_image_path
    ? `background:url('${about.banner_image_path}') center/cover no-repeat;`
    : `background:linear-gradient(135deg,#1a6b3c 0%,#2d9e5f 100%);`;

  const title = about.title || 'Чайное Дерево';

  c.innerHTML = `
    <style>
      .about-rich p { font-size:14px; color:var(--md-on-surface); line-height:1.7; margin:0 0 8px; }
      .about-rich strong { font-weight:700; }
      .about-rich em { font-style:italic; }
      .about-rich u { text-decoration:underline; }
      .about-rich ul { padding-left:20px; margin:4px 0 8px; }
      .about-rich li { font-size:14px; color:var(--md-on-surface); line-height:1.6; margin-bottom:4px; }
      .about-rich a { color:var(--md-primary); }
      .faq-rich p { font-size:13.5px; color:var(--md-on-surface-variant); line-height:1.65; margin:0 0 6px; }
      .faq-rich strong { font-weight:700; }
      .faq-rich em { font-style:italic; }
      .faq-rich u { text-decoration:underline; }
      .faq-rich ul { padding-left:18px; margin:4px 0; }
      .faq-rich li { font-size:13.5px; color:var(--md-on-surface-variant); line-height:1.6; margin-bottom:3px; }
      .faq-rich a { color:var(--md-primary); }
    </style>
    <div style="padding:0 0 24px">

      <div style="${bannerStyle}border-radius:20px;min-height:220px;margin-bottom:20px;position:relative;overflow:hidden">
        ${about.banner_image_path ? '<div style="position:absolute;inset:0;background:rgba(0,0,0,.15);border-radius:20px"></div>' : ''}
        ${!about.banner_image_path ? '<div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:64px">🍵</div>' : ''}
      </div>

      <div style="margin-bottom:20px">
        <h2 style="font-size:22px;font-weight:800;color:var(--md-on-surface);margin:0 0 12px;letter-spacing:-.3px">${esc(title)}</h2>
        ${about.description_html && about.description_html.replace(/<[^>]+>/g,'').trim() ? `
        <div class="about-rich">${about.description_html}</div>
        ` : ''}
      </div>

      ${faq.length ? `
      <p style="font-size:13px;font-weight:700;color:var(--md-on-surface-variant);text-transform:uppercase;letter-spacing:.5px;margin:0 0 12px">
        Часто задаваемые вопросы
      </p>
      <div id="faq-list">
        ${faq.map(f => `
        <div class="faq-item" style="background:var(--md-surface-container-low);border-radius:14px;margin-bottom:8px;overflow:hidden">
          <button onclick="(function(btn){
            var item=btn.closest('.faq-item');
            var body=item.querySelector('.faq-body');
            var inner=item.querySelector('.faq-inner');
            var arrow=btn.querySelector('.faq-arrow');
            var isOpen=item.classList.contains('open');
            document.querySelectorAll('.faq-item.open').forEach(function(el){
              el.classList.remove('open');
              el.querySelector('.faq-body').style.height='0';
              el.querySelector('.faq-arrow').style.transform='';
            });
            if(!isOpen){
              item.classList.add('open');
              body.style.height=inner.offsetHeight+'px';
              arrow.style.transform='rotate(180deg)';
            }
          })(this)"
            style="width:100%;display:flex;justify-content:space-between;align-items:center;padding:15px 16px;background:none;border:none;cursor:pointer;text-align:left;gap:12px">
            <span style="font-size:14px;font-weight:600;color:var(--md-on-surface);line-height:1.4">${esc(f.question)}</span>
            <span class="faq-arrow" style="flex-shrink:0;font-size:18px;color:var(--md-primary);transition:transform .3s">⌄</span>
          </button>
          <div class="faq-body" style="overflow:hidden;transition:height .3s ease;height:0">
            <div class="faq-inner" style="padding:0 16px 15px">
              <div class="faq-rich">${(f.answer||'').replace(/\n/g,'<br>')}</div>
            </div>
          </div>
        </div>`).join('')}
      </div>
      ` : ''}

      ${points.length ? `
      <p style="font-size:13px;font-weight:700;color:var(--md-on-surface-variant);text-transform:uppercase;letter-spacing:.5px;margin:0 0 12px">
        Пункты самовывоза
      </p>
      ${points.map(pointCard).join('')}
      ` : ''}

    </div>`;
};
