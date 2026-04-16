"""
Email service using SendGrid.

Sends welcome emails on registration with getting-started guide, plus
operational notifications such as webhook auto-deactivation.
"""
import logging
from html import escape

import httpx

from app.config import settings

logger = logging.getLogger("nemoflow.email")

SENDGRID_API = "https://api.sendgrid.com/v3/mail/send"


async def _send_via_sendgrid(payload: dict, *, log_label: str) -> None:
    """Single-shot SendGrid POST with timeout + structured logging.

    Tiny helper so every outbound transactional email goes through the same
    timeout, error handling, and "log_label" tag — without each caller
    replicating its own try/except around httpx.
    """
    if not settings.sendgrid_api_key:
        logger.debug("SendGrid not configured, skipping %s", log_label)
        return
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SENDGRID_API,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.sendgrid_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
        if resp.status_code >= 300:
            logger.warning(
                "SendGrid (%s) returned %s: %s",
                log_label, resp.status_code, resp.text[:300],
            )
        else:
            logger.info("Email sent: %s", log_label)
    except Exception as e:
        logger.warning("SendGrid send failed (%s): %s", log_label, e)


async def send_webhook_deactivated_email(
    to_email: str,
    *,
    webhook_url: str,
    failure_count: int,
    last_error: str | None = None,
) -> None:
    """Notify the webhook owner that we just auto-deactivated their endpoint.

    Triggered the moment ``failure_count`` crosses 10. Owners had no way to
    discover this transition before — the dispatcher used to silently flip
    ``is_active`` and stop calling them. The email is fire-and-forget;
    SendGrid not configured = silently skipped, exactly like the welcome
    email path.
    """
    if not to_email:
        return

    safe_url = escape(webhook_url)
    last_error_html = (
        f'<p style="margin:0.5rem 0;color:#666;font-size:0.85rem">'
        f'Last error: <code>{escape(last_error)}</code></p>'
        if last_error else ""
    )

    html = f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;color:#333">
  <div style="text-align:center;padding:1.5rem 0">
    <h1 style="font-size:1.5rem;margin:0;color:#c0392b">Webhook auto-deactivated</h1>
    <p style="color:#666;margin-top:0.5rem">After {failure_count} consecutive failed deliveries</p>
  </div>

  <div style="background:#fff5f5;border-left:4px solid #c0392b;border-radius:4px;padding:1rem 1.25rem;margin-bottom:1rem">
    <p style="margin:0 0 0.5rem"><strong>Endpoint:</strong></p>
    <p style="margin:0;font-family:Menlo,Monaco,monospace;font-size:0.85rem;word-break:break-all"><code>{safe_url}</code></p>
    {last_error_html}
  </div>

  <p style="line-height:1.55">ToolRate stops sending events to a webhook after 10 consecutive failures so we don't keep hammering a dead endpoint. Your webhook is now inactive — no events will be delivered until you re-enable it.</p>

  <p style="margin-top:1.25rem"><strong>To re-enable:</strong></p>
  <ol style="padding-left:1.25rem;line-height:1.7">
    <li>Fix the endpoint (verify TLS, deploy the missing route, etc.)</li>
    <li>Delete and re-create the webhook via <code>POST /v1/webhooks</code></li>
    <li>Or contact <a href="mailto:bleep@toolrate.ai" style="color:#0a95fd">support</a> to reset the failure counter without rotating the signing secret</li>
  </ol>

  <p style="color:#999;font-size:0.75rem;margin-top:2rem;text-align:center">
    ToolRate — Reliability oracle for AI agents<br>
    You received this because you set notification_email on your webhook.
  </p>
</div>
""".strip()

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": settings.sendgrid_from_email, "name": "ToolRate"},
        "subject": "[ToolRate] Webhook auto-deactivated",
        "content": [{"type": "text/html", "value": html}],
    }
    await _send_via_sendgrid(payload, log_label="webhook_deactivated")


async def send_welcome_email(to_email: str, api_key_prefix: str):
    """Send welcome email with getting-started guide. Fire-and-forget."""
    if not settings.sendgrid_api_key:
        logger.debug("SendGrid not configured, skipping welcome email")
        return

    html = f"""
