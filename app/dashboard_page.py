"""Admin dashboard HTML — platform insights rendered from /v1/admin/dashboard.

Gated by an admin API key stored in localStorage. Auto-refreshes every 30s
while the tab is visible.
"""

from app.site_header import SITE_HEADER_CSS, SITE_HEADER_HTML, SITE_HEADER_JS

_DASHBOARD_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>ToolRate — Admin Dashboard</title>
<link rel="icon" href="https://toolrate.ai/toolrate-favicon.png" type="image/png">
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
  --brand: #0a95fd;
  --brand-dim: rgba(10,149,253,0.16);
  --green: #3ddc84;
  --red: #f05a5a;
  --yellow: #f0c53b;
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{background:var(--bg);color:var(--text);font-family:'Poppins','Segoe UI',Arial,sans-serif;font-weight:300;line-height:1.55;-webkit-font-smoothing:antialiased;min-height:100vh}
a{color:inherit;text-decoration:none}
code,.mono{font-family:'Fira Code',monospace}
.page{max-width:1400px;margin:0 auto;padding:0 2rem 4rem}

/* ── Shared marketing topbar (logo + nav + mobile hamburger) ── */
__SITE_HEADER_CSS__

/* ── Auth-specific status strip (admin tag + live dot + refresh/logout) ── */
.status-strip{display:flex;align-items:center;justify-content:space-between;padding:0.85rem 0 1.4rem;margin-bottom:1.5rem;border-bottom:1px solid var(--border);flex-wrap:wrap;gap:0.75rem}
.status-strip-left{display:flex;align-items:center;gap:0.75rem}
.topbar-tag{font-size:0.6rem;color:var(--brand);border:1px solid var(--brand);padding:0.2rem 0.55rem;border-radius:4px;letter-spacing:0.12em;text-transform:uppercase;font-weight:600}
.status-strip-right{display:flex;align-items:center;gap:1rem;font-size:0.74rem;color:var(--text-dim);flex-wrap:wrap}
.status-strip-right .dot{width:8px;height:8px;border-radius:50%;background:var(--green);display:inline-block;box-shadow:0 0 10px var(--green);animation:pulse 2s infinite}
.status-strip-right .dot.err{background:var(--red);box-shadow:0 0 10px var(--red)}
.status-strip-right button{background:transparent;border:1px solid var(--border-strong);color:var(--text-dim);padding:0.35rem 0.7rem;border-radius:6px;font-family:inherit;font-size:0.72rem;cursor:pointer}
.status-strip-right button:hover{color:var(--brand);border-color:var(--brand)}

