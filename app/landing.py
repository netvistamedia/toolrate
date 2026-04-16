"""Landing page HTML — kept separate to avoid cluttering main.py."""

from app.site_header import SITE_HEADER_CSS, SITE_HEADER_HTML, SITE_HEADER_JS

_LANDING_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ToolRate — Real advice for every tool your agent considers</title>
<meta name="description" content="ToolRate delivers objective, crowdsourced reliability ratings and actionable intelligence from thousands of real agent executions. Know before you call. Choose correctly the first time.">
<meta name="author" content="ToolRate">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
<meta name="googlebot" content="index, follow, max-snippet:-1, max-image-preview:large, max-video-preview:-1">
<meta property="og:site_name" content="ToolRate">
<meta property="og:locale" content="en_US">
<meta property="og:title" content="ToolRate — Real advice for every tool your agent considers">
<meta property="og:description" content="Objective, crowdsourced reliability ratings and actionable intelligence for AI agents — based on thousands of real agent executions across production workloads. Know before you call.">
<meta property="og:image" content="https://toolrate.ai/toolrate-og.jpg">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="720">
<meta property="og:image:alt" content="ToolRate — stop AI agents from failing in production. Reliability scores, smart fallbacks, powered by real agent runs.">
<meta property="og:url" content="https://toolrate.ai/">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="ToolRate — Real advice for every tool your agent considers">
<meta name="twitter:description" content="Objective, crowdsourced reliability ratings and actionable intelligence from thousands of real agent executions. Know before you call.">
<meta name="twitter:image" content="https://toolrate.ai/toolrate-og.jpg">
<meta name="twitter:image:alt" content="ToolRate — stop AI agents from failing in production.">
<link rel="canonical" href="https://toolrate.ai/">
<link rel="alternate" hreflang="en" href="https://toolrate.ai/">
<link rel="alternate" hreflang="x-default" href="https://toolrate.ai/">
<link rel="alternate" type="text/markdown" title="llms.txt — LLM-readable overview (41 languages)" href="https://toolrate.ai/llms.txt">
<link rel="alternate" type="text/markdown" title="llms-full.txt — LLM-readable full reference" href="https://toolrate.ai/llms-full.txt">
<link rel="icon" href="https://toolrate.ai/toolrate-favicon.png" type="image/png">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "ToolRate",
  "url": "https://toolrate.ai/",
  "sameAs": [
    "https://api.toolrate.ai/docs",
    "https://github.com/netvistamedia/toolrate",
    "https://pypi.org/project/toolrate/",
    "https://www.npmjs.com/package/toolrate"
  ],
  "description": "Reliability oracle for AI agents. Objective, crowdsourced reliability ratings and actionable intelligence for every tool your agent considers — based on thousands of real agent executions across production workloads. Real-time reliability scores, failure risk, confidence intervals, jurisdiction intelligence, and auto-fallback in one API call.",
  "applicationCategory": "DeveloperApplication",
  "operatingSystem": "Any",
  "offers": [
    {
      "@type": "Offer",
      "name": "Free",
      "price": "0",
      "priceCurrency": "USD",
      "description": "100 assessments per day, public data pool, all endpoints"
    },
    {
      "@type": "Offer",
      "name": "Pay-as-you-go",
      "price": "0.008",
      "priceCurrency": "USD",
      "description": "First 100 assessments/day free, then $0.008 each. No monthly commitment — best for autonomous agents."
    },
    {
      "@type": "Offer",
      "name": "Pro",
      "price": "29",
      "priceCurrency": "USD",
      "billingIncrement": "P1M",
      "description": "$29 per month for 10,000 assessments, webhook alerts, priority support"
    },
    {
      "@type": "Offer",
      "name": "Enterprise / Platform",
      "priceCurrency": "USD",
      "description": "Custom pricing for AI platforms. Private isolated data pool, SSO, 99.99% SLA, white-label and embedded option."
    }
  ],
  "creator": {
    "@type": "Organization",
    "name": "ToolRate",
    "url": "https://toolrate.ai"
  },
  "featureList": [
    "Real-time reliability scoring for __LANDING_TOOLS_COUNT__ tools and APIs",
    "Bayesian-smoothed scores with recency weighting",
    "Auto-fallback with guard() function",
    "Hidden gem tool discovery",
    "Fallback chain analytics from real agent journeys",
    "Webhook alerts for score changes",
    "Python and TypeScript SDKs",
    "MCP server for Claude Code and Cursor integration",
    "Sub-8ms average response time",
    "GDPR compliant, hosted in Germany"
  ]
}
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
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
  --brand-mid: rgba(10, 149, 253, 0.5);
  --green: #34d399;
  --red: #f05a5a;
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

/* ── Subtle dot pattern ── */
body::after {
  content: '';
  position: fixed;
  inset: 0;
  background-image: radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 32px 32px;
  pointer-events: none;
  z-index: 0;
}

/* ── Hero glow ── */
.hero-glow {
  position: absolute;
  top: -120px;
  left: 50%;
  transform: translateX(-50%);
  width: 800px;
  height: 500px;
  background: radial-gradient(ellipse, var(--brand-glow) 0%, transparent 70%);
  opacity: 0.4;
  pointer-events: none;
  z-index: 0;
}

/* ── Layout ── */
.page { position: relative; z-index: 1; }
.container { max-width: 1080px; margin: 0 auto; padding: 0 2rem; }

/* ── Top bar — see app/site_header.py ── */
__SITE_HEADER_CSS__
/* Landing-specific: ensure the fade-in animation still plays. */
.site-topbar { animation: fadeDown 0.5s ease-out both; }

/* ── Buttons ── */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.6rem 1.3rem;
  border-radius: 8px;
  text-decoration: none;
  font-family: var(--sans);
  font-size: 0.82rem;
  font-weight: 500;
  transition: all 0.25s ease;
  cursor: pointer;
  border: none;
}

