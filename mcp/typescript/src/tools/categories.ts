import { apiRequest } from "../client.js";
import { mcpError } from "../errors.js";
import type { RawCategoriesResponse } from "../schema.js";
import { categoriesInputSchema } from "../types.js";

export const name = "toolrate_categories";

export const config = {
  title: "List all tool categories with counts",
  description: "Get the canonical category names + tool counts. Useful to filter toolrate_search_tools or toolrate_hidden_gems.",
  inputSchema: categoriesInputSchema,
};

export async function handler(_input: Record<string, never>) {
  try {
    const { body, rateLimit } = await apiRequest<RawCategoriesResponse>({
      method: "GET",
      path: "/v1/tools/categories",
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
