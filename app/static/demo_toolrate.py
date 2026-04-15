#!/usr/bin/env python3
"""
ToolRate Loom demo — single-file simulation.

Run:
    python demo_toolrate.py

Tip: maximize your terminal, dark background, ~14pt font.
Tune SPEED to stretch/shrink the runtime (1.0 ≈ 70 seconds).
"""
import sys
import time

SPEED = 1.0  # global pause multiplier — bump to 1.2 if you talk slowly

# ---------- ANSI ----------
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RED     = "\033[91m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
BLUE    = "\033[94m"
MAGENTA = "\033[95m"
CYAN    = "\033[96m"
GRAY    = "\033[90m"
WHITE   = "\033[97m"
BG_RED   = "\033[101m"
BG_GREEN = "\033[102m"

WIDTH = 72


def pause(seconds):
    time.sleep(seconds * SPEED)


def slow(text, delay=0.014, end="\n"):
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(end)
    sys.stdout.flush()


def rule(char="─", color=GRAY):
    print(f"{color}{char * WIDTH}{RESET}")


def banner(title, color=CYAN):
    rule("━", color)
    print(f"{color}{BOLD}  {title}{RESET}")
    rule("━", color)


def think(text, delay=0.9):
    print(f"  {DIM}{GRAY}↳ {text}{RESET}")
    pause(delay)


def step(symbol, text, color=WHITE, delay=0.5):
    print(f"  {color}{symbol}{RESET} {text}")
    pause(delay)


