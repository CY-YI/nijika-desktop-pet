// Exercise real DSH SessionStore -> plugin -> frozen shared core in an isolated DB.
// Usage: node tools/smoke_dsh_lifecycle.mjs <dsh modules> <hook.exe> <python.exe>
import assert from "node:assert/strict";
import {mkdtemp, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join, resolve} from "node:path";
import {pathToFileURL} from "node:url";
import {spawnSync} from "node:child_process";
import * as bridge from "../integrations/dsh/lifecycle-bridge.mjs";

const [modules, executable, python] = process.argv.slice(2);
assert(modules && executable && python, "DSH modules, hook and Python paths required");
const {Context} = await import(pathToFileURL(join(modules, "cordis/lib/index.js")).href);
const {SessionStore} = await import(pathToFileURL(join(modules, "dsh-session/lib/index.js")).href);
const temporary = await mkdtemp(join(tmpdir(), "nijika-dsh-events-"));
const previous = process.env.NIJIKA_PET_DB_PATH;
process.env.NIJIKA_PET_DB_PATH = join(temporary, "queue.sqlite3");
const ctx = new Context();
const fibers = [];
const warnings = [];
function sql(code) {
  const result = spawnSync(python, ["-c", code], {
    cwd: resolve(import.meta.dirname, ".."), encoding: "utf8", windowsHide: true,
  });
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
}
function notices() {
  return sql(`import os,json,sqlite3\np=os.environ["NIJIKA_PET_DB_PATH"]\n` +
    `if not os.path.exists(p): print("[]")\n` +
    `else:\n c=sqlite3.connect(p)\n print(json.dumps(c.execute("SELECT agent,message FROM notifications ORDER BY rowid").fetchall()))`);
}
function turn(session, n, {active, origin = "user", repeat = false} = {}) {
  session.append("turn/start", {turn: n});
  session.append("step/start", {turn: n, step: 1});
  session.append("user/message", {id: `u${n}`, role: "user", source: {kind: origin}, content: []},
    {surfaceOp: "append"});
  if (active) {
    session.append("tool/call", {turn: n, callId: "call", name: "mcp__nijika_pet__show_completion"});
    session.append("tool/result", {turn: n, message: {toolCallId: "call",
      content: [{type: "text", text: JSON.stringify({request_id: active, status: "pending"})}]}},
      {surfaceOp: "append"});
  }
  session.append("assistant/message", {turn: n, step: 1, stream: [], message: {
    id: `a${n}`, role: "assistant", content: [{type: "text", text: "本轮短问答已完成。"}],
  }}, {surfaceOp: "append"});
  session.append("step/end", {turn: n, step: 1});
  session.append("turn/end", {turn: n, reason: {kind: "completed"}});
  if (repeat) session.append("turn/end", {turn: n, reason: {kind: "completed"}});
}
try {
  fibers.push(await ctx.plugin(SessionStore));
  // The installed Cordis logger is optional; capture safe failures without payloads.
  ctx.logger = () => ({warn: message => warnings.push(message)});
  fibers.push(await ctx.plugin(bridge, {executable: resolve(executable)}));
  const active = sql(`import json\nfrom notification_store import NotificationStore\n` +
    `s=NotificationStore()\nn=s.create("Agent","主动测试","已主动发送结果。",["知道了"],software="DSH")\nprint(json.dumps(n.id))`);
  const session = ctx.sessions.create("isolated-live-root");
  turn(session, 1, {repeat: true});
  turn(session, 2, {active});
  turn(ctx.sessions.create("isolated-injected"), 1, {origin: "runtime-context"});
  turn(ctx.sessions.create("isolated-child", {meta: {origin: "subagent", delegationDepth: 1}}), 1);
  const deadline = Date.now() + 30000;
  let rows, done = 0;
  // Wait for both root completions, not merely for a subprocess to start.
  while (Date.now() < deadline) {
    rows = notices();
    done = sql(`import json,os,sqlite3\nc=sqlite3.connect(os.environ["NIJIKA_PET_DB_PATH"])\n` +
      `print(json.dumps(c.execute("SELECT COUNT(*) FROM codex_turn_state WHERE completion_notice_sent=1 OR nijika_notice_sent=1").fetchone()[0]))`);
    if (done === 2) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.equal(done, 2, "Both real root turns must reach the shared core");
  assert.equal(rows.length, 2, JSON.stringify(rows));
  assert.equal(rows.filter(row => row[1] === "本轮短问答已完成。").length, 1);
  assert.equal(rows.filter(row => row[1] === "已主动发送结果。").length, 1);
  assert.equal(warnings.length, 0);
  console.log(JSON.stringify({status: "passed", real_session_store: true,
    frozen_subprocess: true, isolated_notices: rows.length,
    external_model_session: false, visible_bubble_verified: false}));
} finally {
  for (const fiber of fibers.reverse()) await fiber.dispose();
  if (previous === undefined) delete process.env.NIJIKA_PET_DB_PATH;
  else process.env.NIJIKA_PET_DB_PATH = previous;
  // This is the exact temporary directory created by this tool, never user state.
  await rm(temporary, {recursive: true, force: true});
}
