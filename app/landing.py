"""Landing page HTML — kept separate to avoid cluttering main.py."""

LANDING_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ToolRate — Reliability Oracle for AI Agents</title>
<meta name="description" content="ToolRate rates AI tools so that you or your agents pick the right tool from the start. Save time, tokens, energy, and money.">
<meta property="og:title" content="ToolRate — Pick the Right Tool from the Start">
<meta property="og:description" content="AI picks a tool, it fails, swaps for another — costing time and tokens. ToolRate rates 600+ tools so agents pick the right one from the start.">
<meta property="og:image" content="https://toolrate.ai/toolrate-logo.webp">
<meta property="og:url" content="https://api.toolrate.ai">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="ToolRate — Reliability Oracle for AI Agents">
<meta name="twitter:description" content="Rate 600+ AI tools. One line of code. Auto-fallback. Built by agents, for agents.">
<meta name="twitter:image" content="https://toolrate.ai/toolrate-logo.webp">
<link rel="canonical" href="https://api.toolrate.ai">
<link rel="icon" href="https://toolrate.ai/toolrate-favicon.png" type="image/png">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "ToolRate",
  "url": "https://api.toolrate.ai",
  "description": "Reliability oracle for AI agents. Rates 600+ tools and APIs so agents pick the right one from the start. Real-time reliability scores, failure risk assessment, auto-fallback, and hidden gem discovery.",
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
    "Real-time reliability scoring for 600+ tools and APIs",
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

/* ── Top bar ── */
.topbar {
  padding: 1.25rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  animation: fadeDown 0.5s ease-out both;
  position: relative;
  z-index: 10;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.topbar-logo { width: 30px; height: 30px; border-radius: 6px; }

.topbar-name {
  font-weight: 600;
  font-size: 1rem;
  color: var(--text-bright);
  letter-spacing: -0.01em;
}

.topbar-tag {
  font-family: var(--mono);
  font-size: 0.6rem;
  font-weight: 500;
  color: var(--brand);
  background: var(--brand-dim);
  padding: 0.15rem 0.45rem;
  border-radius: 3px;
  border: 1px solid rgba(10,149,253,0.15);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.topbar-links { display: flex; gap: 1.25rem; align-items: center; }

.topbar-links a {
  font-size: 0.8rem;
  font-weight: 400;
  color: var(--text-bright);
  text-decoration: none;
  transition: color 0.2s;
}
.topbar-links a:hover { color: var(--brand); }

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

/* ── Hero ── */
.hero {
  padding: 5rem 0 3.5rem;
  display: flex;
  align-items: center;
  gap: 3rem;
  position: relative;
  animation: fadeUp 0.7s ease-out 0.1s both;
}

.hero-content { flex: 1; }

.hero-mascot {
  flex-shrink: 0;
  width: 260px;
  filter: drop-shadow(0 20px 40px rgba(10,149,253,0.15));
}

.hero-eyebrow {
  font-family: var(--mono);
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--brand);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  margin-bottom: 1rem;
}

.hero h1 {
  font-size: clamp(2.2rem, 4.5vw, 3.2rem);
  font-weight: 700;
  color: var(--text-bright);
  line-height: 1.2;
  letter-spacing: -0.02em;
  margin-bottom: 1.25rem;
}

.hero h1 span { color: var(--brand); }

.hero-sub {
  font-size: 1rem;
  font-weight: 300;
  color: var(--text-dim);
  max-width: 480px;
  line-height: 1.7;
  margin-bottom: 2rem;
}

.hero-actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }

/* ── Readout ── */
.readout {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 5rem;
  animation: fadeUp 0.7s ease-out 0.25s both;
}

.readout-cell {
  background: var(--surface);
  padding: 1.5rem;
  text-align: center;
  transition: background 0.3s;
}
.readout-cell:hover { background: var(--surface-2); }

.readout-value {
  font-family: var(--mono);
  font-size: 1.5rem;
  font-weight: 500;
  color: var(--brand);
}

.readout-label {
  font-size: 0.7rem;
  font-weight: 400;
  color: var(--text-dim);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-top: 0.35rem;
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
  padding: 2.75rem 2.5rem;
  border-radius: 16px;
  background:
    radial-gradient(circle at 0% 0%, rgba(52, 211, 153, 0.06) 0%, transparent 55%),
    radial-gradient(circle at 100% 100%, rgba(10, 149, 253, 0.10) 0%, transparent 55%),
    var(--surface);
  border: 1px solid var(--border-bright);
  overflow: hidden;
  animation: fadeUp 0.7s ease-out 0.4s both;
}

