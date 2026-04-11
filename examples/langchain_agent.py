"""
NemoFlow + LangChain Integration Example
=========================================
An agent that uses NemoFlow to check tool reliability before calling tools,
and reports outcomes back to build community intelligence.

Install:
    pip install nemoflow langchain langchain-openai langchain-community

Set environment variables:
    export NEMOFLOW_API_KEY="nf_live_..."
    export OPENAI_API_KEY="sk-..."

Run:
    python langchain_agent.py
"""

from __future__ import annotations

import os
import time
from typing import Any

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from nemoflow import NemoFlowClient, guard

# ---------------------------------------------------------------------------
# 1. Initialize NemoFlow client
# ---------------------------------------------------------------------------

nemo = NemoFlowClient(os.environ.get("NEMOFLOW_API_KEY", "nf_live_your_key_here"))


# ---------------------------------------------------------------------------
# 2. Define your raw tool functions (the actual API calls)
# ---------------------------------------------------------------------------

def _search_web(query: str) -> str:
    """Simulate a web search API call."""
    # In production this would call a real search API
    return f"Top results for '{query}': [Result 1, Result 2, Result 3]"


def _search_web_fallback(query: str) -> str:
    """Simulate a fallback search API call (e.g. Bing instead of Google)."""
    return f"Fallback results for '{query}': [Alt Result 1, Alt Result 2]"


def _get_weather(city: str) -> str:
    """Simulate a weather API call."""
    return f"Weather in {city}: 22C, partly cloudy"


# ---------------------------------------------------------------------------
# 3. Wrap tools with NemoFlow reliability guard
#
# The key pattern: instead of calling the API directly, we wrap each tool
# so that NemoFlow:
#   a) Checks reliability score before executing
#   b) Executes the call
#   c) Reports success/failure + latency back to the platform
#   d) Automatically falls back to alternatives if the primary tool fails
# ---------------------------------------------------------------------------

def nemoflow_search(query: str) -> str:
    """Web search with NemoFlow reliability guard and automatic fallback."""
    return guard(
        nemo,
        "https://serpapi.com/search",                       # primary tool
        lambda: _search_web(query),                          # primary call
        context="langchain-agent:web-search",                # workflow context
        min_score=50,                                        # skip if score < 50
        fallbacks=[
            (
                "https://api.bing.microsoft.com/v7.0/search", # fallback tool
                lambda: _search_web_fallback(query),          # fallback call
            ),
        ],
    )


def nemoflow_weather(city: str) -> str:
    """Weather lookup with NemoFlow assess -> execute -> report loop."""
    tool_url = "https://api.openweathermap.org/data/2.5/weather"

    # Step 1: Assess -- check the tool's current reliability
    assessment = nemo.assess(tool_url, context="langchain-agent:weather")
    print(f"  [NemoFlow] Weather API reliability: {assessment['reliability_score']}/100 "
          f"(confidence: {assessment['confidence']})")

    if assessment.get("common_pitfalls"):
        print(f"  [NemoFlow] Watch out for: {assessment['common_pitfalls']}")

    # Step 2: Execute -- call the tool and measure latency
    start = time.perf_counter()
    try:
        result = _get_weather(city)
        latency_ms = int((time.perf_counter() - start) * 1000)

        # Step 3: Report success -- feed data back to the community
        nemo.report(tool_url, success=True, latency_ms=latency_ms,
                     context="langchain-agent:weather")
        return result

    except Exception as e:
        latency_ms = int((time.perf_counter() - start) * 1000)

        # Step 3 (failure): Report the failure so other agents learn too
        nemo.report(tool_url, success=False, latency_ms=latency_ms,
                     error_category="server_error",
                     context="langchain-agent:weather")
        return f"Weather API failed: {e}"


# ---------------------------------------------------------------------------
# 4. Create LangChain tools from the NemoFlow-wrapped functions
# ---------------------------------------------------------------------------

search_tool = StructuredTool.from_function(
    func=nemoflow_search,
    name="web_search",
    description="Search the web for current information. Includes automatic "
                "fallback to alternative search engines via NemoFlow.",
)

weather_tool = StructuredTool.from_function(
    func=nemoflow_weather,
    name="weather",
    description="Get current weather for a city. Reliability is checked via "
                "NemoFlow before each call.",
)

# ---------------------------------------------------------------------------
# 5. Build the LangChain agent
# ---------------------------------------------------------------------------

llm = ChatOpenAI(model="gpt-4o", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful assistant with access to web search and weather tools. "
     "Use them when the user asks for current information. Each tool call is "
     "automatically checked for reliability by NemoFlow."),
    MessagesPlaceholder("chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

agent = create_openai_tools_agent(llm, [search_tool, weather_tool], prompt)
executor = AgentExecutor(agent=agent, tools=[search_tool, weather_tool], verbose=True)


# ---------------------------------------------------------------------------
# 6. Run the agent
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== NemoFlow + LangChain Agent ===\n")

    # Example 1: Weather query (assess -> execute -> report)
    result = executor.invoke({"input": "What's the weather like in Amsterdam?"})
    print(f"\nAgent: {result['output']}\n")

    # Example 2: Search query (guard with auto-fallback)
    result = executor.invoke({"input": "Search for the latest AI research papers"})
    print(f"\nAgent: {result['output']}\n")

    # Bonus: Discover hidden gem tools for search category
    print("=== Discovering Hidden Gems ===")
    gems = nemo.discover_hidden_gems(category="search", limit=3)
    for gem in gems.get("hidden_gems", []):
        print(f"  - {gem['tool']}: fallback success rate {gem['fallback_success_rate']:.0%}")

    # Bonus: Get fallback chain for a tool
    print("\n=== Fallback Chain for SerpAPI ===")
    chain = nemo.discover_fallback_chain("https://serpapi.com/search")
    for alt in chain.get("fallback_chain", []):
        print(f"  - {alt['fallback_tool']}: success rate {alt['success_rate']:.0%}")

    nemo.close()


if __name__ == "__main__":
    main()
