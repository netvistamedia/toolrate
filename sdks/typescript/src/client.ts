import {
  type NemoFlowOptions,
  type AssessParams,
  type AssessResponse,
  type ReportParams,
  type ReportResponse,
  NemoFlowError,
} from "./types.js";

const DEFAULT_BASE_URL = "https://api.nemoflow.ai";

export class NemoFlow {
  private readonly apiKey: string;
  private readonly baseUrl: string;

  constructor(apiKey: string, options?: NemoFlowOptions) {
    if (!apiKey) {
      throw new Error("An API key is required to create a NemoFlow client.");
    }
    this.apiKey = apiKey;
    this.baseUrl = (options?.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
  }

  // ── Public methods ──────────────────────────────────────────────

  /** Assess a tool's reliability and get recommendations. */
  async assess(params: AssessParams): Promise<AssessResponse> {
    const raw = await this.request<RawAssessResponse>("/v1/assess", {
      tool_identifier: params.toolIdentifier,
      context: params.context,
      sample_payload: params.samplePayload,
    });

    return {
      reliabilityScore: raw.reliability_score,
      confidence: raw.confidence,
      historicalSuccessRate: raw.historical_success_rate,
      predictedFailureRisk: raw.predicted_failure_risk,
      commonPitfalls: raw.common_pitfalls,
      recommendedMitigations: raw.recommended_mitigations,
      topAlternatives: raw.top_alternatives.map((a) => ({
        tool: a.tool,
        score: a.score,
        reason: a.reason,
      })),
      estimatedLatencyMs: raw.estimated_latency_ms,
      lastUpdated: raw.last_updated,
    };
  }

  /** Report an outcome for a tool invocation. */
  async report(params: ReportParams): Promise<ReportResponse> {
    const raw = await this.request<RawReportResponse>("/v1/report", {
      tool_identifier: params.toolIdentifier,
      success: params.success,
      error_category: params.errorCategory,
      latency_ms: params.latencyMs,
      context: params.context,
    });

    return {
      status: raw.status,
      toolId: raw.tool_id,
    };
  }

  // ── Internals ───────────────────────────────────────────────────

  private async request<T>(path: string, body: Record<string, unknown>): Promise<T> {
    const url = `${this.baseUrl}${path}`;

    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Api-Key": this.apiKey,
      },
      body: JSON.stringify(body),
    });

    const responseBody: unknown = await response.json();

    if (!response.ok) {
      throw new NemoFlowError(
        `NemoFlow API error: ${response.status} ${response.statusText}`,
        response.status,
        responseBody,
      );
    }

    return responseBody as T;
  }
}

// ── Raw API shapes (snake_case) ───────────────────────────────────

interface RawAssessResponse {
  reliability_score: number;
  confidence: number;
  historical_success_rate: string;
  predicted_failure_risk: string;
  common_pitfalls: string[];
  recommended_mitigations: string[];
  top_alternatives: { tool: string; score: number; reason: string }[];
  estimated_latency_ms: number;
  last_updated: string;
}

interface RawReportResponse {
  status: string;
  tool_id: string;
}
