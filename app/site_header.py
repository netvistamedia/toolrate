"""Shared marketing header for ToolRate public pages.

Landing, pricing, register, upgrade, and billing success/cancel pages all
inline the same HTML block. Previously each page defined its own `.topbar`
styles and its own nav link list, which drifted — landing said "Pricing,
Docs, API Reference, GitHub" while pricing said "Home, Docs, GitHub". The
mobile experience was also broken: landing collapsed the links into a
vertical column below the logo, pricing just hid them entirely.

Everything here uses the `site-topbar-*` namespace so it can be pasted into
pages that still carry their own unrelated `.topbar-*` styles without
colliding.
"""

SITE_HEADER_CSS = r"""
/* ── Shared site header ──────────────────────────────────────────── */
.site-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 2rem;
  border-bottom: 1px solid var(--border, #1c1f2e);
  position: relative;
  z-index: 50;
}
.site-topbar-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  text-decoration: none;
}
.site-topbar-logo { height: 32px; width: auto; display: block; }
.site-topbar-tag {
  font-family: 'Fira Code', 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  font-weight: 500;
  color: var(--brand, #0a95fd);
  background: rgba(10, 149, 253, 0.08);
  padding: 0.15rem 0.45rem;
  border-radius: 3px;
  border: 1px solid rgba(10, 149, 253, 0.15);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.site-topbar-nav {
  display: flex;
  gap: 1.5rem;
  align-items: center;
}
.site-topbar-nav a {
  font-size: 0.82rem;
  font-weight: 400;
  color: var(--text-bright, #f0f2f8);
  text-decoration: none;
  transition: color 0.2s;
}
.site-topbar-nav a:hover { color: var(--brand, #0a95fd); }
.site-topbar-cta {
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1.1rem;
  background: linear-gradient(135deg, #0a95fd 0%, #2fcffa 100%);
  color: #fff !important;
  border-radius: 8px;
  font-weight: 700;
  font-size: 0.78rem;
  text-decoration: none;
  transition: all 0.2s;
}
.site-topbar-cta:hover {
  filter: brightness(1.08);
  box-shadow: 0 4px 18px rgba(10, 149, 253, 0.35);
}
/* Hamburger — hidden on desktop */
.site-topbar-hamburger {
  display: none;
  width: 40px;
  height: 40px;
  background: transparent;
  border: 1px solid var(--border-strong, #282c40);
  border-radius: 8px;
  cursor: pointer;
  padding: 0;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  gap: 5px;
  transition: border-color 0.2s;
}
.site-topbar-hamburger:hover { border-color: var(--brand, #0a95fd); }
.site-topbar-hamburger span {
  display: block;
  width: 18px;
  height: 2px;
  background: var(--text-bright, #f0f2f8);
  border-radius: 2px;
  transition: transform 0.25s, opacity 0.25s;
}
.site-topbar-hamburger[aria-expanded="true"] span:nth-child(1) {
  transform: translateY(7px) rotate(45deg);
}
.site-topbar-hamburger[aria-expanded="true"] span:nth-child(2) { opacity: 0; }
.site-topbar-hamburger[aria-expanded="true"] span:nth-child(3) {
  transform: translateY(-7px) rotate(-45deg);
}
/* Mobile layout: hide the inline nav, show the hamburger, open as panel. */
@media (max-width: 768px) {
  .site-topbar { padding: 1rem 1.25rem; }
  .site-topbar-hamburger { display: flex; }
  .site-topbar-nav {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    flex-direction: column;
    align-items: stretch;
    gap: 0;
    padding: 0.75rem 1.25rem 1.25rem;
    background: var(--surface, #0f1118);
    border-bottom: 1px solid var(--border, #1c1f2e);
    box-shadow: 0 18px 40px rgba(0, 0, 0, 0.45);
    max-height: 0;
    overflow: hidden;
    opacity: 0;
    transition: max-height 0.28s ease, opacity 0.2s ease, padding 0.28s ease;
    pointer-events: none;
  }
  .site-topbar-nav.open {
    max-height: 420px;
    opacity: 1;
    pointer-events: auto;
  }
  .site-topbar-nav a {
    padding: 0.9rem 0.25rem;
    border-bottom: 1px solid var(--border, #1c1f2e);
    font-size: 0.95rem;
  }
  .site-topbar-nav a:last-child { border-bottom: none; }
  .site-topbar-cta {
    margin-top: 0.85rem;
    justify-content: center;
    padding: 0.85rem 1.25rem;
    font-size: 0.88rem;
  }
}
"""

SITE_HEADER_HTML = """
<header class="site-topbar">
  <a href="/" class="site-topbar-left">
    <img src="https://toolrate.ai/toolrate-logo.webp" alt="ToolRate" class="site-topbar-logo">
  </a>
  <button type="button" class="site-topbar-hamburger"
          aria-label="Toggle menu" aria-expanded="false"
          aria-controls="site-topbar-nav"
          onclick="toggleSiteMenu(this)">
    <span></span><span></span><span></span>
  </button>
  <nav class="site-topbar-nav" id="site-topbar-nav">
    <a href="/">Home</a>
    <a href="/pricing">Pricing</a>
    <a href="/docs">Docs</a>
    <a href="/redoc">API Reference</a>
    <a href="https://github.com/netvistamedia/toolrate">GitHub</a>
    <a href="/register" class="site-topbar-cta">Get API Key</a>
  </nav>
</header>
"""

SITE_HEADER_JS = """
<script>
function toggleSiteMenu(btn) {
  var nav = document.getElementById('site-topbar-nav');
  if (!nav) return;
  var open = nav.classList.toggle('open');
  btn.setAttribute('aria-expanded', open ? 'true' : 'false');
}
// Auto-close menu after tapping a link (mobile).
document.addEventListener('DOMContentLoaded', function () {
  var nav = document.getElementById('site-topbar-nav');
  var btn = document.querySelector('.site-topbar-hamburger');
  if (!nav || !btn) return;
  nav.querySelectorAll('a').forEach(function (a) {
    a.addEventListener('click', function () {
      nav.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
    });
  });
});
</script>
"""
