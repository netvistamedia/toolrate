/** Options for configuring the NemoFlow client. */
export interface NemoFlowOptions {
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

export interface AssessResponse {
  reliabilityScore: number;
  confidence: number;
  historicalSuccessRate: string;
  predictedFailureRisk: string;
  commonPitfalls: string[];
  recommendedMitigations: string[];
  topAlternatives: AlternativeTool[];
  estimatedLatencyMs: number;
  lastUpdated: string;
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

// ── Guard ───────────────────────────────────────────────────────────

export interface GuardOptions<T> {
  /** Workflow context for context-bucketed scoring. */
  context?: string;
  /** Minimum reliability score to proceed (0-100). Default 0 = always try. */
  minScore?: number;
  /** Fallback tools to try on failure, in order. */
  fallbacks?: Array<{ toolIdentifier: string; fn: () => Promise<T> }>;
}

// ── Errors ──────────────────────────────────────────────────────────

export class NemoFlowError extends Error {
  public readonly status: number;
  public readonly body: unknown;

  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "NemoFlowError";
    this.status = status;
    this.body = body;
  }
}