.btn-primary {
  background: var(--brand-gradient);
  color: #fff;
  font-weight: 700;
}
.btn-primary:hover {
  filter: brightness(1.08);
  box-shadow: 0 0 30px var(--brand-glow), 0 4px 14px rgba(0,0,0,0.5);
  transform: translateY(-1px);
}

.btn-ghost {
  background: transparent;
  color: var(--text);
  border: 1px solid var(--border-bright);
}
.btn-ghost:hover {
  border-color: var(--brand-mid);
  color: var(--text-bright);
}

/* Hero-scoped CTA override — larger tap targets and stronger contrast */
.hero .btn {
  padding: 0.95rem 1.85rem;
  font-size: 0.92rem;
  border-radius: 10px;
}
.hero .btn-primary {
  font-weight: 700;
  box-shadow:
    inset 0 0 0 1px rgba(47, 207, 250, 0.35),
    0 12px 32px rgba(10, 149, 253, 0.28);
}
.hero .btn-primary:hover {
  filter: brightness(1.08);
  transform: translateY(-2px);
  box-shadow:
    inset 0 0 0 1px rgba(47, 207, 250, 0.55),
    0 18px 48px rgba(10, 149, 253, 0.4),
    0 0 60px var(--brand-glow);
}
.hero .btn-ghost {
  color: var(--text-bright);
  border: 1px solid var(--border-bright);
  background: rgba(255, 255, 255, 0.02);
}
.hero .btn-ghost:hover {
  border-color: var(--brand);
  color: var(--brand-light);
  background: var(--brand-dim);
}

/* ── Hero ── */
.hero {
  padding: 7rem 0 3rem;
  position: relative;
  text-align: center;
  animation: fadeUp 0.7s ease-out 0.1s both;
}

.hero-content {
  position: relative;
  z-index: 1;
  max-width: 820px;
  margin: 0 auto;
}

.hero h1 {
  font-size: clamp(2.35rem, 5.2vw, 3.5rem);
  font-weight: 700;
  color: var(--text-bright);
  line-height: 1.12;
  letter-spacing: -0.028em;
  margin-bottom: 1.25rem;
  text-wrap: balance;
  position: relative;
  display: inline-block;
  padding-bottom: 0.9rem;
}

.hero h1::after {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 0;
  transform: translateX(-50%);
  width: 72px;
  height: 2px;
  border-radius: 2px;
  background: var(--brand-gradient);
  box-shadow: 0 0 20px rgba(47, 207, 250, 0.45);
}

.hero h1 span {
  background: var(--brand-gradient);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-sub {
  font-size: 1.1rem;
  font-weight: 300;
  color: var(--text-dim);
  max-width: 640px;
  margin: 0 auto 1.25rem;
  line-height: 1.7;
  text-wrap: pretty;
}
.hero-sub strong {
  color: var(--text-bright);
  font-weight: 600;
}

.hero-kicker {
  font-size: 1.05rem;
  font-weight: 500;
  color: var(--text-bright);
  max-width: 640px;
  margin: 0 auto 2.25rem;
  line-height: 1.5;
  letter-spacing: -0.005em;
}
.hero-kicker strong {
  font-weight: 700;
}

.hero-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: center;
}

/* ── Readout ── */
.readout {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1rem;
  margin-top: -0.25rem;
  margin-bottom: 5rem;
  animation: fadeUp 0.7s ease-out 0.25s both;
}

.readout-cell {
  background: var(--surface);
  border: 1px solid var(--border-bright);
  border-radius: 14px;
  padding: 2rem 1.5rem;
  text-align: center;
  position: relative;
  overflow: hidden;
  transition: transform 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}
.readout-cell::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(47, 207, 250, 0.05) 0%, transparent 60%);
  pointer-events: none;
}
.readout-cell:hover {
  transform: translateY(-2px);
  border-color: var(--brand-mid);
  box-shadow: 0 12px 32px rgba(10, 149, 253, 0.12);
}

.readout-value {
  font-family: var(--mono);
  font-size: 1.85rem;
  font-weight: 600;
  background: var(--brand-gradient);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  letter-spacing: -0.015em;
  line-height: 1;
}

.readout-label {
  font-size: 0.68rem;
  font-weight: 500;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin-top: 0.6rem;
}

/* ── Narrative (Problem / Solution) ── */
.narrative {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  margin-bottom: 5rem;
  animation: fadeUp 0.7s ease-out 0.35s both;
}

.narrative-card {
  padding: 2rem;
  border-radius: 12px;
  border: 1px solid var(--border);
  position: relative;
  overflow: hidden;
}

.narrative-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
}

.narrative-problem { background: rgba(240, 90, 90, 0.03); }
.narrative-problem::before { background: linear-gradient(90deg, var(--red), transparent 80%); }

.narrative-solution { background: var(--brand-dim); }
.narrative-solution::before { background: linear-gradient(90deg, var(--brand), transparent 80%); }

.narrative-badge {
  font-family: var(--mono);
  font-size: 0.6rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.narrative-problem .narrative-badge { color: var(--red); }
.narrative-solution .narrative-badge { color: var(--brand); }

.narrative-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  animation: pulse 2s ease-in-out infinite;
}
.narrative-problem .narrative-dot { background: var(--red); }
.narrative-solution .narrative-dot { background: var(--brand); }

.narrative-card h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-bright);
  margin-bottom: 0.6rem;
  line-height: 1.3;
}

.narrative-card p {
  font-size: 0.88rem;
  font-weight: 300;
  color: var(--text-dim);
  line-height: 1.7;
}

