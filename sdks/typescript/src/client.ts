import {
  type NemoFlowOptions,
  type AssessParams,
  type AssessResponse,
  type BatchAssessItem,
  type BatchAssessResponse,
  type ReportParams,
  type ReportResponse,
  type HiddenGemsResponse,
  type FallbackChainResponse,
  type ToolsResponse,
  type CategoriesResponse,
  type PlatformStats,
  type PersonalStats,
  type WebhookResponse,
  type WebhookListResponse,
  type RotateKeyResponse,
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

  // ── Assessment ─────────────────────────────────────────────────

  /** Assess a tool's reliability and get recommendations. */
  async assess(params: AssessParams): Promise<AssessResponse> {
    const raw = await this.post<RawAssessResponse>("/v1/assess", {
      tool_identifier: params.toolIdentifier,
      context: params.context,
      sample_payload: params.samplePayload,
    });

    return mapAssessResponse(raw);
  }

  /** Assess up to 20 tools in a single request. */
  async assessBatch(tools: BatchAssessItem[]): Promise<BatchAssessResponse> {
    const raw = await this.post<RawBatchAssessResponse>("/v1/assess/batch", {
      tools: tools.map((t) => ({
        tool_identifier: t.toolIdentifier,
        context: t.context,
      })),
    });

    return {
      assessments: raw.assessments.map((a) => ({
        toolIdentifier: a.tool_identifier,
        result: a.result ? mapAssessResponse(a.result) : undefined,
        error: a.error,
      })),
      count: raw.count,
    };
  }

  // ── Reporting ──────────────────────────────────────────────────

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

  // ── Discovery ──────────────────────────────────────────────────

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

  // ── Tools ──────────────────────────────────────────────────────

  /** Search and browse all rated tools. */
  async searchTools(options?: {
    q?: string;
    category?: string;
    offset?: number;
    limit?: number;
  }): Promise<ToolsResponse> {
    const params = new URLSearchParams();
    if (options?.q) params.set("q", options.q);
    if (options?.category) params.set("category", options.category);
    if (options?.offset) params.set("offset", String(options.offset));
    if (options?.limit) params.set("limit", String(options.limit));

    const raw = await this.get<RawToolsResponse>(`/v1/tools?${params}`);

    return {
      tools: raw.tools.map((t) => ({
        identifier: t.identifier,
        displayName: t.display_name,
        category: t.category,
        reportCount: t.report_count,
        firstSeenAt: t.first_seen_at,
      })),
      total: raw.total,
      offset: raw.offset,
      limit: raw.limit,
    };
  }

  /** List all tool categories with counts. */
  async listCategories(): Promise<CategoriesResponse> {
    const raw = await this.get<RawCategoriesResponse>("/v1/tools/categories");

    return {
      categories: raw.categories.map((c) => ({
        name: c.name,
        toolCount: c.tool_count,
      })),
      total: raw.total,
    };
  }

  // ── Stats ──────────────────────────────────────────────────────

  /** Get platform-wide statistics. */
  async getStats(): Promise<PlatformStats> {
    const raw = await this.get<Record<string, unknown>>("/v1/stats");
    return camelCaseKeys(raw) as PlatformStats;
  }

  /** Get personal usage statistics (tier, limits, usage). */
  async getMyStats(): Promise<PersonalStats> {
    const raw = await this.get<Record<string, unknown>>("/v1/stats/me");
    return camelCaseKeys(raw) as PersonalStats;
  }

  // ── Webhooks ───────────────────────────────────────────────────

  /** Register a webhook for score change alerts. */
  async createWebhook(options: {
    url: string;
    threshold?: number;
    toolIdentifier?: string;
    event?: string;
  }): Promise<WebhookResponse> {
    const raw = await this.post<RawWebhookResponse>("/v1/webhooks", {
      url: options.url,
      threshold: options.threshold ?? 5,
      tool_identifier: options.toolIdentifier,
      event: options.event ?? "score.change",
    });

    return {
      id: raw.id,
      url: raw.url,
      event: raw.event,
      toolIdentifier: raw.tool_identifier,
      threshold: raw.threshold,
      secret: raw.secret,
      isActive: raw.is_active,
    };
  }

  /** List all your registered webhooks. */
  async listWebhooks(): Promise<WebhookListResponse> {
    const raw = await this.get<RawWebhookListResponse>("/v1/webhooks");

    return {
      webhooks: raw.webhooks.map((w) => ({
        id: w.id,
        url: w.url,
        event: w.event,
        toolIdentifier: w.tool_identifier,
        threshold: w.threshold,
        secret: w.secret,
        isActive: w.is_active,
      })),
      count: raw.count,
    };
  }

  /** Delete a webhook by ID. */
  async deleteWebhook(webhookId: string): Promise<{ status: string }> {
    return this.del<{ status: string }>(`/v1/webhooks/${webhookId}`);
  }

  // ── Account ────────────────────────────────────────────────────

  /** Rotate your API key. Returns a new key; the current key is deactivated. */
  async rotateKey(): Promise<RotateKeyResponse> {
    const raw = await this.post<RawRotateKeyResponse>("/v1/auth/rotate-key", {});

    return {
      newApiKey: raw.new_api_key,
      oldKeyPrefix: raw.old_key_prefix,
      tier: raw.tier,
      dailyLimit: raw.daily_limit,
    };
  }

  /** Permanently delete your account and all associated data. */
  async deleteAccount(): Promise<{ status: string; message: string }> {
    return this.del<{ status: string; message: string }>("/v1/account");
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

  private async del<T>(path: string): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: "DELETE",
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

// ── Response mapping ────────────────────────────────────────────────

function mapAssessResponse(raw: RawAssessResponse): AssessResponse {
  return {
    reliabilityScore: raw.reliability_score,
    confidence: raw.confidence,
    dataSource: raw.data_source,
    historicalSuccessRate: raw.historical_success_rate,
    predictedFailureRisk: raw.predicted_failure_risk,
    trend: raw.trend
      ? {
          direction: raw.trend.direction,
          score24h: raw.trend.score_24h,
          score7d: raw.trend.score_7d,
          change24h: raw.trend.change_24h,
        }
      : null,
    commonPitfalls: (raw.common_pitfalls ?? []).map((p) => ({
      category: p.category,
      percentage: p.percentage,
      count: p.count,
      mitigation: p.mitigation,
    })),
    recommendedMitigations: raw.recommended_mitigations,
    topAlternatives: raw.top_alternatives.map((a) => ({
      tool: a.tool,
      score: a.score,
      reason: a.reason,
    })),
    estimatedLatencyMs: raw.estimated_latency_ms,
    latency: raw.latency
      ? {
          avg: raw.latency.avg,
          p50: raw.latency.p50,
          p95: raw.latency.p95,
          p99: raw.latency.p99,
        }
      : null,
    lastUpdated: raw.last_updated,
  };
}

function camelCaseKeys(obj: Record<string, unknown>): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    const camel = key.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
    result[camel] = value;
  }
  return result;
}

