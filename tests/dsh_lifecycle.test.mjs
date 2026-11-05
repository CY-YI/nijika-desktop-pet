import assert from "node:assert/strict";
import test from "node:test";
import {pathToFileURL} from "node:url";
import {join} from "node:path";
import {createAdapter} from "../integrations/dsh/lifecycle-bridge.mjs";

function fixture(extra = {}) {
  const sent = [];
  const session = {id: "session", firstLiveSeq: 10, header: {}, ...extra};
  const adapter = createAdapter((_, event) => sent.push(event));
  let seq = 10;
  const emit = (type, data, target = session) => adapter(target, {seq: seq++, type, data});
  const begin = () => {
    emit("turn/start", {turn: 1});
    emit("user/message", {source: {kind: "user"}, content: []});
  };
  return {sent, session, adapter, emit, begin};
}

test("human short reply becomes shared start and completion events", () => {
  const f = fixture(); f.begin();
  f.emit("assistant/message", {turn: 1, message: {content: [{type: "text", text: "2"}]}});
  f.emit("turn/end", {turn: 1, reason: {kind: "completed"}});
  assert.deepEqual(f.sent.map(e => e.event), ["turn_started", "turn_completed"]);
  assert.equal(f.sent[1].last_assistant_message, "2");
  assert.equal(f.sent[1].client_id, "dsh");
});
test("history, injected context and child sessions stay quiet", () => {
  for (const header of [{origin: "subagent"}, {delegationDepth: 1}]) {
    const f = fixture({header}); f.begin();
    f.emit("turn/end", {turn: 1, reason: {kind: "completed"}});
    assert.equal(f.sent.length, 0);
  }
  const f = fixture();
  f.adapter(f.session, {seq: 0, type: "turn/start", data: {turn: 1}});
  f.begin();
  f.emit("turn/end", {turn: 1, reason: {kind: "aborted"}});
  assert.equal(f.sent.filter(e => e.event === "turn_completed").length, 0);
  const injected = fixture();
  injected.emit("turn/start", {turn: 1});
  injected.emit("user/message", {source: {kind: "runtime-context"}});
  injected.emit("turn/end", {turn: 1, reason: {kind: "completed"}});
  assert.equal(injected.sent.length, 0);
});
test("successful MCP receipts are forwarded before the turn ends", () => {
  const f = fixture(); f.begin();
  f.emit("tool/call", {turn: 1, callId: "c", name: "mcp__nijika_pet__show_completion"});
  f.emit("tool/result", {turn: 1, message: {
    toolCallId: "c", content: [{type: "text", text: '{"request_id":"id","status":"pending"}'}],
  }});
  f.emit("turn/end", {turn: 1, reason: {kind: "completed"}});
  assert.deepEqual(f.sent.map(e => e.event), ["turn_started", "tool_finished", "turn_completed"]);
});
test("different sessions, repeated end and mismatched turn cannot cross", () => {
  const f = fixture(); f.begin();
  const other = {...f.session};
  f.emit("turn/end", {turn: 1, reason: {kind: "completed"}}, other);
  f.emit("turn/end", {turn: 2, reason: {kind: "completed"}});
  f.emit("turn/end", {turn: 1, reason: {kind: "completed"}});
  f.emit("turn/end", {turn: 1, reason: {kind: "completed"}});
  assert.equal(f.sent.filter(e => e.event === "turn_completed").length, 1);
});

test("installed DSH SessionStore emits the documented live events", {
  skip: !process.env.NIJIKA_DSH_TEST_MODULES,
}, async () => {
  const base = process.env.NIJIKA_DSH_TEST_MODULES;
  const {Context} = await import(pathToFileURL(join(base, "cordis/lib/index.js")).href);
  const {SessionStore} = await import(pathToFileURL(join(base, "dsh-session/lib/index.js")).href);
  const ctx = new Context();
  const sent = [];
  const fiber = await ctx.plugin(SessionStore);
  try {
  ctx.on("session/event", createAdapter((_, event) => sent.push(event)));
  const session = ctx.sessions.create("isolated-runtime");
  session.append("turn/start", {turn: 1});
  session.append("step/start", {turn: 1, step: 1});
  session.append("user/message", {
    id: "u", role: "user", source: {kind: "user"}, content: [{type: "text", text: "1+1?"}],
  }, {surfaceOp: "append"});
  session.append("assistant/message", {
    turn: 1, step: 1, stream: [],
    message: {id: "a", role: "assistant", source: {kind: "model", provider: "test", model: "test"},
              content: [{type: "text", text: "2"}]},
  }, {surfaceOp: "append"});
  session.append("step/end", {turn: 1, step: 1});
  session.append("turn/end", {turn: 1, reason: {kind: "completed"}});
  assert.deepEqual(sent.map(e => e.event), ["turn_started", "turn_completed"]);
  assert.equal(sent[1].last_assistant_message, "2");
  } finally {
    await fiber.dispose();
  }
});
