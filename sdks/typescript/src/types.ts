/** Options for configuring the ToolRate client. */
export interface ToolRateOptions {
  /** Override the default API base URL. */
  baseUrl?: string;
}

// ── Assess ──────────────────────────────────────────────────────────

export interface AssessParams {
  toolIdentifier: string;
  context?: string;
  samplePayload?: Record<string, unknown>;
}

export interface AlternativeTool {
  tool: string;
  score: number;
  reason: string;
}

export interface PitfallDetail {
  category: string;
  percentage: number;
  count: number;
  mitigation: string | null;
}

export interface TrendInfo {
  direction: "improving" | "stable" | "degrading";
  score24h: number | null;
  score7d: number | null;
  change24h: number | null;
}

export interface LatencyInfo {
  avg: number | null;
  p50: number | null;
  p95: number | null;
  p99: number | null;
}

export interface AssessResponse {
  reliabilityScore: number;
  confidence: number;
  dataSource: "empirical" | "llm_estimated" | "bayesian_prior";
  historicalSuccessRate: string;
  predictedFailureRisk: string;
  trend: TrendInfo | null;
  commonPitfalls: PitfallDetail[];
  recommendedMitigations: string[];
  topAlternatives: AlternativeTool[];
  estimatedLatencyMs: number | null;
  latency: LatencyInfo | null;
  lastUpdated: string;
}

// ── Batch Assess ────────────────────────────────────────────────────

export interface BatchAssessItem {
  toolIdentifier: string;
  context?: string;
}

export interface BatchAssessResponse {
  assessments: Array<{
    toolIdentifier: string;
    result?: AssessResponse;
    error?: string;
  }>;
  count: number;
}

// ── Report ──────────────────────────────────────────────────────────

export interface ReportParams {
  toolIdentifier: string;
  success: boolean;
  errorCategory?: string;
  latencyMs?: number;
  context?: string;
  /** Groups related tool calls in the same workflow. */
  sessionId?: string;
  /** Which attempt is this? 1 = first try, 2 = fallback, etc. */
  attemptNumber?: number;
  /** Tool identifier that was tried before this one. */
  previousTool?: string;
}

export interface ReportResponse {
  status: string;
  toolId: string;
}

// ── Discovery ───────────────────────────────────────────────────────

export interface HiddenGem {
  tool: string;
  displayName: string;
  category: string;
  fallbackSuccessRate: number;
  timesUsedAsFallback: number;
  avgLatencyMs: number | null;
}

export interface HiddenGemsResponse {
  hiddenGems: HiddenGem[];
  count: number;
}

export interface FallbackTool {
  fallbackTool: string;
  displayName: string;
  timesChosenAfterFailure: number;
  successRate: number;
  avgLatencyMs: number | null;
}

export interface FallbackChainResponse {
  tool: string;
  fallbackChain: FallbackTool[];
  count: number;
}

// ── Tools ───────────────────────────────────────────────────────────

export interface ToolItem {
  identifier: string;
  displayName: string | null;
  category: string | null;
  reportCount: number;
  firstSeenAt: string | null;
}

export interface ToolsResponse {
  tools: ToolItem[];
  total: number;
  offset: number;
  limit: number;
}

export interface CategoryItem {
  name: string;
  toolCount: number;
}

export interface CategoriesResponse {
  categories: CategoryItem[];
  total: number;
}

// ── Stats ───────────────────────────────────────────────────────────

export interface PlatformStats {
  totalTools: number;
  totalReports: number;
  [key: string]: unknown;
}

export interface PersonalStats {
  tier: string;
  dailyLimit: number;
  [key: string]: unknown;
}

// ── Webhooks ────────────────────────────────────────────────────────

export interface WebhookResponse {
  id: string;
  url: string;
  event: string;
  toolIdentifier: string | null;
  threshold: number;
  secret?: string;
  isActive: boolean;
}

export interface WebhookListResponse {
  webhooks: WebhookResponse[];
  count: number;
}

// ── Account ─────────────────────────────────────────────────────────

export interface RotateKeyResponse {
  newApiKey: string;
  oldKeyPrefix: string;
  tier: string;
  dailyLimit: number;
}

// ── Guard ───────────────────────────────────────────────────────────

export interface GuardOptions<T> {
  /** Workflow context for context-bucketed scoring. */
  context?: string;
  /** Minimum reliability score to proceed (0-100). Default 0 = always try. */
  minScore?: number;
  /**
   * Fallback tools to try on failure, in order.
   * Pass an explicit array, or `"auto"` to have ToolRate pick fallbacks
   * dynamically from the primary tool's top alternatives and fallback-chain
   * data. `"auto"` requires `resolvers`.
   */
  fallbacks?: Array<{ toolIdentifier: string; fn: () => Promise<T> }> | "auto";
  /**
   * Mapping of tool identifier → runner. When `fallbacks="auto"`, ToolRate
   * matches candidate alternatives against these keys and only tries tools
   * the caller has pre-registered a runner for.
   */
  resolvers?: Record<string, () => Promise<T>>;
  /** Max number of auto fallbacks to include (default 3). */
  maxFallbacks?: number;
}

// ── Errors ──────────────────────────────────────────────────────────

export class ToolRateError extends Error {
  public readonly status: number;
  public readonly body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ToolRateError";
    this.status = status;
    this.body = body;
  }
}
