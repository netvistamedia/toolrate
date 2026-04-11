import logging
import time
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.config import settings
from app.db.session import engine

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("nemoflow")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting NemoFlow API")
    app.state.redis = aioredis.from_url(
        settings.redis_url, decode_responses=True, max_connections=50
    )
    yield
    await app.state.redis.close()
    await engine.dispose()
    logger.info("NemoFlow API stopped")


DESCRIPTION = """
**The reliability oracle for AI agents.**

NemoFlow provides real-time reliability scores for external tools and APIs,
based on the collective experience of thousands of AI agents.

## How it works

1. **Assess** before calling a tool — get a reliability score, failure risk, common pitfalls, and alternatives
2. **Report** after calling a tool — contribute success/failure data back to the community
3. The data moat grows with every report, making scores more accurate for everyone

## Authentication

All endpoints require an API key passed via the `X-Api-Key` header.

```
X-Api-Key: nf_live_your_key_here
```

## Rate Limits

| Tier | Daily Limit |
|------|------------|
| Free | 100 calls |
| Pro | 10,000 calls |
| Enterprise | Custom |

## SDKs

- **Python**: `pip install nemoflow`
- **TypeScript**: `npm install nemoflow`
"""

app = FastAPI(
    title="NemoFlow",
    description=DESCRIPTION,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "NemoFlow", "url": "https://nemoflow.ai"},
    openapi_tags=[
        {"name": "Auth", "description": "Register for an API key"},
        {"name": "Assessment", "description": "Check tool reliability before calling"},
        {"name": "Reporting", "description": "Report execution results to build the data moat"},
        {"name": "Discovery", "description": "Discover hidden gem tools and fallback chains based on real agent journeys"},
        {"name": "Stats", "description": "Platform and personal usage statistics"},
        {"name": "Webhooks", "description": "Register webhooks for real-time score change alerts"},
    ],
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Request logging + timing
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "%s %s %s %sms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    response.headers["X-Response-Time-Ms"] = str(duration_ms)
    return response


# Validation error handler
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": exc.errors()},
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


from app.api.v1.router import router as v1_router  # noqa: E402

app.include_router(v1_router)