/* ── Jurisdiction Intelligence ── */
.jurisdiction {
  position: relative;
  margin-bottom: 5rem;
  padding: 3rem 2.75rem;
  border-radius: 18px;
  background:
    radial-gradient(circle at 0% 0%, rgba(52, 211, 153, 0.08) 0%, transparent 55%),
    radial-gradient(circle at 100% 100%, rgba(10, 149, 253, 0.12) 0%, transparent 55%),
    var(--surface);
  border: 1px solid var(--border-bright);
  overflow: hidden;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
  animation: fadeUp 0.7s ease-out 0.4s both;
}

.jurisdiction::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--green), var(--brand) 50%, var(--red));
}

.jurisdiction-eyebrow {
  display: inline-block;
  font-family: var(--mono);
  font-size: 0.66rem;
  font-weight: 600;
  color: var(--brand-light);
  text-transform: uppercase;
  letter-spacing: 0.16em;
  padding: 0.3rem 0.7rem;
  border: 1px solid var(--brand-mid);
  border-radius: 999px;
  background: var(--brand-dim);
  margin-bottom: 1.25rem;
}

.jurisdiction-head {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}

.jurisdiction-icon {
  flex-shrink: 0;
  width: 52px;
  height: 52px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(52, 211, 153, 0.12), rgba(10,149,253,0.12));
  border: 1px solid var(--border-bright);
  font-size: 1.6rem;
}

.jurisdiction-badge {
  font-family: var(--mono);
  font-size: 0.6rem;
  font-weight: 500;
  color: var(--brand);
  background: var(--brand-dim);
  border: 1px solid rgba(10,149,253,0.25);
  padding: 0.2rem 0.55rem;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.jurisdiction h2 {
  font-size: 1.7rem;
  font-weight: 600;
  color: var(--text-bright);
  line-height: 1.25;
  letter-spacing: -0.01em;
  flex: 1 1 auto;
}

.jurisdiction-lead {
  font-size: 1rem;
  font-weight: 300;
  color: var(--text);
  line-height: 1.65;
  max-width: 720px;
  margin-bottom: 2rem;
}

.jurisdiction-tiers {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 2.25rem;
}

.tier {
  padding: 1.1rem 1.25rem;
  border-radius: 10px;
  background: rgba(10, 11, 16, 0.5);
  border: 1px solid var(--border);
  position: relative;
}

.tier-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  display: inline-block;
  margin-right: 0.5rem;
  vertical-align: middle;
}

.tier-eu { border-color: rgba(52, 211, 153, 0.3); }
.tier-eu .tier-dot { background: var(--green); box-shadow: 0 0 10px rgba(52, 211, 153, 0.5); }
.tier-mid { border-color: rgba(10,149,253,0.3); }
.tier-mid .tier-dot { background: var(--brand); box-shadow: 0 0 10px var(--brand-glow); }
.tier-high { border-color: rgba(240, 90, 90, 0.3); }
.tier-high .tier-dot { background: var(--red); box-shadow: 0 0 10px rgba(240, 90, 90, 0.45); }

.tier-label {
  font-family: var(--mono);
  font-size: 0.68rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-bright);
  margin-bottom: 0.35rem;
}

.tier p {
  font-size: 0.78rem;
  color: var(--text-dim);
  line-height: 1.55;
  font-weight: 300;
}

.jurisdiction-benefits-title {
  font-size: 0.72rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--brand);
  margin-bottom: 0.9rem;
}

.jurisdiction-benefits {
  list-style: none;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.7rem 1.5rem;
  margin-bottom: 1.75rem;
}

.jurisdiction-benefits li {
  font-size: 0.85rem;
  color: var(--text);
  line-height: 1.55;
  font-weight: 300;
  padding-left: 1.3rem;
  position: relative;
}

.jurisdiction-benefits li::before {
  content: '→';
  position: absolute;
  left: 0;
  top: 0;
  color: var(--brand);
  font-weight: 600;
}

.jurisdiction-benefits li strong {
  color: var(--text-bright);
  font-weight: 500;
}

.jurisdiction-punch {
  font-size: 0.92rem;
  color: var(--text-dim);
  line-height: 1.7;
  font-weight: 300;
  padding-top: 1.5rem;
  border-top: 1px solid var(--border);
  max-width: 780px;
}

.jurisdiction-punch strong {
  color: var(--brand);
  font-weight: 600;
}

/* ── Install ── */
.install-section {
  margin-bottom: 4rem;
  animation: fadeUp 0.7s ease-out 0.4s both;
}
.install-section > h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-bright);
  margin-bottom: 0.35rem;
}
.install-lead {
  color: var(--text-dim);
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
  max-width: 640px;
  line-height: 1.55;
}
.install-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.25rem;
  margin-bottom: 1.25rem;
}
.install-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.25rem 1.5rem 1.4rem;
  position: relative;
}
.install-card.recommended {
  border-color: rgba(10, 149, 253, 0.35);
  box-shadow: 0 0 0 1px rgba(10, 149, 253, 0.18), 0 0 40px rgba(10, 149, 253, 0.08);
}
.install-card .install-label {
  display: inline-block;
  font-family: var(--sans);
  font-size: 0.68rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-dim);
  margin-bottom: 0.2rem;
}
.install-card.recommended .install-label { color: var(--brand); }
.install-card .install-title {
  font-family: var(--sans);
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-bright);
  margin-bottom: 0.85rem;
}
.install-card pre {
  font-family: var(--mono);
  font-size: 0.78rem;
  line-height: 1.7;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}
