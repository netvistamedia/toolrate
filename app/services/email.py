"""
Email service using SendGrid.

Sends welcome emails on registration with getting-started guide.
"""
import logging

import httpx

from app.config import settings

logger = logging.getLogger("nemoflow.email")

SENDGRID_API = "https://api.sendgrid.com/v3/mail/send"


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
  <pre style="background:#1a1a2e;color:#e0e0e0;padding:1rem;border-radius:8px;font-size:0.85rem;overflow-x:auto"><code>pip install nemoflow    <span style="color:#666"># Python</span>
npm install nemoflow    <span style="color:#666"># TypeScript</span></code></pre>

  <p><strong>2. Check a tool before calling it</strong></p>
  <pre style="background:#1a1a2e;color:#e0e0e0;padding:1rem;border-radius:8px;font-size:0.85rem;overflow-x:auto"><code><span style="color:#7b61ff">from</span> nemoflow <span style="color:#7b61ff">import</span> NemoFlowClient

client = NemoFlowClient(<span style="color:#ff6b9d">"your_full_api_key"</span>)
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