<div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;color:#333">
  <div style="text-align:center;padding:2rem 0">
    <h1 style="font-size:1.8rem;margin:0">Welcome to ToolRate</h1>
    <p style="color:#666;margin-top:0.5rem">Your reliability oracle is ready</p>
  </div>

  <div style="background:#f8f9fa;border-radius:8px;padding:1.5rem;margin-bottom:1.5rem">
    <p style="margin:0 0 0.5rem">Your API key starts with <code style="background:#e9ecef;padding:2px 6px;border-radius:4px;font-size:0.9rem">{api_key_prefix}...</code></p>
    <p style="margin:0;color:#666;font-size:0.85rem">If you didn't save the full key, you'll need to register again.</p>
  </div>

  <h2 style="font-size:1.1rem;margin-bottom:0.75rem">Quick Start</h2>

  <p><strong>1. Install the SDK</strong></p>

  <p style="margin:0.75rem 0 0.35rem;color:#0a95fd;font-size:0.78rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em">Recommended — modern &amp; fastest</p>
  <pre style="background:#1a1a2e;color:#e0e0e0;padding:1rem;border-radius:8px;font-size:0.85rem;overflow-x:auto;margin:0"><code><span style="color:#7a7f99"># Install uv (one-time)</span>
curl -LsSf https://astral.sh/uv/install.sh | sh

<span style="color:#7a7f99"># Add ToolRate to your project</span>
uv add toolrate</code></pre>

  <p style="margin:0.85rem 0 0.35rem;color:#0a95fd;font-size:0.78rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em">Alternative — without uv</p>
  <pre style="background:#1a1a2e;color:#e0e0e0;padding:1rem;border-radius:8px;font-size:0.85rem;overflow-x:auto;margin:0"><code>python3 -m venv .venv
source .venv/bin/activate
pip install toolrate</code></pre>

  <p style="margin:0.75rem 0 0;padding:0.65rem 0.85rem;background:#fff8e1;border-left:3px solid #f0c53b;border-radius:4px;color:#5c4e00;font-size:0.82rem;line-height:1.55"><strong>Note:</strong> If you see a <code style="background:#ffe8a1;padding:1px 5px;border-radius:3px">PEP 668</code> "externally-managed-environment" error with plain <code style="background:#ffe8a1;padding:1px 5px;border-radius:3px">pip</code>, that's because of Homebrew Python. Use one of the methods above instead.</p>

  <p style="margin:0.75rem 0 0;color:#666;font-size:0.85rem">TypeScript / Node 18+: <code style="background:#f1f3f5;padding:1px 5px;border-radius:3px">npm install toolrate</code></p>

  <p><strong>2. Check a tool before calling it</strong></p>
  <pre style="background:#1a1a2e;color:#e0e0e0;padding:1rem;border-radius:8px;font-size:0.85rem;overflow-x:auto"><code><span style="color:#7b61ff">from</span> toolrate <span style="color:#7b61ff">import</span> ToolRate

client = ToolRate(<span style="color:#ff6b9d">"your_full_api_key"</span>)
score = client.assess(<span style="color:#ff6b9d">"https://api.stripe.com/v1/charges"</span>)
print(score.reliability_score)  <span style="color:#666"># e.g. 94.2</span></code></pre>

  <p><strong>3. Report results to make scores better for everyone</strong></p>
  <pre style="background:#1a1a2e;color:#e0e0e0;padding:1rem;border-radius:8px;font-size:0.85rem;overflow-x:auto"><code>client.report(<span style="color:#ff6b9d">"https://api.stripe.com/v1/charges"</span>, success=<span style="color:#7b61ff">True</span>, latency_ms=<span style="color:#00d4ff">420</span>)</code></pre>

  <div style="margin-top:1.5rem;padding-top:1.5rem;border-top:1px solid #e9ecef">
    <p style="margin:0 0 0.5rem"><strong>Useful links</strong></p>
    <p style="margin:0.25rem 0"><a href="https://api.toolrate.ai/docs" style="color:#7b61ff">API Documentation</a></p>
    <p style="margin:0.25rem 0"><a href="https://toolrate.ai/pricing" style="color:#7b61ff">See pricing</a> — Pay-as-you-go at $0.008/call or Pro at $29/month</p>
    <p style="margin:0.25rem 0"><a href="https://github.com/netvistamedia/toolrate" style="color:#7b61ff">GitHub</a></p>
  </div>

  <p style="color:#999;font-size:0.75rem;margin-top:2rem;text-align:center">
    ToolRate — Pick the right tool from the start<br>
    You received this because you registered for an API key.
  </p>
</div>
"""

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": settings.sendgrid_from_email, "name": "ToolRate"},
        "subject": "Your ToolRate API key is ready",
        "content": [{"type": "text/html", "value": html}],
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SENDGRID_API,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.sendgrid_api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10.0,
            )
        if resp.status_code >= 300:
            logger.warning("SendGrid returned %s: %s", resp.status_code, resp.text)
        else:
            logger.info("Welcome email sent to %s", to_email[:3] + "***")
    except Exception as e:
        logger.warning("Failed to send welcome email: %s", e)