# ---------- DEMO ----------
def main():
    # clear screen
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

    # ── session header ─────────────────────────────────────────────
    print()
    print(f"{BOLD}{CYAN}  ◆ Claude Code{RESET}  {GRAY}— agent session{RESET}")
    print(f"  {GRAY}model: claude-opus-4-6  ·  tools: stripe, lemonsqueezy, toolrate{RESET}")
    print()
    rule()
    pause(0.8)

    # ── user task ──────────────────────────────────────────────────
    print()
    print(f"  {BOLD}user ▸{RESET}")
    slow("  Charge the customer $49 for a premium subscription using Stripe.")
    print()
    pause(1.6)

    # ── agent reasoning ────────────────────────────────────────────
    print(f"  {BOLD}{MAGENTA}assistant ▸{RESET}")
    pause(0.4)
    think("Understanding task: process a $49 premium subscription charge…")
    think("Identifying tool: Stripe Payments API → /v1/charges")
    think("Policy: always guard external API calls with ToolRate before invoking.")
    print()
    pause(0.6)

    # ── toolrate.guard call ────────────────────────────────────────
    step("⚡", f"{BOLD}toolrate.guard(\"stripe.charges.create\", fallbacks=\"auto\"){RESET}", CYAN)
    pause(0.6)
    print(f"     {GRAY}POST https://toolrate.ai/v1/assess{RESET}")
    pause(0.5)
    print(f"     {GRAY}↻ analyzing 1,284 recent reports…{RESET}")
    pause(1.4)
    print()

    # ── toolrate response card ─────────────────────────────────────
    banner("  TOOLRATE  ▸  reliability oracle", CYAN)
    print()
    print(f"  {BOLD}tool{RESET}             stripe.charges.create")
    print(f"  {BOLD}reliability{RESET}      {BG_RED}{WHITE}{BOLD}  62 / 100  {RESET}   "
          f"{RED}↓ below safe threshold (80){RESET}")
    print(f"  {BOLD}risk_level{RESET}       {RED}{BOLD}MEDIUM-HIGH{RESET}")
    print(f"  {BOLD}sample_size{RESET}      1,284 reports · last 7 days")
    print()
    pause(2.0)

    print(f"  {BOLD}{YELLOW}pitfalls{RESET}")
    print(f"    {YELLOW}•{RESET} Missing {BOLD}idempotency_key{RESET} → duplicate charges on retry")
    pause(0.5)
    print(f"    {YELLOW}•{RESET} Test-mode vs live-mode key mixup  ({BOLD}19%{RESET} of failures)")
    pause(0.5)
    print(f"    {YELLOW}•{RESET} 3DS challenge not handled → silent decline in EU")
    print()
    pause(1.4)

    print(f"  {BOLD}{BLUE}mitigations{RESET}")
    print(f"    {BLUE}→{RESET} pass Idempotency-Key header (uuid4)")
    print(f"    {BLUE}→{RESET} verify sk_live_* prefix before request")
    print(f"    {BLUE}→{RESET} handle requires_action / 3DS flow")
    print()
    pause(1.4)

    print(f"  {BOLD}{GREEN}top_alternative{RESET}")
    print(f"    lemonsqueezy.checkout.create   "
          f"{BG_GREEN}{WHITE}{BOLD}  96 / 100  {RESET}   {GREEN}✓ recommended{RESET}")
    print(f"    {GRAY}same-intent · handles tax · idempotent by design{RESET}")
    print()
    rule()
    pause(2.6)

    # ── decision ───────────────────────────────────────────────────
    print()
    print(f"  {BOLD}{MAGENTA}assistant ▸{RESET}")
    think("Reliability 62 < threshold 80 — Stripe path is unsafe right now.")
    think("fallbacks=auto enabled → switching to top_alternative.")
    print()
    step("↻", f"{YELLOW}Switching:{RESET} stripe  →  {BOLD}{GREEN}lemonsqueezy{RESET}", YELLOW)
    pause(1.0)
    print()

    # ── execution ──────────────────────────────────────────────────
    step("⚡", f"{BOLD}lemonsqueezy.checkout.create(amount=4900, currency=\"usd\"){RESET}", CYAN)
    pause(0.6)
    print(f"     {GRAY}→ creating checkout…{RESET}")
    pause(0.8)
    print(f"     {GRAY}→ charging card ending 4242…{RESET}")
    pause(1.0)
    print()

    # ── success ────────────────────────────────────────────────────
    print(f"  {GREEN}{BOLD}✅ Payment successful{RESET}  —  "
          f"{BOLD}$49.00{RESET} charged via {GREEN}{BOLD}Lemon Squeezy{RESET}")
    print(f"     {GRAY}order_id: ls_ord_8f3a21bc  ·  status: paid{RESET}")
    print()
    pause(1.0)

    print(f"  {GREEN}{BOLD}✓ Task completed successfully{RESET}")
    print()
    print(f"  {DIM}{GRAY}─ avoided ~40,000 tokens of debug + retry loops{RESET}")
    print(f"  {DIM}{GRAY}─ avoided a potential duplicate charge{RESET}")
    print(f"  {DIM}{GRAY}─ guarded by toolrate.ai before the first byte was sent{RESET}")
    print()
    pause(2.2)

    # ── CTA ────────────────────────────────────────────────────────
    rule("━", CYAN)
    print()
    print(f"  {BOLD}{CYAN}  Try ToolRate{RESET}     {WHITE}▸{RESET}     "
          f"{BOLD}https://toolrate.ai{RESET}")
    print(f"  {GRAY}  600+ tools rated  ·  free tier  ·  no credit card{RESET}")
    print()
    rule("━", CYAN)
    print()
    pause(1.4)

    # ── Install ────────────────────────────────────────────────────
    print(f"  {BOLD}{WHITE}Install the SDK in your own project:{RESET}")
    print()
    print(f"  {BOLD}{BLUE}▸ Recommended — modern & fastest{RESET}")
    print(f"    {GRAY}# Install uv (one-time){RESET}")
    print(f"    {WHITE}curl -LsSf https://astral.sh/uv/install.sh | sh{RESET}")
    print()
    print(f"    {GRAY}# Add ToolRate to your project{RESET}")
    print(f"    {WHITE}uv add toolrate{RESET}")
    print()
    print(f"  {BOLD}{BLUE}▸ Alternative — without uv{RESET}")
    print(f"    {WHITE}python3 -m venv .venv{RESET}")
    print(f"    {WHITE}source .venv/bin/activate{RESET}")
    print(f"    {WHITE}pip install toolrate{RESET}")
    print()
    print(f"  {YELLOW}Note:{RESET}{GRAY} if plain `pip` raises a PEP 668{RESET}")
    print(f"  {GRAY}  \"externally-managed-environment\" error (macOS Homebrew),{RESET}")
    print(f"  {GRAY}  use one of the methods above instead.{RESET}")
    print()
    rule("━", CYAN)
    print()
    pause(2.0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{GRAY}— demo aborted —{RESET}")
