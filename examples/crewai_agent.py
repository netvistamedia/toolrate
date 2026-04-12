"""
ToolRate + CrewAI Integration Example
=======================================
A CrewAI crew with ToolRate acting as a quality gate for tool execution.
ToolRate checks tool reliability before each call, reports results back,
and automatically falls back to alternatives when tools are unreliable.

Install:
    pip install toolrate crewai crewai-tools

Set environment variables:
    export TOOLRATE_API_KEY="nf_live_..."
    export OPENAI_API_KEY="sk-..."

Run:
    python crewai_agent.py
"""

from __future__ import annotations

import os
import time
from typing import Any

from crewai import Agent, Crew, Process, Task
from crewai.tools import BaseTool
from pydantic import Field

from toolrate import ToolRate, guard

# ---------------------------------------------------------------------------
# 1. Initialize ToolRate client
# ---------------------------------------------------------------------------

nemo = ToolRate(os.environ.get("TOOLRATE_API_KEY", "nf_live_your_key_here"))


# ---------------------------------------------------------------------------
# 2. Create ToolRate-guarded CrewAI tools
#
# Each tool wraps the real API call with ToolRate's assess -> execute -> report
# loop. This gives the crew:
#   - Pre-flight reliability checks (skip unreliable tools)
#   - Automatic fallback to alternatives
#   - Latency and success reporting that helps all ToolRate users
# ---------------------------------------------------------------------------

class ToolRateSearchTool(BaseTool):
    """Web search with ToolRate reliability guard."""

    name: str = "web_search"
    description: str = (
        "Search the web for current information. Automatically checks tool "
        "reliability and falls back to alternative search providers if needed."
    )

    def _run(self, query: str) -> str:
        """Execute search with ToolRate guard for auto-fallback."""
        return guard(
            nemo,
            "https://serpapi.com/search",
            lambda: self._call_serpapi(query),
            context="crewai-crew:research",
            min_score=40,
            fallbacks=[
                (
                    "https://api.bing.microsoft.com/v7.0/search",
                    lambda: self._call_bing(query),
                ),
                (
                    "https://api.tavily.com/search",
                    lambda: self._call_tavily(query),
                ),
            ],
        )

    def _call_serpapi(self, query: str) -> str:
        # In production: call SerpAPI
        return f"[SerpAPI] Results for '{query}': Finding 1, Finding 2, Finding 3"

    def _call_bing(self, query: str) -> str:
        # In production: call Bing Search API
        return f"[Bing] Results for '{query}': Finding A, Finding B"

    def _call_tavily(self, query: str) -> str:
        # In production: call Tavily Search API
        return f"[Tavily] Results for '{query}': Finding X, Finding Y"


class ToolRateAPITool(BaseTool):
    """Generic API caller with manual ToolRate assess -> execute -> report."""

    name: str = "api_call"
    description: str = (
        "Make an API call to a specified endpoint. Checks reliability with "
        "ToolRate before calling and reports results afterward."
    )

    def _run(self, endpoint: str, method: str = "GET") -> str:
        """
        Demonstrates the manual assess -> execute -> report pattern,
        useful when you need full control over the flow.
        """
        context = "crewai-crew:api-call"

        # --- ASSESS: Check reliability before committing to the call ---
        try:
            assessment = nemo.assess(endpoint, context=context)
            score = assessment["reliability_score"]
            confidence = assessment["confidence"]
            risk = assessment["predicted_failure_risk"]

            print(f"\n  [ToolRate] {endpoint}")
            print(f"    Reliability: {score}/100 (confidence: {confidence})")
            print(f"    Failure risk: {risk}")

            if assessment.get("common_pitfalls"):
                # common_pitfalls is a list of dicts with category/percentage/
                # count/mitigation — join their category labels rather than the
                # dicts themselves.
                pitfall_labels = ", ".join(
                    p["category"] for p in assessment["common_pitfalls"]
                )
                print(f"    Pitfalls: {pitfall_labels}")

            if assessment.get("recommended_mitigations"):
                print(f"    Mitigations: {', '.join(assessment['recommended_mitigations'])}")

            # Quality gate: refuse to call extremely unreliable tools
            if score < 20:
                nemo.report(endpoint, success=False,
                            error_category="skipped_low_score", context=context)
                return (f"Skipped {endpoint} -- reliability score {score}/100 is too low. "
                        f"Pitfalls: {assessment.get('common_pitfalls', [])}")

        except Exception as e:
            print(f"  [ToolRate] Could not assess {endpoint}: {e}")

        # --- EXECUTE: Make the actual API call ---
        start = time.perf_counter()
        try:
            # In production: make the real HTTP request
            result = f"Response from {method} {endpoint}: {{\"status\": \"ok\", \"data\": [...]}}"
            latency_ms = int((time.perf_counter() - start) * 1000)

            # --- REPORT: Feed success data back to the community ---
            nemo.report(endpoint, success=True, latency_ms=latency_ms, context=context)
            return result

        except Exception as e:
            latency_ms = int((time.perf_counter() - start) * 1000)

            # --- REPORT: Feed failure data back so others can avoid pitfalls ---
            nemo.report(endpoint, success=False, latency_ms=latency_ms,
                        error_category="server_error", context=context)
            return f"API call to {endpoint} failed: {e}"


