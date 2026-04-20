import { apiRequest } from "../client.js";
import { mcpError } from "../errors.js";
import type { RawPersonalStats } from "../schema.js";
import { myUsageInputSchema } from "../types.js";

export const name = "toolrate_my_usage";

export const config = {
  title: "Check your ToolRate API key quota and usage",
  description: "Returns your tier, daily/monthly limit, calls used, and remaining quota. Use this to self-throttle before burning your free tier.",
  inputSchema: myUsageInputSchema,
};

export async function handler(_input: Record<string, never>) {
  try {
    const { body, rateLimit } = await apiRequest<RawPersonalStats>({
      method: "GET",
      path: "/v1/stats/me",
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
