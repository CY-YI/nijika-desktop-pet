# 接入 Agent：Codex、ChatGPT Work、DSH 与其他本机客户端

虹夏的两个核心程序是：`虹夏桌宠.exe` 负责桌面显示，`虹夏MCP-v2.exe` 是 Agent 按需启动的 stdio MCP 服务；另附可选的 `虹夏审批提醒.exe` 用于 Codex 的命令审批事件。它们须在**同一台 Windows 10/11 x64 电脑、同一用户会话**中运行；只需手动启动桌宠，不要手动双击 MCP 或审批程序。MCP 不开放网络端口，普通云端聊天无法直接调用本机 EXE。

## 已收到 Windows 私下试用 ZIP

完整解压 ZIP，在解压目录打开 PowerShell。先安装桌宠：

```powershell
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1
```

已有相应 Agent 客户端时，退出桌宠和旧任务，再按需运行以下命令；也可以把 `-Codex -Work -Dsh` 合并在同一次安装中：

```powershell
# Codex：注册 MCP、安装技能，并添加全局触发规则
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1 -Codex -NoLaunch

# ChatGPT 桌面客户端的本机 Work：安装本地插件和技能
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1 -Work -NoLaunch

# DeepSeek Harness：配置 desktop/web、安装技能与触发规则
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1 -Dsh -NoLaunch
```

`-Codex` 和 `-Work` 要求 PowerShell 能找到 `codex` 命令；`-Work` 还要求能找到 `python.exe`。`-Dsh` 要求该用户已经初始化 `%USERPROFILE%\.dsh`。安装脚本默认将程序放到 `%LOCALAPPDATA%\NijikaDesktopPet\app`，因此解压目录搬走后配置仍有效。想开机启动桌宠，可在首次安装命令后加 `-AutoStart`。

## 从 Git 源码构建

先按 [INSTALL.md](INSTALL.md) 安装 Python 依赖并运行 `build.ps1`，确认 `dist/` 中生成三个 EXE。桌宠仍需单独启动。

### Codex

在项目根目录运行：

```powershell
$mcpExe = (Resolve-Path -LiteralPath '.\dist\虹夏MCP-v2.exe').Path
codex mcp add nijika-pet -- $mcpExe
codex mcp get nijika-pet

$skillDir = Join-Path $env:USERPROFILE '.codex\skills\nijika-desktop-dialog'
New-Item -ItemType Directory -Path $skillDir -Force | Out-Null
Copy-Item -LiteralPath '.\skills\nijika-desktop-dialog\SKILL.md' -Destination $skillDir -Force
```

把 [Codex 全局触发规则](distribution/codex-global-instructions.txt) 合并到 `%USERPROFILE%\.codex\AGENTS.md`，可使其他工程的新 Codex 任务也知道何时使用桌宠；本仓库的 `AGENTS.md` 只覆盖本仓库。若已存在同名 `nijika-pet` 服务，先用 `codex mcp get nijika-pet` 核对旧路径，不要重复添加。新开 Codex 任务后再测试；旧任务不保证热加载工具和技能。

### Codex 命令审批提醒（可选）

