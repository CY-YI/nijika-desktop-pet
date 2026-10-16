# 接入 Agent：Codex、ChatGPT Work、DSH、Claude Code 与其他本机客户端

## 优先使用设置中心（2026-10-16）

双击桌面的“虹夏桌宠设置”，或右键已更新的桌宠选择“设置中心 / 添加 Agent”（等价于 `虹夏桌宠.exe --control-panel`）。选择客户端、给伙伴命名，常用配置路径会自动填入；仅使用其他用户目录时展开高级位置。点击“检测并继续”，核对具体文件、备份和保留行为，再选择“应用并添加”。已有 Codex `nijika-pet` 服务会保留；同名服务路径失效或存在冲突时停止并提示，不盲目覆盖。

Codex 向导合并 MCP、交互技能和全局触发规则；DSH 向导合并 desktop/web 配置与专用技能；Work 向导在用户数据目录准备本机插件，再调用 Codex CLI 注册与安装。Work 当前仍需 PATH 中可用的 `codex` 和 `python.exe`，仅限能运行本机程序的 Work。

**其他客户端的最短接入流程**：选择“其他 MCP 客户端”并命名 → “检测并继续” → “生成并保存接入文件” → “复制自动配置提示词”，直接发给同一电脑上有文件读写、执行能力的 AI。它会识别自身客户端，核实配置位置，备份、合并 MCP 与持久提醒规则，再验证。无需手动下载 JSON 或逐项填写字段；卡片的“下载配置副本”仅供高级用途。

