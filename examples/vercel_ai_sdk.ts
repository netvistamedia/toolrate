/**
 * ToolRate + Vercel AI SDK Integration Example
 * ==============================================
 * A TypeScript server that uses the Vercel AI SDK with ToolRate reliability
 * checks on every tool call. Demonstrates the assess -> execute -> report
 * loop and the guard() pattern for automatic fallback.
 *
 * Install:
 *   npm install toolrate ai @ai-sdk/openai zod
 *
 * Set environment variables:
 *   export TOOLRATE_API_KEY="nf_live_..."
 *   export OPENAI_API_KEY="sk-..."
 *
 * Run:
 *   npx tsx vercel_ai_sdk.ts
 */

import { generateText, tool } from "ai";
import { openai } from "@ai-sdk/openai";
import { z } from "zod";
import { ToolRate } from "toolrate";

// ---------------------------------------------------------------------------
// 1. Initialize ToolRate client
// ---------------------------------------------------------------------------

const client = new ToolRate(process.env.TOOLRATE_API_KEY ?? "nf_live_your_key_here");

// ---------------------------------------------------------------------------
// 2. Helper: wrap any async function with ToolRate assess -> execute -> report
//
// This is the core pattern. For every external tool call your agent makes:
//   a) Assess the tool's reliability score
//   b) Execute the call and measure latency
//   c) Report the outcome back to ToolRate
// ---------------------------------------------------------------------------

async function withToolRate<T>(
  toolIdentifier: string,
  fn: () => Promise<T>,
  context: string = "",
): Promise<T> {
  // ASSESS: Check reliability before calling
  const assessment = await nemo.assess({ toolIdentifier, context });
  console.log(
    `  [ToolRate] ${toolIdentifier}: reliability ${assessment.reliabilityScore}/100 ` +
      `(confidence: ${assessment.confidence})`,
  );

  if (assessment.commonPitfalls.length > 0) {
    console.log(`  [ToolRate] Pitfalls: ${assessment.commonPitfalls.join(", ")}`);
  }

  // EXECUTE: Call the tool and measure latency
  const start = performance.now();
  try {
    const result = await fn();
    const latencyMs = Math.round(performance.now() - start);

    // REPORT: Feed success data back
    await nemo.report({
      toolIdentifier,
      success: true,
      latencyMs,
      context,
    });

    return result;
  } catch (error) {
    const latencyMs = Math.round(performance.now() - start);

    // REPORT: Feed failure data back so other agents can learn
    await nemo.report({
      toolIdentifier,
      success: false,
      latencyMs,
      errorCategory: error instanceof Error && error.message.includes("timeout")
        ? "timeout"
        : "server_error",
      context,
    });

    throw error;
  }
}

// ---------------------------------------------------------------------------
// 3. Define Vercel AI SDK tools with ToolRate reliability checks
// ---------------------------------------------------------------------------

const searchTool = tool({
  description:
    "Search the web for current information. Each call is checked for " +
    "reliability by ToolRate and results are reported back.",
  parameters: z.object({
    query: z.string().describe("The search query"),
  }),
  execute: async ({ query }) => {
    // Using the guard() pattern for automatic fallback:
    // If the primary search API fails, ToolRate automatically tries the
    // fallback, reports both outcomes, and returns the first success.
    return nemo.guard<string>(
      "https://serpapi.com/search",
      async () => {
        // In production: call SerpAPI
        return `[SerpAPI] Top results for "${query}": Result 1, Result 2, Result 3`;
      },
      {
        context: "vercel-ai:search",
        minScore: 40,
        fallbacks: [
          {
            toolIdentifier: "https://api.tavily.com/search",
            fn: async () => {
              // In production: call Tavily
              return `[Tavily] Results for "${query}": Finding A, Finding B`;
            },
          },
        ],
      },
    );
  },
});

const weatherTool = tool({
  description:
    "Get the current weather for a city. Reliability is assessed " +
    "via ToolRate before each call.",
  parameters: z.object({
    city: z.string().describe("The city name"),
  }),
  execute: async ({ city }) => {
    // Using the manual assess -> execute -> report pattern
    // for full control over the flow
    return withToolRate(
      "https://api.openweathermap.org/data/2.5/weather",
      async () => {
        // In production: call OpenWeatherMap API
        return `Weather in ${city}: 22C, partly cloudy, humidity 65%`;
      },
      "vercel-ai:weather",
    );
  },
});

const stockTool = tool({
  description:
    "Get the current stock price for a ticker symbol. ToolRate checks " +
    "the API health before calling and reports latency afterward.",
  parameters: z.object({
    ticker: z.string().describe("The stock ticker symbol (e.g., AAPL)"),
  }),
  execute: async ({ ticker }) => {
    // Another guard() example with a quality gate:
    // If the primary API scores below 50, skip it and go straight to fallback
    return nemo.guard<string>(
      "https://api.polygon.io/v2/aggs/ticker",
      async () => {
        // In production: call Polygon.io
        return `[Polygon] ${ticker}: $185.42 (+1.2%)`;
      },
      {
        context: "vercel-ai:stocks",
        minScore: 50,
        fallbacks: [
          {
            toolIdentifier: "https://www.alphavantage.co/query",
            fn: async () => {
              // In production: call Alpha Vantage
              return `[AlphaVantage] ${ticker}: $185.40 (+1.2%)`;
            },
          },
        ],
      },
    );
  },
});

// ---------------------------------------------------------------------------
// 4. Run the agent
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  console.log("=== ToolRate + Vercel AI SDK ===\n");

  const { text, toolCalls, toolResults } = await generateText({
    model: openai("gpt-4o"),
    tools: {
      search: searchTool,
      weather: weatherTool,
      stock: stockTool,
    },
    maxSteps: 5,
    prompt:
      "What's the weather in San Francisco, the current AAPL stock price, " +
      "and the latest news about AI agents?",
  });

  console.log("\n--- Tool Calls Made ---");
  for (const call of toolCalls ?? []) {
    console.log(`  ${call.toolName}(${JSON.stringify(call.args)})`);
  }

  console.log("\n--- Tool Results ---");
  for (const result of toolResults ?? []) {
    console.log(`  ${result.toolName}: ${result.result}`);
  }

  console.log("\n--- Agent Response ---");
  console.log(text);

  // ---------------------------------------------------------------------------
  // 5. Post-run: Use ToolRate discovery to optimize tool selection
  // ---------------------------------------------------------------------------

  console.log("\n=== ToolRate Discovery Insights ===\n");

  // Find hidden gems: tools the community found reliable as fallbacks
  const gems = await nemo.discoverHiddenGems({ category: "search", limit: 3 });
  console.log("Hidden Gems (reliable fallback tools):");
  for (const gem of gems.hiddenGems) {
    console.log(
      `  ${gem.tool}: fallback success ${(gem.fallbackSuccessRate * 100).toFixed(0)}%, ` +
        `used ${gem.timesUsedAsFallback} times`,
    );
  }

  // Get fallback chain: what works best when Polygon fails
  const chain = await nemo.discoverFallbackChain("https://api.polygon.io/v2/aggs/ticker");
  console.log("\nFallback Chain for Polygon.io:");
  for (const alt of chain.fallbackChain) {
    console.log(
      `  -> ${alt.fallbackTool}: success ${(alt.successRate * 100).toFixed(0)}%, ` +
        `avg latency ${alt.avgLatencyMs ?? "N/A"}ms`,
    );
  }
}

main().catch(console.error);