.jurisdiction::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--green), var(--brand) 50%, var(--red));
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
  margin-bottom: 2.5rem;
}

.features-header h2 {
  font-size: 1.7rem;
  font-weight: 600;
  color: var(--text-bright);
  margin-bottom: 0.4rem;
}

.features-header p {
  font-size: 0.9rem;
  color: var(--text-dim);
  font-weight: 300;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}

.feature {
  background: var(--surface);
  padding: 1.75rem;
  transition: background 0.3s;
}
.feature:hover { background: var(--surface-2); }

.feature-num {
  font-family: var(--mono);
  font-size: 0.65rem;
  font-weight: 500;
  color: var(--brand);
  letter-spacing: 0.08em;
  margin-bottom: 0.75rem;
}

.feature h3 {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-bright);
  margin-bottom: 0.4rem;
}

.feature p {
  font-size: 0.78rem;
  font-weight: 300;
  color: var(--text-dim);
  line-height: 1.65;
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
  .hero { flex-direction: column-reverse; text-align: center; padding: 3rem 0 2.5rem; }
  .hero-mascot { width: 180px; }
  .hero-sub { margin-left: auto; margin-right: auto; }
  .hero-actions { justify-content: center; }
  .readout { grid-template-columns: repeat(2, 1fr); }
  .narrative { grid-template-columns: 1fr; }
  .jurisdiction { padding: 2rem 1.5rem; }
  .jurisdiction h2 { font-size: 1.35rem; }
  .jurisdiction-tiers { grid-template-columns: 1fr; }
  .jurisdiction-benefits { grid-template-columns: 1fr; }
  .features-grid { grid-template-columns: 1fr; }
  .pricing-grid { grid-template-columns: 1fr; max-width: 420px; }
  .topbar { flex-direction: column; gap: 0.75rem; }
  .footer { flex-direction: column; gap: 0.75rem; text-align: center; }
  .code-header { flex-direction: column; gap: 0.75rem; align-items: flex-start; }
}
</style>
</head>
<body>

<div class="page">

<!-- Top bar -->
<header class="topbar">
  <div class="topbar-left">
    <img src="https://toolrate.ai/toolrate-logo.webp" alt="ToolRate" style="height:32px">
    <span class="topbar-tag">v0.1</span>
  </div>
  <nav class="topbar-links">
    <a href="/pricing">Pricing</a>
    <a href="/docs">Docs</a>
    <a href="/redoc">API Reference</a>
    <a href="https://github.com/netvistamedia/nemoflow">GitHub</a>
    <a href="/register" class="btn btn-primary" style="padding:0.4rem 1rem;font-size:0.78rem;color:#fff">Get API Key</a>
  </nav>
</header>

<main class="container">

<!-- Hero -->
<section class="hero">
  <div class="hero-glow"></div>
  <div class="hero-content">
    <div class="hero-eyebrow">Reliability Oracle for AI Agents</div>
    <h1>Pick the <span>right tool</span><br>from the start</h1>
    <p class="hero-sub">
      AI agents pick tools, they fail, swap for another &mdash; costing time, tokens, and money.
      ToolRate rates 600+ tools so your agents pick correctly the first time.
    </p>
    <div class="hero-actions">
      <a href="/docs" class="btn btn-primary">Get Started Free</a>
      <a href="https://github.com/netvistamedia/nemoflow" class="btn btn-ghost">View on GitHub</a>
    </div>
  </div>
  <img src="https://nemoflow.com/nemo-tool-rating.webp" alt="ToolRate AI Robot" class="hero-mascot">
</section>

<!-- Readout -->
<div class="readout">
  <div class="readout-cell">
    <div class="readout-value">637</div>
    <div class="readout-label">Tools Rated</div>
  </div>
  <div class="readout-cell">
    <div class="readout-value">68.4K</div>
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
    <h3>Agents waste cycles on failing tools</h3>
    <p>Your agent picks Stripe, it times out. Falls back to LemonSqueezy, auth fails. Tries PayPal, finally works. Three attempts, wasted tokens, frustrated users.</p>
  </div>
  <div class="narrative-card narrative-solution">
    <div class="narrative-badge"><span class="narrative-dot"></span> The Solution</div>
    <h3>One call before every tool call</h3>
    <p>ToolRate scores every tool in real time based on the collective experience of thousands of agents. Check the score, pick the best option first, fall back intelligently.</p>
  </div>
</div>

