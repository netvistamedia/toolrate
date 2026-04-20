const DEFAULT_BASE_URL = "https://api.toolrate.ai";
const DEFAULT_TIMEOUT_MS = 30_000;

export interface ApiResponse<T> {
  body: T;
  rateLimit: RateLimitInfo | null;
}

export interface RateLimitInfo {
  limit: number | null;
  remaining: number | null;
  reset_at: string | null;
}

export class ApiError extends Error {
  public readonly status: number;
  public readonly body: unknown;
  public readonly rateLimit: RateLimitInfo | null;

  constructor(message: string, status: number, body: unknown, rateLimit: RateLimitInfo | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
    this.rateLimit = rateLimit;
  }
}

export function getApiKey(): string | undefined {
  return process.env.TOOLRATE_API_KEY?.trim() || undefined;
}

export function getBaseUrl(): string {
  return (process.env.TOOLRATE_BASE_URL?.trim() || DEFAULT_BASE_URL).replace(/\/+$/, "");
}

interface RequestOptions {
  method: "GET" | "POST" | "DELETE";
  path: string;
  body?: Record<string, unknown>;
  query?: Record<string, string | number | undefined>;
  authenticated?: boolean;
}

export async function apiRequest<T>(opts: RequestOptions): Promise<ApiResponse<T>> {
  const baseUrl = getBaseUrl();
  const url = buildUrl(baseUrl, opts.path, opts.query);

  const headers: Record<string, string> = {
    Accept: "application/json",
    "User-Agent": "toolrate-mcp/0.1.2",
  };

  if (opts.authenticated !== false) {
    const apiKey = getApiKey();
    if (!apiKey) {
      throw new ApiError(
        "TOOLRATE_API_KEY env var is not set. Add it to your MCP server config or call toolrate_register to get a free key.",
        401,
        undefined,
      );
    }
    headers["X-Api-Key"] = apiKey;
  }

  let bodyText: string | undefined;
  if (opts.body !== undefined) {
    headers["Content-Type"] = "application/json";
    bodyText = JSON.stringify(stripUndefined(opts.body));
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method: opts.method,
      headers,
      body: bodyText,
      signal: AbortSignal.timeout(DEFAULT_TIMEOUT_MS),
    });
  } catch (e) {
    const err = e instanceof Error ? e : new Error(String(e));
    if (err.name === "TimeoutError" || err.name === "AbortError") {
      throw new ApiError(`ToolRate request timed out after ${DEFAULT_TIMEOUT_MS}ms`, 0, undefined);
    }
    throw new ApiError(`ToolRate network error: ${err.message}`, 0, undefined);
  }

  const rateLimit = readRateLimit(response.headers);

  let parsed: unknown = undefined;
  let parseFailed = false;
  try {
    const text = await response.text();
    parsed = text.length > 0 ? JSON.parse(text) : undefined;
  } catch {
    parseFailed = true;
  }

  if (!response.ok) {
    throw new ApiError(
      `ToolRate API error: ${response.status} ${response.statusText}`,
      response.status,
      parsed,
      rateLimit,
    );
  }

  if (parseFailed || parsed === null || parsed === undefined) {
    throw new ApiError(
      `ToolRate API returned an empty or malformed response body (HTTP ${response.status})`,
      response.status,
      undefined,
      rateLimit,
    );
  }

  return { body: parsed as T, rateLimit };
}

function buildUrl(base: string, path: string, query?: Record<string, string | number | undefined>): string {
  const url = new URL(`${base}${path}`);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v === undefined || v === null || v === "") continue;
      url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

function stripUndefined(o: Record<string, unknown>): Record<string, unknown> {
  return Object.fromEntries(Object.entries(o).filter(([, v]) => v !== undefined));
}

function readRateLimit(headers: Headers): RateLimitInfo | null {
  const limit = headers.get("x-ratelimit-limit");
  const remaining = headers.get("x-ratelimit-remaining");
  const reset = headers.get("x-ratelimit-reset");
  if (!limit && !remaining && !reset) return null;
  return {
    limit: limit ? Number(limit) : null,
    remaining: remaining ? Number(remaining) : null,
    reset_at: reset ?? null,
  };
}
