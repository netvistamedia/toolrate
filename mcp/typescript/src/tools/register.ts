import { apiRequest } from "../client.js";
import { mcpError } from "../errors.js";
import type { RawRegisterResponse } from "../schema.js";
import { registerInputSchema, type RegisterInput } from "../types.js";

export const name = "toolrate_register";

export const config = {
  title: "Bootstrap: register a new ToolRate API key",
  description: [
    "Creates a new ToolRate API key tied to your email and returns it. Only available when TOOLRATE_API_KEY is unset on the MCP server.",
    "",
    "After getting the key: paste it into your MCP server config under env.TOOLRATE_API_KEY and restart the editor. The other 8 ToolRate tools will then become available.",
  ].join("\n"),
  inputSchema: registerInputSchema,
};

export async function handler(input: RegisterInput) {
  try {
    const { body } = await apiRequest<RawRegisterResponse>({
      method: "POST",
      path: "/v1/auth/register",
      body: { email: input.email, source: "mcp" },
      authenticated: false,
    });

    const text = [
      "ToolRate API key created.",
      "",
      `API key: ${body.api_key}`,
      `Tier: ${body.tier}`,
      `Daily limit: ${body.daily_limit}`,
      "",
      "Add this to your MCP server config and restart the editor:",
      "",
      JSON.stringify(
        {
          mcpServers: {
            toolrate: {
              command: "npx",
              args: ["-y", "@toolrate/mcp-server"],
              env: { TOOLRATE_API_KEY: body.api_key },
            },
          },
        },
        null,
        2,
      ),
      "",
      "Save the key now — it cannot be retrieved later.",
    ].join("\n");

    return { content: [{ type: "text" as const, text }] };
  } catch (err) {
    return mcpError(err);
  }
}
