import { spawn } from "node:child_process";
import { setTimeout as wait } from "node:timers/promises";

const EXPECTED_BASE = [
  "toolrate_assess",
  "toolrate_categories",
  "toolrate_fallback_chain",
  "toolrate_hidden_gems",
  "toolrate_my_usage",
  "toolrate_report",
  "toolrate_route_llm",
  "toolrate_search_tools",
].sort();
const EXPECTED_WITH_REGISTER = [...EXPECTED_BASE, "toolrate_register"].sort();

async function listTools(env) {
  const proc = spawn("node", ["dist/index.js"], {
    stdio: ["pipe", "pipe", "inherit"],
    env: { ...process.env, ...env },
  });

  let buffer = "";
  const responses = [];
  proc.stdout.on("data", (chunk) => {
    buffer += chunk.toString("utf8");
    let idx;
    while ((idx = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, idx).trim();
      buffer = buffer.slice(idx + 1);
      if (line.length === 0) continue;
      try {
        responses.push(JSON.parse(line));
      } catch {
        console.error("non-JSON line:", line);
      }
    }
  });

  function send(msg) {
    proc.stdin.write(JSON.stringify(msg) + "\n");
  }

  send({
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "smoke", version: "0.0.0" },
    },
  });
  await wait(200);
  send({ jsonrpc: "2.0", method: "notifications/initialized" });
  await wait(100);
  send({ jsonrpc: "2.0", id: 2, method: "tools/list", params: {} });
  await wait(400);
  proc.stdin.end();
  await wait(150);
  proc.kill();

  const listResp = responses.find((r) => r.id === 2);
  if (!listResp?.result?.tools) {
    throw new Error(`no tools/list response. responses=${JSON.stringify(responses)}`);
  }
  return listResp.result.tools.map((t) => t.name).sort();
}

function assertEqual(label, actual, expected) {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    console.error(`FAIL [${label}]:\n  expected: ${JSON.stringify(expected)}\n  actual:   ${JSON.stringify(actual)}`);
    process.exit(1);
  }
  console.log(`OK [${label}]: ${actual.length} tools`);
}

const withKey = await listTools({ TOOLRATE_API_KEY: "nf_live_smoke_dummy" });
assertEqual("with key — 8 tools, no register", withKey, EXPECTED_BASE);

const withoutKey = await listTools({ TOOLRATE_API_KEY: "" });
assertEqual("no key — 9 tools, register included", withoutKey, EXPECTED_WITH_REGISTER);

console.log("\nALL SMOKE TESTS PASSED");