// ── Error classification ─────────────────────────────────────────

function classifyError(error: Error): string {
  const name = error.name.toLowerCase();
  const msg = error.message.toLowerCase();

  if (name.includes("timeout") || msg.includes("timeout") || msg.includes("timed out"))
    return "timeout";
  if (name.includes("ratelimit") || (msg.includes("rate") && msg.includes("limit")) || msg.includes("429") || msg.includes("too many"))
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
  top_alternatives: { tool: string; score: number; reason: string }[];
  estimated_latency_ms: number | null;
  latency: { avg: number | null; p50: number | null; p95: number | null; p99: number | null } | null;
  last_updated: string;
}

interface RawBatchAssessResponse {
  assessments: Array<{
    tool_identifier: string;
    result?: RawAssessResponse;
    error?: string;
  }>;
  count: number;
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

interface RawToolsResponse {
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

interface RawCategoriesResponse {
  categories: Array<{ name: string; tool_count: number }>;
  total: number;
}

interface RawWebhookResponse {
  id: string;
  url: string;
  event: string;
  tool_identifier: string | null;
  threshold: number;
  secret?: string;
  is_active: boolean;
}

interface RawWebhookListResponse {
  webhooks: RawWebhookResponse[];
  count: number;
}

interface RawRotateKeyResponse {
  new_api_key: string;
  old_key_prefix: string;
  tier: string;
  daily_limit: number;
}
