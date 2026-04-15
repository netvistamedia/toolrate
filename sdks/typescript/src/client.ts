import {
  type ToolRateOptions,
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
  ToolRateError,
} from "./types.js";

const DEFAULT_BASE_URL = "https://api.toolrate.ai";
const DEFAULT_TIMEOUT_MS = 30000;

export class ToolRate {
  private readonly apiKey: string;
  private readonly baseUrl: string;
  private readonly timeoutMs: number;

  constructor(apiKey: string, options?: ToolRateOptions) {
    if (!apiKey) {
      throw new Error("An API key is required to create a ToolRate client.");
    }
    this.apiKey = apiKey;
    this.baseUrl = (options?.baseUrl ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
    this.timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  }

  // ── Assessment ─────────────────────────────────────────────────

  /** Assess a tool's reliability and get recommendations. */
  async assess(params: AssessParams): Promise<AssessResponse> {
    const raw = await this.post<RawAssessResponse>("/v1/assess", {
      tool_identifier: params.toolIdentifier,
      context: params.context,
      sample_payload: params.samplePayload,
      max_price_per_call: params.maxPricePerCall,
      max_monthly_budget: params.maxMonthlyBudget,
      expected_calls_per_month: params.expectedCallsPerMonth,
      budget_strategy: params.budgetStrategy,
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
    const raw = await this.get<RawPlatformStats>("/v1/stats");
    // Explicit mapping — `camelCaseKeys` only flattens the top level, which
    // left the declared `totalTools` / `totalReports` fields as undefined at
    // runtime on the actual nested response. This restores a shape that
    // matches the PlatformStats interface.
    return {
      platform: {
        totalTools: raw.platform.total_tools,
        totalReports: raw.platform.total_reports,
        totalApiKeys: raw.platform.total_api_keys,
        journeyReports: raw.platform.journey_reports,
      },
      activity: {
        reportsToday: raw.activity.reports_today,
        reportsLast7d: raw.activity.reports_last_7d,
      },
      topTools: raw.top_tools.map((t) => ({
        identifier: t.identifier,
        displayName: t.display_name,
        reportCount: t.report_count,
      })),
      generatedAt: raw.generated_at,
    };
  }

  /** Get personal usage statistics (tier, limits, usage). */
  async getMyStats(): Promise<PersonalStats> {
    const raw = await this.get<RawPersonalStats>("/v1/stats/me");
    return {
      keyPrefix: raw.key_prefix,
      tier: raw.tier,
      billingPeriod: raw.billing_period,
      limit: raw.limit,
      used: raw.used,
      remaining: raw.remaining,
      dailyLimit: raw.daily_limit,
      dailyUsed: raw.daily_used,
      dailyRemaining: raw.daily_remaining,
      createdAt: raw.created_at,
    };
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
   * 4. Reports success/failure back to ToolRate
   * 5. On failure with fallbacks, tries the next option
   *
   * Pass `fallbacks: "auto"` plus a `resolvers` map to let ToolRate pick the
   * fallback chain dynamically from real agent journey data — only tools the
   * caller has pre-registered a runner for will be invoked.
   */
  async guard<T>(
    toolIdentifier: string,
    fn: () => Promise<T>,
    options?: GuardOptions<T>,
  ): Promise<T> {
    const context = options?.context ?? "";
    const minScore = options?.minScore ?? 0;
    const maxFallbacks = options?.maxFallbacks ?? 3;
    const maxPricePerCall = options?.maxPricePerCall;
    const maxMonthlyBudget = options?.maxMonthlyBudget;
    const expectedCallsPerMonth = options?.expectedCallsPerMonth;
    const budgetStrategy = options?.budgetStrategy;
    const sessionId = makeSessionId();

    const autoMode = options?.fallbacks === "auto";
    const explicitFallbacks: Array<{ toolIdentifier: string; fn: () => Promise<T> }> =
      !options?.fallbacks || options.fallbacks === "auto" ? [] : options.fallbacks;

    const allTools: Array<{ toolIdentifier: string; fn: () => Promise<T> }> = [
      { toolIdentifier, fn },
      ...explicitFallbacks,
    ];

    let resolvedAuto = !autoMode;
    let lastError: Error | undefined;

    for (let i = 0; i < allTools.length; i++) {
      const attempt = i + 1;
      const tool = allTools[i];
      const previousTool = i > 0 ? allTools[i - 1].toolIdentifier : undefined;

      // Assess — forward budget params so `withinBudget` is evaluated against
      // the caller's constraints. `this.post` strips undefined values, so
      // unset params stay off the wire and older API versions stay happy.
      let score = 100;
      let assessment: AssessResponse | undefined;
      try {
        assessment = await this.assess({
          toolIdentifier: tool.toolIdentifier,
          context,
          maxPricePerCall,
          maxMonthlyBudget,
          expectedCallsPerMonth,
          budgetStrategy,
        });
        score = assessment.reliabilityScore;
      } catch {
        // If assess fails, don't block the tool call
      }

      // Resolve auto fallbacks once, using the primary assessment we already fetched
      if (!resolvedAuto && i === 0) {
        const autoTools = await this.resolveAutoFallbacks<T>(
          tool.toolIdentifier,
          assessment,
          options?.resolvers ?? {},
          maxFallbacks,
        );
        allTools.push(...autoTools);
        resolvedAuto = true;
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

      // Skip if explicitly over budget and we have more options. Only skip
      // when `withinBudget` is literally false — null means "no budget was
      // asked about" and must not be treated as a failure.
      if (
        assessment?.withinBudget === false &&
        attempt < allTools.length
      ) {
        try {
          await this.report({
            toolIdentifier: tool.toolIdentifier,
            success: false,
            errorCategory: "skipped_over_budget",
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

  /** Pick fallback callables by matching ToolRate's alternatives against user resolvers.
   *
   * When the primary assessment carries `withinBudget` on its alternatives
   * (i.e. the caller passed budget params), tools that fit the budget are
   * preferred over tools flagged as over-budget. Ties fall back to the
   * reliability order the API returned.
   */
  private async resolveAutoFallbacks<T>(
    primaryIdentifier: string,
    primaryAssessment: AssessResponse | undefined,
    resolvers: Record<string, () => Promise<T>>,
    maxN: number,
  ): Promise<Array<{ toolIdentifier: string; fn: () => Promise<T> }>> {
    if (Object.keys(resolvers).length === 0 || maxN <= 0) return [];

    let candidates: string[] = [];

    // 1. Reuse top_alternatives from the assessment we already fetched, with
    //    a stable sort that keeps within-budget tools ahead of over-budget
    //    ones without disturbing the underlying reliability order.
    if (primaryAssessment) {
      const entries: Array<{ priority: number; index: number; tool: string }> = [];
      (primaryAssessment.topAlternatives ?? []).forEach((alt, index) => {
        if (alt?.tool) {
          entries.push({
            priority: alt.withinBudget === false ? 1 : 0,
            index,
            tool: alt.tool,
          });
        }
      });
      entries.sort((a, b) => a.priority - b.priority || a.index - b.index);
      candidates = entries.map((e) => e.tool);
    }

    // 2. If no alternatives in assess response, query the fallback-chain endpoint
    if (candidates.length === 0) {
      try {
        const chain = await this.discoverFallbackChain(primaryIdentifier);
        for (const item of chain.fallbackChain ?? []) {
          if (item?.fallbackTool) candidates.push(item.fallbackTool);
        }
      } catch {
        // Best-effort — keep candidates empty and return []
      }
    }

    const out: Array<{ toolIdentifier: string; fn: () => Promise<T> }> = [];
    const seen = new Set<string>([primaryIdentifier]);
    for (const ident of candidates) {
      if (seen.has(ident)) continue;
      const runner = resolvers[ident];
      if (!runner) continue;
      out.push({ toolIdentifier: ident, fn: runner });
      seen.add(ident);
      if (out.length >= maxN) break;
    }

    return out;
  }

  // ── Internals ──────────────────────────────────────────────────

  private async post<T>(path: string, body: Record<string, unknown>): Promise<T> {
    // Strip undefined values
    const clean = Object.fromEntries(
      Object.entries(body).filter(([, v]) => v !== undefined),
    );

    return this.request<T>("POST", path, JSON.stringify(clean));
  }

  private async get<T>(path: string): Promise<T> {
    return this.request<T>("GET", path);
  }

  private async del<T>(path: string): Promise<T> {
    return this.request<T>("DELETE", path);
  }

  private async request<T>(
    method: "GET" | "POST" | "DELETE",
    path: string,
    body?: string,
  ): Promise<T> {
    const headers: Record<string, string> = { "X-Api-Key": this.apiKey };
    if (body !== undefined) headers["Content-Type"] = "application/json";

    // AbortSignal.timeout() is available in Node 18.17+, modern browsers, and
    // all supported Bun/Deno runtimes. It enforces the per-request timeout so
    // an unresponsive server cannot leave an agent hanging forever.
    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers,
        body,
        signal: AbortSignal.timeout(this.timeoutMs),
      });
    } catch (e) {
      const err = e instanceof Error ? e : new Error(String(e));
      if (err.name === "TimeoutError" || err.name === "AbortError") {
        throw new ToolRateError(
          `ToolRate request timed out after ${this.timeoutMs}ms`,
          0,
          undefined,
        );
      }
      throw new ToolRateError(
        `ToolRate network error: ${err.message}`,
        0,
        undefined,
      );
    }

    let responseBody: unknown = undefined;
    let parseError = false;
    try {
      responseBody = await response.json();
    } catch {
      // Non-JSON body (e.g. 502 HTML from an upstream proxy). Leave undefined
      // and remember we couldn't parse — we'll only throw if the response was
      // otherwise "ok", so error responses still surface their status cleanly.
      parseError = true;
    }

    if (!response.ok) {
      throw new ToolRateError(
        `ToolRate API error: ${response.status} ${response.statusText}`,
        response.status,
        responseBody,
      );
    }

    // 2xx but no usable JSON body (empty body, literal JSON null, or a
    // garbled response from a broken upstream). Without this guard the SDK
    // would happily return `undefined as T` and every caller's response
    // mapping (`raw.reliability_score`, etc.) would crash with a bare
    // `TypeError: Cannot read properties of undefined` instead of a clean
    // ToolRateError the caller can catch.
    if (parseError || responseBody === null || responseBody === undefined) {
      throw new ToolRateError(
        `ToolRate API returned an empty or malformed response body (HTTP ${response.status})`,
        response.status,
        undefined,
      );
    }

    return responseBody as T;
  }
}

// ── Session ID generation ────────────────────────────────────────────
// The bare `crypto` global was only promoted to a Node.js global in 18.18.0,
// but package.json advertises `node: ">=18.0.0"`, so pre-18.18 would throw
// `ReferenceError: crypto is not defined`. Try a Web Crypto global first,
// then fall back to a Math.random hex string — good enough for session IDs.
function makeSessionId(): string {
  const g = (globalThis as { crypto?: { randomUUID?: () => string } }).crypto;
  if (g?.randomUUID) {
    return g.randomUUID().replace(/-/g, "").slice(0, 16);
  }
  // Non-crypto fallback: 16 hex chars from Math.random. Session IDs only
  // need to be collision-resistant within a single agent run.
  let out = "";
  for (let i = 0; i < 16; i++) {
    out += Math.floor(Math.random() * 16).toString(16);
  }
  return out;
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
      pricePerCall: a.price_per_call ?? null,
      withinBudget: a.within_budget ?? null,
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
    pricePerCall: raw.price_per_call ?? null,
    pricingModel: raw.pricing_model ?? null,
    costAdjustedScore: raw.cost_adjusted_score ?? null,
    estimatedMonthlyCost: raw.estimated_monthly_cost ?? null,
    withinBudget: raw.within_budget ?? null,
    budgetExplanation: raw.budget_explanation ?? null,
  };
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
  top_alternatives: Array<{
    tool: string;
    score: number;
    reason: string;
    price_per_call?: number | null;
    within_budget?: boolean | null;
  }>;
  estimated_latency_ms: number | null;
  latency: { avg: number | null; p50: number | null; p95: number | null; p99: number | null } | null;
  last_updated: string;
  price_per_call?: number | null;
  pricing_model?: string | null;
  cost_adjusted_score?: number | null;
  estimated_monthly_cost?: number | null;
  within_budget?: boolean | null;
  budget_explanation?: string | null;
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

interface RawPlatformStats {
  platform: {
    total_tools: number;
    total_reports: number;
    total_api_keys: number;
    journey_reports: number;
  };
  activity: {
    reports_today: number;
    reports_last_7d: number;
  };
  top_tools: Array<{
    identifier: string;
    display_name: string | null;
    report_count: number;
  }>;
  generated_at: string;
}

interface RawPersonalStats {
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