<!-- Jurisdiction Intelligence -->
<section class="jurisdiction">
  <div class="jurisdiction-head">
    <div class="jurisdiction-icon">🌍</div>
    <h2>Jurisdiction Intelligence</h2>
    <span class="jurisdiction-badge">Exclusive to ToolRate</span>
  </div>
  <p class="jurisdiction-lead">
    Know the real data residency risk <em>before</em> your agent makes the call.
    Every tool is tagged with its true hosting jurisdiction and GDPR risk &mdash; with a confidence level included.
  </p>

  <div class="jurisdiction-tiers">
    <div class="tier tier-eu">
      <div class="tier-label"><span class="tier-dot"></span>EU-hosted</div>
      <p>Clearly marked as GDPR-compliant with low residency risk.</p>
    </div>
    <div class="tier tier-mid">
      <div class="tier-label"><span class="tier-dot"></span>US &amp; Other Regions</div>
      <p>Accurate risk level shown so your agent can weigh it in real time.</p>
    </div>
    <div class="tier tier-high">
      <div class="tier-label"><span class="tier-dot"></span>High-risk Jurisdictions</div>
      <p>Explicitly flagged &mdash; never quietly routed through.</p>
    </div>
  </div>

  <div class="jurisdiction-benefits-title">Benefits for every agent</div>
  <ul class="jurisdiction-benefits">
    <li><strong>Privacy-first agents</strong> automatically prefer EU tools for sensitive data.</li>
    <li><strong>Compliance-aware agents</strong> enforce rules like “never use non-GDPR tools for customer data.”</li>
    <li><strong>Global agents</strong> get instant risk scoring and smart fallbacks to the best alternative.</li>
    <li><strong>Enterprise teams</strong> prove data sovereignty to auditors with one query.</li>
  </ul>

  <p class="jurisdiction-punch">
    Your agent no longer guesses whether Stripe, OpenAI, Tavily or Supabase is safe for a regulated workflow &mdash; it <strong>knows</strong>, with confidence level included.
  </p>
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
    <div id="tab-python" class="code-panel active"><pre><span class="kw">from</span> nemoflow <span class="kw">import</span> NemoFlowClient, guard

client = NemoFlowClient(<span class="str">"nf_live_..."</span>)

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
    <div id="tab-typescript" class="code-panel"><pre><span class="kw">import</span> { NemoFlowClient } <span class="kw">from</span> <span class="str">"nemoflow"</span>;

<span class="kw">const</span> client = <span class="kw">new</span> <span class="fn">NemoFlowClient</span>(<span class="str">"nf_live_..."</span>);

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
    <p>Everything your agent needs to make smarter tool choices</p>
  </div>
  <div class="features-grid">
    <div class="feature">
      <div class="feature-num">01</div>
      <h3>Reliability Scoring</h3>
      <p>Bayesian-smoothed scores with recency weighting. 70% weight on last 7 days. Confidence intervals included.</p>
    </div>
    <div class="feature">
      <div class="feature-num">02</div>
      <h3>Auto-Fallback</h3>
      <p>guard() checks the score, runs your function, auto-retries with the next best alternative on failure.</p>
    </div>
    <div class="feature">
      <div class="feature-num">03</div>
      <h3>Hidden Gems</h3>
      <p>Discover tools that nobody talks about but everyone ends up using. Found by analyzing real fallback patterns.</p>
    </div>
    <div class="feature">
      <div class="feature-num">04</div>
      <h3>Fallback Chains</h3>
      <p>When Stripe fails, what do agents switch to? Real journey data from thousands of agent sessions.</p>
    </div>
    <div class="feature">
      <div class="feature-num">05</div>
      <h3>Webhooks</h3>
      <p>Get notified when a tool's reliability drops. HMAC-signed payloads, configurable thresholds per tool.</p>
    </div>
    <div class="feature">
      <div class="feature-num">06</div>
      <h3>MCP Server</h3>
      <p>Native integration with Claude Code and Cursor. Check tool reliability without leaving your editor.</p>
    </div>
  </div>
</section>

<!-- Pricing -->
<section class="pricing" id="pricing">
  <div class="pricing-header">
    <h2>Simple pricing</h2>
    <p style="font-size:0.85rem;color:var(--text-dim);margin-top:0.5rem;font-weight:300">Start free. Scale with pay-as-you-go. Flat-rate when you need it. <a href="/pricing" style="color:var(--brand)">See all plans &rarr;</a></p>
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
  <div class="footer-left">Built for agents, by agents &middot; GDPR compliant &middot; Hosted in Germany</div>
  <div class="footer-right">
    <a href="/docs">Documentation</a>
    <a href="https://github.com/netvistamedia/nemoflow">GitHub</a>
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

</body>
</html>"""
