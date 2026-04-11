import {
  type NemoFlowOptions,
  type AssessParams,
  type AssessResponse,
  type ReportParams,
  type ReportResponse,
  type HiddenGemsResponse,
  type FallbackChainResponse,
  type GuardOptions,
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

  // ── Core endpoints ─────────────────────────────────────────────

  /** Assess a tool's reliability and get recommendations. */
  async assess(params: AssessParams): Promise<AssessResponse> {
    const raw = await this.post<RawAssessResponse>("/v1/assess", {
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
    const raw = await this.post<RawReportResponse>("/v1/report", {
      tool_identifier: params.toolIdentifier,
      success: params.success,
      error_category: params.errorCategory,
      latency_ms: params.latencyMs,
      context: params.context,
      session_id: params.sessionId,
      attempt_number: params.attemptNumber,
      previous_tool: params.previousTool,
    });

    return {
      status: raw.status,
      toolId: raw.tool_id,
    };
  }

  // ── Discovery endpoints ────────────────────────────────────────

  /** Find hidden gem tools that shine as fallbacks. */
  async discoverHiddenGems(
    options?: { category?: string; limit?: number },
  ): Promise<HiddenGemsResponse> {
    const params = new URLSearchParams();
    if (options?.category) params.set("category", options.category);
    if (options?.limit) params.set("limit", String(options.limit));

    const raw = await this.get<RawHiddenGemsResponse>(
      `/v1/discover/hidden-gems?${params}`,
    );

    return {
      hiddenGems: raw.hidden_gems.map((g) => ({
        tool: g.tool,
        displayName: g.display_name,
        category: g.category,
        fallbackSuccessRate: g.fallback_success_rate,
        timesUsedAsFallback: g.times_used_as_fallback,
        avgLatencyMs: g.avg_latency_ms,
      })),
      count: raw.count,
    };
  }

  /** Get the best fallback tools when a specific tool fails. */
  async discoverFallbackChain(
    toolIdentifier: string,
    options?: { limit?: number },
  ): Promise<FallbackChainResponse> {
    const params = new URLSearchParams({
      tool_identifier: toolIdentifier,
    });
    if (options?.limit) params.set("limit", String(options.limit));

    const raw = await this.get<RawFallbackChainResponse>(
      `/v1/discover/fallback-chain?${params}`,
    );

    return {
      tool: raw.tool,
      fallbackChain: raw.fallback_chain.map((f) => ({
        fallbackTool: f.fallback_tool,
        displayName: f.display_name,
        timesChosenAfterFailure: f.times_chosen_after_failure,
        successRate: f.success_rate,
        avgLatencyMs: f.avg_latency_ms,
      })),
      count: raw.count,
    };
  }

  // ── Guard ──────────────────────────────────────────────────────

  /**
   * Execute a tool call with automatic reliability guard.
   *
   * 1. Assesses the tool's reliability score
   * 2. If score < minScore and fallbacks exist, skips to next
   * 3. Executes the tool call
   * 4. Reports success/failure back to NemoFlow
   * 5. On failure with fallbacks, tries the next option
   */
  async guard<T>(
    toolIdentifier: string,
    fn: () => Promise<T>,
    options?: GuardOptions<T>,
  ): Promise<T> {
    const context = options?.context ?? "";
    const minScore = options?.minScore ?? 0;
    const sessionId = crypto.randomUUID().replace(/-/g, "").slice(0, 16);

    const allTools: Array<{ toolIdentifier: string; fn: () => Promise<T> }> = [
      { toolIdentifier, fn },
      ...(options?.fallbacks ?? []),
    ];

    let lastError: Error | undefined;

    for (let i = 0; i < allTools.length; i++) {
      const attempt = i + 1;
      const tool = allTools[i];
      const previousTool = i > 0 ? allTools[i - 1].toolIdentifier : undefined;

      // Assess
      let score = 100;
      try {
        const assessment = await this.assess({
          toolIdentifier: tool.toolIdentifier,
          context,
        });
        score = assessment.reliabilityScore;
      } catch {
        // If assess fails, don't block the tool call
      }

      // Skip if score too low and we have more options
      if (score < minScore && attempt < allTools.length) {
        try {
          await this.report({
            toolIdentifier: tool.toolIdentifier,
            success: false,
            errorCategory: "skipped_low_score",
            context,
            sessionId,
            attemptNumber: attempt,
            previousTool,
          });
        } catch {
          // Best-effort reporting
        }
        continue;
      }

      // Execute
      const start = performance.now();
      try {
        const result = await tool.fn();
        const latencyMs = Math.round(performance.now() - start);

        // Report success (best-effort)
        try {
          await this.report({
            toolIdentifier: tool.toolIdentifier,
            success: true,
            latencyMs,
            context,
            sessionId,
            attemptNumber: attempt,
            previousTool,
          });
        } catch {
          // Don't fail the call if reporting fails
        }

        return result;
      } catch (e) {
        const latencyMs = Math.round(performance.now() - start);
        lastError = e instanceof Error ? e : new Error(String(e));

        // Report failure (best-effort)
        try {
          await this.report({
            toolIdentifier: tool.toolIdentifier,
            success: false,
            errorCategory: classifyError(lastError),
            latencyMs,
            context,
            sessionId,
            attemptNumber: attempt,
            previousTool,
          });
        } catch {
          // Best-effort reporting
        }

        // If no more fallbacks, throw
        if (attempt >= allTools.length) {
          throw lastError;
        }
      }
    }

    throw lastError;
  }

  // ── Internals ──────────────────────────────────────────────────

  private async post<T>(path: string, body: Record<string, unknown>): Promise<T> {
    // Strip undefined values
    const clean = Object.fromEntries(
      Object.entries(body).filter(([, v]) => v !== undefined),
    );

    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Api-Key": this.apiKey,
      },
      body: JSON.stringify(clean),
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

  private async get<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "GET",
      headers: { "X-Api-Key": this.apiKey },
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

// ── Error classification ─────────────────────────────────────────

function classifyError(error: Error): string {
  const name = error.name.toLowerCase();
  const msg = error.message.toLowerCase();

  if (name.includes("timeout") || msg.includes("timeout") || msg.includes("timed out"))
    return "timeout";
  if (name.includes("ratelimit") || msg.includes("rate") || msg.includes("429") || msg.includes("too many"))
    return "rate_limit";
  if (name.includes("auth") || msg.includes("unauthorized") || msg.includes("401") || msg.includes("403"))
    return "auth_failure";
  if (name.includes("validation") || msg.includes("invalid") || msg.includes("422"))
    return "validation_error";
  if (msg.includes("not found") || msg.includes("404"))
    return "not_found";
  if (msg.includes("permission") || msg.includes("forbidden"))
    return "permission_denied";
  if (name.includes("connect") || msg.includes("connection") || msg.includes("econnrefused"))
    return "connection_error";

  return "server_error";
}

// ── Raw API shapes (snake_case) ──────────────────────────────────

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

interface RawHiddenGemsResponse {
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

interface RawFallbackChainResponse {
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
