"""Pricing page HTML — four-tier plan: Free, Pay-as-you-go (featured), Pro, Enterprise."""

from app.site_header import SITE_HEADER_CSS, SITE_HEADER_HTML, SITE_HEADER_JS

_PRICING_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ToolRate — Pricing</title>
<meta name="description" content="ToolRate pricing — Free for hackers, Pay-as-you-go at $0.008 per assessment (best for agents and bots), Pro $29/mo for power users, Enterprise / Platform for AI platforms.">
<meta property="og:title" content="ToolRate — Pricing">
<meta property="og:description" content="Four clean plans for the reliability oracle for AI agents — Free, Pay-as-you-go, Pro, and Enterprise.">
<meta property="og:image" content="https://toolrate.ai/toolrate-og.jpg">
<meta property="og:image:width" content="1280">
<meta property="og:image:height" content="720">
<meta property="og:image:alt" content="ToolRate — stop AI agents from failing in production.">
<meta property="og:url" content="https://toolrate.ai/pricing">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="ToolRate — Pricing">
<meta name="twitter:description" content="Four clean plans for the reliability oracle for AI agents — Free, Pay-as-you-go, Pro, and Enterprise.">
<meta name="twitter:image" content="https://toolrate.ai/toolrate-og.jpg">
<meta name="twitter:image:alt" content="ToolRate — stop AI agents from failing in production.">
<link rel="canonical" href="https://toolrate.ai/pricing">
<link rel="icon" href="https://toolrate.ai/toolrate-favicon.png" type="image/png">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap" rel="stylesheet">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "ToolRate",
  "description": "Reliability oracle for AI agents — real-time scores, failure risk, fallback chains.",
  "brand": {"@type": "Organization", "name": "ToolRate"},
  "offers": [
    {"@type": "Offer", "name": "Free", "price": "0", "priceCurrency": "USD",
     "description": "100 assessments per day, public data pool, all endpoints"},
    {"@type": "Offer", "name": "Pay-as-you-go", "price": "0.008", "priceCurrency": "USD",
     "description": "First 100 assessments per day free, then $0.008 per assessment. No monthly commitment."},
    {"@type": "Offer", "name": "Pro", "price": "29", "priceCurrency": "USD",
     "description": "$29 per month for 10,000 assessments, webhook alerts, priority support"},
    {"@type": "Offer", "name": "Enterprise", "priceCurrency": "USD",
     "description": "Custom volume, private data pool, SSO, 99.99% SLA, dedicated support, white-label"}
  ]
}
</script>
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
}
*{margin:0;padding:0;box-sizing:border-box}
html,body{background:var(--bg);color:var(--text);font-family:'Poppins','Segoe UI',Arial,sans-serif;font-weight:300;line-height:1.55;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
code{font-family:'Fira Code',monospace;font-size:0.82em;background:rgba(10,149,253,0.12);color:#7dd3fc;padding:0.1rem 0.35rem;border-radius:4px}
.page{max-width:1200px;margin:0 auto;padding:0 2rem}

/* ── Topbar (shared — see app/site_header.py) ── */
__SITE_HEADER_CSS__
.btn{display:inline-flex;align-items:center;justify-content:center;padding:0.7rem 1.2rem;font-family:inherit;font-size:0.8rem;font-weight:600;border-radius:8px;border:1px solid var(--border-strong);background:transparent;color:var(--text-bright);cursor:pointer;transition:all 0.2s;text-decoration:none}
.btn:hover{border-color:var(--brand);color:var(--brand)}
.btn-primary{background:var(--brand);border-color:var(--brand);color:#fff}
.btn-primary:hover{background:#0784e6;color:#fff;box-shadow:0 0 40px var(--brand-dim)}
.btn-ghost{background:transparent;color:var(--text)}

/* ── Hero ── */
.hero{text-align:center;padding:3.5rem 0 2.5rem}
.eyebrow{display:inline-block;font-size:0.7rem;letter-spacing:0.14em;text-transform:uppercase;color:var(--brand);border:1px solid var(--brand);padding:0.25rem 0.8rem;border-radius:999px;margin-bottom:1.25rem;font-weight:500}
.hero h1{font-size:2.6rem;font-weight:700;color:var(--text-bright);letter-spacing:-0.02em;margin-bottom:0.8rem}
.hero p{font-size:1.02rem;color:var(--text-dim);max-width:680px;margin:0 auto;font-weight:300}

/* ── Plans grid ── */
.plans{display:grid;grid-template-columns:repeat(4,1fr);gap:1.25rem;margin-top:3rem;align-items:stretch}
.plan{position:relative;display:flex;flex-direction:column;padding:2.1rem 1.6rem 1.8rem;background:var(--surface);border:1px solid var(--border);border-radius:16px;transition:border-color 0.2s, transform 0.2s}
.plan:hover{border-color:var(--border-strong)}
.plan.featured{border-color:var(--brand);box-shadow:0 0 80px var(--brand-dim);transform:translateY(-6px)}
.plan.featured:hover{transform:translateY(-8px)}
.plan.enterprise{background:linear-gradient(180deg,#141015 0%,#0f1118 100%);border-color:#3a2a18}
.plan-badge{position:absolute;top:-0.72rem;left:50%;transform:translateX(-50%);font-size:0.6rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#fff;background:var(--brand);padding:0.32rem 0.85rem;border-radius:999px;white-space:nowrap}
.plan-badge.gray{background:#2a2e42}
.plan-tier{font-size:0.68rem;font-weight:600;letter-spacing:0.12em;text-transform:uppercase;color:var(--brand);margin-bottom:0.8rem}
.plan.enterprise .plan-tier{color:#f0c53b}
.plan-price{font-size:2.3rem;font-weight:700;color:var(--text-bright);margin-bottom:0.1rem;letter-spacing:-0.02em;line-height:1.1}
.plan-price span.unit{font-size:0.78rem;font-weight:400;color:var(--text-dim);margin-left:0.25rem}
.plan-price .from{font-size:0.72rem;color:var(--text-dim);display:block;font-weight:400;margin-bottom:0.25rem;letter-spacing:0.04em}
.plan-sub{font-size:0.78rem;color:var(--text-dim);margin-bottom:1.25rem;min-height:2.6em;line-height:1.55}
.plan-features{list-style:none;margin-bottom:1.75rem;flex:1}
.plan-features li{font-size:0.78rem;color:var(--text);padding:0.5rem 0;border-bottom:1px solid var(--border);display:flex;align-items:flex-start;gap:0.55rem;font-weight:400;line-height:1.5}
.plan-features li:last-child{border-bottom:none}
.plan-features li::before{content:'✓';color:var(--brand);font-weight:700;flex-shrink:0}
.plan.enterprise .plan-features li::before{color:#f0c53b}
.plan-features li.muted{color:var(--text-dim)}
.plan-features li.muted::before{color:var(--text-mute)}
.plan-cta{width:100%}

/* ── Why PAYG section ── */
.why-payg{margin-top:5rem;padding:3rem;background:linear-gradient(135deg,#101218 0%,#0f1118 50%,#121620 100%);border:1px solid var(--border-strong);border-radius:18px;position:relative;overflow:hidden}
.why-payg::before{content:'';position:absolute;top:-60px;right:-60px;width:340px;height:340px;background:radial-gradient(circle,rgba(10,149,253,0.1) 0%,transparent 65%);pointer-events:none}
.why-payg-inner{position:relative}
.why-payg .eyebrow{border-color:var(--brand);color:var(--brand)}
.why-payg h2{font-size:1.9rem;font-weight:700;color:var(--text-bright);margin-bottom:0.85rem;letter-spacing:-0.01em;line-height:1.2;max-width:720px}
.why-payg p.lead{font-size:0.95rem;color:var(--text);margin-bottom:2rem;max-width:720px;font-weight:400}
.why-payg-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1.5rem}
.why-payg-card{padding:1.6rem;background:rgba(15,17,24,0.6);border:1px solid var(--border);border-radius:12px}
.why-payg-card h4{font-size:0.92rem;font-weight:600;color:var(--text-bright);margin-bottom:0.5rem;display:flex;align-items:center;gap:0.5rem}
.why-payg-card h4::before{content:'→';color:var(--brand);font-weight:700}
.why-payg-card p{font-size:0.78rem;color:var(--text-dim);line-height:1.65;font-weight:300}

/* ── Enterprise section ── */
.enterprise-section{margin-top:5rem;padding:3rem;background:linear-gradient(135deg,#141015 0%,#0f1118 50%,#151a24 100%);border:1px solid #2a2018;border-radius:18px;position:relative;overflow:hidden}
.enterprise-section::before{content:'';position:absolute;top:0;right:0;width:320px;height:320px;background:radial-gradient(circle,rgba(240,201,59,0.08) 0%,transparent 65%);pointer-events:none}
.enterprise-grid{display:grid;grid-template-columns:1.15fr 1fr;gap:3rem;align-items:center;position:relative}
.enterprise-eyebrow{font-size:0.7rem;letter-spacing:0.14em;text-transform:uppercase;color:#f0c53b;margin-bottom:0.75rem;font-weight:500}
.enterprise-section h2{font-size:1.9rem;font-weight:700;color:var(--text-bright);letter-spacing:-0.01em;margin-bottom:1rem;line-height:1.2}
.enterprise-section p.lead{font-size:0.95rem;color:var(--text);margin-bottom:1.25rem;font-weight:400}
.enterprise-points{list-style:none;margin-bottom:1.5rem}
.enterprise-points li{font-size:0.84rem;color:var(--text-dim);padding:0.45rem 0;display:flex;gap:0.65rem;align-items:flex-start;line-height:1.55}
.enterprise-points li::before{content:'→';color:var(--brand);font-weight:700;flex-shrink:0}
.enterprise-points strong{color:var(--text-bright);font-weight:500}

/* ── Contact form ── */
.contact-card{background:var(--surface);border:1px solid var(--border-strong);border-radius:14px;padding:2rem}
.contact-card h3{font-size:1.05rem;font-weight:600;color:var(--text-bright);margin-bottom:0.35rem}
.contact-card .hint{font-size:0.78rem;color:var(--text-dim);margin-bottom:1.25rem}
.form-row{margin-bottom:0.9rem}
.form-row label{display:block;font-size:0.7rem;font-weight:500;color:var(--text-dim);margin-bottom:0.35rem;text-transform:uppercase;letter-spacing:0.06em}
.form-row input,.form-row textarea,.form-row select{width:100%;padding:0.7rem 0.9rem;background:var(--surface-2);border:1px solid var(--border-strong);border-radius:8px;color:var(--text-bright);font-family:inherit;font-size:0.85rem;outline:none;transition:border-color 0.2s;font-weight:400}
.form-row textarea{resize:vertical;min-height:90px;line-height:1.5}
.form-row input:focus,.form-row textarea:focus,.form-row select:focus{border-color:var(--brand)}
.form-row input::placeholder,.form-row textarea::placeholder{color:var(--text-mute)}
.form-status{display:none;margin-top:0.75rem;padding:0.75rem 1rem;border-radius:8px;font-size:0.82rem}
.form-status.ok{display:block;background:rgba(61,220,132,0.08);border:1px solid rgba(61,220,132,0.25);color:var(--green)}
.form-status.err{display:block;background:rgba(240,90,90,0.08);border:1px solid rgba(240,90,90,0.25);color:#f05a5a}

/* ── Cost calculator ── */
.calc{margin-top:3rem;padding:2rem 2.25rem;background:var(--surface);border:1px solid var(--border);border-radius:14px;display:grid;grid-template-columns:1fr 1fr;gap:2rem;align-items:center}
.calc h3{font-size:1rem;font-weight:600;color:var(--text-bright);margin-bottom:0.4rem}
.calc p.hint{font-size:0.78rem;color:var(--text-dim);margin-bottom:1rem;line-height:1.55}
.calc input[type=range]{width:100%;accent-color:var(--brand)}
.calc .calls{font-size:1.1rem;font-weight:600;color:var(--text-bright);margin-bottom:0.35rem;font-variant-numeric:tabular-nums}
.calc .breakdown{display:flex;gap:1.25rem;margin-top:1rem;padding-top:1rem;border-top:1px solid var(--border);font-size:0.78rem}
.calc .breakdown div{flex:1}
.calc .breakdown .label{color:var(--text-dim);margin-bottom:0.2rem}
.calc .breakdown .val{color:var(--text-bright);font-weight:600;font-size:0.95rem;font-variant-numeric:tabular-nums}
.calc .breakdown .val.accent{color:var(--brand)}
.calc .rec{font-size:0.78rem;color:var(--text);padding:0.7rem 0.9rem;background:rgba(10,149,253,0.08);border:1px solid rgba(10,149,253,0.2);border-radius:8px;margin-top:1rem}
.calc .rec strong{color:var(--brand)}

/* ── FAQ ── */
.faq{margin-top:5rem}
.faq-header{text-align:center;margin-bottom:2.5rem}
.faq-header h2{font-size:1.55rem;font-weight:700;color:var(--text-bright)}
.faq-grid{display:grid;grid-template-columns:1fr 1fr;gap:1.25rem 2.5rem;max-width:900px;margin:0 auto}
.faq-item h4{font-size:0.9rem;font-weight:600;color:var(--text-bright);margin-bottom:0.35rem}
.faq-item p{font-size:0.8rem;color:var(--text-dim);line-height:1.6}

/* ── Footer ── */
.footer{border-top:1px solid var(--border);padding:2rem 0;margin-top:5rem;display:flex;justify-content:space-between;align-items:center}
.footer-left{font-size:0.72rem;color:var(--text-dim)}
.footer-right{display:flex;gap:1.25rem}
.footer-right a{font-size:0.72rem;color:var(--text-dim)}
.footer-right a:hover{color:var(--brand)}

/* ── Responsive ── */
@media (max-width:1080px){
  .plans{grid-template-columns:repeat(2,1fr);max-width:720px;margin-left:auto;margin-right:auto}
  .plan.featured{transform:none}
  .why-payg-grid{grid-template-columns:1fr}
  .enterprise-grid{grid-template-columns:1fr;gap:2rem}
  .calc{grid-template-columns:1fr}
}
@media (max-width:640px){
  .page{padding:0 1.25rem}
  .plans{grid-template-columns:1fr;max-width:420px}
  .faq-grid{grid-template-columns:1fr}
  .hero h1{font-size:2rem}
  .enterprise-section,.why-payg{padding:2rem}
  .footer{flex-direction:column;gap:0.75rem}
}
</style>
</head>
<body>

__SITE_HEADER_HTML__

<div class="page">

<section class="hero">
  <span class="eyebrow">Pricing</span>
  <h1>Built for agents. Priced for agents.</h1>
  <p>Start free in 30 seconds — no credit card. Upgrade to pay-as-you-go when your agent goes into production. Subscribe only if you know you'll hit it hard. Every plan uses the same API, the same SDKs, and the same data pool.</p>
</section>

<section class="plans">

  <!-- FREE -->
  <div class="plan">
    <div class="plan-tier">Free</div>
    <div class="plan-price">$0<span class="unit">/ forever</span></div>
    <p class="plan-sub">For prototypes, side projects and hackers exploring the API.</p>
    <ul class="plan-features">
      <li>100 assessments / day</li>
      <li>Public data pool</li>
      <li>Python &amp; TypeScript SDKs</li>
      <li>All endpoints included</li>
      <li class="muted">Standard support</li>
      <li class="muted">No SLA</li>
    </ul>
    <a href="/register" class="btn btn-ghost plan-cta">Create Free Key</a>
  </div>

  <!-- PAY-AS-YOU-GO (FEATURED) -->
  <div class="plan featured">
    <div class="plan-badge">Best for agents &amp; bots</div>
    <div class="plan-tier">Pay-as-you-go</div>
    <div class="plan-price">$0.008<span class="unit">/ assessment</span></div>
    <p class="plan-sub">First 100 assessments every day on us. Then $0.008 each — no minimum, no commitment.</p>
    <ul class="plan-features">
      <li><strong>100 free assessments every day</strong></li>
      <li>$0.008 per assessment after that</li>
      <li>Scales to zero automatically</li>
      <li>Webhook alerts included</li>
      <li>Higher rate limits</li>
      <li>Cancel any time — pay only for what you use</li>
    </ul>
    <a href="/upgrade?plan=payg" class="btn btn-primary plan-cta">Start Pay-as-you-go</a>
  </div>

  <!-- PRO -->
  <div class="plan">
    <div class="plan-tier">Pro</div>
    <div class="plan-price">$29<span class="unit">/ month</span></div>
    <p class="plan-sub">For power users and teams that know they'll use ToolRate heavily every month.</p>
    <ul class="plan-features">
      <li>10,000 assessments / month</li>
      <li>Webhook alerts on score drops</li>
      <li>Priority email support</li>
      <li>Higher per-minute rate limits</li>
      <li>Flat monthly cost</li>
      <li>Cancel anytime</li>
    </ul>
    <a href="/upgrade?plan=pro" class="btn btn-ghost plan-cta">Upgrade to Pro</a>
  </div>

  <!-- ENTERPRISE -->
  <div class="plan enterprise">
    <div class="plan-badge gray">Platform</div>
    <div class="plan-tier">Enterprise</div>
    <div class="plan-price"><span class="from">Custom — talk to us</span>Let's talk</div>
    <p class="plan-sub">For AI platforms and large teams that need a private reliability oracle of their own.</p>
    <ul class="plan-features">
      <li>Unlimited or custom call volume</li>
      <li><strong>Private, isolated data pool</strong></li>
      <li>99.99% SLA + dedicated support</li>
      <li>SSO, SCIM, audit log export</li>
      <li>White-label / embedded option</li>
      <li>Custom benchmarks &amp; reports</li>
    </ul>
    <a href="#contact-sales" class="btn btn-ghost plan-cta">Contact Sales</a>
  </div>

</section>

<!-- Cost calculator -->
<div class="calc">
  <div>
    <h3>How much will Pay-as-you-go cost me?</h3>
    <p class="hint">Move the slider to estimate what you'd pay based on your typical assessment volume. Remember — the first 100 calls every day are free, and you never pay a subscription on top.</p>
    <label for="calc-slider" style="font-size:0.72rem;color:var(--text-dim);letter-spacing:0.08em;text-transform:uppercase;font-weight:500">Assessments per day</label>
    <input type="range" id="calc-slider" min="0" max="5000" step="50" value="500">
    <div class="calls" id="calc-calls">500 / day</div>
  </div>
  <div>
    <div class="breakdown">
      <div>
        <div class="label">Free calls</div>
        <div class="val" id="calc-free">100 / day</div>
      </div>
      <div>
        <div class="label">Billable</div>
        <div class="val" id="calc-bill">400 / day</div>
      </div>
      <div>
        <div class="label">Monthly total</div>
        <div class="val accent" id="calc-total">$96.00</div>
      </div>
    </div>
    <div class="rec" id="calc-rec">At this volume, <strong>Pay-as-you-go</strong> is recommended — you pay only for what your agent actually uses.</div>
  </div>
</div>

<!-- Why PAYG -->
<section class="why-payg">
  <div class="why-payg-inner">
    <span class="eyebrow">For autonomous agents</span>
    <h2>Pay-as-you-go is the plan we recommend for almost every agent.</h2>
    <p class="lead">Autonomous agents have unpredictable workloads. One hour you're idle, the next you're scoring a thousand tools because a user asked for a complex task. A flat subscription leaves you paying for headroom you don't need — or worse, getting rate-limited right when you need ToolRate most.</p>
    <div class="why-payg-grid">
      <div class="why-payg-card">
        <h4>Zero friction sign-up</h4>
        <p>Any agent with a credit card can self-serve in under a minute. No "pick your tier" decision, no usage forecasting. Start free, pay only when you cross the 100/day mark.</p>
      </div>
      <div class="why-payg-card">
        <h4>Scales with your traffic</h4>
        <p>Quiet day? You pay $0. Launch day with 50k assessments? You pay exactly what you used, no surprise overage fees or throttling at midnight.</p>
      </div>
      <div class="why-payg-card">
        <h4>Cheaper than Pro until you hit ~3,700/month</h4>
        <p>PAYG beats the $29 subscription for any agent that runs fewer than ~3,700 billable assessments/month. The calculator above shows your break-even.</p>
      </div>
    </div>
  </div>
</section>

<!-- Enterprise section -->
<section class="enterprise-section" id="contact-sales">
  <div class="enterprise-grid">
    <div>
      <div class="enterprise-eyebrow">For AI Platforms</div>
      <h2>Embed ToolRate for every agent on your platform.</h2>
      <p class="lead">Building the next Cursor, Claude Code, Manus or Devin? Give every user on your platform a reliability oracle that's tuned to your own workloads — not a shared public pool.</p>
      <ul class="enterprise-points">
        <li><strong>Private data moat.</strong> Your users' reports build your own isolated scoring model. Your data never mixes with the public pool — and your insights never leak to competitors.</li>
        <li><strong>Compliance-ready.</strong> EU hosting, GDPR, audit log export, SSO, SCIM provisioning. Ships with everything your procurement team asks for.</li>
        <li><strong>Scale without worry.</strong> 99.99% SLA, dedicated infrastructure, and a support channel staffed by the engineers who built ToolRate.</li>
        <li><strong>Custom integrations.</strong> White-label the API, embed scores in your UI, get custom benchmarks for the tools your users rely on most.</li>
      </ul>
    </div>

    <div class="contact-card">
      <h3>Talk to sales</h3>
      <p class="hint">Platforms get a same-day response. We'll scope the integration on a 30-minute call.</p>
      <form id="salesForm" onsubmit="return submitSales(event)">
        <div class="form-row">
          <label for="f-company">Company</label>
          <input type="text" id="f-company" name="company" placeholder="Acme AI" required maxlength="120">
        </div>
        <div class="form-row">
          <label for="f-name">Your name</label>
          <input type="text" id="f-name" name="name" placeholder="Jane Doe" maxlength="120">
        </div>
        <div class="form-row">
          <label for="f-email">Work email</label>
          <input type="email" id="f-email" name="email" placeholder="jane@acme.ai" required>
        </div>
        <div class="form-row">
          <label for="f-volume">Estimated monthly volume</label>
          <select id="f-volume" name="volume" required>
            <option value="">Select&hellip;</option>
            <option value="100k">Up to 100k calls</option>
            <option value="1M">Up to 1M calls</option>
            <option value="10M">Up to 10M calls</option>
            <option value="50M+">50M+ calls</option>
            <option value="unsure">Not sure yet</option>
          </select>
        </div>
        <div class="form-row">
          <label for="f-use">What are you building?</label>
          <textarea id="f-use" name="use_case" placeholder="We're building an AI coding platform with ~50k active developers and need ToolRate scores surfaced in-editor&hellip;" required minlength="10" maxlength="2000"></textarea>
        </div>
        <button type="submit" class="btn btn-primary" id="salesBtn" style="width:100%">Request a call</button>
        <div class="form-status" id="salesStatus"></div>
      </form>
    </div>
  </div>
</section>

<!-- FAQ -->
<section class="faq">
  <div class="faq-header"><h2>Pricing FAQ</h2></div>
  <div class="faq-grid">
    <div class="faq-item">
      <h4>What counts as an "assessment"?</h4>
      <p>Any call to <code>/v1/assess</code>. Reports, webhook calls, and tool browsing don't count — you're only billed when you actually ask ToolRate to score a tool.</p>
    </div>
    <div class="faq-item">
      <h4>Does the 100/day free grant apply to Pay-as-you-go?</h4>
      <p>Yes. Every Pay-as-you-go account gets the same 100 free assessments per UTC day. You're billed $0.008 only for calls 101 and beyond, reset daily.</p>
    </div>
    <div class="faq-item">
      <h4>When does Pro make sense over Pay-as-you-go?</h4>
      <p>When you reliably make more than ~3,700 billable assessments per month, Pro's flat $29/month becomes cheaper. Below that threshold, PAYG wins — and you keep 100 free calls/day.</p>
    </div>
    <div class="faq-item">
      <h4>Can I set a spend limit on Pay-as-you-go?</h4>
      <p>Yes — we apply a conservative daily hard cap on every PAYG key by default. Contact support if you want a custom ceiling for a specific agent.</p>
    </div>
    <div class="faq-item">
      <h4>Can I switch plans later?</h4>
      <p>Any time, in either direction. We migrate your key instantly — no downtime, no re-integration. Enterprise customers get a dedicated tier on top of everything below.</p>
    </div>
    <div class="faq-item">
      <h4>How does the private data pool work?</h4>
      <p>Enterprise keys are tagged with a pool ID. All reports and scoring from your pool are isolated — queries scoped to your pool never see public data and vice versa.</p>
    </div>
  </div>
</section>

<footer class="footer">
  <div class="footer-left">© 2026 ToolRate &middot; Built for agents, by agents &middot; Hosted in Germany</div>
  <div class="footer-right">
    <a href="/">Home</a>
    <a href="/docs">Docs</a>
    <a href="/register">Register</a>
    <a href="/health">Status</a>
  </div>
</footer>

</div>

<script>
// ── Cost calculator ──
(function() {
  var slider = document.getElementById('calc-slider');
  var callsEl = document.getElementById('calc-calls');
  var freeEl = document.getElementById('calc-free');
  var billEl = document.getElementById('calc-bill');
  var totalEl = document.getElementById('calc-total');
  var recEl = document.getElementById('calc-rec');
  var FREE_PER_DAY = 100;
  var PRICE = 0.008;
  var PRO_PRICE = 29;
  var PRO_INCLUDED = 10000; // per month

  function update() {
    var perDay = parseInt(slider.value, 10);
    var billablePerDay = Math.max(0, perDay - FREE_PER_DAY);
    var billablePerMonth = billablePerDay * 30;
    var cost = billablePerMonth * PRICE;
    callsEl.textContent = perDay.toLocaleString() + ' / day';
    freeEl.textContent = Math.min(perDay, FREE_PER_DAY) + ' / day';
    billEl.textContent = billablePerDay.toLocaleString() + ' / day';
    totalEl.textContent = '$' + cost.toFixed(2);

    if (billablePerMonth >= PRO_INCLUDED && cost > PRO_PRICE) {
      recEl.innerHTML = 'At this volume, <strong>Pro ($29/month)</strong> is cheaper. You\'d save $' +
        (cost - PRO_PRICE).toFixed(2) + '/month vs. Pay-as-you-go.';
    } else if (perDay === 0) {
      recEl.innerHTML = 'Stay on <strong>Free</strong> — you\'re well under the 100/day grant.';
    } else if (perDay <= FREE_PER_DAY) {
      recEl.innerHTML = 'You\'re inside the <strong>free grant</strong> — Pay-as-you-go is effectively free at this volume.';
    } else {
      recEl.innerHTML = 'At this volume, <strong>Pay-as-you-go</strong> is recommended — you pay only for what your agent actually uses.';
    }
  }
  slider.addEventListener('input', update);
  update();
})();

// ── Sales form ──
async function submitSales(e) {
  e.preventDefault();
  var btn = document.getElementById('salesBtn');
  var status = document.getElementById('salesStatus');
  status.className = 'form-status';
  status.textContent = '';
  btn.disabled = true;
  var oldText = btn.textContent;
  btn.textContent = 'Sending...';

  var payload = {
    company: document.getElementById('f-company').value.trim(),
    name: document.getElementById('f-name').value.trim() || null,
    email: document.getElementById('f-email').value.trim(),
    volume: document.getElementById('f-volume').value,
    use_case: document.getElementById('f-use').value.trim()
  };

  try {
    var resp = await fetch('/v1/billing/contact-sales', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    var data = await resp.json();
    if (!resp.ok) {
      status.className = 'form-status err';
      status.textContent = data.detail || 'Something went wrong. Please try again.';
      btn.disabled = false;
      btn.textContent = oldText;
      return;
    }
    status.className = 'form-status ok';
    status.textContent = data.message || 'Thanks — we will be in touch shortly.';
    document.getElementById('salesForm').reset();
    btn.textContent = 'Sent ✓';
    setTimeout(function(){ btn.disabled = false; btn.textContent = oldText; }, 3000);
  } catch (err) {
    status.className = 'form-status err';
    status.textContent = 'Network error — please try again or email bleep@toolrate.ai directly.';
    btn.disabled = false;
    btn.textContent = oldText;
  }
}
</script>
__SITE_HEADER_JS__
</body>
</html>"""


PRICING_HTML = (
    _PRICING_TEMPLATE
    .replace("__SITE_HEADER_CSS__", SITE_HEADER_CSS)
    .replace("__SITE_HEADER_HTML__", SITE_HEADER_HTML)
    .replace("__SITE_HEADER_JS__", SITE_HEADER_JS)
)
