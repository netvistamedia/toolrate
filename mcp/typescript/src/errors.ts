import { ApiError } from "./client.js";

export interface McpToolError {
  isError: true;
  content: Array<{ type: "text"; text: string }>;
  // Required for assignability to the MCP SDK's tool-handler return type, which
  // declares `[x: string]: unknown` so handlers can attach extra metadata.
  [k: string]: unknown;
}

export function mcpError(err: unknown): McpToolError {
  return {
    isError: true,
    content: [{ type: "text", text: formatError(err) }],
  };
}

function formatError(err: unknown): string {
  if (err instanceof ApiError) return formatApiError(err);
  if (err instanceof Error) return `ToolRate MCP error: ${err.message}`;
  return `ToolRate MCP error: ${String(err)}`;
}

function formatApiError(err: ApiError): string {
  const detail = extractDetail(err.body);

  switch (err.status) {
    case 0:
      return `Cannot reach the ToolRate API. ${err.message} — check your internet or TOOLRATE_BASE_URL.`;
    case 401:
      return "ToolRate API rejected the API key (401). Check TOOLRATE_API_KEY in your MCP config.";
    case 403:
      return `ToolRate API forbade this request (403). ${detail ?? "Your tier likely cannot access this endpoint."}`;
    case 404:
      return `ToolRate API: not found (404). ${detail ?? "If this was an unrated tool, the assess endpoint usually triggers an LLM-estimated cold start instead."}`;
    case 422:
      return `ToolRate API validation error (422): ${detail ?? "check the parameters you passed."}`;
    case 429: {
      const remaining = err.rateLimit?.remaining;
      const limit = err.rateLimit?.limit;
      const ctx =
        remaining !== undefined && limit !== undefined
          ? ` (${remaining}/${limit} remaining)`
          : "";
      return `ToolRate API rate limit exceeded (429)${ctx}. Free tier is 100 assessments/day. Run toolrate_my_usage to check your quota.`;
    }
    case 500:
    case 502:
    case 503:
    case 504:
      return `ToolRate API is having issues (${err.status}). ${detail ?? "Please retry in a moment."}`;
    default:
      return `ToolRate API error (${err.status}): ${detail ?? err.message}`;
  }
}

function extractDetail(body: unknown): string | undefined {
  if (body && typeof body === "object") {
    const b = body as Record<string, unknown>;
    if (typeof b.detail === "string") return b.detail;
    if (typeof b.message === "string") return b.message;
    if (Array.isArray(b.errors) && b.errors.length > 0) {
      const first = b.errors[0] as Record<string, unknown>;
      if (typeof first.msg === "string") return first.msg;
    }
  }
  return undefined;
}
