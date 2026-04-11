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
}

export interface ReportResponse {
  status: string;
  toolId: string;
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
