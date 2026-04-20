import { apiRequest } from "../client.js";
import { mcpError } from "../errors.js";
import type { RawHiddenGemsResponse } from "../schema.js";
import { hiddenGemsInputSchema, type HiddenGemsInput } from "../types.js";

export const name = "toolrate_hidden_gems";

export const config = {
  title: "Discover underrated tools that excel as fallbacks",
  description: [
    "Returns tools that have a high success rate in the fallback position but are rarely picked first. Use this to discover lesser-known but reliable APIs in a given category.",
    "",
    "Filter by category — call toolrate_categories first to see the canonical names.",
  ].join("\n"),
  inputSchema: hiddenGemsInputSchema,
};

export async function handler(input: HiddenGemsInput) {
  try {
    const { body, rateLimit } = await apiRequest<RawHiddenGemsResponse>({
      method: "GET",
      path: "/v1/discover/hidden-gems",
      query: {
        category: input.category,
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
