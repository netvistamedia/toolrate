import { z } from "zod";

const TASK_COMPLEXITY = ["low", "medium", "high", "very_high"] as const;
const BUDGET_STRATEGY = [
  "reliability_first",
  "balanced",
  "cost_first",
  "speed_first",
] as const;
const ERROR_CATEGORY = [
  "timeout",
  "rate_limit",
  "auth_failure",
  "validation_error",
  "server_error",
  "connection_error",
  "not_found",
  "permission_denied",
] as const;

export const assessInputSchema = {
  tool_identifier: z
    .string()
    .min(1)
    .max(512)
    .describe("URL or canonical name of the tool to assess. Examples: 'https://api.stripe.com/v1/charges', 'sendgrid'."),
  context: z
    .string()
    .max(1024)
    .optional()
    .describe("Workflow context for context-bucketed scoring, e.g. 'high-value payment processing'."),
  max_price_per_call: z
    .number()
    .nonnegative()
    .optional()
    .describe("USD cap per call. Tools above are flagged within_budget=false (not filtered)."),
  max_monthly_budget: z
    .number()
    .nonnegative()
    .optional()
    .describe("Max USD spend per month. Combines with expected_calls_per_month for the budget check."),
  expected_calls_per_month: z
    .number()
    .int()
    .nonnegative()
    .max(100_000_000)
    .optional()
    .describe("Expected call volume. Drives estimated_monthly_cost."),
  expected_tokens: z
    .number()
    .int()
    .nonnegative()
    .max(1_000_000)
    .optional()
    .describe("Total tokens (input+output) per LLM call. Triggers exact per-token math for LLM providers."),
  task_complexity: z
    .enum(TASK_COMPLEXITY)
    .optional()
    .describe("Task complexity hint for LLM model picker. low=Haiku/mini, very_high=Opus/4o."),
  budget_strategy: z
    .enum(BUDGET_STRATEGY)
    .optional()
    .describe("How to weigh reliability vs cost vs latency. Default: reliability_first (80/20)."),
  eu_only: z.boolean().optional().describe("Filter alternatives to EU-hosted only."),
  gdpr_required: z.boolean().optional().describe("Filter alternatives to GDPR-adequate jurisdictions."),
  verbose: z
    .boolean()
    .optional()
    .describe("Include extra fields (jurisdiction details, eu_alternatives, recommended_for) in the response."),
};

export const reportInputSchema = {
  tool_identifier: z.string().min(1).max(512).describe("Tool identifier that was called."),
  success: z.boolean().describe("Whether the call succeeded."),
  error_category: z
    .enum(ERROR_CATEGORY)
    .optional()
    .describe("Failure category. Required when success=false to be useful."),
  latency_ms: z
    .number()
    .int()
    .min(1)
    .max(300_000)
    .optional()
    .describe("How long the call took in milliseconds."),
  context: z.string().max(1024).optional().describe("Workflow context, hashed for privacy."),
  session_id: z
    .string()
    .max(64)
    .optional()
    .describe("UUID grouping related calls in one workflow (for journey analytics)."),
  attempt_number: z
    .number()
    .int()
    .min(1)
    .max(20)
    .optional()
    .describe("Which attempt this was. 1 = first try, 2 = first fallback, etc."),
  previous_tool: z
    .string()
    .max(512)
    .optional()
    .describe("Tool identifier that was tried before this one (for fallback chains)."),
};

export const routeLlmInputSchema = {
  task_description: z
    .string()
    .min(1)
    .max(2048)
    .describe("One-sentence description of what the LLM needs to do. Used as scoring context."),
  expected_tokens: z
    .number()
    .int()
    .positive()
    .max(1_000_000)
    .describe("Total tokens (input+output) per call. Required — drives the cost math."),
  task_complexity: z
    .enum(TASK_COMPLEXITY)
    .optional()
    .describe("low=Haiku/mini, medium=Sonnet/4o-mini, high=Sonnet/4o, very_high=Opus/4o-large."),
  max_price_per_call: z.number().nonnegative().optional(),
  max_monthly_budget: z.number().nonnegative().optional(),
  expected_calls_per_month: z.number().int().nonnegative().max(100_000_000).optional(),
  budget_strategy: z
    .enum(BUDGET_STRATEGY)
    .optional()
    .describe("Default: reliability_first. Use cost_first to minimize spend, speed_first for low latency."),
  provider: z
    .enum([
      "anthropic",
      "openai",
      "groq",
      "together",
      "mistral",
      "deepseek",
      "ollama",
    ])
    .optional()
    .describe("Restrict to one provider. Omit to compare all 7 and pick the best."),
};

export const fallbackChainInputSchema = {
  tool_identifier: z.string().min(1).max(512).describe("The tool to find fallbacks for."),
  limit: z.number().int().min(1).max(20).optional().describe("Max results (default 5)."),
};

export const hiddenGemsInputSchema = {
  category: z
    .string()
    .max(128)
    .optional()
    .describe("Filter by category (e.g. 'LLM APIs', 'Payment APIs'). Use toolrate_categories to list."),
  limit: z.number().int().min(1).max(50).optional().describe("Max results (default 10)."),
};

export const searchToolsInputSchema = {
  q: z.string().max(256).optional().describe("Search by tool name or identifier (case-insensitive substring)."),
  category: z.string().max(128).optional().describe("Filter by category."),
  limit: z.number().int().min(1).max(200).optional().describe("Max results (default 50)."),
  offset: z.number().int().min(0).max(10_000).optional().describe("Pagination offset."),
};

export const categoriesInputSchema = {};

export const myUsageInputSchema = {};

export const registerInputSchema = {
  email: z.string().email().describe("Your email — used for the API key, not for marketing."),
};

export type AssessInput = {
  tool_identifier: string;
  context?: string;
  max_price_per_call?: number;
  max_monthly_budget?: number;
  expected_calls_per_month?: number;
  expected_tokens?: number;
  task_complexity?: (typeof TASK_COMPLEXITY)[number];
  budget_strategy?: (typeof BUDGET_STRATEGY)[number];
  eu_only?: boolean;
  gdpr_required?: boolean;
  verbose?: boolean;
};

export type ReportInput = {
  tool_identifier: string;
  success: boolean;
  error_category?: (typeof ERROR_CATEGORY)[number];
  latency_ms?: number;
  context?: string;
  session_id?: string;
  attempt_number?: number;
  previous_tool?: string;
};

export type RouteLlmInput = {
  task_description: string;
  expected_tokens: number;
  task_complexity?: (typeof TASK_COMPLEXITY)[number];
  max_price_per_call?: number;
  max_monthly_budget?: number;
  expected_calls_per_month?: number;
  budget_strategy?: (typeof BUDGET_STRATEGY)[number];
  provider?:
    | "anthropic"
    | "openai"
    | "groq"
    | "together"
    | "mistral"
    | "deepseek"
    | "ollama";
};

export type FallbackChainInput = { tool_identifier: string; limit?: number };
export type HiddenGemsInput = { category?: string; limit?: number };
export type SearchToolsInput = { q?: string; category?: string; limit?: number; offset?: number };
export type RegisterInput = { email: string };
