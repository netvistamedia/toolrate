import { apiRequest, type RateLimitInfo } from "../client.js";
import { mcpError } from "../errors.js";
import type { RawAssessResponse } from "../schema.js";
import { makeSummary, type AssessSummary } from "../summary.js";
import { assessInputSchema, type AssessInput } from "../types.js";

export const name = "toolrate_assess";

export const config = {
  title: "Assess a tool's reliability before calling it",
  description: [
    "Get ToolRate's reliability score (0-100), pitfalls, mitigations, and the best alternatives for any third-party tool/API the agent is about to call.",
    "",
    "Guard pattern: call this BEFORE invoking the actual third-party tool. After the real call returns, call toolrate_report.",
    "",
    "For LLM provider selection, prefer toolrate_route_llm — it's a simpler interface that returns just the routing fields.",
    "",
    "Quota tip: assess once per tool per workflow, not per call. The API caches 5min server-side. Use toolrate_my_usage to check remaining quota.",
  ].join("\n"),
  inputSchema: assessInputSchema,
};

export async function handler(input: AssessInput) {
  try {
    const { body, rateLimit } = await apiRequest<RawAssessResponse>({
      method: "POST",
      path: "/v1/assess",
      body: {
        tool_identifier: input.tool_identifier,
        context: input.context,
        max_price_per_call: input.max_price_per_call,
        max_monthly_budget: input.max_monthly_budget,
        expected_calls_per_month: input.expected_calls_per_month,
        expected_tokens: input.expected_tokens,
        task_complexity: input.task_complexity,
        budget_strategy: input.budget_strategy,
        eu_only: input.eu_only,
        gdpr_required: input.gdpr_required,
      },
    });

    const trimmed = trimResponse(body, input.verbose === true);
    const summary = makeSummary(body);
    const result: TrimmedAssess = { summary, ...trimmed };
    if (rateLimit) result._meta = { rate_limit: rateLimit };

    return {
      content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }],
    };
  } catch (err) {
    return mcpError(err);
  }
}

interface TrimmedAssess {
  summary: AssessSummary;
  reliability_score: number;
  confidence: number;
  data_source: string;
  historical_success_rate: string;
  predicted_failure_risk: string;
  trend: { direction: string; change_24h: number | null } | null;
  common_pitfalls: Array<{ category: string; percentage: number; mitigation: string | null }>;
  recommended_mitigations: string[];
  top_alternatives: RawAssessResponse["top_alternatives"];
  latency: { p50: number | null; p95: number | null; p99: number | null } | null;
  hosting_jurisdiction: string | null;
  gdpr_compliant: boolean;
  data_residency_risk: string;
  price_per_call: number | null;
  pricing_model: string | null;
  cost_adjusted_score: number | null;
  estimated_monthly_cost: number | null;
  within_budget: boolean | null;
  budget_explanation: string | null;
  recommended_model: string | null;
  reasoning: string | null;
  last_updated: string;
  jurisdiction_source?: string | null;
  jurisdiction_confidence?: string | null;
  jurisdiction_notes?: string | null;
  recommended_for?: string[];
  eu_alternatives?: RawAssessResponse["eu_alternatives"];
  _meta?: { rate_limit: RateLimitInfo };
}

function trimResponse(a: RawAssessResponse, verbose: boolean): Omit<TrimmedAssess, "summary" | "_meta"> {
  const base: Omit<TrimmedAssess, "summary" | "_meta"> = {
    reliability_score: a.reliability_score,
    confidence: a.confidence,
    data_source: a.data_source,
    historical_success_rate: a.historical_success_rate,
    predicted_failure_risk: a.predicted_failure_risk,
    trend: a.trend ? { direction: a.trend.direction, change_24h: a.trend.change_24h } : null,
    common_pitfalls: (a.common_pitfalls ?? []).map((p) => ({
      category: p.category,
      percentage: p.percentage,
      mitigation: p.mitigation,
    })),
    recommended_mitigations: a.recommended_mitigations ?? [],
    top_alternatives: a.top_alternatives ?? [],
    latency: a.latency ? { p50: a.latency.p50, p95: a.latency.p95, p99: a.latency.p99 } : null,
    hosting_jurisdiction: a.hosting_jurisdiction,
    gdpr_compliant: a.gdpr_compliant,
    data_residency_risk: a.data_residency_risk,
    price_per_call: a.price_per_call,
    pricing_model: a.pricing_model,
    cost_adjusted_score: a.cost_adjusted_score,
    estimated_monthly_cost: a.estimated_monthly_cost,
    within_budget: a.within_budget,
    budget_explanation: a.budget_explanation,
    recommended_model: a.recommended_model,
    reasoning: a.reasoning,
    last_updated: a.last_updated,
  };

  if (verbose) {
    base.jurisdiction_source = a.jurisdiction_source;
    base.jurisdiction_confidence = a.jurisdiction_confidence;
    base.jurisdiction_notes = a.jurisdiction_notes;
    base.recommended_for = a.recommended_for ?? [];
    base.eu_alternatives = a.eu_alternatives ?? [];
  }

  return base;
}