.install-card pre .cm {
  color: var(--text-dim);
  font-style: italic;
}
.install-note {
  padding: 0.85rem 1.1rem;
  background: rgba(240, 197, 59, 0.05);
  border-left: 3px solid rgba(240, 197, 59, 0.5);
  border-radius: 4px;
  color: var(--text);
  font-size: 0.85rem;
  line-height: 1.6;
}
.install-note strong { color: #f0c53b; }
.install-note code {
  font-family: var(--mono);
  font-size: 0.8rem;
  color: var(--text-bright);
  background: rgba(255, 255, 255, 0.04);
  padding: 1px 6px;
  border-radius: 3px;
}

/* ── Code ── */
.code-section {
  margin-bottom: 5rem;
  animation: fadeUp 0.7s ease-out 0.45s both;
}

.code-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
}

.code-header h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-bright);
}

.code-tabs {
  display: flex;
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}

.code-tab {
  font-family: var(--sans);
  font-size: 0.72rem;
  font-weight: 500;
  padding: 0.4rem 0.85rem;
  color: var(--text-dim);
  cursor: pointer;
  transition: all 0.2s;
  background: transparent;
  border: none;
  border-right: 1px solid var(--border);
}
.code-tab:last-child { border-right: none; }
.code-tab.active { background: var(--brand-dim); color: var(--brand); }
.code-tab:hover:not(.active) { color: var(--text); }

.code-block {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.75rem 2rem;
  overflow-x: auto;
  position: relative;
}

.code-block::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--brand-glow), transparent);
}

.code-block pre {
  font-family: var(--mono);
  font-size: 0.8rem;
  line-height: 1.8;
  color: var(--text);
}

