"""Customer-facing account dashboard HTML.

Renders the data from GET /v1/me/dashboard. Any active API key can use it —
the page prompts for the key, stores it only in browser localStorage, and
polls the endpoint every 60 seconds while the tab is visible.
"""

ME_PAGE_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>ToolRate — Your Dashboard</title>
<link rel="icon" href="https://api.toolrate.ai/static/toolrate-favicon.png" type="image/png">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0a0b10;
  --surface: #0f1118;
  --surface-2: #141620;
  --border: #1c1f2e;
  --border-strong: #282c40;
  --text: #d4d8e8;
  --text-bright: #f0f2f8;
  --text-dim: #9299b0;
  --text-mute: #6a6f85;
  --orange: #f07019;
  --orange-dim: rgba(240,112,25,0.16);
  --green: #3ddc84;
  --red: #f05a5a;
  --yellow: #f0c53b;
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{background:var(--bg);color:var(--text);font-family:'Poppins','Segoe UI',Arial,sans-serif;font-weight:300;line-height:1.55;-webkit-font-smoothing:antialiased;min-height:100vh}
a{color:inherit;text-decoration:none}
code,.mono{font-family:'Fira Code',monospace}
.page{max-width:1180px;margin:0 auto;padding:0 2rem 4rem}

/* ── Topbar ── */
.topbar{display:flex;align-items:center;justify-content:space-between;padding:1.4rem 0;border-bottom:1px solid var(--border);margin-bottom:2rem;flex-wrap:wrap;gap:0.75rem}
.topbar-left{display:flex;align-items:center;gap:0.75rem}
.topbar-left img{height:28px}
.topbar-tag{font-size:0.6rem;color:var(--orange);border:1px solid var(--orange);padding:0.2rem 0.55rem;border-radius:4px;letter-spacing:0.12em;text-transform:uppercase;font-weight:600}
.topbar-right{display:flex;align-items:center;gap:1rem;font-size:0.74rem;color:var(--text-dim)}
.topbar-right .dot{width:8px;height:8px;border-radius:50%;background:var(--green);display:inline-block;box-shadow:0 0 10px var(--green);animation:pulse 2s infinite}
.topbar-right .dot.err{background:var(--red);box-shadow:0 0 10px var(--red)}
.topbar-right button{background:transparent;border:1px solid var(--border-strong);color:var(--text-dim);padding:0.35rem 0.7rem;border-radius:6px;font-family:inherit;font-size:0.72rem;cursor:pointer}
.topbar-right button:hover{color:var(--orange);border-color:var(--orange)}

