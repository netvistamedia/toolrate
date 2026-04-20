import { apiRequest, type RateLimitInfo } from "../client.js";
import { mcpError } from "../errors.js";
import type { RawAssessResponse } from "../schema.js";
import { routeLlmInputSchema, type RouteLlmInput } from "../types.js";

export const name = "toolrate_route_llm";

export const config = {
  title: "Route an LLM task to the best provider+model under your budget",
  description: [
    "Pick the most cost-effective LLM provider+model for a task given expected token volume, complexity, and budget caps.",
    "",
    "Considers all 7 supported providers (Anthropic, OpenAI, Groq, Together, Mistral, DeepSeek, Ollama) by default. Pass `provider` to restrict to one.",
    "",
    "Returns a flat decision object: { recommended_provider, recommended_model, cost_adjusted_score, estimated_monthly_cost, within_budget, reasoning, alternatives[] }. Use this instead of toolrate_assess when picking a model.",
    "",
    "Costs 1 ToolRate quota call per provider considered (so up to 7 by default). Use the `provider` arg to limit, or call once per workflow and reuse the result.",
  ].join("\n"),
  inputSchema: routeLlmInputSchema,
};

interface ProviderEntry {
  key: string;
  identifier: string;
  display: string;
}

const PROVIDERS: ProviderEntry[] = [
  { key: "anthropic", identifier: "https://api.anthropic.com/v1/messages", display: "Anthropic" },
  { key: "openai", identifier: "https://api.openai.com/v1/chat/completions", display: "OpenAI" },
  { key: "groq", identifier: "https://api.groq.com/openai/v1/chat/completions", display: "Groq" },
  { key: "together", identifier: "https://api.together.xyz/v1/chat/completions", display: "Together" },
  { key: "mistral", identifier: "https://api.mistral.ai/v1/chat/completions", display: "Mistral" },
  { key: "deepseek", identifier: "https://api.deepseek.com/v1/chat/completions", display: "DeepSeek" },
  { key: "ollama", identifier: "http://localhost:11434/api/chat", display: "Ollama (local)" },
];

interface RouteResult {
  recommended_provider: string;
  recommended_model: string | null;
  cost_adjusted_score: number | null;
  reliability_score: number;
  estimated_monthly_cost: number | null;
  within_budget: boolean | null;
  budget_explanation: string | null;
  reasoning: string | null;
  alternatives: Array<{
    provider: string;
    recommended_model: string | null;
    cost_adjusted_score: number | null;
    reliability_score: number;
    estimated_monthly_cost: number | null;
    within_budget: boolean | null;
  }>;
  _meta?: { rate_limit: RateLimitInfo; providers_assessed: number };
}

export async function handler(input: RouteLlmInput) {
  try {
    const targets = input.provider
      ? PROVIDERS.filter((p) => p.key === input.provider)
      : PROVIDERS;

    if (targets.length === 0) {
      return mcpError(new Error(`Unknown provider '${input.provider}'.`));
    }

    const taskComplexity = input.task_complexity ?? "medium";
    const budgetStrategy = input.budget_strategy ?? "reliability_first";

    const settled = await Promise.allSettled(
      targets.map((p) =>
        apiRequest<RawAssessResponse>({
          method: "POST",
          path: "/v1/assess",
          body: {
            tool_identifier: p.identifier,
            context: input.task_description,
            expected_tokens: input.expected_tokens,
            task_complexity: taskComplexity,
            budget_strategy: budgetStrategy,
            max_price_per_call: input.max_price_per_call,
            max_monthly_budget: input.max_monthly_budget,
            expected_calls_per_month: input.expected_calls_per_month,
          },
        }).then((r) => ({ provider: p, ...r })),
      ),
    );

    const successes = settled
      .filter(
        (s): s is PromiseFulfilledResult<{ provider: ProviderEntry; body: RawAssessResponse; rateLimit: RateLimitInfo | null }> =>
          s.status === "fulfilled",
      )
      .map((s) => s.value);

    if (successes.length === 0) {
      const firstReason = settled[0].status === "rejected" ? settled[0].reason : new Error("All provider assessments failed");
      return mcpError(firstReason);
    }

    const ranked = [...successes].sort((a, b) => {
      const costScoreA = a.body.cost_adjusted_score ?? a.body.reliability_score;
      const costScoreB = b.body.cost_adjusted_score ?? b.body.reliability_score;
      const aOver = a.body.within_budget === false;
      const bOver = b.body.within_budget === false;
      if (aOver !== bOver) return aOver ? 1 : -1;
      return costScoreB - costScoreA;
    });

    const winner = ranked[0];
    const lastRateLimit = successes[successes.length - 1]?.rateLimit ?? null;

    const result: RouteResult = {
      recommended_provider: winner.provider.display,
      recommended_model: winner.body.recommended_model,
      cost_adjusted_score: winner.body.cost_adjusted_score,
      reliability_score: winner.body.reliability_score,
      estimated_monthly_cost: winner.body.estimated_monthly_cost,
      within_budget: winner.body.within_budget,
      budget_explanation: winner.body.budget_explanation,
      reasoning: winner.body.reasoning,
      alternatives: ranked.slice(1).map((r) => ({
        provider: r.provider.display,
        recommended_model: r.body.recommended_model,
        cost_adjusted_score: r.body.cost_adjusted_score,
        reliability_score: r.body.reliability_score,
        estimated_monthly_cost: r.body.estimated_monthly_cost,
        within_budget: r.body.within_budget,
      })),
    };

    if (lastRateLimit) {
      result._meta = { rate_limit: lastRateLimit, providers_assessed: successes.length };
    }

    return {
      content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }],
    };
  } catch (err) {
    return mcpError(err);
  }
}