普通决策由 Agent 调用 MCP，命令权限申请则由 Codex 的审批事件触发，两者是不同入口。源码构建完成后运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\integrations\codex\install-hooks.ps1
```

试用包安装时可改用 `distribution/install.ps1 -Codex -CodexHooks -NoLaunch`。脚本向 `%USERPROFILE%\.codex\hooks.json` 添加 `PermissionRequest` 和 `PostToolUse` 定义，保留其他 hook 并备份已有文件；重复安装替换本项目条目，不重复叠加。

**安装定义后还须本人审阅并信任这两个 hook。** 在 Codex CLI 交互会话输入 `/hooks`，核对它们调用的是本机 `虹夏审批提醒.exe`，按界面完成审阅，再开新任务。[Codex 官方 hooks 文档](https://learn.chatgpt.com/docs/hooks)要求非托管 hook 在审阅并信任前跳过执行；本脚本不会替你写入信任或修改审批策略。

当前 CLI 的 `/hooks` 页分别显示 `Installed / Active / Review`：仅安装时两项均为 `1 / 0 / 1`，不能视为已启用执行。回车可审阅选中的事件；页面底部的 `t trust all` 用于保存信任（仅在核对所有列出的 hook 都愿意信任时使用）。确认本项目两项的 `Active` 变为 `1`、`Review` 变为 `0`。在桌宠选择“已设置信任”只是状态回传，不会修改 Codex 的信任配置；若仍显示 `untrusted`，请核对该 CLI 使用的配置目录与来源路径。

在会产生审批卡的任务中测试：保持虹夏运行，执行一个由当前审批策略要求授权的实际操作，应同时看到 Codex 审批卡和“命令需要授权”气泡。气泡“知道了”只记录收到提醒，**不会授予权限**；仍在 Codex 审批卡批准或拒绝。操作完成后，尚未点击的匹配提醒由 `PostToolUse` 收起。使用“不请求审批”的任务不会产生 `PermissionRequest` 事件。当前集成只覆盖本机 Codex 的受支持事件；不能据此声称 Work、DSH 或云端执行的系统权限也已接通。

2026-10-11 本机实测：用户完成信任后，运行时确认两项 hook 均已信任、启用。独立 Codex CLI 在 `on-request` / `read-only` 下弹出真实审批卡，虹夏自动显示提醒，用户点击“知道了”的回执已保存；原审批继续等待授权，随后取消测试申请，未执行申请中的写入操作。这项验收覆盖本机 Codex CLI。安装到其他电脑仍须由该电脑的用户自行审阅并信任，不分发本机的信任记录。

维护者可运行 `.\.venv\Scripts\python.exe tools\smoke_approval_hook.py` 隔离检查安装幂等性、打包 hook 的 stdin 输入、去重与操作完成后的收起。模拟事件不执行其中的命令，也不等同于真实平台审批验收。

### ChatGPT 桌面客户端 Work（本机任务）

源码插件位于 `plugins/nijika-work-local/`，`mcp.json` 使用可移植标记，由启动脚本查找本项目的 `dist/虹夏MCP-v2.exe`、`NIJIKA_MCP_EXE` 指定的程序，或默认安装目录。确保 `python.exe` 和 `codex` 都能从 PowerShell 找到，再从项目根目录运行：

```powershell
codex plugin marketplace add . --json
codex plugin add nijika-work-local@nijika-local --json
codex plugin list --marketplace nijika-local --json
```

确认插件为 `installed: true`、`enabled: true`，重启 ChatGPT 桌面客户端，然后在**本机运行的新 Work 任务**中测试。普通聊天和云端 Work 不会自动获得本机 stdio MCP 工具。插件文件更新后也要刷新安装并重启客户端；当前已打开任务不保证热更新。

### DeepSeek Harness（DSH）

DSH 已在本机建立 `%USERPROFILE%\.dsh` 后，在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\integrations\dsh\install.ps1
```

安装脚本将 desktop/web 两个 profile 指向本机 MCP EXE，并复制 `nijika-dsh-dialog` 技能、写入全局触发规则。若只需要一个 profile，可传 `-Profiles desktop` 或 `-Profiles web`。重启 DSH 并新开会话；配置细节见 [DSH 接入说明](integrations/dsh/README.md)。

## 其他支持 stdio MCP 的本机 Agent

其配置格式由客户端决定。核心字段是以**绝对路径**启动 `虹夏MCP-v2.exe`，不传命令行参数；可设置 `NIJIKA_AGENT_NAME`，让桌面气泡标明来源。例如采用 `mcpServers` 格式的客户端可参考：

```json
{
  "mcpServers": {
    "nijika-pet": {
      "command": "C:/path/to/虹夏MCP-v2.exe",
      "args": [],
      "env": {"NIJIKA_AGENT_NAME": "MyAgent"}
    }
  }
}
```

把示例路径改成该电脑上 EXE 的真实绝对路径。为了让 Agent **主动**在需要审阅或选择时调用工具，还需给该客户端添加触发说明，可参考 [Codex 技能](skills/nijika-desktop-dialog/SKILL.md) 或 [DSH 技能](integrations/dsh/nijika-dsh-dialog/SKILL.md) 并适配其工具名称。仅注册 MCP 不保证模型每次都会主动调用。

## 验证与当前边界

三个本机入口默认共用 `%USERPROFILE%\.nijika-desktop-pet\notifications.sqlite3`。更新桌宠与 MCP 后重新启动桌宠；已有旧 MCP 进程的待处理消息由兼容桥接保留原 ID，点击仍会回传。新配置不要继续指定旧 AppData 路径；隔离测试可显式设置 `NIJIKA_PET_DB_PATH`。

1. 确认桌面能看到虹夏；在 Agent **新任务**里提出一个确实需要你二选一的简短问题。
2. Agent 应调用 `request_decision`，气泡显示来源、问题、各选项的一句影响说明；点击后 Agent 应通过 `wait_for_reply`/`get_reply` 读回，并在**原聊天**写明所选项。
3. 任务完成但内容太长时，Agent 可调用 `show_completion` 提醒你回聊天查看。`pending` 只表示本机排队，不代表气泡已显示或你已批准。

晚到的点击保存在本机消息库，但 Agent 任务若已经结束，当前 stdio MCP **不会自动唤醒该任务**；在原聊天发送“继续”，技能要求先读取旧请求。Codex、Work 和 DSH 的长期等待与晚到回复仍需各自在新任务中现场验收。