.code-block .kw { color: #c792ea; }
.code-block .fn { color: var(--brand); }
.code-block .str { color: #ecc48d; }
.code-block .cm { color: var(--text-dim); font-style: italic; }

.code-panel { display: none; }
.code-panel.active { display: block; }

/* ── Features ── */
.features {
  margin-bottom: 5rem;
  animation: fadeUp 0.7s ease-out 0.55s both;
}

.features-header {
  text-align: center;
  margin-bottom: 3.25rem;
}

.features-header h2 {
  font-size: clamp(1.65rem, 2.6vw, 2.1rem);
  font-weight: 700;
  color: var(--text-bright);
  margin-bottom: 0.75rem;
  letter-spacing: -0.015em;
}

.features-header p {
  font-size: 1rem;
  color: var(--text-dim);
  font-weight: 300;
  max-width: 580px;
  margin: 0 auto;
  line-height: 1.65;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.feature {
  background: var(--surface);
  padding: 2rem 1.9rem;
  border: 1px solid var(--border-bright);
  border-radius: 14px;
  transition: background 0.25s ease, border-color 0.25s ease, transform 0.25s ease, box-shadow 0.25s ease;
  position: relative;
}
.feature:hover {
  background: var(--surface-2);
  border-color: var(--brand-mid);
  transform: translateY(-2px);
  box-shadow: 0 14px 36px rgba(10, 149, 253, 0.12);
}

.feature-num {
  font-family: var(--mono);
  font-size: 0.68rem;
  font-weight: 600;
  background: var(--brand-gradient);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  letter-spacing: 0.12em;
  margin-bottom: 1rem;
}

.feature h3 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-bright);
  margin-bottom: 0.55rem;
  letter-spacing: -0.005em;
}

.feature p {
  font-size: 0.82rem;
  font-weight: 300;
  color: var(--text-dim);
  line-height: 1.7;
}

.feature p code {
  font-family: var(--mono);
  font-size: 0.78rem;
  color: var(--brand-light);
  background: var(--brand-dim);
  padding: 0.08rem 0.35rem;
  border-radius: 4px;
}

.feature-code {
  font-family: var(--mono);
  font-size: 0.72rem;
  color: var(--text-bright);
  background: #0a0b10;
  border: 1px solid var(--border-bright);
  border-radius: 8px;
  padding: 0.7rem 0.85rem;
  margin: 0 0 0.9rem;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
}
.feature-code .kw { color: var(--brand-light); font-weight: 500; }
.feature-code .fn { color: #c792ea; }
.feature-code .str { color: #ecc48d; }

/* ── LLM Router spotlight ── */
.llm-router {
  margin-bottom: 5rem;
  animation: fadeUp 0.7s ease-out 0.6s both;
  position: relative;
}
.llm-router-card {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, rgba(10, 149, 253, 0.08) 0%, rgba(47, 207, 250, 0.04) 100%);
  border: 1px solid var(--brand-mid);
  border-radius: 18px;
  padding: 3rem 2.5rem;
}
.llm-router-card::before {
  content: '';
  position: absolute;
  top: -60%;
  left: -25%;
  width: 85%;
  height: 220%;
  background: radial-gradient(ellipse, var(--brand-glow) 0%, transparent 60%);
  opacity: 0.20;
  pointer-events: none;
}
.llm-router-card > * { position: relative; z-index: 1; }
.llm-router-badge {
  display: inline-block;
  font-family: var(--mono);
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  background: var(--brand-gradient);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  margin-bottom: 1rem;
}
.llm-router-card h2 {
  font-size: clamp(1.7rem, 3vw, 2.25rem);
  font-weight: 700;
  color: var(--text-bright);
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin-bottom: 1rem;
  max-width: 720px;
}
.llm-router-lead {
  font-size: 0.95rem;
  font-weight: 300;
  color: var(--text-dim);
  line-height: 1.75;
  max-width: 700px;
  margin-bottom: 1.75rem;
}
.llm-router-strategies {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-bottom: 2.25rem;
}
.llm-router-strategy {
  font-family: var(--mono);
  font-size: 0.72rem;
  padding: 0.42rem 0.85rem;
  border-radius: 999px;
  border: 1px solid var(--border-bright);
  background: var(--surface);
  color: var(--text);
  white-space: nowrap;
}
.llm-router-strategy strong {
  color: var(--brand-light);
  font-weight: 600;
}
.llm-router-grid {
  display: grid;
  grid-template-columns: 1.15fr 0.85fr;
  gap: 2rem;
  align-items: start;
}
.llm-router-code {
  font-family: var(--mono);
  font-size: 0.72rem;
  color: var(--text-bright);
  background: #07080d;
  border: 1px solid var(--border-bright);
  border-radius: 12px;
  padding: 1.25rem 1.35rem;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
  overflow-x: auto;
  margin: 0;
}
.llm-router-code .cm { color: var(--text-dim); font-style: italic; }
.llm-router-code .kw { color: var(--brand-light); font-weight: 500; }
.llm-router-code .fn { color: #c792ea; }
.llm-router-code .str { color: #ecc48d; }
.llm-router-code .num { color: #f78c6c; }
.llm-router-getlist h3 {
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--text-bright);
  margin-bottom: 0.9rem;
  letter-spacing: -0.005em;
}
.llm-router-getlist ul {
  list-style: none;
  padding: 0;
  margin: 0 0 1.4rem;
}
.llm-router-getlist li {
  font-size: 0.82rem;
  color: var(--text-dim);
  font-weight: 300;
  line-height: 1.75;
  padding-left: 1.1rem;
  position: relative;
  margin-bottom: 0.55rem;
}
.llm-router-getlist li:last-child { margin-bottom: 0; }
.llm-router-getlist li::before {
  content: '+';
  position: absolute;
  left: 0;
  color: var(--brand);
  font-weight: 600;
}
.llm-router-getlist li code {
  font-family: var(--mono);
  font-size: 0.76rem;
  color: var(--brand-light);
  background: var(--brand-dim);
  padding: 0.08rem 0.35rem;
  border-radius: 4px;
}
.llm-router-providers {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin-top: 1.5rem;
}
.llm-router-provider {
  font-family: var(--mono);
  font-size: 0.65rem;
  padding: 0.48rem 0.6rem;
  border-radius: 6px;
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text-dim);
  text-align: center;
  letter-spacing: 0.02em;
}
.llm-router-provider--free {
  grid-column: 1 / -1;
  background: linear-gradient(90deg, rgba(10, 149, 253, 0.10), rgba(47, 207, 250, 0.06));
  border-color: rgba(10, 149, 253, 0.35);
  color: var(--brand-light);
}

@media (max-width: 860px) {
  .llm-router-grid { grid-template-columns: 1fr; }
  .llm-router-card { padding: 2rem 1.5rem; }
  .llm-router-providers { grid-template-columns: repeat(2, 1fr); }
}

/* ── Pricing ── */
.pricing {
  margin-bottom: 5rem;
  animation: fadeUp 0.7s ease-out 0.65s both;
}

.pricing-header {
  text-align: center;
  margin-bottom: 2.5rem;
}

.pricing-header h2 {
  font-size: 1.7rem;
  font-weight: 600;
  color: var(--text-bright);
}

.pricing-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  max-width: 1020px;
  margin: 0 auto;
}

.pricing-card {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 2rem;
  background: var(--surface);
  position: relative;
}

.pricing-card.featured {
  border-color: var(--brand);
  box-shadow: 0 0 50px var(--brand-dim);
}

.pricing-card.featured::before {
  content: 'BEST FOR AGENTS';
  position: absolute;
  top: -0.55rem;
  left: 1.5rem;
  font-size: 0.6rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  color: #fff;
  background: var(--brand);
  padding: 0.15rem 0.6rem;
  border-radius: 4px;
}

.pricing-tier {
  font-size: 0.72rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-dim);
  margin-bottom: 0.4rem;
}

.pricing-price {
  font-size: 2.2rem;
  font-weight: 700;
  color: var(--text-bright);
  margin-bottom: 0.2rem;
}
.pricing-price span {
  font-size: 0.85rem;
  font-weight: 300;
  color: var(--text-dim);
}

.pricing-desc {
  font-size: 0.8rem;
  color: var(--text-dim);
  font-weight: 300;
  margin-bottom: 1.5rem;
}

.pricing-features { list-style: none; margin-bottom: 1.5rem; }

.pricing-features li {
  font-size: 0.78rem;
  color: var(--text);
  padding: 0.45rem 0;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 400;
}
.pricing-features li::before { content: '+'; color: var(--brand); font-weight: 600; }
.pricing-features li:last-child { border-bottom: none; }

/* ── Footer ── */
.footer {
  border-top: 1px solid var(--border);
  padding: 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  animation: fadeUp 0.7s ease-out 0.75s both;
}

.footer-left {
  font-size: 0.72rem;
  color: var(--text-dim);
}

.footer-right { display: flex; gap: 1.25rem; }

.footer-right a {
  font-size: 0.72rem;
  color: var(--text-dim);
  text-decoration: none;
  transition: color 0.2s;
}
.footer-right a:hover { color: var(--brand); }

/* ── Animations ── */
@keyframes fadeUp {
  from { opacity: 0; transform: translateY(18px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeDown {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-12px); }
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .hero { padding: 4rem 0 3rem; }
  .readout { grid-template-columns: repeat(2, 1fr); }
  .narrative { grid-template-columns: 1fr; }
  .jurisdiction { padding: 2rem 1.5rem; }
  .jurisdiction h2 { font-size: 1.35rem; }
  .jurisdiction-tiers { grid-template-columns: 1fr; }
  .jurisdiction-benefits { grid-template-columns: 1fr; }
  .features-grid { grid-template-columns: 1fr; }
  .pricing-grid { grid-template-columns: 1fr; max-width: 420px; }
  .footer { flex-direction: column; gap: 0.75rem; text-align: center; }
  .code-header { flex-direction: column; gap: 0.75rem; align-items: flex-start; }
  .install-grid { grid-template-columns: 1fr; }
}
</style>
</head>
<body>

<div class="page">

__SITE_HEADER_HTML__

<main class="container">

<!-- Hero -->
<section class="hero">
  <div class="hero-glow"></div>
  <div class="hero-content">
    <h1>Real advice for every tool your <span>agent considers</span>.</h1>
    <p class="hero-sub">
      AI agents burn tokens retrying flaky, slow, or non-compliant tools.
      ToolRate delivers objective reliability ratings and smart recommendations
      from thousands of real agent executions in production.
    </p>
    <p class="hero-kicker"><strong>Know before you call.</strong></p>
    <div class="hero-actions">
      <a href="/docs" class="btn btn-primary">Get Started Free</a>
      <a href="/demo" class="btn btn-ghost">▶ Watch 1min Demo</a>
      <a href="https://github.com/netvistamedia/toolrate" class="btn btn-ghost">View on GitHub</a>
    </div>
  </div>
</section>

<!-- Readout -->
<div class="readout">
  <div class="readout-cell">
    <div class="readout-value">__LANDING_TOOLS_COUNT__</div>
    <div class="readout-label">Tools Rated</div>
  </div>
  <div class="readout-cell">
    <div class="readout-value">__LANDING_REPORTS_COUNT__</div>
    <div class="readout-label">Data Points</div>
  </div>
  <div class="readout-cell">
    <div class="readout-value">&lt;8ms</div>
    <div class="readout-label">Avg Response</div>
  </div>
  <div class="readout-cell">
    <div class="readout-value">10</div>
    <div class="readout-label">LLM Sources</div>
  </div>
</div>

<!-- Problem / Solution -->
<div class="narrative">
  <div class="narrative-card narrative-problem">
    <div class="narrative-badge"><span class="narrative-dot"></span> The Problem</div>
    <h3>Agents burn cycles on failing tools</h3>
    <p>Stripe times out. LemonSqueezy rejects auth. PayPal finally works. Three attempts, wasted tokens, degraded UX &mdash; and no record of why any of it happened.</p>
  </div>
  <div class="narrative-card narrative-solution">
    <div class="narrative-badge"><span class="narrative-dot"></span> The Solution</div>
    <h3>One assessment before every call</h3>
    <p>ToolRate scores every tool in real time from the collective experience of thousands of production agents. Pick the best option first, fall back intelligently. Every decision is logged with a confidence score attached.</p>
  </div>
</div>

<!-- Jurisdiction Intelligence -->
<section class="jurisdiction">
  <div class="jurisdiction-eyebrow">Global Compliance Layer</div>
  <div class="jurisdiction-head">
    <div class="jurisdiction-icon">🌍</div>
    <h2>Jurisdiction, Made Visible</h2>
    <span class="jurisdiction-badge">Exclusive to ToolRate</span>
  </div>
  <p class="jurisdiction-lead">
    Every tool in ToolRate comes with clear, real-world jurisdiction data &mdash; hosting location, GDPR risk level, and confidence score. So your agents decide based on facts, not assumptions.
  </p>

  <ul class="jurisdiction-benefits">
    <li><strong>Reliability first</strong> &mdash; every tool is scored neutrally, with no geographic penalty.</li>
    <li><strong>GDPR risk made explicit</strong> &mdash; clear signals for data-residency compliance when it matters.</li>
    <li><strong>Region as a choice, never a default</strong> &mdash; EU, US, and global tools ranked by performance.</li>
    <li><strong>Your rules, your ranking</strong> &mdash; pass <code>preferences</code> once via the SDK and ToolRate weighs every recommendation against your policy (e.g. <em>&ldquo;prefer EU for European data&rdquo;</em> or <em>&ldquo;optimize for lowest latency worldwide&rdquo;</em>).</li>
  </ul>

  <p class="jurisdiction-punch">
    From San Francisco to Berlin to Singapore, every agent builder gets the same transparent view &mdash; with full control to match how <strong>you</strong> actually build.
  </p>
</section>

<!-- Install -->
<section class="install-section">
  <h2>Install ToolRate</h2>
  <p class="install-lead">Beginner-friendly in two commands. Works on every platform &mdash; no PEP 668 drama, no virtualenv archaeology.</p>
  <div class="install-grid">
    <div class="install-card recommended">
      <div class="install-label">Recommended</div>
      <div class="install-title">Modern &amp; fastest</div>
      <pre><span class="cm"># Install uv (one-time)</span>
curl -LsSf https://astral.sh/uv/install.sh | sh

<span class="cm"># Add ToolRate to your project</span>
uv add toolrate</pre>
    </div>
    <div class="install-card">
      <div class="install-label">Alternative</div>
      <div class="install-title">Without uv</div>
      <pre>python3 -m venv .venv
source .venv/bin/activate
pip install toolrate</pre>
    </div>
  </div>
  <div class="install-note"><strong>Note:</strong> If you see a <code>PEP 668</code> &ldquo;externally-managed-environment&rdquo; error with plain <code>pip</code>, that&rsquo;s because of Homebrew Python. Use one of the methods above instead. For TypeScript / Node 18+: <code>npm install toolrate</code>.</div>
</section>

<!-- Code -->
<section class="code-section">
  <div class="code-header">
    <h2>Three lines to get started</h2>
    <div class="code-tabs">
      <button class="code-tab active" onclick="showTab('python')">Python</button>
      <button class="code-tab" onclick="showTab('typescript')">TypeScript</button>
      <button class="code-tab" onclick="showTab('curl')">cURL</button>
    </div>
  </div>
  <div class="code-block">
    <div id="tab-python" class="code-panel active"><pre><span class="kw">from</span> toolrate <span class="kw">import</span> ToolRate, guard

client = ToolRate(<span class="str">"nf_live_..."</span>)

<span class="cm"># Check reliability before calling</span>
score = client.assess(<span class="str">"https://api.stripe.com/v1/charges"</span>)
<span class="cm"># =&gt; { reliability_score: 94.2, failure_risk: "low", ... }</span>

<span class="cm"># Or use guard() for auto-fallback</span>
result = <span class="fn">guard</span>(client, <span class="str">"https://api.stripe.com/v1/charges"</span>,
               <span class="kw">lambda</span>: stripe.Charge.create(...),
               fallbacks=[
                   (<span class="str">"https://api.lemonsqueezy.com/v1/checkouts"</span>,
                    <span class="kw">lambda</span>: lemon.create_checkout(...)),
               ])</pre></div>
    <div id="tab-typescript" class="code-panel"><pre><span class="kw">import</span> { ToolRate } <span class="kw">from</span> <span class="str">"toolrate"</span>;

<span class="kw">const</span> client = <span class="kw">new</span> <span class="fn">ToolRate</span>(<span class="str">"nf_live_..."</span>);

<span class="cm">// Check reliability before calling</span>
<span class="kw">const</span> score = <span class="kw">await</span> client.<span class="fn">assess</span>(<span class="str">"https://api.stripe.com/v1/charges"</span>);

<span class="cm">// Or use guard() for auto-fallback</span>
<span class="kw">const</span> result = <span class="kw">await</span> client.<span class="fn">guard</span>(
  <span class="str">"https://api.stripe.com/v1/charges"</span>,
  () => stripe.charges.create({...}),
  { fallbacks: [
    [<span class="str">"https://api.lemonsqueezy.com/v1/checkouts"</span>,
     () => lemon.createCheckout({...})],
  ]}
);</pre></div>
    <div id="tab-curl" class="code-panel"><pre><span class="cm"># Assess a tool</span>
curl -X POST https://api.toolrate.ai/v1/assess \
  -H <span class="str">"X-Api-Key: nf_live_..."</span> \
  -H <span class="str">"Content-Type: application/json"</span> \
  -d <span class="str">'{"tool_identifier": "https://api.stripe.com/v1/charges"}'</span>

<span class="cm"># Report a result</span>
curl -X POST https://api.toolrate.ai/v1/report \
  -H <span class="str">"X-Api-Key: nf_live_..."</span> \
  -H <span class="str">"Content-Type: application/json"</span> \
  -d <span class="str">'{"tool_identifier": "https://api.stripe.com/v1/charges",
    "success": true, "latency_ms": 420}'</span></pre></div>
  </div>
</section>

<!-- Features -->
<section class="features">
  <div class="features-header">
    <h2>Built for production agents</h2>
    <p>Reliability intelligence for the developers, enterprises, and agents running production AI workloads.</p>
  </div>
  <div class="features-grid">
    <div class="feature">
      <div class="feature-num">01</div>
      <h3>Reliability Scoring</h3>
      <p>Real-world success rates, common failure modes, and recommended mitigations &mdash; so agents know exactly how much to trust the tool, and auditors know precisely how the score was calculated.</p>
    </div>
    <div class="feature">
      <div class="feature-num">02</div>
      <h3>One-Line Guard</h3>
      <pre class="feature-code"><span class="kw">result</span> = toolrate.<span class="fn">guard</span>(tool=<span class="str">"stripe/charges"</span>, context=plan)</pre>
      <p>Zero branching logic. Zero retry boilerplate. Production-ready in one line.</p>
    </div>
    <div class="feature">
      <div class="feature-num">03</div>
      <h3>Hidden Gems</h3>
      <p>The tools nobody pitches but production agents quietly rely on &mdash; surfaced from real fallback patterns across thousands of sessions and ranked by recovery rate.</p>
    </div>
    <div class="feature">
      <div class="feature-num">04</div>
      <h3>Fallback Chains</h3>
      <p>When OpenAI, Stripe, or SendGrid drops, what do production agents actually switch to? Live journey data, ranked by downstream completion rate.</p>
    </div>
    <div class="feature">
      <div class="feature-num">05</div>
      <h3>Reliability Webhooks</h3>
      <p>Get paged the moment a tool's reliability crosses a threshold you define. HMAC-signed, per-tool, exponential-backoff delivery &mdash; wired into PagerDuty or Slack in seconds.</p>
    </div>
    <div class="feature">
      <div class="feature-num">06</div>
      <h3>MCP Server</h3>
      <p>Native integration with Claude Code, Cursor, and any MCP-aware client. Run assessments from inside your editor without breaking the loop.</p>
    </div>
  </div>
</section>

<!-- LLM Router spotlight -->
<section class="llm-router">
  <div class="llm-router-card">
    <div class="llm-router-badge">NEW &middot; LLM Router</div>
    <h2>LLM Router &mdash; one call, the right model.</h2>
    <p class="llm-router-lead">
      The ToolRate LLM Router picks the optimal model for each task &mdash; combining real-time
      reliability, exact per-token pricing, and latency awareness across all major providers,
      plus Ollama for local and free.
    </p>
    <div class="llm-router-strategies">
      <div class="llm-router-strategy"><strong>reliability_first</strong> &nbsp;80 / 20</div>
      <div class="llm-router-strategy"><strong>balanced</strong> &nbsp;55 / 45</div>
      <div class="llm-router-strategy"><strong>cost_first</strong> &nbsp;25 / 75</div>
      <div class="llm-router-strategy"><strong>speed_first</strong> &nbsp;35 / 45 / 20</div>
    </div>
    <div class="llm-router-grid">
      <div>
<pre class="llm-router-code"><span class="cm"># Tell ToolRate your constraints, get the right model back.</span>
<span class="kw">result</span> = client.<span class="fn">assess</span>(
  tool_identifier=<span class="str">"https://api.anthropic.com/v1/messages"</span>,
  task_complexity=<span class="str">"low"</span>,
  expected_tokens=<span class="num">500</span>,
  max_price_per_call=<span class="num">0.01</span>,
  budget_strategy=<span class="str">"cost_first"</span>,
)

<span class="cm"># → recommended_model: "claude-haiku-4-5"</span>
<span class="cm"># → price_per_call:    $0.00152  (exact per-token math)</span>
<span class="cm"># → within_budget:     true</span>
<span class="cm"># → reasoning:         "Anthropic Messages scored 91.7/100</span>
<span class="cm">#                       for reliability (low risk). Recommended</span>
<span class="cm">#                       model: claude-haiku-4-5. Cost: $0.0015/call.</span>
<span class="cm">#                       Typical latency ~500ms. Strategy: cost-first;</span>
<span class="cm">#                       task complexity: low. Fits within your budget."</span></pre>
      </div>
      <div class="llm-router-getlist">
        <h3>What you get per call</h3>
        <ul>
          <li>Exact per-million-token cost at your expected volume</li>
          <li>Specific model inside each provider (Haiku for low, Opus for reasoning)</li>
          <li>Human-readable <code>reasoning</code> string &mdash; drop it in your logs</li>
          <li>Over-budget tools flagged, never silently filtered</li>
          <li>Drop-in <code>LLMRouter</code> class with automatic fallback cascade</li>
        </ul>
        <div class="llm-router-providers">
          <div class="llm-router-provider">anthropic</div>
          <div class="llm-router-provider">openai</div>
          <div class="llm-router-provider">groq</div>
          <div class="llm-router-provider">together</div>
          <div class="llm-router-provider">mistral</div>
          <div class="llm-router-provider">deepseek</div>
          <div class="llm-router-provider llm-router-provider--free">ollama &middot; local &middot; free</div>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- Pricing -->
<section class="pricing" id="pricing">
  <div class="pricing-header">
    <h2>Pricing that scales with your agents</h2>
    <p style="font-size:0.9rem;color:var(--text-dim);margin-top:0.6rem;font-weight:300">Start free. Scale with pay-as-you-go. Flat-rate when you need it. <a href="/pricing" style="color:var(--brand)">See all plans &rarr;</a></p>
  </div>
  <div class="pricing-grid">
    <div class="pricing-card">
      <div class="pricing-tier">Free</div>
      <div class="pricing-price">$0 <span>/ forever</span></div>
      <p class="pricing-desc">For testing and side projects</p>
      <ul class="pricing-features">
        <li>100 assessments / day</li>
        <li>Public data pool</li>
        <li>Python &amp; TypeScript SDKs</li>
        <li>Standard support</li>
      </ul>
      <a href="/register" class="btn btn-ghost" style="width:100%;justify-content:center">Create Free Key</a>
    </div>
    <div class="pricing-card featured">
      <div class="pricing-tier">Pay-as-you-go</div>
      <div class="pricing-price">$0.008 <span>/ assessment</span></div>
      <p class="pricing-desc">Best for autonomous agents and bots</p>
      <ul class="pricing-features">
        <li>First 100 / day free</li>
        <li>$0.008 per assessment after</li>
        <li>No monthly commitment</li>
        <li>Webhook alerts included</li>
      </ul>
      <a href="/upgrade?plan=payg" class="btn btn-primary" style="width:100%;justify-content:center">Start Pay-as-you-go</a>
    </div>
    <div class="pricing-card">
      <div class="pricing-tier">Pro</div>
      <div class="pricing-price">$29 <span>/ month</span></div>
      <p class="pricing-desc">Flat rate for heavy usage</p>
      <ul class="pricing-features">
        <li>10,000 assessments / month</li>
        <li>Priority support</li>
        <li>Higher rate limits</li>
        <li>Webhook alerts</li>
      </ul>
      <a href="/upgrade?plan=pro" class="btn btn-ghost" style="width:100%;justify-content:center">Upgrade to Pro</a>
    </div>
  </div>
  <p style="text-align:center;margin-top:2rem;font-size:0.82rem;color:var(--text-dim)">
    Building an AI platform? <a href="/pricing#contact-sales" style="color:var(--brand);font-weight:500">Talk to sales about Enterprise →</a>
  </p>
</section>

</main>

<!-- Footer -->
<footer class="footer container">
  <div class="footer-left">Built for production agents &middot; GDPR compliant &middot; Hosted in Germany</div>
  <div class="footer-right">
    <a href="/docs">Documentation</a>
    <a href="https://github.com/netvistamedia/toolrate">GitHub</a>
    <a href="/privacy">Privacy</a>
    <a href="/health">Status</a>
  </div>
</footer>

</div>

<script>
function showTab(lang) {
  document.querySelectorAll('.code-tab').forEach(function(t) { t.classList.remove('active'); });
  document.querySelectorAll('.code-panel').forEach(function(p) { p.classList.remove('active'); });
  document.querySelector('[onclick="showTab(\'' + lang + '\')"]').classList.add('active');
  document.getElementById('tab-' + lang).classList.add('active');
}
</script>
__SITE_HEADER_JS__
</body>
</html>"""


# Rendered once at import — `main.py` substitutes the live-stat placeholders
# (`__LANDING_TOOLS_COUNT__`, `__LANDING_REPORTS_COUNT__`) at request time so
# the homepage always reflects the current DB numbers without re-reading the
# whole template on every hit.
LANDING_HTML_TEMPLATE = (
    _LANDING_TEMPLATE
    .replace("__SITE_HEADER_CSS__", SITE_HEADER_CSS)
    .replace("__SITE_HEADER_HTML__", SITE_HEADER_HTML)
    .replace("__SITE_HEADER_JS__", SITE_HEADER_JS)
)

# Kept as an alias so any legacy importer still works.
LANDING_HTML = LANDING_HTML_TEMPLATE