# ---------------------------------------------------------------------------
# 3. Define CrewAI agents
# ---------------------------------------------------------------------------

researcher = Agent(
    role="Senior Research Analyst",
    goal="Find comprehensive, accurate information on the given topic",
    backstory=(
        "You are an expert researcher who always verifies information from "
        "multiple sources. You rely on ToolRate-guarded tools to ensure the "
        "APIs you call are reliable before spending time on them."
    ),
    tools=[ToolRateSearchTool(), ToolRateAPITool()],
    verbose=True,
)

writer = Agent(
    role="Technical Writer",
    goal="Create a clear, well-structured summary of the research findings",
    backstory=(
        "You take research findings and turn them into concise, actionable "
        "summaries. You focus on accuracy and clarity."
    ),
    verbose=True,
)


# ---------------------------------------------------------------------------
# 4. Define tasks
# ---------------------------------------------------------------------------

research_task = Task(
    description=(
        "Research the current state of AI agent reliability. "
        "Use the web_search tool to find recent information. "
        "Use the api_call tool to check https://api.github.com/repos/langchain-ai/langchain "
        "for the latest activity. "
        "Gather at least 3 key findings."
    ),
    expected_output="A list of key findings about AI agent reliability with sources.",
    agent=researcher,
)

writing_task = Task(
    description=(
        "Based on the research findings, write a brief executive summary "
        "(3-5 paragraphs) about the state of AI agent reliability. "
        "Include specific data points where available."
    ),
    expected_output="A well-written executive summary with key insights.",
    agent=writer,
)


# ---------------------------------------------------------------------------
# 5. Assemble and run the crew
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== ToolRate + CrewAI Integration ===\n")

    crew = Crew(
        agents=[researcher, writer],
        tasks=[research_task, writing_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    print("\n" + "=" * 60)
    print("CREW OUTPUT:")
    print("=" * 60)
    print(result)

    # ---------------------------------------------------------------------------
    # 6. Post-run: Use ToolRate discovery to improve future runs
    # ---------------------------------------------------------------------------

    print("\n=== Post-Run: ToolRate Discovery Insights ===\n")

    # Find hidden gems -- tools other agents found reliable as fallbacks.
    # The API returns success rates as 0-100 percentages, so format directly.
    print("Hidden Gems (tools that work great as fallbacks):")
    gems = nemo.discover_hidden_gems(category="search", limit=5)
    for gem in gems.get("hidden_gems", []):
        print(f"  {gem['tool']}: "
              f"fallback success {gem['fallback_success_rate']:.1f}%, "
              f"used {gem['times_used_as_fallback']} times")

    # Get fallback chain -- what to try when SerpAPI fails
    print("\nFallback Chain for SerpAPI:")
    chain = nemo.discover_fallback_chain("https://serpapi.com/search", limit=3)
    for alt in chain.get("fallback_chain", []):
        print(f"  -> {alt['fallback_tool']}: "
              f"success {alt['success_rate']:.1f}%, "
              f"avg latency {alt.get('avg_latency_ms', 'N/A')}ms")

    nemo.close()


if __name__ == "__main__":
    main()
