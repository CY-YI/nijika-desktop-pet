/**
 * Exercise an installed DSH bridge plugin, not a handwritten client identity.
 * Uses a fresh isolated database; never reads host conversations or credentials.
 * Usage: node tools/smoke_dsh_bridge.mjs <bridge/lib/index.js> <MCP.exe> <python.exe>
 */
import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { execFileSync } from "node:child_process";

const [bridgeFile, executable, python] = process.argv.slice(2);
if (!bridgeFile || !executable || !python) {
  throw new Error("Expected bridge module path, MCP executable and Python executable");
}
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const directory = await mkdtemp(join(tmpdir(), "nijika-dsh-bridge-"));
const database = join(directory, "isolated.sqlite3");
const definitions = new Map();
const disposers = [];
const context = {
  root: {},
  logger: console,
  tools: {
    register(definition) {
      definitions.set(definition.name, definition);
      return () => definitions.delete(definition.name);
    },
  },
  effect(callback) {
    const dispose = callback();
    if (dispose) disposers.push(dispose);
  },
  on() {},
  inject() {}, // Optional UI/resource services are outside this bridge check.
  get() { return undefined; },
};
try {
  const bridge = await import(pathToFileURL(resolve(bridgeFile)).href);
  await bridge.apply(context, {
    transport: "stdio",
    serverName: "nijika_probe",
    command: resolve(executable),
    args: [],
    env: {
      NIJIKA_PET_DB_PATH: database,
      NIJIKA_AGENT_NAME: "auto",
      NIJIKA_HOST_NAME: "",
    },
    toolCallTimeoutMs: 15000,
    failOnStartupError: true,
    reconnect: { enabled: false, initialDelayMs: 1000, maxDelayMs: 1000, maxAttempts: 1 },
  });
  assert.equal(definitions.size, 4);
  const call = async (name, args) =>
    (await definitions.get(`mcp__nijika_probe__${name}`).execute(args, {
      signal: new AbortController().signal,
    })).structuredContent;
  const complete = await call("show_completion", {
    task: "隔离桥接检查", summary: "真实 DSH bridge 来源测试，不进入桌面队列。",
  });
  const decision = await call("request_decision", {
    task: "隔离选择检查", question: "验证哪个环节？", options: [
      { label: "来源", description: "检查真实 DSH 桥接的来源字段。" },
      { label: "回执", description: "检查选择回复是否独立回传。" },
    ],
  });
  const verify = `
import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from notification_store import NotificationStore
s=NotificationStore(Path(sys.argv[2]))
for key in sys.argv[3:]:
 n=s.get(key)
 assert (n.agent,n.software)==("Agent","DSH"),(n.agent,n.software)
s.answer(sys.argv[4],0)
print(json.dumps({"agent":"Agent","software":"DSH","notices":2}))
`;
  const checked = execFileSync(resolve(python), [
    "-X", "utf8", "-c", verify, root, database, complete.request_id, decision.request_id,
  ], { encoding: "utf8", windowsHide: true });
  const reply = await call("get_reply", { request_id: decision.request_id });
  assert.equal(reply.status, "answered");
  assert.equal(reply.choice, "来源");
  console.log(checked.trim());
  console.log("Installed DSH bridge: registration, auto source, completion, decision and reply passed.");
} finally {
  for (const dispose of disposers.reverse()) await dispose();
  // Only the unique temporary directory created above is removed.
  assert.equal(dirname(resolve(directory)), resolve(tmpdir()));
  assert.ok(directory.split(/[\\/]/).at(-1).startsWith("nijika-dsh-bridge-"));
  await rm(directory, { recursive: true, force: true });
}
