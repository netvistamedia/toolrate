/**
 * Raw snake_case shapes returned by the ToolRate REST API. Mirrors
 * app/schemas/assess.py and app/schemas/report.py — kept in sync by hand.
 *
 * Defining these in the MCP server (rather than reusing the published `toolrate`
 * SDK's camelCase types) lets us pass responses straight through to agents in
 * the snake_case the docs use, and surfaces fields the SDK strips during its
 * camelCase mapping (jurisdiction, GDPR, eu_alternatives, recommended_for).
 */

export interface RawAssessResponse {
  reliability_score: number;
  confidence: number;
  data_source: "empirical" | "llm_estimated" | "bayesian_prior";
  historical_success_rate: string;
  predicted_failure_risk: string;
  trend: {
    direction: "improving" | "stable" | "degrading";
    score_24h: number | null;
    score_7d: number | null;
    change_24h: number | null;
  } | null;
  common_pitfalls: Array<{
    category: string;
    percentage: number;
    count: number;
    mitigation: string | null;
  }>;
  recommended_mitigations: string[];
  top_alternatives: Array<{
    tool: string;
    score: number;
    reason: string;
    price_per_call?: number | null;
    within_budget?: boolean | null;
  }>;
  estimated_latency_ms: number | null;
  latency: {
    avg: number | null;
    p50: number | null;
    p95: number | null;
    p99: number | null;
  } | null;
  last_updated: string;
  hosting_jurisdiction: string | null;
  gdpr_compliant: boolean;
  data_residency_risk: string;
  jurisdiction_source: string | null;
  jurisdiction_confidence: string | null;
  jurisdiction_notes: string | null;
  recommended_for: string[];
  eu_alternatives: Array<{
    tool: string;
    score: number;
    reason: string;
    price_per_call?: number | null;
    within_budget?: boolean | null;
  }>;
  price_per_call: number | null;
  pricing_model: string | null;
  cost_adjusted_score: number | null;
  estimated_monthly_cost: number | null;
  within_budget: boolean | null;
  budget_explanation: string | null;
  recommended_model: string | null;
  reasoning: string | null;
}

export interface RawReportResponse {
  status: string;
  tool_id: string;
}

export interface RawHiddenGemsResponse {
  hidden_gems: Array<{
    tool: string;
    display_name: string;
    category: string;
    fallback_success_rate: number;
    times_used_as_fallback: number;
    avg_latency_ms: number | null;
  }>;
  count: number;
}

export interface RawFallbackChainResponse {
  tool: string;
  fallback_chain: Array<{
    fallback_tool: string;
    display_name: string;
    times_chosen_after_failure: number;
    success_rate: number;
    avg_latency_ms: number | null;
  }>;
  count: number;
}

export interface RawToolsResponse {
  tools: Array<{
    identifier: string;
    display_name: string | null;
    category: string | null;
    report_count: number;
    first_seen_at: string | null;
  }>;
  total: number;
  offset: number;
  limit: number;
}

export interface RawCategoriesResponse {
  categories: Array<{ name: string; tool_count: number }>;
  total: number;
}

export interface RawPersonalStats {
  key_prefix: string;
  tier: string;
  billing_period: "daily" | "monthly";
  limit: number;
  used: number;
  remaining: number;
  daily_limit: number;
  daily_used: number;
  daily_remaining: number;
  created_at: string | null;
}

export interface RawRegisterResponse {
  api_key: string;
  tier: string;
  daily_limit: number;
  message: string;
  docs_url: string;
  quickstart: string;
}