/* ── Auth screen ── */
.auth{max-width:440px;margin:6rem auto;padding:2.5rem;background:var(--surface);border:1px solid var(--border);border-radius:14px}
.auth h1{font-size:1.4rem;font-weight:700;color:var(--text-bright);margin-bottom:0.4rem}
.auth p{font-size:0.82rem;color:var(--text-dim);margin-bottom:1.5rem;line-height:1.55}
.auth label{display:block;font-size:0.68rem;font-weight:500;color:var(--text-dim);margin-bottom:0.4rem;text-transform:uppercase;letter-spacing:0.08em}
.auth input{width:100%;padding:0.75rem 1rem;background:var(--surface-2);border:1px solid var(--border-strong);border-radius:8px;color:var(--text-bright);font-family:'Fira Code',monospace;font-size:0.82rem;outline:none;transition:border-color 0.2s}
.auth input:focus{border-color:var(--orange)}
.auth button{width:100%;padding:0.8rem;margin-top:1rem;background:var(--orange);border:none;color:#fff;border-radius:8px;font-family:inherit;font-size:0.85rem;font-weight:600;cursor:pointer;transition:all 0.2s}
.auth button:hover{background:#e0650f}
.auth .err{display:none;margin-top:1rem;padding:0.7rem 0.9rem;background:rgba(240,90,90,0.08);border:1px solid rgba(240,90,90,0.25);color:var(--red);border-radius:8px;font-size:0.78rem}
.auth .err.show{display:block}
.auth .hint{font-size:0.72rem;color:var(--text-mute);margin-top:1.25rem;line-height:1.5;text-align:center}
.auth .hint a{color:var(--orange)}

/* ── Layout ── */
.grid-2{display:grid;grid-template-columns:1.4fr 1fr;gap:1.25rem;margin-bottom:1.25rem}
.grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:1.25rem}
.section{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:1.6rem 1.75rem;margin-bottom:1.25rem}
.section-head{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:1.25rem;gap:1rem;flex-wrap:wrap}
.section-head h2{font-size:0.95rem;font-weight:600;color:var(--text-bright)}
.section-head .meta{font-size:0.7rem;color:var(--text-dim)}

/* ── Usage gauge ── */
.gauge{display:flex;align-items:baseline;gap:0.75rem;margin-bottom:1rem}
.gauge .used{font-size:2.6rem;font-weight:700;color:var(--text-bright);font-variant-numeric:tabular-nums;letter-spacing:-0.02em;line-height:1}
.gauge .sep{font-size:1.3rem;color:var(--text-mute)}
.gauge .lim{font-size:1.3rem;font-weight:500;color:var(--text-dim);font-variant-numeric:tabular-nums}
.gauge .pct{margin-left:auto;font-size:0.82rem;color:var(--text-dim);font-variant-numeric:tabular-nums}
.gbar{position:relative;height:10px;background:var(--surface-2);border-radius:999px;overflow:hidden;border:1px solid var(--border)}
.gbar .fill{position:absolute;top:0;left:0;bottom:0;background:var(--orange);border-radius:999px;transition:width 0.6s ease}
.gbar .fill.warn{background:var(--yellow)}
.gbar .fill.bad{background:var(--red)}
.gauge-sub{display:flex;justify-content:space-between;align-items:center;margin-top:0.75rem;font-size:0.74rem;color:var(--text-dim)}
.gauge-sub strong{color:var(--text)}

/* ── Pills ── */
.pill{display:inline-block;padding:0.15rem 0.55rem;border-radius:999px;font-size:0.64rem;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;font-family:inherit}
.pill.good{background:rgba(61,220,132,0.14);color:var(--green)}
.pill.warn{background:rgba(240,197,59,0.14);color:var(--yellow)}
.pill.bad{background:rgba(240,90,90,0.14);color:var(--red)}
.pill.dim{background:var(--surface-2);color:var(--text-dim)}

/* ── Sparkline ── */
.spark{width:100%;height:80px;margin-top:0.3rem}
.spark path.area{fill:rgba(240,112,25,0.14)}
.spark path.line{fill:none;stroke:var(--orange);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.spark text{font-family:'Poppins',sans-serif;font-size:9px;fill:var(--text-mute)}

/* ── Account rows ── */
.rows{display:grid;grid-template-columns:1fr 1fr;gap:0.75rem 1.5rem;font-size:0.82rem}
.rows .lbl{font-size:0.62rem;color:var(--text-dim);letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.25rem}
.rows .val{color:var(--text-bright);font-weight:500;font-family:'Fira Code',monospace;font-size:0.82rem;word-break:break-all}
.rows .val.plain{font-family:'Poppins',sans-serif;font-weight:500}

/* ── Tiles ── */
.tile{padding:1.2rem 1.4rem;background:var(--surface);border:1px solid var(--border);border-radius:12px}
.tile .label{font-size:0.62rem;color:var(--text-dim);letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.4rem;font-weight:500}
.tile .value{font-size:1.55rem;font-weight:700;color:var(--text-bright);font-variant-numeric:tabular-nums;line-height:1.1}
.tile .sub{font-size:0.7rem;color:var(--text-dim);margin-top:0.3rem}

/* ── Upgrade banner ── */
.upgrade{margin-bottom:1.25rem;padding:1rem 1.25rem;background:linear-gradient(180deg,rgba(240,112,25,0.08),rgba(240,112,25,0.02));border:1px solid rgba(240,112,25,0.25);border-radius:12px;display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap}
.upgrade .msg{font-size:0.82rem;color:var(--text);flex:1;min-width:260px;line-height:1.5}
.upgrade .msg strong{color:var(--orange);font-weight:600}
.upgrade a{padding:0.55rem 1rem;background:var(--orange);color:#fff;border-radius:8px;font-size:0.78rem;font-weight:600;text-decoration:none;transition:background 0.2s;white-space:nowrap}
.upgrade a:hover{background:#e0650f}

/* ── Danger zone ── */
.danger{border-color:rgba(240,90,90,0.2)}
.danger .section-head h2{color:var(--red)}
.danger .actions{display:grid;gap:0.75rem;grid-template-columns:1fr 1fr}
.danger .act{padding:0.9rem 1rem;border:1px solid var(--border-strong);border-radius:10px;background:var(--surface-2);font-size:0.78rem;color:var(--text)}
.danger .act strong{display:block;color:var(--text-bright);font-size:0.82rem;margin-bottom:0.25rem;font-weight:600}
.danger .act .hint{font-size:0.7rem;color:var(--text-mute);margin-top:0.4rem;font-family:'Fira Code',monospace;word-break:break-all}

@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}

@media (max-width:900px){
  .grid-2,.grid-3{grid-template-columns:1fr}
  .rows{grid-template-columns:1fr}
  .danger .actions{grid-template-columns:1fr}
}
@media (max-width:600px){
  .page{padding:0 1rem 3rem}
}
</style>
</head>
<body>

<!-- Auth prompt -->
<div class="auth" id="auth-screen">
  <h1>Your ToolRate account</h1>
  <p>Paste your API key to view usage, quota, and billing. Your key is kept only in your browser's localStorage — we never store it on the server.</p>
  <label for="user-key">API Key</label>
  <input type="password" id="user-key" placeholder="nf_live_...">
  <button onclick="authenticate()">Open Dashboard</button>
  <div class="err" id="auth-err"></div>
  <p class="hint">Don't have one yet? <a href="/register">Get a free key</a></p>
</div>

<!-- Dashboard -->
<div class="page" id="dashboard" style="display:none">

<header class="topbar">
  <div class="topbar-left">
    <img src="https://api.toolrate.ai/static/toolrate-logo.webp" alt="ToolRate">
    <span class="topbar-tag" id="tier-tag">—</span>
  </div>
  <div class="topbar-right">
    <span><span class="dot" id="status-dot"></span> <span id="status-text">Live</span></span>
    <span id="last-update">&mdash;</span>
    <button onclick="refresh()">Refresh</button>
    <button onclick="logout()">Log out</button>
  </div>
</header>

<!-- Upgrade banner (only shown when backend suggests one) -->
<div class="upgrade" id="upgrade-banner" style="display:none">
  <div class="msg" id="upgrade-msg"></div>
  <a id="upgrade-cta" href="/pricing">See plans</a>
</div>

<!-- Top row: usage gauge + quick tiles -->
<div class="grid-2">
  <div class="section">
    <div class="section-head">
      <h2 id="gauge-title">Current period</h2>
      <div class="meta"><span class="pill" id="status-pill">—</span></div>
    </div>
    <div class="gauge">
      <div class="used" id="g-used">&mdash;</div>
      <div class="sep">/</div>
      <div class="lim" id="g-limit">&mdash;</div>
      <div class="pct" id="g-pct">&mdash;</div>
    </div>
    <div class="gbar"><div class="fill" id="g-fill" style="width:0%"></div></div>
    <div class="gauge-sub">
      <span><strong id="g-remaining">&mdash;</strong> remaining</span>
      <span>Resets <strong id="g-resets">&mdash;</strong></span>
    </div>
  </div>

  <div>
    <div class="tile" style="margin-bottom:1rem">
      <div class="label">30-day total</div>
      <div class="value" id="t-30d">&mdash;</div>
      <div class="sub"><span id="t-days">0</span> active days · avg <span id="t-avg">0</span>/day</div>
    </div>
    <div class="tile">
      <div class="label">Peak day</div>
      <div class="value" id="t-peak">&mdash;</div>
      <div class="sub" id="t-peak-date">—</div>
    </div>
  </div>
</div>

<!-- Usage history sparkline -->
<div class="section">
  <div class="section-head">
    <h2>Assessments — last 30 days</h2>
    <div class="meta" id="chart-meta">&mdash;</div>
  </div>
  <svg class="spark" id="spark-30d"></svg>
</div>

<!-- Billing + Account -->
<div class="grid-2">
  <div class="section" id="billing-section">
    <div class="section-head">
      <h2>Billing</h2>
      <div class="meta" id="billing-meta">&mdash;</div>
    </div>
    <div id="billing-body">&mdash;</div>
  </div>

  <div class="section">
    <div class="section-head"><h2>Account</h2></div>
    <div class="rows">
      <div>
        <div class="lbl">Key prefix</div>
        <div class="val" id="a-prefix">&mdash;</div>
      </div>
      <div>
        <div class="lbl">Tier</div>
        <div class="val plain" id="a-tier">&mdash;</div>
      </div>
      <div>
        <div class="lbl">Billing period</div>
        <div class="val plain" id="a-period">&mdash;</div>
      </div>
      <div>
        <div class="lbl">Data pool</div>
        <div class="val plain" id="a-pool">&mdash;</div>
      </div>
      <div>
        <div class="lbl">Created</div>
        <div class="val plain" id="a-created">&mdash;</div>
      </div>
      <div>
        <div class="lbl">Last used</div>
        <div class="val plain" id="a-last">&mdash;</div>
      </div>
    </div>
  </div>
</div>

<!-- Danger zone -->
<div class="section danger">
  <div class="section-head">
    <h2>Danger zone</h2>
    <div class="meta">account management</div>
  </div>
  <div class="actions">
    <div class="act">
      <strong>Rotate API key</strong>
      Generate a fresh key and retire the current one. Use it when a key is exposed.
      <div class="hint">POST /v1/auth/rotate-key</div>
    </div>
    <div class="act">
      <strong>Delete account</strong>
      Permanent — removes your API key and all associated records.
      <div class="hint">DELETE /v1/account</div>
    </div>
  </div>
</div>

</div><!-- /.page -->

<script>
const STORAGE_KEY = 'nemoflow_user_key';
let refreshTimer = null;

function getKey() { return localStorage.getItem(STORAGE_KEY); }
function setKey(k) { localStorage.setItem(STORAGE_KEY, k); }
function clearKey() { localStorage.removeItem(STORAGE_KEY); }

function showAuth(errMsg) {
  document.getElementById('auth-screen').style.display = 'block';
  document.getElementById('dashboard').style.display = 'none';
  if (errMsg) {
    var e = document.getElementById('auth-err');
    e.textContent = errMsg;
    e.classList.add('show');
  }
}
function showDashboard() {
  document.getElementById('auth-screen').style.display = 'none';
  document.getElementById('dashboard').style.display = 'block';
}

function authenticate() {
  var key = document.getElementById('user-key').value.trim();
  if (!key) return;
  setKey(key);
  refresh();
}

function logout() {
  clearKey();
  if (refreshTimer) clearInterval(refreshTimer);
  location.reload();
}

async function refresh() {
  var key = getKey();
  if (!key) { showAuth(); return; }

  try {
    var resp = await fetch('/v1/me/dashboard', {
      headers: {'X-Api-Key': key}
    });
    if (resp.status === 401) {
      clearKey();
      showAuth('That API key is not valid.');
      return;
    }
    if (resp.status === 429) {
      document.getElementById('status-dot').classList.add('err');
      document.getElementById('status-text').textContent = 'Rate limited';
      return;
    }
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    var data = await resp.json();
    showDashboard();
    render(data);
    document.getElementById('status-dot').classList.remove('err');
    document.getElementById('status-text').textContent = 'Live';
    document.getElementById('last-update').textContent =
      'Updated ' + new Date().toLocaleTimeString();
  } catch (err) {
    document.getElementById('status-dot').classList.add('err');
    document.getElementById('status-text').textContent = 'Disconnected';
    console.error(err);
  }
}

function fmtNum(n) {
  if (n === null || n === undefined) return '—';
  return Number(n).toLocaleString();
}
function fmtDate(iso) {
  if (!iso) return '—';
  try {
    var d = new Date(iso);
    return d.toLocaleDateString(undefined, {month:'short', day:'numeric', year:'numeric'});
  } catch (_) { return iso; }
}
function fmtDateTime(iso) {
  if (!iso) return '—';
  try {
    var d = new Date(iso);
    return d.toLocaleString(undefined, {month:'short', day:'numeric', hour:'2-digit', minute:'2-digit'});
  } catch (_) { return iso; }
}
function fmtUsd(n) {
  if (n === null || n === undefined) return '—';
  return '$' + Number(n).toFixed(2);
}

function render(d) {
  // ── Tier tag in topbar ──
  var tier = (d.account.tier || '').toUpperCase();
  document.getElementById('tier-tag').textContent = tier || '—';

  // ── Usage gauge ──
  var cp = d.current_period;
  document.getElementById('gauge-title').textContent = cp.label || 'Current period';
  document.getElementById('g-used').textContent = fmtNum(cp.used);
  document.getElementById('g-limit').textContent = fmtNum(cp.limit);
  document.getElementById('g-pct').textContent = cp.percent_used.toFixed(1) + '%';
  document.getElementById('g-remaining').textContent = fmtNum(cp.remaining);
  document.getElementById('g-resets').textContent = fmtDateTime(cp.resets_at);

  var fill = document.getElementById('g-fill');
  fill.style.width = Math.min(100, cp.percent_used).toFixed(1) + '%';
  fill.className = 'fill';
  if (d.status.health === 'over_limit') fill.classList.add('bad');
  else if (d.status.health === 'near_limit') fill.classList.add('warn');

  var statusPill = document.getElementById('status-pill');
  if (d.status.health === 'over_limit') {
    statusPill.textContent = 'Over limit';
    statusPill.className = 'pill bad';
  } else if (d.status.health === 'near_limit') {
    statusPill.textContent = 'Near limit';
    statusPill.className = 'pill warn';
  } else {
    statusPill.textContent = 'Healthy';
    statusPill.className = 'pill good';
  }

  // ── 30d tiles ──
  var tot = d.usage_totals;
  document.getElementById('t-30d').textContent = fmtNum(tot.total_30d);
  document.getElementById('t-days').textContent = tot.days_active_30d;
  document.getElementById('t-avg').textContent = tot.daily_avg;
  if (tot.peak_day) {
    document.getElementById('t-peak').textContent = fmtNum(tot.peak_day.count);
    document.getElementById('t-peak-date').textContent = fmtDate(tot.peak_day.date);
  } else {
    document.getElementById('t-peak').textContent = '0';
    document.getElementById('t-peak-date').textContent = 'no activity yet';
  }

  // ── Sparkline ──
  drawSpark('spark-30d', d.usage_last_30d || []);
  document.getElementById('chart-meta').textContent =
    fmtNum(tot.total_30d) + ' assessments · avg ' + tot.daily_avg + '/day';

  // ── Billing ──
  renderBilling(d);

  // ── Account ──
  document.getElementById('a-prefix').textContent = d.account.key_prefix || '—';
  document.getElementById('a-tier').textContent = d.account.tier || '—';
  document.getElementById('a-period').textContent = d.account.billing_period || '—';
  document.getElementById('a-pool').textContent = d.account.data_pool || 'default';
  document.getElementById('a-created').textContent = fmtDate(d.account.created_at);
  document.getElementById('a-last').textContent = fmtDateTime(d.account.last_used_at);

  // ── Upgrade banner ──
  var up = d.upgrade || {};
  var banner = document.getElementById('upgrade-banner');
  if (up.suggested_plan && up.reason) {
    document.getElementById('upgrade-msg').innerHTML =
      '<strong>Suggested: ' + up.suggested_plan.toUpperCase() + '</strong> — ' + up.reason;
    var cta = document.getElementById('upgrade-cta');
    if (up.suggested_plan === 'payg' || up.suggested_plan === 'pro') {
      cta.href = '/upgrade?plan=' + up.suggested_plan;
      cta.textContent = 'Upgrade now';
    } else {
      cta.href = '/pricing';
      cta.textContent = 'Contact sales';
    }
    banner.style.display = 'flex';
  } else {
    banner.style.display = 'none';
  }
}

function renderBilling(d) {
  var b = d.billing || {};
  var body = document.getElementById('billing-body');
  var meta = document.getElementById('billing-meta');
  var html = '';

  if (b.plan === 'payg') {
    meta.textContent = 'month-to-date';
    html =
      '<div class="rows">' +
        '<div><div class="lbl">Plan</div><div class="val plain">Pay-as-you-go</div></div>' +
        '<div><div class="lbl">Free grant / day</div><div class="val plain">' + fmtNum(b.payg_free_daily_calls) + '</div></div>' +
        '<div><div class="lbl">Billable this month</div><div class="val plain">' + fmtNum(b.payg_billable_mtd) + '</div></div>' +
        '<div><div class="lbl">Est. cost this month</div><div class="val plain">' + fmtUsd(b.payg_estimated_cost_usd) + '</div></div>' +
        '<div><div class="lbl">Price per call</div><div class="val plain">$' + Number(b.payg_price_per_call_usd).toFixed(4) + '</div></div>' +
      '</div>';
  } else if (b.plan === 'pro') {
    meta.textContent = '$29 / month, flat';
    html =
      '<div class="rows">' +
        '<div><div class="lbl">Plan</div><div class="val plain">Pro</div></div>' +
        '<div><div class="lbl">Monthly included</div><div class="val plain">' + fmtNum(b.pro_monthly_included) + '</div></div>' +
      '</div>';
  } else if (b.plan === 'free') {
    meta.textContent = 'no charge';
    html =
      '<div class="rows">' +
        '<div><div class="lbl">Plan</div><div class="val plain">Free</div></div>' +
        '<div><div class="lbl">Daily limit</div><div class="val plain">' + fmtNum(b.free_daily_calls) + '</div></div>' +
      '</div>' +
      '<p style="margin-top:1rem;font-size:0.78rem;color:var(--text-dim)">Upgrade to unlock webhook alerts and higher limits.</p>';
  } else if (b.plan === 'enterprise') {
    meta.textContent = 'custom contract';
    html = '<p style="font-size:0.82rem;color:var(--text)">Enterprise plan — contact sales for billing and usage details.</p>';
  } else {
    meta.textContent = '';
    html = '<p class="empty" style="color:var(--text-mute);font-size:0.8rem">No billing info for this tier.</p>';
  }
  body.innerHTML = html;
}

function drawSpark(id, points) {
  var svg = document.getElementById(id);
  svg.innerHTML = '';
  var w = svg.clientWidth, h = svg.clientHeight;
  if (!points || points.length === 0 || w === 0) {
    svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle">no data</text>';
    return;
  }
  var padX = 8, padY = 12;
  var maxY = Math.max.apply(null, points.map(function(p){return p.count;})) || 1;
  var innerW = w - padX*2, innerH = h - padY*2;
  var stepX = innerW / Math.max(points.length - 1, 1);

  var lineD = '', areaD = 'M ' + padX + ' ' + (h - padY);
  points.forEach(function(p, i) {
    var x = padX + stepX * i;
    var y = padY + innerH - (p.count / maxY) * innerH;
    var cmd = (i === 0 ? 'M' : 'L') + ' ' + x.toFixed(1) + ' ' + y.toFixed(1) + ' ';
    lineD += cmd;
    areaD += 'L ' + x.toFixed(1) + ' ' + y.toFixed(1) + ' ';
  });
  areaD += 'L ' + (padX + stepX * (points.length - 1)).toFixed(1) + ' ' + (h - padY) + ' Z';

  svg.innerHTML =
    '<path class="area" d="' + areaD + '"/>' +
    '<path class="line" d="' + lineD + '"/>' +
    '<text x="' + (w - padX) + '" y="' + (padY + 2) + '" text-anchor="end">max ' + fmtNum(maxY) + '</text>';
}

// ── Init ──
if (getKey()) {
  refresh();
} else {
  showAuth();
}

document.getElementById('user-key').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') authenticate();
});

// Auto-refresh every 60s while tab visible
refreshTimer = setInterval(function() {
  if (document.visibilityState === 'visible' && getKey()) refresh();
}, 60000);
</script>
</body>
</html>"""
