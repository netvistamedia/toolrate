import { apiRequest } from "../client.js";
import { mcpError } from "../errors.js";
import type { RawToolsResponse } from "../schema.js";
import { searchToolsInputSchema, type SearchToolsInput } from "../types.js";

export const name = "toolrate_search_tools";

export const config = {
  title: "Search and browse rated tools in ToolRate",
  description: [
    "Search the ToolRate catalog by name, identifier substring, or category. Returns identifiers you can pass to toolrate_assess.",
    "",
    "Use this when the agent needs to find candidate tools for a task but doesn't know the canonical identifier.",
  ].join("\n"),
  inputSchema: searchToolsInputSchema,
};

export async function handler(input: SearchToolsInput) {
  try {
    const { body, rateLimit } = await apiRequest<RawToolsResponse>({
      method: "GET",
      path: "/v1/tools",
      query: {
        q: input.q,
        category: input.category,
        limit: input.limit,
        offset: input.offset,
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
