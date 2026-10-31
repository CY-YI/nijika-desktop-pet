// DSH 0.2.1-rc.3 session-event adapter. Notification policy stays in Python.
import {spawn} from "node:child_process";

export const name = "nijika-lifecycle-bridge";
export const inject = ["sessions"];

const text = content => Array.isArray(content)
  ? content.filter(part => part?.type === "text" && typeof part.text === "string")
    .map(part => part.text).join("\n").slice(0, 65536)
  : "";

export function createAdapter(send) {
  const turns = new WeakMap();
  return (session, event) => {
    if (!session || typeof session.id !== "string" || !event ||
        !Number.isSafeInteger(session.firstLiveSeq) ||
        !Number.isSafeInteger(event.seq) || event.seq < session.firstLiveSeq ||
        session.header?.origin === "subagent" || session.header?.delegationDepth > 0) return;
    const data = event.data;
    if (!data || typeof data !== "object") return;
    if (event.type === "turn/start") {
      if (Number.isSafeInteger(data.turn) && data.turn >= 1)
        turns.set(session, {turn: data.turn, user: false, last: "", calls: new Map()});
      return;
    }
    const current = turns.get(session);
    if (!current || (data.turn !== undefined && data.turn !== current.turn)) return;
    const emit = (type, extra = {}) => send(session, {
      version: 1, client_id: "dsh", origin: "user",
      session_id: session.id, turn_id: String(current.turn), event: type, ...extra,
    });
    if (event.type === "user/message" && data.source?.kind === "user") {
      if (!current.user) {
        current.user = true;
        emit("turn_started");
      }
    } else if (current.user && event.type === "assistant/message" && !data.interrupted) {
      current.last = text(data.message?.content);
    } else if (current.user && event.type === "tool/call") {
      if (typeof data.callId === "string" && typeof data.name === "string" &&
          data.name.includes("nijika") && current.calls.size < 256)
        current.calls.set(data.callId, data.name);
    } else if (current.user && event.type === "tool/result") {
      const toolName = current.calls.get(data.message?.toolCallId);
      if (toolName) {
        current.calls.delete(data.message.toolCallId);
        emit("tool_finished", {tool_name: toolName, tool_response: {
          isError: data.message.isError === true, content: data.message.content,
        }});
      }
    } else if (event.type === "turn/end") {
      turns.delete(session);
      // Failed/aborted/empty model attempts are not successful replies.
      if (current.user && data.reason?.kind === "completed")
        emit("turn_completed", {last_assistant_message: current.last});
    }
  };
}

export function apply(ctx, config = {}) {
  if (typeof config.executable !== "string" || !config.executable)
    throw new Error("Nijika lifecycle executable is required");
  const queues = new WeakMap();
  const children = new Set();
  let disposed = false;
  const logger = ctx.logger?.(name);
  const failure = () => logger?.warn("Nijika lifecycle delivery failed; no user content logged.");
  const deliver = event => new Promise(resolve => {
    if (disposed) return resolve();
    const child = spawn(config.executable, ["--lifecycle"], {
      windowsHide: true, shell: false, stdio: ["pipe", "pipe", "ignore"],
    });
    children.add(child);
    let output = "";
    let finished = false;
    const finish = ok => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      if (!ok) child.kill();
      children.delete(child);
      if (!ok && !disposed) failure();
      resolve();
    };
    const timer = setTimeout(() => {child.kill(); finish(false);}, 10000);
    child.on("error", () => finish(false));
    child.stdin.on("error", () => finish(false));
    child.stdout.on("data", data => {
      output += data.toString("utf8");
      if (output.length > 4096) {child.kill(); finish(false);}
    });
    child.on("close", code => {
      try {
        const status = JSON.parse(output).status;
        finish(code === 0 && ["queued", "ignored"].includes(status));
      } catch {finish(false);}
    });
    child.stdin.end(JSON.stringify(event));
  });
  const adapter = createAdapter((session, event) => {
    // Keep start -> tool -> end ordered without blocking DSH's model loop.
    const next = (queues.get(session) || Promise.resolve()).then(() => deliver(event)).catch(failure);
    queues.set(session, next);
  });
  ctx.on("session/event", adapter);
  ctx.on("dispose", () => {
    disposed = true;
    for (const child of children) child.kill();
    children.clear();
  });
  logger?.info?.("Nijika lifecycle bridge connected (protocol v1).");
}
