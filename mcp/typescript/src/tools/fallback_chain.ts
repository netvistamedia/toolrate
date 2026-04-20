import { apiRequest } from "../client.js";
import { mcpError } from "../errors.js";
import type { RawFallbackChainResponse } from "../schema.js";
import { fallbackChainInputSchema, type FallbackChainInput } from "../types.js";

export const name = "toolrate_fallback_chain";

export const config = {
  title: "Find the best alternatives when a specific tool fails",
  description: [
    "Given a tool identifier, return the tools that real agents actually switched to after this one failed — ranked by success rate in the fallback position.",
    "",
    "Use this when toolrate_assess flagged the primary tool as risky, or when a live call just failed and you need a fallback.",
  ].join("\n"),
  inputSchema: fallbackChainInputSchema,
};

export async function handler(input: FallbackChainInput) {
  try {
    const { body, rateLimit } = await apiRequest<RawFallbackChainResponse>({
      method: "GET",
      path: "/v1/discover/fallback-chain",
      query: {
        tool_identifier: input.tool_identifier,
        limit: input.limit,
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