/* ── Auth screen ── */
.auth{max-width:440px;margin:6rem auto;padding:2.5rem;background:var(--surface);border:1px solid var(--border);border-radius:14px}
.auth h1{font-size:1.4rem;font-weight:700;color:var(--text-bright);margin-bottom:0.4rem}
.auth p{font-size:0.82rem;color:var(--text-dim);margin-bottom:1.5rem;line-height:1.55}
.auth label{display:block;font-size:0.68rem;font-weight:500;color:var(--text-dim);margin-bottom:0.4rem;text-transform:uppercase;letter-spacing:0.08em}
.auth input{width:100%;padding:0.75rem 1rem;background:var(--surface-2);border:1px solid var(--border-strong);border-radius:8px;color:var(--text-bright);font-family:'Fira Code',monospace;font-size:0.82rem;outline:none;transition:border-color 0.2s}
.auth input:focus{border-color:var(--brand)}
.auth button{width:100%;padding:0.8rem;margin-top:1rem;background:var(--brand);border:none;color:#fff;border-radius:8px;font-family:inherit;font-size:0.85rem;font-weight:600;cursor:pointer;transition:all 0.2s}
.auth button:hover{background:#0784e6}
.auth .err{display:none;margin-top:1rem;padding:0.7rem 0.9rem;background:rgba(240,90,90,0.08);border:1px solid rgba(240,90,90,0.25);color:var(--red);border-radius:8px;font-size:0.78rem}
.auth .err.show{display:block}
.auth .hint{font-size:0.7rem;color:var(--text-mute);margin-top:1rem;line-height:1.5}

/* ── Tiles ── */
.tiles{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-bottom:2rem}
.tile{padding:1.4rem 1.5rem;background:var(--surface);border:1px solid var(--border);border-radius:12px;position:relative;overflow:hidden}
.tile .label{font-size:0.68rem;font-weight:500;color:var(--text-dim);letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.6rem}
.tile .value{font-size:2rem;font-weight:700;color:var(--text-bright);letter-spacing:-0.02em;font-variant-numeric:tabular-nums;line-height:1.1}
.tile .sub{font-size:0.72rem;color:var(--text-dim);margin-top:0.3rem}
.tile.accent{border-color:var(--brand);background:linear-gradient(180deg,rgba(10,149,253,0.06),var(--surface))}
.tile.accent .label{color:var(--brand)}

/* ── Section card ── */
.section{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:1.6rem 1.75rem;margin-bottom:1.25rem}
.section-head{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:1.25rem}
.section-head h2{font-size:0.95rem;font-weight:600;color:var(--text-bright)}
.section-head .meta{font-size:0.7rem;color:var(--text-dim)}

/* ── Grid layouts ── */
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:1.25rem}
.grid-3{display:grid;grid-template-columns:2fr 1fr 1fr;gap:1.25rem}

/* ── Sparkline ── */
.spark{width:100%;height:70px;margin-top:0.5rem}
.spark path.area{fill:rgba(10,149,253,0.14)}
.spark path.line{fill:none;stroke:var(--brand);stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.spark circle{fill:var(--brand)}
.spark text{font-family:'Poppins',sans-serif;font-size:9px;fill:var(--text-mute)}

/* ── Bars (histogram) ── */
.bars{display:flex;align-items:flex-end;gap:0.5rem;height:110px;margin-top:0.6rem}
.bar{flex:1;display:flex;flex-direction:column;align-items:center;gap:0.3rem}
.bar .col{width:100%;background:var(--brand);border-radius:4px 4px 0 0;min-height:2px;transition:height 0.4s}
.bar .col.low{background:var(--red)}
.bar .col.mid{background:var(--yellow)}
.bar .lbl{font-size:0.62rem;color:var(--text-mute);letter-spacing:0.04em}
.bar .cnt{font-size:0.7rem;color:var(--text);font-weight:500;font-variant-numeric:tabular-nums}

/* ── Tables ── */
table{width:100%;border-collapse:collapse;font-size:0.76rem}
th{text-align:left;font-weight:500;color:var(--text-dim);text-transform:uppercase;letter-spacing:0.06em;font-size:0.62rem;padding:0.5rem 0.6rem;border-bottom:1px solid var(--border-strong)}
td{padding:0.55rem 0.6rem;border-bottom:1px solid var(--border);color:var(--text);font-variant-numeric:tabular-nums}
tr:last-child td{border-bottom:none}
td.num{text-align:right;font-family:'Fira Code',monospace}
td.tool{max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
td.tool .name{color:var(--text-bright);font-weight:500}
td.tool .id{color:var(--text-mute);font-size:0.68rem;font-family:'Fira Code',monospace;display:block;margin-top:0.1rem}
.pill{display:inline-block;padding:0.15rem 0.5rem;border-radius:999px;font-size:0.66rem;font-weight:600;font-family:inherit}
.pill.good{background:rgba(61,220,132,0.14);color:var(--green)}
.pill.warn{background:rgba(240,197,59,0.14);color:var(--yellow)}
.pill.bad{background:rgba(240,90,90,0.14);color:var(--red)}
.pill.dim{background:var(--surface-2);color:var(--text-dim)}
.empty{color:var(--text-mute);font-style:italic;font-size:0.78rem;padding:1rem 0;text-align:center}

/* ── Errors list ── */
.err-item{display:flex;justify-content:space-between;padding:0.55rem 0;border-bottom:1px solid var(--border);font-size:0.78rem}
.err-item:last-child{border-bottom:none}
.err-item .cat{color:var(--text)}
.err-item .cnt{color:var(--red);font-weight:600;font-family:'Fira Code',monospace}

/* ── Billing footer ── */
.billing{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin-top:1rem}
.billing .tile{padding:1.1rem 1.25rem}
.billing .tile .value{font-size:1.4rem}

/* ── Synthetic disclosure banner ── */
.disclosure{padding:0.7rem 1rem;background:rgba(240,197,59,0.05);border:1px solid rgba(240,197,59,0.2);border-radius:10px;font-size:0.76rem;color:var(--text);margin-bottom:1.75rem;display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap}
.disclosure .dim{color:var(--text-dim);text-transform:uppercase;letter-spacing:0.08em;font-size:0.64rem;font-weight:600}
.disclosure strong{color:var(--yellow);font-family:'Fira Code',monospace;font-weight:600}
.disclosure .hint{color:var(--text-mute);font-size:0.72rem;font-weight:300}

@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}

@media (max-width:1080px){
  .tiles{grid-template-columns:repeat(2,1fr)}
  .grid-2,.grid-3{grid-template-columns:1fr}
  .billing{grid-template-columns:repeat(2,1fr)}
}
@media (max-width:600px){
  .page{padding:0 1rem 3rem}
  .tiles{grid-template-columns:1fr}
  .billing{grid-template-columns:1fr}
}
</style>
</head>
<body>

__SITE_HEADER_HTML__

<!-- Auth prompt (shown first) -->
<div class="auth" id="auth-screen">
  <h1>Admin Dashboard</h1>
  <p>Enter an admin-tier API key to view platform insights. Your key is kept only in your browser's localStorage.</p>
  <label for="admin-key">Admin API Key</label>
  <input type="password" id="admin-key" placeholder="nf_live_...">
  <button onclick="authenticate()">Open Dashboard</button>
  <div class="err" id="auth-err"></div>
  <p class="hint">Don't have one? On the server:<br>
  <code>docker compose exec app python -m app.cli create-key --tier admin</code></p>
</div>

<!-- Dashboard (hidden until authed) -->
<div class="page" id="dashboard" style="display:none">

<div class="status-strip">
  <div class="status-strip-left">
    <span class="topbar-tag">Admin</span>
  </div>
  <div class="status-strip-right">
    <span><span class="dot" id="status-dot"></span> <span id="status-text">Live</span></span>
    <span id="last-update">&mdash;</span>
    <button onclick="refresh()">Refresh</button>
    <button onclick="logout()">Log out</button>
  </div>
</div>

<!-- Today tiles -->
<div class="tiles">
  <div class="tile accent">
    <div class="label">Reports today</div>
    <div class="value" id="t-reports">&mdash;</div>
    <div class="sub" id="t-reports-sub">since midnight UTC</div>
  </div>
  <div class="tile">
    <div class="label">Success rate</div>
    <div class="value" id="t-rate">&mdash;</div>
    <div class="sub" id="t-rate-sub">today</div>
  </div>
  <div class="tile">
    <div class="label">New signups</div>
    <div class="value" id="t-signups">&mdash;</div>
    <div class="sub">API keys created today</div>
  </div>
  <div class="tile">
    <div class="label">Active reporters</div>
    <div class="value" id="t-reporters">&mdash;</div>
    <div class="sub" id="t-reporters-sub">unique agents today</div>
  </div>
</div>

<!-- Disclosure: synthetic bootstrap activity -->
<div class="disclosure" id="synth-banner" style="display:none">
  <span class="dim">Background:</span>
  <strong id="synth-count">—</strong> synthetic bootstrap reports today
  <span class="hint">(LLM-generated priors for newly discovered tools — excluded from the numbers above)</span>
</div>

<!-- Trends -->
<div class="grid-2">
  <div class="section">
    <div class="section-head">
      <h2>Last 24 hours</h2>
      <div class="meta" id="t24-meta">&mdash;</div>
    </div>
    <svg class="spark" id="spark-24h"></svg>
  </div>
  <div class="section">
    <div class="section-head">
      <h2>Last 30 days</h2>
      <div class="meta" id="t30-meta">&mdash;</div>
    </div>
    <svg class="spark" id="spark-30d"></svg>
  </div>
</div>

<!-- Reliability snapshot -->
<div class="section">
  <div class="section-head">
    <h2>Reliability distribution</h2>
    <div class="meta" id="rel-meta">&mdash;</div>
  </div>
  <div class="grid-3">
    <div>
      <div class="bars" id="hist"></div>
    </div>
    <div>
      <div class="label" style="font-size:0.65rem;color:var(--text-dim);letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.4rem">Healthy (≥80%)</div>
      <div style="font-size:1.6rem;font-weight:700;color:var(--green);font-variant-numeric:tabular-nums" id="rel-healthy">&mdash;</div>
      <div class="label" style="font-size:0.65rem;color:var(--text-dim);letter-spacing:0.08em;text-transform:uppercase;margin:1rem 0 0.4rem">At risk (&lt;60%)</div>
      <div style="font-size:1.6rem;font-weight:700;color:var(--red);font-variant-numeric:tabular-nums" id="rel-risk">&mdash;</div>
    </div>
    <div>
      <div class="label" style="font-size:0.65rem;color:var(--text-dim);letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.4rem">Avg success rate</div>
      <div style="font-size:1.6rem;font-weight:700;color:var(--text-bright);font-variant-numeric:tabular-nums" id="rel-avg">&mdash;</div>
      <div class="label" style="font-size:0.65rem;color:var(--text-dim);letter-spacing:0.08em;text-transform:uppercase;margin:1rem 0 0.4rem">Sample size</div>
      <div style="font-size:1.6rem;font-weight:700;color:var(--text-bright);font-variant-numeric:tabular-nums" id="rel-sample">&mdash;</div>
    </div>
  </div>
</div>

<!-- Top tools tables -->
<div class="grid-2">
  <div class="section">
    <div class="section-head">
      <h2>Busiest tools &mdash; 24h</h2>
      <div class="meta">by report count</div>
    </div>
    <table id="tbl-busiest">
      <thead><tr><th>Tool</th><th class="num">Reports</th><th class="num">Success</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
  <div class="section">
    <div class="section-head">
      <h2>Most failing &mdash; 24h</h2>
      <div class="meta">min 5 reports</div>
    </div>
    <table id="tbl-failing">
      <thead><tr><th>Tool</th><th class="num">Reports</th><th class="num">Success</th></tr></thead>
      <tbody></tbody>
    </table>
  </div>
</div>

<!-- Errors + totals -->
<div class="grid-2">
  <div class="section">
    <div class="section-head">
      <h2>Error categories today</h2>
      <div class="meta" id="err-meta">&mdash;</div>
    </div>
    <div id="err-list"></div>
  </div>
  <div class="section">
    <div class="section-head">
      <h2>Platform totals</h2>
      <div class="meta">all-time</div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.8rem 1.5rem;font-size:0.82rem">
      <div>
        <div class="label" style="font-size:0.62rem;color:var(--text-dim);letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.3rem">Tools indexed</div>
        <div style="font-size:1.3rem;font-weight:600;color:var(--text-bright);font-variant-numeric:tabular-nums" id="p-tools">&mdash;</div>
      </div>
      <div>
        <div class="label" style="font-size:0.62rem;color:var(--text-dim);letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.3rem">Reports total</div>
        <div style="font-size:1.3rem;font-weight:600;color:var(--text-bright);font-variant-numeric:tabular-nums" id="p-reports">&mdash;</div>
      </div>
      <div>
        <div class="label" style="font-size:0.62rem;color:var(--text-dim);letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.3rem">Active API keys</div>
        <div style="font-size:1.3rem;font-weight:600;color:var(--text-bright);font-variant-numeric:tabular-nums" id="p-keys">&mdash;</div>
      </div>
      <div>
        <div class="label" style="font-size:0.62rem;color:var(--text-dim);letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.3rem">Tiers</div>
        <div style="font-size:0.78rem;font-weight:400;color:var(--text);line-height:1.7" id="p-tiers">&mdash;</div>
      </div>
    </div>
  </div>
</div>

<!-- Registration sources -->
<div class="section">
  <div class="section-head">
    <h2>Registration sources</h2>
    <div class="meta" id="src-meta">&mdash;</div>
  </div>
  <table id="tbl-sources" style="width:100%;border-collapse:collapse;font-size:0.82rem">
    <thead>
      <tr style="text-align:left;color:var(--text-dim);font-size:0.66rem;letter-spacing:0.08em;text-transform:uppercase">
        <th style="padding:0.5rem 0.4rem;border-bottom:1px solid var(--border)">Source</th>
        <th style="padding:0.5rem 0.4rem;border-bottom:1px solid var(--border);text-align:right">24h</th>
        <th style="padding:0.5rem 0.4rem;border-bottom:1px solid var(--border);text-align:right">7d</th>
        <th style="padding:0.5rem 0.4rem;border-bottom:1px solid var(--border);text-align:right">All-time</th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>
</div>

<!-- Billing -->
<div class="section">
  <div class="section-head">
    <h2>Billing snapshot</h2>
    <div class="meta">month-to-date</div>
  </div>
  <div class="billing">
    <div class="tile">
      <div class="label">PAYG billable</div>
      <div class="value" id="b-billable">&mdash;</div>
      <div class="sub">assessments over free grant</div>
    </div>
    <div class="tile">
      <div class="label">PAYG keys</div>
      <div class="value" id="b-payg">&mdash;</div>
    </div>
    <div class="tile">
      <div class="label">Pro keys</div>
      <div class="value" id="b-pro">&mdash;</div>
    </div>
    <div class="tile">
      <div class="label">Enterprise keys</div>
      <div class="value" id="b-ent">&mdash;</div>
    </div>
  </div>
</div>

</div><!-- /.page -->

<script>
const STORAGE_KEY = 'toolrate_admin_key';
// Migrate pre-rename admin key so the dashboard session survives the
// nemoflow → toolrate transition. Safe to remove after 2026-07.
const LEGACY_STORAGE_KEY = 'nemoflow_admin_key';
(function migrateLegacyKey() {
  var legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
  if (legacy && !localStorage.getItem(STORAGE_KEY)) {
    localStorage.setItem(STORAGE_KEY, legacy);
  }
  if (legacy) localStorage.removeItem(LEGACY_STORAGE_KEY);
})();
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
  var key = document.getElementById('admin-key').value.trim();
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
    var resp = await fetch('/v1/admin/dashboard', {
      headers: {'X-Api-Key': key}
    });
    if (resp.status === 403 || resp.status === 401) {
      clearKey();
      showAuth(resp.status === 403 ? 'That key is not admin-tier.' : 'Invalid API key.');
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
function fmtPct(n, digits) {
  if (n === null || n === undefined) return '—';
  return (n * 100).toFixed(digits || 1) + '%';
}
// Escape user-controlled strings before interpolating them into innerHTML.
// Error categories, tool identifiers, and display names all flow into this
// admin page from untrusted /v1/report and /v1/assess payloads, so any
// innerHTML usage without escaping is a stored XSS sink.
function esc(s) {
  if (s === null || s === undefined) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
function shortTool(t) {
  return t.replace(/^https?:\/\//, '').replace(/\/$/, '');
}
function pillForRate(rate) {
  var pct = (rate * 100).toFixed(1) + '%';
  var cls = rate >= 0.8 ? 'good' : (rate >= 0.6 ? 'warn' : 'bad');
  return '<span class="pill ' + cls + '">' + pct + '</span>';
}

function render(d) {
  // Tiles
  var t = d.today;
  document.getElementById('t-reports').textContent = fmtNum(t.reports_total);
  document.getElementById('t-reports-sub').textContent =
    fmtNum(t.reports_successful) + ' ok · ' + fmtNum(t.reports_failed) + ' failed';
  document.getElementById('t-rate').textContent =
    t.success_rate_pct !== null ? t.success_rate_pct.toFixed(1) + '%' : '—';
  document.getElementById('t-signups').textContent = fmtNum(t.new_signups);
  document.getElementById('t-reporters').textContent = fmtNum(t.unique_reporters);
  document.getElementById('t-reporters-sub').textContent =
    fmtNum(t.tools_touched) + ' tools assessed';

  // Synthetic bootstrap disclosure
  var synth = t.synthetic_bootstrap_reports || 0;
  var banner = document.getElementById('synth-banner');
  if (synth > 0) {
    document.getElementById('synth-count').textContent = fmtNum(synth);
    banner.style.display = 'flex';
  } else {
    banner.style.display = 'none';
  }

  // Sparklines
  drawSpark('spark-24h', d.trend.hourly_24h, 24);
  drawSpark('spark-30d', d.trend.daily_30d, 30);
  var tot24 = d.trend.hourly_24h.reduce(function(s,r){return s+r.count;},0);
  var tot30 = d.trend.daily_30d.reduce(function(s,r){return s+r.count;},0);
  document.getElementById('t24-meta').textContent = fmtNum(tot24) + ' reports';
  document.getElementById('t30-meta').textContent = fmtNum(tot30) + ' reports';

  // Histogram
  drawHistogram(d.reliability.histogram);
  document.getElementById('rel-healthy').textContent = fmtNum(d.reliability.healthy_tools);
  document.getElementById('rel-risk').textContent = fmtNum(d.reliability.at_risk_tools);
  document.getElementById('rel-avg').textContent =
    d.reliability.avg_success_rate !== null ? fmtPct(d.reliability.avg_success_rate) : '—';
  document.getElementById('rel-sample').textContent = fmtNum(d.reliability.sample_size);
  document.getElementById('rel-meta').textContent =
    'across ' + fmtNum(d.reliability.sample_size) + ' tools (≥5 reports, last 30d)';

  // Top tools tables
  renderToolTable('tbl-busiest', d.top_tools.busiest_24h);
  renderToolTable('tbl-failing', d.top_tools.most_failing_24h);

  // Error categories
  var list = document.getElementById('err-list');
  list.innerHTML = '';
  var totalErrors = 0;
  d.errors_today.forEach(function(e) {
    totalErrors += e.count;
    var row = document.createElement('div');
    row.className = 'err-item';
    row.innerHTML = '<span class="cat">' + esc(e.category) + '</span><span class="cnt">' + fmtNum(e.count) + '</span>';
    list.appendChild(row);
  });
  if (d.errors_today.length === 0) {
    list.innerHTML = '<div class="empty">No failures today ✨</div>';
  }
  document.getElementById('err-meta').textContent = totalErrors > 0 ?
    fmtNum(totalErrors) + ' failures' : 'all clear';

  // Platform totals
  document.getElementById('p-tools').textContent = fmtNum(d.totals.tools);
  document.getElementById('p-reports').textContent = fmtNum(d.totals.reports);
  document.getElementById('p-keys').textContent = fmtNum(d.totals.active_keys);
  var tierHtml = Object.keys(d.totals.by_tier).sort().map(function(t){
    return '<span class="pill dim">' + t + ' · ' + d.totals.by_tier[t] + '</span>';
  }).join(' ');
  document.getElementById('p-tiers').innerHTML = tierHtml || '—';

  // Registration sources
  var srcTbody = document.querySelector('#tbl-sources tbody');
  srcTbody.innerHTML = '';
  var sources = d.registration_sources || [];
  var src24hTotal = 0;
  sources.forEach(function(row) {
    src24hTotal += row.last_24h;
    var tr = document.createElement('tr');
    var label = row.source === null || row.source === undefined ? '(legacy / unknown)' : row.source;
    var labelClass = row.source === null || row.source === undefined ? 'color:var(--text-dim)' : 'color:var(--text-bright);font-weight:500';
    tr.innerHTML =
      '<td style="padding:0.45rem 0.4rem;border-bottom:1px solid var(--border);' + labelClass + '">' + esc(label) + '</td>' +
      '<td style="padding:0.45rem 0.4rem;border-bottom:1px solid var(--border);text-align:right;font-variant-numeric:tabular-nums">' + fmtNum(row.last_24h) + '</td>' +
      '<td style="padding:0.45rem 0.4rem;border-bottom:1px solid var(--border);text-align:right;font-variant-numeric:tabular-nums">' + fmtNum(row.last_7d) + '</td>' +
      '<td style="padding:0.45rem 0.4rem;border-bottom:1px solid var(--border);text-align:right;font-variant-numeric:tabular-nums">' + fmtNum(row.all_time) + '</td>';
    srcTbody.appendChild(tr);
  });
  if (sources.length === 0) {
    srcTbody.innerHTML = '<tr><td colspan="4" style="padding:0.8rem 0.4rem;color:var(--text-dim);text-align:center">No data yet.</td></tr>';
  }
  document.getElementById('src-meta').textContent = src24hTotal > 0 ?
    fmtNum(src24hTotal) + ' new in 24h' : 'no new signups in 24h';

  // Billing
  document.getElementById('b-billable').textContent = fmtNum(d.billing.payg_billable_month_to_date);
  document.getElementById('b-payg').textContent = fmtNum(d.billing.payg_keys);
  document.getElementById('b-pro').textContent = fmtNum(d.billing.pro_keys);
  document.getElementById('b-ent').textContent = fmtNum(d.billing.enterprise_keys);
}

function renderToolTable(id, rows) {
  var tbody = document.querySelector('#' + id + ' tbody');
  tbody.innerHTML = '';
  if (!rows || rows.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" class="empty">No activity in the last 24h</td></tr>';
    return;
  }
  rows.forEach(function(r) {
    var tr = document.createElement('tr');
    var short = shortTool(r.identifier || '');
    tr.innerHTML =
      '<td class="tool"><span class="name">' + esc(r.display_name || short) + '</span>' +
      '<span class="id">' + esc(short) + '</span></td>' +
      '<td class="num">' + fmtNum(r.reports_24h) + '</td>' +
      '<td class="num">' + pillForRate(r.success_rate) + '</td>';
    tbody.appendChild(tr);
  });
}

function drawSpark(id, points, expected) {
  var svg = document.getElementById(id);
  svg.innerHTML = '';
  var w = svg.clientWidth, h = svg.clientHeight;
  if (!points || points.length === 0 || w === 0) {
    svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle">no data</text>';
    return;
  }
  var padX = 8, padY = 10;
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
    '<text x="' + (w - padX) + '" y="' + (padY + 4) + '" text-anchor="end">max ' + fmtNum(maxY) + '</text>';
}

function drawHistogram(hist) {
  var container = document.getElementById('hist');
  container.innerHTML = '';
  var labels = ['0-20','20-40','40-60','60-80','80-100'];
  var max = Math.max.apply(null, labels.map(function(l){ return hist[l] || 0; })) || 1;
  labels.forEach(function(l) {
    var n = hist[l] || 0;
    var pct = (n / max) * 100;
    var colCls = (l === '0-20' || l === '20-40') ? 'low' : (l === '40-60' ? 'mid' : '');
    var bar = document.createElement('div');
    bar.className = 'bar';
    bar.innerHTML =
      '<span class="cnt">' + fmtNum(n) + '</span>' +
      '<div class="col ' + colCls + '" style="height:' + pct + '%"></div>' +
      '<span class="lbl">' + l + '%</span>';
    container.appendChild(bar);
  });
}

// ── Init ──
if (getKey()) {
  refresh();
} else {
  showAuth();
}

document.getElementById('admin-key').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') authenticate();
});

// Auto-refresh every 30s when tab visible
refreshTimer = setInterval(function() {
  if (document.visibilityState === 'visible' && getKey()) refresh();
}, 30000);
</script>
__SITE_HEADER_JS__
</body>
</html>"""


DASHBOARD_HTML = (
    _DASHBOARD_TEMPLATE
    .replace("__SITE_HEADER_CSS__", SITE_HEADER_CSS)
    .replace("__SITE_HEADER_HTML__", SITE_HEADER_HTML)
    .replace("__SITE_HEADER_JS__", SITE_HEADER_JS)
)
