"""/privacy page — Netvista Media S.L. privacy policy."""

from app.site_header import SITE_HEADER_CSS, SITE_HEADER_HTML, SITE_HEADER_JS

_PRIVACY_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Privacy Policy — ToolRate</title>
<meta name="description" content="ToolRate privacy policy: what Netvista Media S.L. collects, why, and your GDPR rights when using the ToolRate reliability oracle for AI agents.">
<meta name="robots" content="index,follow">
<meta property="og:title" content="Privacy Policy — ToolRate">
<meta property="og:description" content="How ToolRate handles your data. GDPR compliant. Hosted in Germany.">
<meta property="og:image" content="https://toolrate.ai/toolrate-logo.webp">
<meta property="og:url" content="https://toolrate.ai/privacy">
<link rel="canonical" href="https://toolrate.ai/privacy">
<link rel="icon" href="https://toolrate.ai/toolrate-favicon.png" type="image/png">
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
  --mono: 'Fira Code', 'SF Mono', 'Consolas', monospace;
  --sans: 'Poppins', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
}
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: var(--sans);
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
  font-weight: 300;
  line-height: 1.65;
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
a { color: var(--brand-light); text-decoration: none; }
a:hover { text-decoration: underline; }

__SITE_HEADER_CSS__

.container {
  max-width: 820px;
  margin: 0 auto;
  padding: 0 2rem;
  position: relative;
  z-index: 1;
}
.legal-hero {
  padding: 4rem 0 2rem;
  text-align: center;
  border-bottom: 1px solid var(--border);
  margin-bottom: 3rem;
}
.legal-eyebrow {
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
.legal-hero h1 {
  font-size: clamp(2rem, 4.2vw, 2.8rem);
  font-weight: 700;
  color: var(--text-bright);
  letter-spacing: -0.02em;
  margin-bottom: 0.8rem;
}
.legal-hero .updated {
  font-family: var(--mono);
  font-size: 0.82rem;
  color: var(--text-dim);
}

.legal-body {
  padding-bottom: 4rem;
}
.legal-body .intro {
  background: var(--surface);
  border: 1px solid var(--border);
  border-left: 3px solid var(--brand);
  border-radius: 10px;
  padding: 1.25rem 1.4rem;
  margin-bottom: 2.5rem;
  font-size: 0.95rem;
  color: var(--text);
}
.legal-body h2 {
  font-size: 1.28rem;
  color: var(--text-bright);
  font-weight: 600;
  letter-spacing: -0.01em;
  margin-top: 2.6rem;
  margin-bottom: 0.85rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border);
}
.legal-body h2 .num {
  font-family: var(--mono);
  font-size: 0.82rem;
  color: var(--brand-light);
  font-weight: 500;
  margin-right: 0.55rem;
}
.legal-body p {
  font-size: 0.95rem;
  color: var(--text);
  margin-bottom: 0.85rem;
  font-weight: 300;
}
.legal-body ul {
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 1rem;
}
.legal-body li {
  position: relative;
  padding-left: 1.35rem;
  margin-bottom: 0.55rem;
  font-size: 0.94rem;
  color: var(--text);
  font-weight: 300;
}
.legal-body li::before {
  content: '';
  position: absolute;
  left: 0.1rem;
  top: 0.65rem;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--brand);
  box-shadow: 0 0 0 3px rgba(10, 149, 253, 0.12);
}
.legal-body li strong { color: var(--text-bright); font-weight: 500; }

.contact-card {
  margin-top: 1.25rem;
  background: var(--surface);
  border: 1px solid var(--border-bright);
  border-radius: 14px;
  padding: 1.6rem 1.75rem;
  font-family: var(--mono);
  font-size: 0.85rem;
  color: var(--text);
  line-height: 1.75;
}
.contact-card .company {
  color: var(--text-bright);
  font-weight: 500;
  font-size: 0.95rem;
  margin-bottom: 0.4rem;
}
.contact-card .label {
  display: inline-block;
  width: 84px;
  color: var(--text-dim);
}

.legal-footer {
  border-top: 1px solid var(--border);
  padding: 2rem 1rem 3rem;
  text-align: center;
  font-size: 0.8rem;
  color: var(--text-dim);
}
.legal-footer a { color: var(--brand-light); }

@media (max-width: 768px) {
  .container { padding: 0 1.25rem; }
  .legal-hero { padding: 2.5rem 0 1.5rem; margin-bottom: 2rem; }
  .legal-body h2 { font-size: 1.15rem; margin-top: 2rem; }
  .contact-card { padding: 1.25rem; font-size: 0.8rem; }
  .contact-card .label { width: 70px; }
}
</style>
</head>
<body>

__SITE_HEADER_HTML__