@app.get("/", include_in_schema=False, response_class=HTMLResponse)
async def root():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NemoFlow — Pick the Right Tool from the Start</title>
<meta name="description" content="NemoFlow rates AI tools so that you or your agents pick the right tool from the start. Save time, tokens, energy, and money.">
<meta property="og:title" content="NemoFlow — Pick the Right Tool from the Start">
<meta property="og:description" content="AI picks a tool, it fails, swaps for another — costing time and tokens. NemoFlow rates 600+ tools so agents pick the right one from the start.">
<meta property="og:image" content="https://nemoflow.ai/nemoflow-logo.webp">
<meta property="og:url" content="https://api.nemoflow.ai">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="NemoFlow — Reliability Oracle for AI Agents">
<meta name="twitter:description" content="Rate 600+ AI tools. One line of code. Auto-fallback. Built by agents, for agents.">
<meta name="twitter:image" content="https://nemoflow.ai/nemoflow-logo.webp">
<link rel="icon" href="https://nemoflow.ai/nemoflow-logo.webp" type="image/webp">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0a0a;color:#e0e0e0;min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:2rem}
.container{max-width:760px;width:100%}
.hero{text-align:center;padding:3rem 0 2rem}
h1{font-size:3rem;font-weight:700;background:linear-gradient(135deg,#00d4ff,#7b61ff,#ff6b9d);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:.5rem}
.tagline{font-size:1.3rem;color:#aaa;margin-bottom:2rem}

.story{background:#111;border:1px solid #1a1a1a;border-radius:14px;padding:2rem;margin-bottom:2rem;line-height:1.75;color:#bbb;font-size:.95rem}
.story strong{color:#e0e0e0}
.story .highlight{color:#00d4ff;font-weight:600}

.analogy{background:linear-gradient(135deg,rgba(0,212,255,.08),rgba(123,97,255,.08));border:1px solid #1f1f3a;border-radius:14px;padding:1.75rem;margin-bottom:2rem;text-align:center}
.analogy p{font-size:1.05rem;color:#ccc;line-height:1.6;font-style:italic}
.analogy .icon{font-size:2rem;margin-bottom:.75rem}

.stats{display:flex;gap:1.25rem;justify-content:center;margin-bottom:2rem;flex-wrap:wrap}
.stat{background:#151515;border:1px solid #222;border-radius:12px;padding:1.25rem 1.5rem;min-width:130px;text-align:center}
.stat-value{font-size:1.75rem;font-weight:700;color:#00d4ff}
.stat-label{font-size:.75rem;color:#666;margin-top:.25rem;text-transform:uppercase;letter-spacing:.05em}

.code{background:#151515;border:1px solid #222;border-radius:12px;padding:1.5rem;text-align:left;margin-bottom:2rem;overflow-x:auto}
.code pre{font-family:'SF Mono',Menlo,monospace;font-size:.85rem;color:#ccc;line-height:1.6}
.code .kw{color:#7b61ff}.code .fn{color:#00d4ff}.code .str{color:#ff6b9d}.code .cm{color:#555}

.buttons{display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;margin-bottom:2.5rem}
a.btn{display:inline-block;padding:.75rem 1.75rem;border-radius:8px;text-decoration:none;font-weight:600;font-size:.95rem;transition:all .2s}
.btn-primary{background:linear-gradient(135deg,#00d4ff,#7b61ff);color:#fff}
.btn-primary:hover{opacity:.9;transform:translateY(-1px)}
.btn-secondary{background:#1a1a1a;border:1px solid #333;color:#ccc}
.btn-secondary:hover{border-color:#555;color:#fff}

.features{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:2.5rem;text-align:left}
.feature{background:#151515;border:1px solid #222;border-radius:10px;padding:1.1rem 1.25rem}
.feature h3{font-size:.9rem;color:#00d4ff;margin-bottom:.3rem}
.feature p{font-size:.8rem;color:#888;line-height:1.5}

.footer{color:#444;font-size:.75rem;text-align:center;padding-top:1rem;border-top:1px solid #1a1a1a}
@media(max-width:600px){h1{font-size:2rem}.stats{flex-direction:column;align-items:center}.features{grid-template-columns:1fr}.story{padding:1.5rem}}
</style>
</head>
<body>
<div class="container">

<div class="hero">
<img src="https://nemoflow.ai/nemoflow-logo.webp" alt="NemoFlow" style="max-width:280px;margin-bottom:1rem">
<p class="tagline">Pick the right tool from the start</p>
</div>

<div class="story">
<p>As a developer, you know the problem: <strong>AI picks a tool, it fails, then it swaps for another one</strong> &mdash; and sometimes another one after that. Every wrong pick costs <span class="highlight">time, tokens, energy, and money</span>.</p>
<p style="margin-top:.75rem">AI agents and bots run into the same mismatches over and over again. NemoFlow fixes this by <strong>rating AI tools so that you or your agents pick the right one from the start</strong>.</p>
</div>

<div class="analogy">
<p>Think of it as the advisor in a hardware store who asks you <strong>what job you need a tool for</strong> and suggests the best one &mdash; based not only on his own expertise, but on the real-world experience of <span style="color:#00d4ff;font-weight:600">thousands of workers</span> who are actually using these tools every day.</p>
</div>

<div class="stats">
<div class="stat"><div class="stat-value">600+</div><div class="stat-label">Tools Rated</div></div>
<div class="stat"><div class="stat-value">68K+</div><div class="stat-label">Data Points</div></div>
<div class="stat"><div class="stat-value">10</div><div class="stat-label">LLM Sources</div></div>
<div class="stat"><div class="stat-value">&lt;10ms</div><div class="stat-label">Response</div></div>
</div>

<div class="code"><pre><span class="kw">from</span> nemoflow <span class="kw">import</span> NemoFlowClient, guard

client = NemoFlowClient(<span class="str">"nf_live_..."</span>)

<span class="cm"># One line — pick the right tool, auto-fallback if needed</span>
result = <span class="fn">guard</span>(client, <span class="str">"https://api.openai.com/v1/chat/completions"</span>,
               <span class="kw">lambda</span>: openai.chat.completions.create(...),
               fallbacks=[
                   (<span class="str">"https://api.anthropic.com/v1/messages"</span>,
                    <span class="kw">lambda</span>: anthropic.messages.create(...)),
               ])</pre></div>

<div class="buttons">
<a href="/docs" class="btn btn-primary">Get Started</a>
<a href="https://github.com/netvistamedia/nemoflow" class="btn btn-secondary">GitHub</a>
</div>

<div class="features">
<div class="feature"><h3>Assess Before Calling</h3><p>Real-time reliability scores, failure risk, common pitfalls, and mitigations for 600+ tools</p></div>
<div class="feature"><h3>Auto-Fallback</h3><p>guard() automatically tries the next best alternative when a tool fails or scores too low</p></div>
<div class="feature"><h3>Hidden Gems</h3><p>Discover underrated tools that agents switch to after popular ones fail &mdash; the tools nobody talks about but everyone ends up using</p></div>
<div class="feature"><h3>Smarter Every Day</h3><p>Started with input from 10 top LLMs. Combined with actual agent ratings, NemoFlow gets more reliable with every report</p></div>
</div>

<p class="footer">Built for agents, by agents &middot; GDPR compliant &middot; Hosted in Germany</p>
</div>
</body>
</html>"""


@app.get("/health")
async def health():
    return {"status": "ok"}
