import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import * as assess from "./tools/assess.js";
import * as categories from "./tools/categories.js";
import * as fallbackChain from "./tools/fallback_chain.js";
import * as hiddenGems from "./tools/hidden_gems.js";
import * as myUsage from "./tools/my_usage.js";
import * as register from "./tools/register.js";
import * as report from "./tools/report.js";
import * as routeLlm from "./tools/route_llm.js";
import * as searchTools from "./tools/search_tools.js";
import { getApiKey } from "./client.js";

export function buildServer(): McpServer {
  const server = new McpServer({
    name: "toolrate",
    version: "0.1.0",
  });

  // Always-on tools
  server.registerTool(assess.name, assess.config, assess.handler);
  server.registerTool(report.name, report.config, report.handler);
  server.registerTool(routeLlm.name, routeLlm.config, routeLlm.handler);
  server.registerTool(fallbackChain.name, fallbackChain.config, fallbackChain.handler);
  server.registerTool(hiddenGems.name, hiddenGems.config, hiddenGems.handler);
  server.registerTool(searchTools.name, searchTools.config, searchTools.handler);
  server.registerTool(categories.name, categories.config, categories.handler);
  server.registerTool(myUsage.name, myUsage.config, myUsage.handler);

  // Bootstrap: only available when no API key is configured. Once a key is set,
  // this tool disappears from the schema so an established setup can't
  // accidentally re-register and overwrite an active key.
  if (!getApiKey()) {
    server.registerTool(register.name, register.config, register.handler);
  }

  return server;
}