<main class="container">

  <section class="legal-hero">
    <div class="legal-eyebrow">· Legal ·</div>
    <h1>Privacy Policy</h1>
    <div class="updated">Last updated: April 14, 2026</div>
  </section>

  <section class="legal-body">

    <div class="intro">
      Netvista Media S.L. (&ldquo;we&rdquo;, &ldquo;us&rdquo;, or &ldquo;our&rdquo;) operates the
      website <a href="https://toolrate.ai">https://toolrate.ai</a> (the &ldquo;Service&rdquo;).
      This Privacy Policy explains how we collect, use, disclose, and safeguard
      your information when you visit our website, use our Service, or interact
      with us. Please read this Privacy Policy carefully. If you do not agree
      with the terms of this Privacy Policy, please do not access the Service.
    </div>

    <h2><span class="num">1.</span>Information We Collect</h2>
    <p>We may collect the following types of information:</p>
    <ul>
      <li><strong>Personal Data:</strong> Name, email address, company name, and other information you voluntarily provide when you create an account, sign up for our newsletter, or contact us.</li>
      <li><strong>Usage Data:</strong> Information about how you access and use the Service, including your IP address, browser type, device information, pages visited, and time spent on the Service.</li>
      <li><strong>Technical Data:</strong> Log files, cookies, and similar tracking technologies that help us improve the Service.</li>
      <li><strong>AI-Related Data:</strong> When you use ToolRate (our crowdsourced reliability oracle for AI agents), we may process anonymized or aggregated data from agent runs to improve reliability scores, identify common pitfalls, and suggest alternatives. We do not use your individual prompts or sensitive inputs to train models without your explicit consent.</li>
    </ul>

    <h2><span class="num">2.</span>How We Use Your Information</h2>
    <p>We use the collected information for the following purposes:</p>
    <ul>
      <li>To provide, maintain, and improve our Service</li>
      <li>To process registrations and manage user accounts</li>
      <li>To communicate with you, including responding to inquiries and sending important updates</li>
      <li>To analyze usage patterns and improve user experience</li>
      <li>To detect, prevent, and address technical issues or fraudulent activity</li>
      <li>To comply with legal obligations</li>
    </ul>

    <h2><span class="num">3.</span>Legal Basis for Processing (GDPR)</h2>
    <p>For users in the European Economic Area, we process your personal data based on:</p>
    <ul>
      <li>Your consent</li>
      <li>Performance of a contract with you</li>
      <li>Our legitimate business interests</li>
      <li>Compliance with legal obligations</li>
    </ul>

    <h2><span class="num">4.</span>Sharing Your Information</h2>
    <p>We do not sell your personal data. We may share your information only in the following cases:</p>
    <ul>
      <li>With service providers who assist us in operating the Service (e.g., hosting providers, analytics tools)</li>
      <li>When required by law or to protect our rights</li>
      <li>In connection with a business transfer (merger, acquisition, etc.)</li>
    </ul>

    <h2><span class="num">5.</span>Data Retention</h2>
    <p>We retain your personal data only as long as necessary to fulfill the purposes outlined in this Privacy Policy or as required by law.</p>

    <h2><span class="num">6.</span>Your Data Protection Rights (GDPR)</h2>
    <p>As a resident of the European Union, you have the following rights:</p>
    <ul>
      <li>Right to access, correct, or delete your personal data</li>
      <li>Right to restrict or object to processing</li>
      <li>Right to data portability</li>
      <li>Right to withdraw consent at any time</li>
    </ul>
    <p>To exercise these rights, please contact us at <a href="mailto:petergiesbers@gmail.com">petergiesbers@gmail.com</a>.</p>

    <h2><span class="num">7.</span>Cookies and Tracking Technologies</h2>
    <p>We use cookies and similar technologies to enhance your experience. You can manage your cookie preferences through your browser settings.</p>

    <h2><span class="num">8.</span>International Data Transfers</h2>
    <p>Your data may be transferred to and processed in countries outside the European Economic Area. We ensure appropriate safeguards are in place to protect your data.</p>

    <h2><span class="num">9.</span>Security</h2>
    <p>We implement reasonable technical and organizational measures to protect your personal data. However, no method of transmission over the internet is 100% secure.</p>

    <h2><span class="num">10.</span>Children&rsquo;s Privacy</h2>
    <p>Our Service is not intended for children under 16 years of age. We do not knowingly collect personal data from children.</p>

    <h2><span class="num">11.</span>Changes to This Privacy Policy</h2>
    <p>We may update this Privacy Policy from time to time. We will notify you of any changes by posting the new Privacy Policy on this page and updating the &ldquo;Last updated&rdquo; date.</p>

    <h2><span class="num">12.</span>Contact Us</h2>
    <p>If you have any questions about this Privacy Policy, please contact us:</p>
    <div class="contact-card">
      <div class="company">Netvista Media S.L.</div>
      Av. Sant Rafel 23<br>
      03580 Alfaz del Pi<br>
      España<br><br>
      <span class="label">Email:</span> <a href="mailto:info@netvista.es">info@netvista.es</a><br>
      <span class="label">Phone:</span> +34 628 662 912<br>
      <span class="label">Website:</span> <a href="https://netvista.es">https://netvista.es</a><br>
      <span class="label">CIF:</span> B54981352<br>
      <span class="label">Tax&nbsp;No.:</span> ESB54981352
    </div>

  </section>

</main>

<footer class="legal-footer">
  <p>
    ToolRate &middot; <a href="/">Home</a> &middot; <a href="/pricing">Pricing</a>
    &middot; <a href="/docs">Docs</a> &middot; <a href="/privacy">Privacy</a>
  </p>
</footer>

__SITE_HEADER_JS__

</body>
</html>
"""


PRIVACY_HTML = (
    _PRIVACY_TEMPLATE
    .replace("__SITE_HEADER_CSS__", SITE_HEADER_CSS)
    .replace("__SITE_HEADER_HTML__", SITE_HEADER_HTML)
    .replace("__SITE_HEADER_JS__", SITE_HEADER_JS)
)