每个伙伴都有固定的本机接入目录，界面显示实际绝对路径，默认位于 `%USERPROFILE%\.nijika-desktop-pet\integrations\agents\<档案ID>\`（自定义消息库时跟随其目录）。目录内自动保存：

| 文件 | 用途 |
| --- | --- |
| `nijika-mcp.json` | 含本机 MCP 程序完整路径及来源名称的标准 stdio 配置 |
| `nijika-agent-instructions.txt` | 任务完成、选择题、推荐选项与等待回执的持久提醒规则 |
| `nijika-setup-prompt.txt` | 与“复制自动配置提示词”完全相同的完整安装提示词 |
| `SKILL.md` | 对应客户端的桌宠交互技能，按客户端能力安装 |

提示词自身也附完整 JSON、规则、上述文件路径及客户端已知目标路径；不依赖接收方先手动寻找文件。已添加的旧伙伴点击“接入步骤”时会补生成这些文件；仅刷新页面不写入文件。接入目录保留用于后续核对和重新接入，移除伙伴档案不删除它或外部客户端配置。文件不包含模型密钥，不进入 Git 或分享包。

**能力边界**：普通云端聊天不能修改本机文件；未知客户端的目标配置路径必须由接收 AI 检测，无法唯一识别时只询问客户端名称或配置作用域。客户端若必须重载或本人确认权限，仍需完成这一必要步骤；提示词要求如实报告“配置已写入，待新会话验证”，不虚报全部完成。

配置成功后按说明重启客户端或新建任务。面板“测试提醒”由面板直接发送，点击结果会显示“本机测试已点击”，证明桌宠显示与队列回传可用；这不等于外部 Agent 已发现工具或会主动调用。还需在客户端新任务让 Agent 发出一次选择题。普通通知的状态与命令审批 hook 的本人信任分别处理。移除面板档案不删除客户端原配置。

向导第三步和已有卡片的“接入步骤”均提供上述完整自动配置提示词。以下短提示词仅供**已完成配置、工具已经可见**时单独验证；首次接入请优先复制界面中的完整提示词。

**Codex 与 DSH 通用验证提示词**（把客户端的虹夏工具已经可见作为前提）：

```text
这个任务结束时，请用虹夏桌宠的 show_completion 给我发一条桌面完成提醒，标题写任务名，summary 写一句话结果。如果中途需要我在两个方案里做选择，请改用 request_decision，每个选项写清楚名称和一句说明，然后等我点击。现在先调用一次工具让我确认链路是否通。
```

**ChatGPT 桌面客户端 Work**：先重启客户端并打开一个本机运行的 Work 新任务，再粘贴上段提示词；云端 Work 不能运行本机程序。

**其他 MCP 客户端**（工具名统一为 `nijika-pet`）：

```text
你有一个名为 nijika-pet 的 MCP 工具。任务结束时用 show_completion 发桌面完成提醒；需要我在方案间选择时用 request_decision，给出每个选项的名称和一句说明，等待我点击后再继续。
```

看不到“接入步骤”时，在“Agent 接入”页对应伙伴卡片上点“接入步骤”，可随时重新查看该客户端的步骤与提示词。

向导的“接入步骤”里同时列出这次配置用到的每个文件与绝对路径，可逐条复制或点“复制全部路径”。各客户端的文件位置如下（`<用户目录>` 为你的 Windows 用户目录，例如 `C:\Users\CY`）：

| 客户端 | MCP 程序 | 客户端配置 | 主动提醒规则 | 技能（可选） |
| --- | --- | --- | --- | --- |
| Codex | `dist\虹夏MCP-v2.exe` | `<用户目录>\.codex\config.toml` | `<用户目录>\.codex\AGENTS.md` | `<用户目录>\.codex\skills\nijika-desktop-dialog\SKILL.md` |
| Claude Code | `dist\虹夏MCP-v2.exe` | `<用户目录>\.claude.json`（用户级 MCP）；审批钩子在 `<用户目录>\.claude\settings.json` | `<用户目录>\.claude\CLAUDE.md` | `<用户目录>\.claude\skills\nijika-desktop-dialog\SKILL.md` |
| Work | `dist\虹夏MCP-v2.exe` | `<用户目录>\.nijika-desktop-pet\integrations\work\plugins\nijika-work-local\mcp.json`（另有插件清单） | 插件技能内的规则 | 插件内 `skills\nijika-work-dialog\SKILL.md` |
| DSH | `dist\虹夏MCP-v2.exe` | `<用户目录>\.dsh\profiles\desktop\cordis.patch.yml` 与 `profiles\web\cordis.patch.yml` | `<用户目录>\.dsh\AGENTS.md` | `<用户目录>\.dsh\skills\nijika-dsh-dialog\SKILL.md` |
| 其他 MCP 客户端 | `dist\虹夏MCP-v2.exe` | 专属接入目录的 `nijika-mcp.json`；实际客户端目标由接收 AI 核实 | 同目录的 `nijika-agent-instructions.txt` | 同目录的 `SKILL.md`，由接收 AI 按客户端规则安装 |

`config.toml` 与 `cordis.patch.yml` 中写入的服务名分别为 `nijika-pet` 和 `mcp-nijika-pet`，`NIJIKA_AGENT_NAME` 决定气泡显示的来源名。路径由向导自动填入，不需要手抄；上述表格用于手动排查。

向导不读取或要求填写模型密钥，不替用户信任 hook，不开放云端入口。以下命令说明保留，供高级配置和故障排查。

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

先按 [INSTALL.md](INSTALL.md) 安装 Python 依赖并运行 `build.ps1`，确认 `dist/` 中生成三个 EXE（桌宠与设置共用一个）。桌宠仍需单独启动。

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

### Claude Code

Claude Code 的用户级接入由三部分组成；设置中心向导可为 Claude Code 档案生成 MCP 配置与提示词，审批钩子需按本节手动注册。

1. 注册 MCP：`claude mcp add -s user nijika-pet -- "<项目>\dist\虹夏MCP-v2.exe"`，用户级配置写入 `%USERPROFILE%\.claude.json`（改动前先备份原文件）。注册后可用 `claude mcp list` 核对已连接，并在新会话中确认 `nijika-pet` 的四个工具可见：`show_completion`、`request_decision`、`wait_for_reply`、`get_reply`。
2. 提醒规则：把何时提醒、同一请求连续等待、恢复会话先 `get_reply` 的规则合并进 `%USERPROFILE%\.claude\CLAUDE.md`；仓库级 `AGENTS.md` 只覆盖本仓库。
3. 可选技能：把 `skills\nijika-desktop-dialog\SKILL.md` 复制到 `%USERPROFILE%\.claude\skills\nijika-desktop-dialog\`。

**Claude Code 命令审批提醒（可选）**：普通决策由 Agent 调 MCP，权限提示出现时的自动气泡则由 Claude Code 自己的权限事件钩子触发，两者是不同入口。编辑用户级 `%USERPROFILE%\.claude\settings.json` 前先备份，然后只新增顶层 `hooks` 键（保留文件其余内容）：

```json
{
  "hooks": {
    "PermissionRequest": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "C:\\path\\to\\提示功能作用的桌宠\\.venv\\Scripts\\python.exe",
            "args": ["C:\\path\\to\\提示功能作用的桌宠\\approval_hook.py", "--source", "claude-code"],
            "timeout": 10
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [
          {
            "type": "command",
            "command": "C:\\path\\to\\提示功能作用的桌宠\\.venv\\Scripts\\python.exe",
            "args": ["C:\\path\\to\\提示功能作用的桌宠\\approval_hook.py", "--source", "claude-code"],
            "timeout": 10,
            "async": true
          }
        ]
      }
    ]
  }
}
```

把两处 `command` 与 `args` 换成该电脑上项目 venv 的 `python.exe` 与 `approval_hook.py` 的真实绝对路径。示例采用 exec 形式直接拉起程序、不经 shell，路径含空格或中文也安全；`PostToolUse` 的 `async: true` 不阻塞任务。JSON 必须合法，否则整个设置文件会被忽略。与 Codex 不同，Claude Code 自有 hook 没有单独的信任步骤，请自行核对上述路径；会话运行中也会热加载新配置。测试时应在产生权限提示的任务中同时看到 Claude Code 权限提示与“命令需要授权”气泡；气泡“知道了”只记录收到提醒，**不授予权限**，授权仍在 Claude Code 权限提示中完成；命令完成后，尚未点击的匹配提醒由 `PostToolUse` 收起。

与 Codex 一样，源码侧 `approval_hook.py` 用 `--source claude-code` 区分署名与文案，Codex 行为不受影响。2026-10-16 本机实测：合成事件经注册命令全链路通过、运行中会话热加载生效，预创建的匹配通知被一次真实 `PostToolUse` 自动收起；真实 `PermissionRequest` 的自然触发在低提示权限模式下仍待验收。回退：删除上述 `hooks` 键或恢复编辑前的备份；源码侧 `git revert` 对应提交。分享包暂不含 Claude Code 钩子的注册脚本，需按本节手动注册；重建 `虹夏审批提醒.exe` 后，同款去重修复才适用于 Codex 打包路径。

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
