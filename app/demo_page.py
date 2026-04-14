"""/demo page — video walkthrough + copy-paste ready Python demo script.

The page pairs a YouTube walkthrough with the full `demo_toolrate.py` script
that ships in `app/static/`. The script is read once at module import so the
rendered HTML has zero DB/disk cost per request.
"""

from html import escape
from pathlib import Path

from app.site_header import SITE_HEADER_CSS, SITE_HEADER_HTML, SITE_HEADER_JS

_DEMO_SCRIPT_PATH = Path(__file__).parent / "static" / "demo_toolrate.py"
_DEMO_SCRIPT_SOURCE = _DEMO_SCRIPT_PATH.read_text(encoding="utf-8")
_DEMO_SCRIPT_ESCAPED = escape(_DEMO_SCRIPT_SOURCE)
_DEMO_SCRIPT_LINES = _DEMO_SCRIPT_SOURCE.count("\n") + 1

YOUTUBE_VIDEO_ID = "8aA2qge_xMU"

_DEMO_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Live Demo — Watch an AI agent avoid a 62/100 tool · ToolRate</title>
<meta name="description" content="Watch Claude catch a failing Stripe charge before it costs 40k tokens, then run the exact same 1-minute demo on your own machine. No API keys required.">
<meta property="og:title" content="ToolRate live demo — agent catches a failing Stripe charge">
<meta property="og:description" content="1-minute walkthrough plus the copy-paste Python script that simulates guard() + auto-fallback.">
<meta property="og:image" content="https://toolrate.ai/toolrate-logo.webp">
<meta property="og:url" content="https://toolrate.ai/demo">
<meta property="og:type" content="video.other">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="ToolRate live demo — agent catches a failing Stripe charge">
<meta name="twitter:description" content="Watch an AI agent avoid a 62/100 tool and auto-fallback to a 96/100 alternative, live.">
<meta name="twitter:image" content="https://toolrate.ai/toolrate-logo.webp">
<link rel="canonical" href="https://toolrate.ai/demo">
<link rel="icon" href="https://toolrate.ai/toolrate-favicon.png" type="image/png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/themes/prism-tomorrow.min.css">
<style>
:root {
  --bg: #0a0b10;
  --surface: #0f1118;
  --surface-2: #141620;
  --border: #1c1f2e;
  --border-bright: #282c40;
  --text: #d4d8e8;
  --text-dim: #9299b0;
  --text-bright: #f0f2f8;
  --brand: #0a95fd;
  --brand-light: #2fcffa;
  --brand-gradient: linear-gradient(135deg, #2fcffa 0%, #0a95fd 100%);
  --brand-dim: rgba(10, 149, 253, 0.10);
  --brand-glow: rgba(47, 207, 250, 0.28);
  --green: #34d399;
  --red: #f05a5a;
  --yellow: #fbbf24;
  --mono: 'Fira Code', 'SF Mono', 'Consolas', monospace;
  --sans: 'Poppins', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
}
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: var(--sans);
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  overflow-x: hidden;
  -webkit-font-smoothing: antialiased;
}
body::after {
  content: '';
  position: fixed;
  inset: 0;
  background-image: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.025) 1px, transparent 0);
  background-size: 32px 32px;
  pointer-events: none;
  z-index: 0;
}
a { color: var(--brand-light); }

__SITE_HEADER_CSS__

