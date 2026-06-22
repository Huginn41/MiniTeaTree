"""HTML-страница настроек бонусной системы."""

from __future__ import annotations


def render_bonus_settings(tiers: list, max_pct: int, admin_username: str = "") -> str:
    from app.admin.dashboard import _topnav

    nav = _topnav("settings")

    tiers_json = "[" + ",".join(
        f'{{"id":{t.id},"min_amount":{float(t.min_amount):.2f},"cashback_pct":{float(t.cashback_pct):.2f}}}'
        for t in tiers
    ) + "]"

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Бонусная система — настройки</title>
<link rel="icon" type="image/svg+xml" href="/static/favicon.svg">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
<style>
:root {{ --c-primary:#1a6b3c; --c-primary-light:#e8f5ee; --c-bg:#f0f2f7; --c-card:#fff; --c-border:#e5e7eb; }}
body {{ background:var(--c-bg); font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; }}
.wrap {{ max-width:760px; margin:0 auto; padding:24px 16px 72px; }}
.page-title {{ font-size:22px; font-weight:700; margin-bottom:4px; }}
.page-sub {{ font-size:13px; color:#6b7280; margin-bottom:24px; }}
.card {{ background:var(--c-card); border-radius:14px; border:1px solid var(--c-border); margin-bottom:20px; overflow:hidden; }}
.card-hdr {{ padding:16px 20px; border-bottom:1px solid var(--c-border); font-weight:700; font-size:15px; display:flex; align-items:center; gap:8px; }}
.card-hdr span.icon {{ font-size:18px; }}
.card-body {{ padding:20px; }}
.tier-row {{ display:grid; grid-template-columns:1fr 1fr auto; gap:12px; align-items:end; margin-bottom:12px; padding:16px; background:#f8fafb; border-radius:10px; border:1px solid var(--c-border); position:relative; }}
.tier-row .del-btn {{ background:none; border:none; color:#ef4444; font-size:18px; cursor:pointer; padding:4px 8px; line-height:1; border-radius:6px; }}
.tier-row .del-btn:hover {{ background:#fef2f2; }}
.lbl {{ font-size:12px; font-weight:600; color:#374151; margin-bottom:4px; display:block; }}
.inp {{ width:100%; border:1px solid #d1d5db; border-radius:8px; padding:8px 12px; font-size:14px; }}
.inp:focus {{ outline:none; border-color:var(--c-primary); box-shadow:0 0 0 3px rgba(26,107,60,.1); }}
.btn-add {{ background:var(--c-primary-light); color:var(--c-primary); border:none; border-radius:8px; padding:10px 18px; font-weight:600; font-size:14px; cursor:pointer; }}
.btn-add:hover {{ background:#d1e9db; }}
.btn-save {{ background:var(--c-primary); color:#fff; border:none; border-radius:8px; padding:11px 24px; font-weight:600; font-size:14px; cursor:pointer; }}
.btn-save:hover {{ background:#155d33; }}
.pct-wrap {{ display:flex; align-items:center; gap:14px; }}
.pct-slider {{ flex:1; accent-color:var(--c-primary); }}
.pct-badge {{ background:var(--c-primary); color:#fff; border-radius:8px; padding:6px 14px; font-weight:700; font-size:18px; min-width:64px; text-align:center; }}
.hint {{ font-size:12px; color:#6b7280; margin-top:6px; }}
.toast {{ position:fixed; bottom:24px; right:24px; background:#1a6b3c; color:#fff; padding:12px 20px; border-radius:10px; font-weight:600; font-size:14px; display:none; z-index:9999; box-shadow:0 4px 20px rgba(0,0,0,.2); }}
.toast.err {{ background:#dc2626; }}
.empty-hint {{ color:#9ca3af; font-size:13px; text-align:center; padding:12px 0; }}
</style>
</head>
<body>
{nav}
<div class="wrap">
  <div class="page-title">🎁 Бонусная система</div>
  <div class="page-sub">Настройте кешбэк и условия списания баллов</div>

  <!-- Tiers -->
  <div class="card">
    <div class="card-hdr"><span class="icon">📊</span> Ступени кешбэка</div>
    <div class="card-body">
      <div id="tiers-list"></div>
      <button class="btn-add" onclick="addTier()">+ Добавить ступень</button>
      <div class="hint" style="margin-top:10px">Кешбэк начисляется от суммы заказа по ступени, соответствующей общим тратам клиента. Каждая следующая ступень должна быть больше предыдущей.</div>
    </div>
  </div>

  <!-- Max payment pct -->
  <div class="card">
    <div class="card-hdr"><span class="icon">💳</span> Оплата баллами</div>
    <div class="card-body">
      <label class="lbl">Максимальный процент заказа, который можно оплатить баллами</label>
      <div class="pct-wrap">
        <input type="range" class="pct-slider" id="max-pct-slider" min="0" max="99" value="{max_pct}" oninput="document.getElementById('pct-val').textContent=this.value+'%'">
        <div class="pct-badge" id="pct-val">{max_pct}%</div>
      </div>
      <div class="hint">0% — оплата баллами отключена. 99% — клиент может оплатить баллами почти весь заказ.</div>
    </div>
  </div>

  <div style="display:flex;justify-content:flex-end">
    <button class="btn-save" onclick="saveAll()">💾 Сохранить настройки</button>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
var tiers = {tiers_json};

function renderTiers() {{
  var list = document.getElementById('tiers-list');
  if (!tiers.length) {{
    list.innerHTML = '<div class="empty-hint">Ступеней нет — добавьте хотя бы одну</div>';
    return;
  }}
  tiers.sort(function(a,b){{return a.min_amount-b.min_amount;}});
  list.innerHTML = tiers.map(function(t,i){{
    return '<div class="tier-row" data-idx="'+i+'">'
      +'<div><label class="lbl">От суммы покупок, ₽</label>'
      +'<input class="inp" type="number" min="0" step="100" value="'+t.min_amount+'" onchange="tiers['+i+'].min_amount=+this.value"></div>'
      +'<div><label class="lbl">Кешбэк, %</label>'
      +'<input class="inp" type="number" min="0.1" max="99" step="0.1" value="'+t.cashback_pct+'" onchange="tiers['+i+'].cashback_pct=+this.value"></div>'
      +'<button class="del-btn" onclick="deleteTier('+i+')">✕</button>'
      +'</div>';
  }}).join('');
}}

function addTier() {{
  var lastMax = tiers.length ? Math.max.apply(null, tiers.map(function(t){{return t.min_amount;}})) : 0;
  tiers.push({{id:null, min_amount: lastMax+1000, cashback_pct:5}});
  renderTiers();
}}

function deleteTier(idx) {{
  tiers.splice(idx, 1);
  renderTiers();
}}

async function saveAll() {{
  // Validate: amounts must be unique and increasing
  var sorted = tiers.slice().sort(function(a,b){{return a.min_amount-b.min_amount;}});
  for (var i=1;i<sorted.length;i++) {{
    if (sorted[i].min_amount <= sorted[i-1].min_amount) {{
      showToast('Каждая следующая ступень должна быть больше предыдущей', true);
      return;
    }}
  }}
  var maxPct = +document.getElementById('max-pct-slider').value;
  try {{
    var r1 = await fetch('/admin-api/bonus/settings', {{
      method:'PATCH', headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{bonus_max_payment_pct: maxPct}})
    }});
    var r2 = await fetch('/admin-api/bonus/tiers', {{
      method:'PUT', headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify(tiers.map(function(t){{return {{min_amount:t.min_amount, cashback_pct:t.cashback_pct}}}}))
    }});
    if (!r1.ok || !r2.ok) throw new Error('Ошибка сервера');
    var data = await r2.json();
    tiers = data.tiers;
    renderTiers();
    showToast('Настройки сохранены ✓');
  }} catch(e) {{
    showToast(e.message||'Ошибка', true);
  }}
}}

function showToast(msg, err) {{
  var t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast' + (err?' err':'');
  t.style.display = 'block';
  setTimeout(function(){{t.style.display='none';}}, 3000);
}}

renderTiers();
</script>
</body>
</html>"""
