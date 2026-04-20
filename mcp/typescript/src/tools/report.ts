import { apiRequest } from "../client.js";
import { mcpError } from "../errors.js";
import type { RawReportResponse } from "../schema.js";
import { reportInputSchema, type ReportInput } from "../types.js";

export const name = "toolrate_report";

export const config = {
  title: "Report the outcome of a tool call",
  description: [
    "Tell ToolRate what happened after you invoked a third-party tool/API. This is how the reliability scores improve.",
    "",
    "Guard pattern: call this AFTER every third-party tool call you make. Report success=true on success; on failure, set success=false and pass error_category.",
    "",
    "When chaining attempts, set attempt_number (2 = first fallback, 3 = second, …) and previous_tool — this builds the fallback-chain analytics that power toolrate_fallback_chain.",
  ].join("\n"),
  inputSchema: reportInputSchema,
};

export async function handler(input: ReportInput) {
  try {
    const { body, rateLimit } = await apiRequest<RawReportResponse>({
      method: "POST",
      path: "/v1/report",
      body: {
        tool_identifier: input.tool_identifier,
        success: input.success,
        error_category: input.error_category,
        latency_ms: input.latency_ms,
        context: input.context,
        session_id: input.session_id,
        attempt_number: input.attempt_number,
        previous_tool: input.previous_tool,
      },
    });

    const result = {
      ...body,
      ...(rateLimit ? { _meta: { rate_limit: rateLimit } } : {}),
    };

    return {
      content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }],
    };
  } catch (err) {
    return mcpError(err);
  }
}
