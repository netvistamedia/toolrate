"""
Load test for NemoFlow API.

Setup:
    pip install locust

Run against local:
    locust -f loadtest/locustfile.py --host http://localhost:8000

Run against production:
    locust -f loadtest/locustfile.py --host https://api.nemoflow.ai

Headless mode (10K users, ramp 500/s, run 2 min):
    locust -f loadtest/locustfile.py --host http://localhost:8000 \
        --headless -u 10000 -r 500 -t 2m --csv loadtest/results

Set your API key via environment variable:
    export NEMOFLOW_API_KEY=nf_live_...
"""
import os
import random

from locust import HttpUser, task, between


# Tool identifiers from the seed data
TOOL_IDENTIFIERS = [
    "https://api.stripe.com/v1/charges",
    "https://api.openai.com/v1/chat/completions",
    "https://api.github.com/repos",
    "https://api.twilio.com/2010-04-01/Accounts",
    "https://api.sendgrid.com/v3/mail/send",
    "https://api.slack.com/api/chat.postMessage",
    "https://api.aws.amazon.com/s3",
    "https://api.cloudflare.com/client/v4/zones",
    "https://api.resend.com/emails",
    "https://api.vercel.com/v9/deployments",
]

ERROR_CATEGORIES = [
    "timeout", "rate_limit", "auth_failure", "validation_error",
    "server_error", "connection_error",
]

CONTEXTS = [
    "e-commerce checkout", "customer support chatbot",
    "data pipeline", "ci/cd automation", "monitoring alert",
]


class NemoFlowAgent(HttpUser):
    """Simulates an AI agent querying NemoFlow before tool calls."""

    wait_time = between(0.1, 0.5)

    def on_start(self):
        api_key = os.environ.get("NEMOFLOW_API_KEY", "")
        self.headers = {"X-Api-Key": api_key} if api_key else {}

    @task(10)
    def assess_tool(self):
        """Most common call: check reliability before calling a tool."""
        self.client.post(
            "/v1/assess",
            json={
                "tool_identifier": random.choice(TOOL_IDENTIFIERS),
                "context": random.choice(CONTEXTS),
            },
            headers=self.headers,
        )

    @task(5)
    def report_success(self):
        """Report a successful tool execution."""
        self.client.post(
            "/v1/report",
            json={
                "tool_identifier": random.choice(TOOL_IDENTIFIERS),
                "success": True,
                "latency_ms": random.randint(50, 2000),
                "context": random.choice(CONTEXTS),
            },
            headers=self.headers,
        )

    @task(2)
    def report_failure(self):
        """Report a failed tool execution."""
        self.client.post(
            "/v1/report",
            json={
                "tool_identifier": random.choice(TOOL_IDENTIFIERS),
                "success": False,
                "error_category": random.choice(ERROR_CATEGORIES),
                "latency_ms": random.randint(5000, 30000),
                "context": random.choice(CONTEXTS),
            },
            headers=self.headers,
        )

    @task(3)
    def discover_hidden_gems(self):
        self.client.get("/v1/discover/hidden-gems", headers=self.headers)

    @task(2)
    def discover_fallback_chain(self):
        tool = random.choice(TOOL_IDENTIFIERS)
        self.client.get(
            f"/v1/discover/fallback-chain?tool_identifier={tool}",
            headers=self.headers,
        )

    @task(1)
    def get_stats(self):
        self.client.get("/v1/stats", headers=self.headers)

    @task(1)
    def health_check(self):
        self.client.get("/health")
