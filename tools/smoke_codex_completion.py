"""Run real Codex CLI lifecycle events against an isolated notification queue.

Uses the current login/model endpoint without copying credentials or changing
the user's config/trust. Hook trust is bypassed only for this vetted invocation.
No pet UI is launched and no production queue is used.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import time
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def toml_text(value: object) -> str:
    # JSON string escaping also produces a valid TOML basic string for these
    # local paths. This is subprocess argv data, never shell interpolation.
    return json.dumps(value, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=("work", "question", "notice"), default="work")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--approval-exe", type=Path,
                        default=ROOT / "dist" / "虹夏审批提醒.exe")
    parser.add_argument("--event-log", type=Path,
                        help="Write redacted hook event metadata for diagnosing a failed isolated run")
    options = parser.parse_args()
    options.approval_exe = options.approval_exe.resolve()
    if options.event_log:
        options.event_log = options.event_log.resolve()
    cli = shutil.which("codex")
    if not cli:
        raise RuntimeError("Codex CLI not found")
    config_path = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    before = config_path.read_bytes()
    settings = tomllib.loads(before.decode("utf-8-sig"))
    with tempfile.TemporaryDirectory(prefix="nijika-codex-stop-") as directory:
        temporary = Path(directory)
        database = temporary / "notifications.sqlite3"
        overrides = [
            "notify=[]", "features.hooks=true", "project_doc_max_bytes=0",
            "shell_environment_policy.inherit=core",
            "shell_environment_policy.set.NIJIKA_PET_DB_PATH=" + toml_text(str(database)),
        ]
        # Reuse only non-secret endpoint/model settings in ephemeral argv. The
        # CLI reads its own existing login. No config/token is copied to disk.
        for key in ("model", "openai_base_url", "model_reasoning_effort", "model_provider"):
            if isinstance(settings.get(key), str):
                overrides.append(key + "=" + toml_text(settings[key]))
        if settings.get("model_provider", "openai") != "openai":
            raise RuntimeError("Custom providers require a separately reviewed isolated setup")
        for event in ("UserPromptSubmit", "PermissionRequest", "PostToolUse", "Stop"):
            invocation = "$env:NIJIKA_PET_DB_PATH = '" + str(database).replace("'", "''") + "'; "
            if options.event_log:
                event_log = str(options.event_log).replace("'", "''")
                invocation += (
                    "$payload=[Console]::In.ReadToEnd(); "
                    "$obj=$payload | ConvertFrom-Json; "
                    "$record=[ordered]@{event=$obj.hook_event_name; "
                    "has_message=($null -ne $obj.last_assistant_message); "
                    "message_length=$(if($null -eq $obj.last_assistant_message){-1}else{$obj.last_assistant_message.Length}); "
                    "has_prompt=($null -ne $obj.prompt); "
                    "prompt_length=$(if($null -eq $obj.prompt){-1}else{$obj.prompt.Length})}; "
                    "[IO.File]::AppendAllText('" + event_log + "', "
                    "(($record | ConvertTo-Json -Compress) + [Environment]::NewLine)); "
                    "$payload | "
                )
            invocation += "& '" + str(options.approval_exe).replace("'", "''") + "'"
            invocation += (" --event " + event if event in {"Stop", "UserPromptSubmit"} else "")
            command = 'powershell.exe -NoLogo -NoProfile -NonInteractive -Command "' + invocation + '"'
            timeout = 15 if event in {"Stop", "UserPromptSubmit"} else 5
            group = ('{ hooks = [{ type = "command", timeout = ' + str(timeout)
                     + ', command = ' + toml_text(command) + ' }] }')
            overrides.append("hooks." + event + "=[" + group + "]")
        if options.case == "notice":
            overrides.extend([
                "mcp_servers.nijika-pet.command=" + toml_text(str(ROOT / "dist" / "虹夏MCP-v2.exe")),
                "mcp_servers.nijika-pet.env.NIJIKA_PET_DB_PATH=" + toml_text(str(database)),
                'mcp_servers.nijika-pet.env.NIJIKA_AGENT_NAME="Codex"',
                'mcp_servers.nijika-pet.tools.show_completion.approval_mode="approve"',
            ])
        arguments = [cli, "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
                     "--dangerously-bypass-hook-trust", "--sandbox", "danger-full-access",
                     "--json", "-C", str(temporary)]
        for value in overrides:
            arguments.extend(["-c", value])
        prompts = {
            "work": "请只在当前临时目录创建 proof.txt，内容为 nijika-codex-stop-test，然后读取确认。"
                    "最后用中文简述实际检查结果并写明已完成。不要调用任何桌宠工具，不要读写其他目录。",
            "question": "1+1等于几？只回答数字，不调用工具。",
            "notice": "请只调用一次 nijika-pet 的 show_completion，task 为 Codex独立提醒测试，"
                      "summary 为 已完成本机隔离工具测试。不要读写文件，不要等待点击；工具返回后直接结束任务。",
        }
        environment = os.environ.copy()
        environment["NIJIKA_PET_DB_PATH"] = str(database)
        # codex.cmd is only a launcher on Windows. subprocess receives argument
        # lists; avoid composing a cmd.exe script out of user-provided text.
        result = subprocess.run(arguments + ["-"], input=prompts[options.case].encode("utf-8"),
                                capture_output=True, env=environment, timeout=options.timeout)
        if options.event_log:
            with options.event_log.open("a", encoding="utf-8") as log:
                log.write(json.dumps({
                    "runner": "codex",
                    "returncode": result.returncode,
                    "stdout_length": len(result.stdout),
                    "stderr_length": len(result.stderr),
                }) + "\n")
        if config_path.read_bytes() != before:
            raise AssertionError("Real user config unexpectedly changed")
        if result.returncode:
            # Do not dump model output or environment/config; errors may contain
            # unrelated local details. Keep the type and exit code actionable.
            raise RuntimeError(f"Codex CLI failed ({result.returncode}); no production config changed")
        events = []
        for line in result.stdout.decode("utf-8", errors="replace").splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
        assert any(event.get("type") == "turn.completed" for event in events), "No completed CLI turn"
        assert database.is_file(), "Lifecycle hooks did not create isolated queue"
        # Hook processes are launched asynchronously by the CLI. Give the
        # completion hook a short drain window before asserting the queue.
        for _ in range(40):
            with contextlib.closing(sqlite3.connect(database)) as connection:
                state = connection.execute(
                    "SELECT COUNT(*), SUM(has_user_prompt), SUM(completion_notice_sent) "
                    "FROM codex_turn_state",
                ).fetchone()
                notices = connection.execute("SELECT agent, title FROM notifications").fetchall()
            if options.case == "notice" and notices:
                break
            if options.case != "notice" and state[2]:
                break
            time.sleep(0.25)
        with contextlib.closing(sqlite3.connect(database)) as connection:
            state = connection.execute(
                "SELECT COUNT(*), SUM(has_user_prompt), SUM(completion_notice_sent) FROM codex_turn_state",
            ).fetchone()
            notices = connection.execute("SELECT agent, title FROM notifications").fetchall()
        assert state[0] >= 1 and state[1] >= 1, (
            "No valid UserPromptSubmit event; "
            f"state_rows={state[0]}, notices={len(notices)}, "
            f"stderr_timeout_mentions={result.stderr.lower().count(b'timeout')}, "
            f"stderr_hook_mentions={result.stderr.lower().count(b'hook')}"
        )
        if options.case == "work":
            assert (temporary / "proof.txt").read_text(encoding="utf-8-sig").strip() == "nijika-codex-stop-test"
            assert notices == [("ChatGPT", "任务完成")] and state[2] == 1, "Expected one fallback notice"
        elif options.case == "question":
            assert notices == [("ChatGPT", "任务完成")] and state[2] == 1, (
                "Every non-empty reply should create one completion notice: "
                f"notices={notices!r}, state={state!r}"
            )
        else:
            assert notices == [("ChatGPT", "Codex独立提醒测试")] and not state[2], (
                f"Explicit notice duplicated: notices={notices!r}, state={state!r}"
            )
        print(f"Real Codex CLI {options.case}: turn completed, valid prompt state, "
              f"{len(notices)} total notices ({state[2]} fallback); user config/notify/trust unchanged "
              f"(SHA256 {hashlib.sha256(before).hexdigest()[:12]}).")


if __name__ == "__main__":
    main()