.container {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 2rem;
  position: relative;
  z-index: 1;
}
.demo-hero {
  padding: 4rem 0 2rem;
  text-align: center;
  position: relative;
}
.demo-eyebrow {
  display: inline-block;
  font-family: var(--mono);
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--brand-light);
  background: var(--brand-dim);
  border: 1px solid rgba(10, 149, 253, 0.22);
  padding: 0.4rem 0.85rem;
  border-radius: 999px;
  margin-bottom: 1.5rem;
}
.demo-hero h1 {
  font-size: clamp(2rem, 4.8vw, 3.4rem);
  line-height: 1.08;
  font-weight: 700;
  color: var(--text-bright);
  margin-bottom: 1.25rem;
  letter-spacing: -0.02em;
}
.demo-hero h1 span {
  background: var(--brand-gradient);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.demo-hero p.lead {
  max-width: 720px;
  margin: 0 auto;
  font-size: 1.08rem;
  line-height: 1.65;
  color: var(--text-dim);
}
.demo-hero p.lead strong { color: var(--text-bright); font-weight: 600; }

/* Video */
.video-wrap {
  position: relative;
  max-width: 980px;
  margin: 3rem auto 0;
  border-radius: 18px;
  overflow: hidden;
  background: var(--surface-2);
  border: 1px solid var(--border-bright);
  box-shadow:
    0 0 0 1px rgba(47, 207, 250, 0.08),
    0 30px 80px -20px rgba(10, 149, 253, 0.25),
    0 0 120px -20px var(--brand-glow);
}
.video-wrap::before {
  content: '';
  display: block;
  padding-top: 56.25%;
}
.video-wrap iframe {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
}
.video-caption {
  max-width: 980px;
  margin: 1rem auto 0;
  text-align: center;
  font-size: 0.82rem;
  color: var(--text-dim);
  font-family: var(--mono);
}
.video-caption span { color: var(--brand-light); }

/* Stats row under video */
.demo-stats {
  max-width: 980px;
  margin: 2.5rem auto 0;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
}
.demo-stats-cell {
  padding: 1.4rem 1rem;
  text-align: center;
  border-right: 1px solid var(--border);
}
.demo-stats-cell:last-child { border-right: none; }
.demo-stats-value {
  font-family: var(--mono);
  font-size: 1.6rem;
  font-weight: 600;
  color: var(--text-bright);
  margin-bottom: 0.2rem;
}
.demo-stats-value.good { color: var(--green); }
.demo-stats-value.bad { color: var(--red); }
.demo-stats-label {
  font-size: 0.72rem;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

/* Code section */
.code-section {
  padding: 4.5rem 0 2rem;
}
.code-head {
  max-width: 980px;
  margin: 0 auto 1.25rem;
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}
.code-head h2 {
  font-size: clamp(1.4rem, 2.6vw, 1.9rem);
  color: var(--text-bright);
  font-weight: 600;
  letter-spacing: -0.01em;
}
.code-head h2 span { color: var(--brand-light); }
.code-head p {
  margin-top: 0.5rem;
  color: var(--text-dim);
  font-size: 0.92rem;
}
.code-run-hint {
  font-family: var(--mono);
  font-size: 0.78rem;
  color: var(--text-dim);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.55rem 0.9rem;
  white-space: nowrap;
}
.code-run-hint code {
  color: var(--brand-light);
  font-family: inherit;
}

.code-panel {
  max-width: 980px;
  margin: 0 auto;
  background: #0c0e16;
  border: 1px solid var(--border-bright);
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 24px 60px -24px rgba(0, 0, 0, 0.7);
}
.code-panel-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem 0.75rem 1.1rem;
  background: #12141d;
  border-bottom: 1px solid var(--border);
}
.code-panel-bar-left {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  min-width: 0;
}
.code-panel-dots {
  display: flex;
  gap: 0.4rem;
  flex-shrink: 0;
}
.code-panel-dots span {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: #2a2e3f;
}
.code-panel-dots span:nth-child(1) { background: #ff5f57; }
.code-panel-dots span:nth-child(2) { background: #febc2e; }
.code-panel-dots span:nth-child(3) { background: #28c840; }
.code-panel-filename {
  font-family: var(--mono);
  font-size: 0.78rem;
  color: var(--text-dim);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.code-panel-filename strong { color: var(--text-bright); font-weight: 500; }
.code-panel-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-shrink: 0;
}
.code-action {
  font-family: var(--mono);
  font-size: 0.72rem;
  color: var(--text-dim);
  background: transparent;
  border: 1px solid var(--border-bright);
  border-radius: 7px;
  padding: 0.45rem 0.8rem;
  cursor: pointer;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  transition: all 0.15s;
}
.code-action:hover {
  border-color: var(--brand);
  color: var(--brand-light);
}
.code-action.copy-btn.ok {
  border-color: var(--green);
  color: var(--green);
}
.code-panel pre {
  margin: 0 !important;
  padding: 1.25rem 1.35rem !important;
  max-height: 70vh;
  overflow: auto;
  background: transparent !important;
  font-family: var(--mono) !important;
  font-size: 0.82rem;
  line-height: 1.55;
}
.code-panel pre code { font-family: inherit !important; }
.code-panel pre::-webkit-scrollbar { width: 10px; height: 10px; }
.code-panel pre::-webkit-scrollbar-track { background: #0c0e16; }
.code-panel pre::-webkit-scrollbar-thumb {
  background: #242838;
  border-radius: 6px;
}
.code-panel pre::-webkit-scrollbar-thumb:hover { background: #2f3448; }

/* Trust line */
.trust-line {
  max-width: 980px;
  margin: 1.25rem auto 0;
  text-align: center;
  font-size: 0.8rem;
  color: var(--text-dim);
}
.trust-line strong { color: var(--text-bright); font-weight: 500; }

/* CTA */
.demo-cta {
  max-width: 900px;
  margin: 5rem auto 5rem;
  text-align: center;
  padding: 3rem 2rem;
  background: radial-gradient(ellipse at top, rgba(10, 149, 253, 0.14) 0%, transparent 65%), var(--surface);
  border: 1px solid var(--border-bright);
  border-radius: 18px;
}
.demo-cta h3 {
  font-size: clamp(1.4rem, 2.4vw, 1.85rem);
  color: var(--text-bright);
  font-weight: 600;
  margin-bottom: 0.65rem;
  letter-spacing: -0.01em;
}
.demo-cta p {
  color: var(--text-dim);
  max-width: 560px;
  margin: 0 auto 1.8rem;
  line-height: 1.6;
}
.demo-cta-actions {
  display: flex;
  gap: 0.9rem;
  justify-content: center;
  flex-wrap: wrap;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.85rem 1.6rem;
  border-radius: 10px;
  font-weight: 600;
  font-size: 0.9rem;
  text-decoration: none;
  transition: all 0.2s;
  border: 1px solid transparent;
}
.btn-primary {
  background: var(--brand-gradient);
  color: #fff;
  box-shadow: 0 10px 30px -10px rgba(10, 149, 253, 0.6);
}
.btn-primary:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
}
.btn-ghost {
  background: transparent;
  color: var(--text-bright);
  border-color: var(--border-bright);
}
.btn-ghost:hover {
  border-color: var(--brand);
  color: var(--brand-light);
}

/* Footer */
.demo-footer {
  text-align: center;
  padding: 2rem 1rem 3rem;
  color: var(--text-dim);
  font-size: 0.78rem;
  border-top: 1px solid var(--border);
}
.demo-footer a { color: var(--brand-light); text-decoration: none; }
.demo-footer a:hover { text-decoration: underline; }

@media (max-width: 768px) {
  .container { padding: 0 1.1rem; }
  .demo-hero { padding: 2.5rem 0 1rem; }
  .video-wrap { margin-top: 2rem; border-radius: 14px; }
  .demo-stats { grid-template-columns: 1fr; }
  .demo-stats-cell { border-right: none; border-bottom: 1px solid var(--border); }
  .demo-stats-cell:last-child { border-bottom: none; }
  .code-section { padding: 3rem 0 1rem; }
  .code-head { flex-direction: column; align-items: flex-start; }
  .code-panel pre { font-size: 0.74rem; max-height: 60vh; }
  .code-panel-filename { font-size: 0.7rem; }
  .code-action { font-size: 0.68rem; padding: 0.4rem 0.65rem; }
  .demo-cta { margin: 3rem auto; padding: 2rem 1.25rem; }
}
</style>
</head>
<body>

__SITE_HEADER_HTML__

<main class="container">

  <section class="demo-hero">
    <div class="demo-eyebrow">· Live walkthrough ·</div>
    <h1>Watch an agent catch a failing<br><span>Stripe charge</span> before it costs 40k tokens.</h1>
    <p class="lead">
      A 1-minute demo of <strong>toolrate.guard()</strong> in action — the
      agent consults ToolRate, sees a 62/100 reliability score, and automatically
      falls back to a 96/100 alternative. <strong>No retries. No wasted tokens.
      No duplicate charges.</strong>
    </p>

    <div class="video-wrap">
      <iframe
        src="https://www.youtube-nocookie.com/embed/__YOUTUBE_VIDEO_ID__?rel=0&modestbranding=1"
        title="ToolRate live demo"
        loading="lazy"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen
        referrerpolicy="strict-origin-when-cross-origin"></iframe>
    </div>
    <p class="video-caption">1 minute · <span>turn sound on</span> for the live commentary</p>

    <div class="demo-stats">
      <div class="demo-stats-cell">
        <div class="demo-stats-value bad">62 / 100</div>
        <div class="demo-stats-label">Stripe reliability</div>
      </div>
      <div class="demo-stats-cell">
        <div class="demo-stats-value good">96 / 100</div>
        <div class="demo-stats-label">Fallback chosen</div>
      </div>
      <div class="demo-stats-cell">
        <div class="demo-stats-value">~40K</div>
        <div class="demo-stats-label">Tokens saved</div>
      </div>
    </div>
  </section>

  <section class="code-section">
    <div class="code-head">
      <div>
        <h2>Copy-paste ready <span>·</span> run locally in one command</h2>
        <p>The exact script from the video. Pure Python, no dependencies, no API keys.</p>
      </div>
      <div class="code-run-hint">
        <code>python demo_toolrate.py</code>
      </div>
    </div>

    <div class="code-panel">
      <div class="code-panel-bar">
        <div class="code-panel-bar-left">
          <div class="code-panel-dots"><span></span><span></span><span></span></div>
          <div class="code-panel-filename"><strong>demo_toolrate.py</strong> · __DEMO_LINE_COUNT__ lines · Python</div>
        </div>
        <div class="code-panel-actions">
          <a class="code-action" href="/static/demo_toolrate.py" download="demo_toolrate.py" title="Download raw file">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2v9M4 8l4 4 4-4M3 14h10"/></svg>
            download
          </a>
          <button type="button" class="code-action copy-btn" id="copy-demo" onclick="copyDemo(this)">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="5" width="9" height="9" rx="1.5"/><path d="M2 11V3.5A1.5 1.5 0 0 1 3.5 2H11"/></svg>
            <span class="copy-label">copy</span>
          </button>
        </div>
      </div>
      <pre><code class="language-python" id="demo-code">__DEMO_CODE__</code></pre>
    </div>

    <p class="trust-line">
      Based on <strong>1,284 real agent reports</strong> · Hosted in Germany · <strong>pip install toolrate</strong>
    </p>
  </section>

  <section class="demo-cta">
    <h3>Make your agents this reliable — today.</h3>
    <p>
      Free tier gives you 100 assessments per day. No credit card. Drop one
      <code style="font-family: var(--mono); color: var(--brand-light);">toolrate.guard()</code>
      call in front of any tool and watch failure rates collapse.
    </p>
    <div class="demo-cta-actions">
      <a href="/register" class="btn btn-primary">Get your API key →</a>
      <a href="/docs" class="btn btn-ghost">Read the docs</a>
    </div>
  </section>

</main>

<footer class="demo-footer">
  <p>
    ToolRate · <a href="/">Home</a> · <a href="/pricing">Pricing</a> ·
    <a href="/docs">Docs</a> · <a href="/privacy">Privacy</a> ·
    <a href="https://github.com/netvistamedia/toolrate">GitHub</a>
  </p>
</footer>

__SITE_HEADER_JS__

<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-core.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/prismjs@1.29.0/components/prism-python.min.js"></script>
<script>
function copyDemo(btn) {
  var code = document.getElementById('demo-code');
  if (!code) return;
  var text = code.innerText;
  var done = function () {
    btn.classList.add('ok');
    var label = btn.querySelector('.copy-label');
    if (label) label.textContent = 'copied';
    setTimeout(function () {
      btn.classList.remove('ok');
      if (label) label.textContent = 'copy';
    }, 1800);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text); done(); });
  } else {
    fallbackCopy(text);
    done();
  }
}
function fallbackCopy(text) {
  var ta = document.createElement('textarea');
  ta.value = text;
  ta.setAttribute('readonly', '');
  ta.style.position = 'absolute';
  ta.style.left = '-9999px';
  document.body.appendChild(ta);
  ta.select();
  try { document.execCommand('copy'); } catch (e) {}
  document.body.removeChild(ta);
}
</script>

</body>
</html>
"""


DEMO_HTML = (
    _DEMO_TEMPLATE
    .replace("__SITE_HEADER_CSS__", SITE_HEADER_CSS)
    .replace("__SITE_HEADER_HTML__", SITE_HEADER_HTML)
    .replace("__SITE_HEADER_JS__", SITE_HEADER_JS)
    .replace("__YOUTUBE_VIDEO_ID__", YOUTUBE_VIDEO_ID)
    .replace("__DEMO_LINE_COUNT__", str(_DEMO_SCRIPT_LINES))
    .replace("__DEMO_CODE__", _DEMO_SCRIPT_ESCAPED)
)
