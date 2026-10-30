# 接入 Agent：Codex、ChatGPT Work、DSH、Claude Code 与其他本机客户端

## 2026-10-29 扫描本机与批量接入

设置中心的“扫描本机”只检查已知命令和配置位置，不读取聊天、凭据、登录或额度，不扫描全盘。勾选后点“预览勾选项”，确认每项文件、预期气泡来源和外部操作，再“应用可接入项”。每个客户端独立备份、检查预览后的变更并返回结果；一项失败不回滚其他成功项。Work 注册可能部分完成或超时，需先核对插件状态，不能盲目重试。

| 客户端 | 本轮接入方式 | 用户级配置与规则 |
| --- | --- | --- |
| Codex | 现有 TOML 安全适配 | `CODEX_HOME` 或 `~/.codex` 的 config.toml、AGENTS.md、交互技能 |
| 本机 Work | 现有插件注册 | 本机插件暂存目录；需要 Codex CLI 和 python.exe；发现依赖不证明 Work 应用已安装 |
| DSH | 现有双 profile 适配 | `~/.dsh/profiles/{desktop,web}/cordis.patch.yml`、AGENTS.md、技能 |
| Claude Code | 新增 JSON 适配 | `~/.claude.json`、`~/.claude/CLAUDE.md`；发现项目级虹夏配置时停止自动写入 |
| Gemini CLI | 新增 JSON 适配 | `~/.gemini/settings.json`、GEMINI.md |
| Copilot CLI | 新增 JSON 适配 | `COPILOT_HOME` 或 `~/.copilot` 的 mcp-config.json、copilot-instructions.md |
| WorkBuddy / WorkBuddy AI / VS Code / Obsidian / Claude Desktop | 发现入口，生成指引 | 具体扩展、项目或插件作用域由接收方 AI 核对，不自动猜格式或写入 |

若 MAGPIE 已向该目标分发虹夏，本向导只保存档案与只读核对提示词，不写客户端配置、不修改 MAGPIE 库、不执行插件注册。想切换管理器时，先在 MAGPIE 取消该目标分发，再重新扫描。库无法安全读取或预览后有变更时停止应用，避免两个管理器争抢配置。同名未知程序、别名权限冲突、JSON 重复字段或过大配置也不会自动覆盖。

来源仍按“Agent · 所在软件”显示，底层模型不明的多模型软件使用 Agent。这里的路由是本机 MCP 配置分发和独立回执，不代理模型 API，也不读取账户密钥。

**验证分为四件事**：找到入口、写入配置、收到宿主工具调用、桌面消息点击。面板测试只能证明本机链路。新版直接配置含非秘密 `NIJIKA_PROFILE_ID`，新 MCP 在成功创建通知后记录该档案最新请求编号，界面据此显示调用与点击；只列出工具不会算调用。旧连接、旧配置或 MAGPIE 共享服务没有该编号时，不自动认领为某个档案已验证。档案编号与来源名称都不是身份认证或权限隔离，同一用户的可信客户端仍共享本地消息库。

格式依据：Claude Code 的 MCP / memory 官方文档，Gemini CLI 的 MCP / GEMINI.md 官方文档，GitHub Copilot CLI 的 MCP / custom instructions 官方文档。自定义配置根目录或工作区覆盖需单独核对；不承诺已在每个真实宿主、登录环境及版本中完成自然任务测试。

## 2026-10-29 新版向导与旧配置迁移

“其他 MCP 客户端”现在分开填写管理昵称、Agent 名称、所在软件：例如昵称“编程伙伴”、Agent“Claude”、软件“VS Code”，气泡头部为“Claude · VS Code”。软件必填；不知道模型时 Agent 留空即为 Agent。Codex、Work、DSH 的两项来源由专属适配器填写。生成 JSON、自动配置提示词、下载副本与本机测试使用同一来源。

同一份固定软件来源配置只用于对应宿主，不要在共享管理器中分配给全部软件。共享的 auto 握手仍有识别边界，编辑器复用引擎时应逐软件配置。面板显示“气泡来源”是预期来源，不能证明外部客户端已加载；最后仍需新会话实际调用，并对照气泡头部。旧会话须重连，第三方管理器以后再次覆盖配置时需重新核对。

Codex 将当前虹夏程序的已验证别名合并为 nijika-pet，保留权限等设置。有冲突或旧程序无法核实时停止，不覆盖、不新增第二份；只有旧路径程序与当前程序摘要一致才自动迁到当前路径，并在确认页列出前后路径。旧版本摘要不同，需要先人工核实后迁移。内联服务或特殊 TOML 布局不支持时也停止。

DSH 前端和独立安装脚本只移除旧 Magpie 虹夏列表项，同 insert 中其他服务保留；不支持的复杂 YAML 会报错并停止。预览不写文件，应用前备份并检查预览后变化；权限信任仍由用户在宿主内处理。


## 2026-10-28：通知头部的 Agent 与软件

DSH 桌面实际使用 `dsh-mcp-client` 握手名；现已覆盖该名称及旧包名别名。更新 MCP 后，现有 stdio 连接仍可能持有旧程序。重连虹夏服务后生效，无需重复安装或重新配置所有 Agent。旧记录缺软件字段时不会根据任务正文猜测或批量改写历史来源。

头部第一行显示 `Agent · 软件`，第二行是任务名。例如 `ChatGPT · Codex`、`ChatGPT · Work`、`Claude · VS Code`、`ChatGPT · Obsidian`。这是显示身份，不代表授权身份，也不保证能得知实际模型版本。

新配置将两个字段分开：

```json
{"env":{"NIJIKA_AGENT_NAME":"ChatGPT","NIJIKA_HOST_NAME":"Codex"}}
```

- `NIJIKA_AGENT_NAME`：Agent 名称，20 字符以内；多模型宿主未知时使用 `Agent`。
- `NIJIKA_HOST_NAME`：实际软件或模式，40 字符以内，例如 Work、Codex、VS Code、Obsidian。共享管理库分发同一服务到多客户端时使用 `NIJIKA_AGENT_NAME=auto` 且不固定 HOST，让每次握手分别识别；不能把写死 DSH 的配置勾选给全部客户端。
- 单次工具调用也可传可选 `agent_name` 和 `software` 来细化来源。例如 `show_completion(task="接入检查",summary="配置检查已完成。",agent_name="Claude",software="VS Code")`。旧连接没有这两个参数时先按旧 schema 调用，重新连接后才使用新参数。
- `task` 只写具体任务名。桌宠仅去除任务开头带分隔符的自身重复前缀；正文里正常提及其他 Agent 不受影响，历史数据库不批量重写。
- 一台客户端、同一配置作用域中，同一虹夏程序只留一个 MCP 服务。`nijika-pet` 和 `nijika_pet` 同时指向同一程序会产生重复工具入口；两条相同正文不能简单按文字去重，因为可能来自不同会话的独立问题。
- DSH/WorkBuddy 可切换模型，不自动推测为 DeepSeek/Claude。默认显示 `Agent · DSH` 或 `Agent · WorkBuddy`，有可靠身份时由配置/单次调用补充。
- 编辑器内运行的 Agent 可能仍握手为 Codex/Claude Code/DSH。需要编辑器专用配置或单次 `software="VS Code"`/`"Obsidian"`；引擎握手本身无法证明外层软件。

更新 EXE 和配置不会热更新已连接的 stdio 进程。保存当前工作后，在客户端重新连接虹夏或重开对应任务；共享管理器也应重新打开以读取已修正库。无需重建模型 API 配置。审批气泡仍只提醒，不能授予命令权限。

维护审计：`python tools/repair_nijika_sources.py --output diagnostics/source-audit.json` 默认只读；本机 DSH YAML 审计需 PyYAML（工具依赖，不是桌宠运行依赖）。执行 `--apply --backup <本机目录>` 才修正已识别的虹夏条目；备份只保存虹夏片段，不复制完整账号配置。不要将本机备份或诊断上传。


## 优先使用设置中心（2026-10-16）

双击桌面的“虹夏桌宠设置”，或右键已更新的桌宠选择“设置中心 / 添加 Agent”（等价于 `虹夏桌宠.exe --control-panel`）。选择客户端、给伙伴命名，常用配置路径会自动填入；仅使用其他用户目录时展开高级位置。点击“检测并继续”，核对具体文件、备份和保留行为，再选择“应用并添加”。已有 Codex `nijika-pet` 服务会保留；同名服务路径失效或存在冲突时停止并提示，不盲目覆盖。

Codex 向导合并 MCP、交互技能和全局触发规则；DSH 向导合并 desktop/web 配置与专用技能；Work 向导在用户数据目录准备本机插件，再调用 Codex CLI 注册与安装。Work 当前仍需 PATH 中可用的 `codex` 和 `python.exe`，仅限能运行本机程序的 Work。Claude Code 尚无专属向导选项，可使用“其他 MCP 客户端”的完整提示词让接收 AI 核对自身格式，或按下方专节手动接入。

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

2026-10-18 教程复验：动画/养成增量没有改变四个 MCP 工具、共享队列或标准安装路径，现有连接无需因动画代码变更重配。自动提示词现已明确短成果可在气泡直接审阅、完整字段限制、实际客户端工具前缀、无效输入修正、连续等待和晚到回执；不承诺每次都主动调用或点击唤醒已结束的会话。Codex 清单另列可选 hooks.json、安装脚本与通知程序的实际路径，说明四事件及本人信任；默认 MCP 向导并不自动安装原生钩子，只有用户要求该能力时才由接收 AI 按既有授权补装。Work/DSH 当前没有同等原生审批/完成桥接，不能照抄 Codex 钩子或将 MCP 测试当成其已接通。

本机已更新正式桌宠与三份旧接入文件；旧文件有本机备份。已配置的 Agent 无需重配或重复信任；需要给其他 AI 配置时，重新打开“设置中心 → Agent 接入 → 接入步骤 → 复制自动配置提示词”即可。桌面快捷方式仍指向同一安装目录。本次正式程序基于已验收版本只补教程及管理参数转发，未包含待定的互动预览。

本轮验证包括 69 项源码回归、5 项前端控制器测试、61 项正式版构建源回归，以及构建版和确切安装版 EXE 的隔离 plan→apply→prepare；安装版与工作区的 MCP 均完成真实 stdio 四工具发现和选择回执。Work 的 CLI 安装通过隔离模拟验证，本轮没有重装真实插件或进行 Work 会话端到端验收。浏览器权限仍拒绝本地地址，本轮没有重复执行页面点击/布局验收；API 结果不当作页面或外部 Agent 自动调用的证明。

配置成功后按说明重启客户端或新建任务。面板“测试提醒”由面板直接发送，点击结果会显示“本机测试已点击”，证明桌宠显示与队列回传可用；这不等于外部 Agent 已发现工具或会主动调用。还需在客户端新任务让 Agent 发出一次选择题。普通通知的状态与命令审批 hook 的本人信任分别处理。移除面板档案不删除客户端原配置。

向导第三步和已有卡片的“接入步骤”均提供上述完整自动配置提示词。以下短提示词仅供**已完成配置、工具已经可见**时单独验证；首次接入请优先复制界面中的完整提示词。

**Codex 与 DSH 通用验证提示词**（把客户端的虹夏工具已经可见作为前提）：

```text
这个任务结束时，请用虹夏桌宠的 show_completion 给我发一条桌面完成提醒，标题写任务名，summary 写一句话结果。如果中途需要我在两个方案里做选择，请改用 request_decision，每个选项写清楚名称和一句说明，然后等我点击。现在先调用一次工具让我确认链路是否通。
```

**ChatGPT 桌面客户端 Work**：先重启客户端并打开一个本机运行的 Work 新任务，再粘贴上段提示词；云端 Work 不能运行本机程序。

**其他 MCP 客户端**（`nijika-pet` 是服务名，使用客户端实际显示的工具名称）：

```text
请使用已接入的虹夏 MCP 服务，工具名以当前客户端实际暴露的前缀为准。任务结束时用 show_completion 发桌面完成提醒；需要我在方案间选择时用 request_decision，给出每个选项的名称和一句说明，等待并读取我点击后再继续。
```

看不到“接入步骤”时，在“Agent 接入”页对应伙伴卡片上点“接入步骤”，可随时重新查看该客户端的步骤与提示词。

向导的“接入步骤”里同时列出这次配置用到的每个文件与绝对路径，可逐条复制或点“复制全部路径”。各客户端的文件位置如下（`<用户目录>` 为你的 Windows 用户目录，例如 `C:\Users\YourName`；以自己机器上向导生成的实际路径为准）：

| 客户端 | MCP 程序 | 客户端配置 | 主动提醒规则 | 技能（可选） |
| --- | --- | --- | --- | --- |
| Codex | `dist\虹夏MCP-v2.exe` | `<用户目录>\.codex\config.toml` | `<用户目录>\.codex\AGENTS.md` | `<用户目录>\.codex\skills\nijika-desktop-dialog\SKILL.md` |
| Claude Code | `dist\虹夏MCP-v2.exe` | `<用户目录>\.claude.json`（用户级 MCP）；审批钩子在 `<用户目录>\.claude\settings.json` | `<用户目录>\.claude\CLAUDE.md` | `<用户目录>\.claude\skills\nijika-desktop-dialog\SKILL.md` |
| Work | `dist\虹夏MCP-v2.exe` | `<用户目录>\.nijika-desktop-pet\integrations\work\plugins\nijika-work-local\mcp.json`（另有插件清单） | 插件技能内的规则 | 插件内 `skills\nijika-work-dialog\SKILL.md` |
| DSH | `dist\虹夏MCP-v2.exe` | `<用户目录>\.dsh\profiles\desktop\cordis.patch.yml` 与 `profiles\web\cordis.patch.yml` | `<用户目录>\.dsh\AGENTS.md` | `<用户目录>\.dsh\skills\nijika-dsh-dialog\SKILL.md` |
| 其他 MCP 客户端 | `dist\虹夏MCP-v2.exe` | 专属接入目录的 `nijika-mcp.json`；实际客户端目标由接收 AI 核实 | 同目录的 `nijika-agent-instructions.txt` | 同目录的 `SKILL.md`，由接收 AI 按客户端规则安装 |

`config.toml` 与 `cordis.patch.yml` 中写入的服务名分别为 `nijika-pet` 和 `mcp-nijika-pet`，`NIJIKA_AGENT_NAME` 提供气泡的默认来源名。内置客户端使用固定来源名：Codex=`Codex`、Claude Code=`Claude code`、DSH=`DSH`、Work=`Work`；同一个安装版 MCP 可以被多个客户端共用，每个客户端仍应配置正确名称。一个客户端只保留自己的虹夏注册：Codex 用 `nijika-pet`，Claude Code 用 `nijika-pet`，DSH 用 `mcp-nijika-pet`，Work 用 `nijika-work-pet`。旧的 `nijika_pet`、`magpie-mcp-nijika-pet` 重复条目会造成顶部来源错配，接入脚本会清理已识别的旧副本。路径由向导自动填入，不需要手抄；上述表格用于手动排查。

2026-10-25 来源复发修复：新 MCP 在每次完成/选择请求中读取协议的客户端信息。明确识别为 Codex 的调用可纠正遗留的 DSH 内置标签；自定义助手名称保留，Work 使用 Codex 本地引擎时仍保留 Work。未知或未提供客户端信息时沿用已配置名称，不根据任务正文猜来源。来源名仅用于显示，不证明调用者身份或授权。

仅改配置或替换磁盘 EXE 不会改变正在运行的旧 MCP 进程。已打开会话仍误标时，在客户端“设置 → MCP servers → nijika-pet → Restart”重启连接，或按客户端提供的重连方式操作；无需重复配置 Agent、安装技能或重新信任审批钩子。Codex 官方步骤见 [MCP 配置说明](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)。四个 MCP 工具的调用参数保持不变。

向导不读取或要求填写模型密钥，不替用户信任 hook，不开放云端入口。以下命令说明保留，供高级配置和故障排查。

虹夏的两个核心程序是：`虹夏桌宠.exe` 负责桌面显示，`虹夏MCP-v2.exe` 是 Agent 按需启动的 stdio MCP 服务；另附可选的 `虹夏审批提醒.exe`，支持 Codex 审批/完成事件及 Claude Code 审批事件，两者须分别安装。它们须在**同一台 Windows 10/11 x64 电脑、同一用户会话**中运行；只需手动启动桌宠，不要手动双击 MCP 或审批程序。MCP 不开放网络端口，普通云端聊天无法直接调用本机 EXE。

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

### Codex 完成兜底与命令审批提醒（可选）

普通决策由 Agent 调用 MCP，命令权限申请则由 Codex 的审批事件触发，两者是不同入口。源码构建完成后运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\integrations\codex\install-hooks.ps1
```

试用包安装时可改用 `distribution/install.ps1 -Codex -CodexHooks -NoLaunch`。脚本向 `%USERPROFILE%\.codex\hooks.json` 添加 `UserPromptSubmit`、`PermissionRequest`、`PostToolUse` 和 `Stop` 四类定义，保留其他 hook（含同组 handler）并备份已有文件；重复安装替换本项目条目，不重复叠加。既有 Computer Use 的 `notify` 保持原文。

**安装定义后还须本人审阅并信任 hook。** 在 Codex CLI 交互会话输入 `/hooks`，核对它们调用的是本机 `虹夏审批提醒.exe`，按界面完成审阅，再开新任务。旧版已信任审批两项的用户，至少还需审阅新增的 **UserPromptSubmit 与 Stop**。[Codex 官方 hooks 文档](https://learn.chatgpt.com/docs/hooks)要求非托管 hook 在审阅并信任前跳过执行；本脚本不会替你写入信任或修改审批策略。

当前 CLI 的 `/hooks` 页分别显示 `Installed / Active / Review`：仅安装而未信任时会有 `Active=0` / `Review=1`，不能视为已启用执行。回车可审阅选中的事件；若界面提供 `t trust all`，仅在核对所有列出的 hook 都愿意信任时使用。确认虹夏各事件 `Active` 为 `1`、`Review` 为 `0`。在桌宠选择“已设置信任”只是状态回传，不会修改 Codex 的信任配置；若仍显示 `untrusted`，请核对该 CLI 使用的配置目录与来源路径。

完成兜底用于 Agent 漏调工具的情形：新一轮存在真实工作或多步骤成果时，Stop 写一条“Codex · 任务完成”固定文案气泡；简短事实问答、内部标题、无有效轮次状态及仍在等待选择的回复尽量保持安静。成功调用过虹夏 show_completion 或 request_decision 的同轮不再补发，点击/关闭后重放 Stop 也不重复。过滤采用启发式，少见表述可能误判；它不补造决策选项、不自动执行审批、不唤醒结束的会话。桌宠未运行时仍只是排队，pending 不表示桌面可见。Work/DSH/Claude Code 的完成事件桥接不在本次范围。

信任后在一个新 Codex 任务中验收：让它在临时目录创建并读取一个测试文件，明确这一次不要主动调用桌宠工具；完成时应收到一条“任务完成”。再问一次“1+1等于几，只回答数字”，应不补发。最后让它主动调用一次 show_completion，应只收到一条带任务名的通知。正式会话的自然触发仍须在本机按此验证，隔离 CLI 测试不代替本人信任。

2026-10-17 本机正式信任后已复验：用户本人信任新增两项，运行时 hooks/list 确认四项 enabled/trusted；不跳过信任、不覆写 Hook 的新 Codex CLI 任务，完成隔离文件创建和读取后自动补发 1 条通知。之前的三场景隔离测试另已覆盖短问答不补发与有效主动通知不重复。本机无需重复完成新增两项信任；其他电脑仍须由其用户审阅，更新 Hook 定义后按客户端实际状态核对是否需要重新信任。

在会产生审批卡的任务中测试：保持虹夏运行，执行一个由当前审批策略要求授权的实际操作，应同时看到 Codex 审批卡和“命令需要授权”气泡。气泡“知道了”只记录收到提醒，**不会授予权限**；仍在 Codex 审批卡批准或拒绝。操作完成后，尚未点击的匹配提醒由 `PostToolUse` 收起。使用“不请求审批”的任务不会产生 `PermissionRequest` 事件。当前集成只覆盖本机 Codex 的受支持事件；不能据此声称 Work、DSH 或云端执行的系统权限也已接通。

2026-10-11 本机实测：用户完成信任后，运行时确认两项 hook 均已信任、启用。独立 Codex CLI 在 `on-request` / `read-only` 下弹出真实审批卡，虹夏自动显示提醒，用户点击“知道了”的回执已保存；原审批继续等待授权，随后取消测试申请，未执行申请中的写入操作。这项验收覆盖本机 Codex CLI。安装到其他电脑仍须由该电脑的用户自行审阅并信任，不分发本机的信任记录。

维护者可运行 `.\.venv\Scripts\python.exe tools\smoke_approval_hook.py` 隔离检查安装幂等性、打包 hook 的 stdin 输入、完成去重、保留 notify 与操作完成后的收起。模拟事件不执行其中的命令，也不等同于真实平台审批验收。`tools\smoke_codex_completion.py --case work|question|notice` 额外运行真实 Codex CLI，使用当前登录与模型端点，在临时队列验收补发、静默和主动工具去重；它仅在该次已审阅测试调用中跳过 hook 信任，不保存信任、不触碰正式消息库，且校验用户 config.toml 原字节不变。

### Claude Code

Claude Code 的用户级接入由三部分组成；目前设置中心没有专属 Claude Code 档案选项，可选“其他 MCP 客户端”生成自包含提示词，再由 Claude Code 核对配置格式，或按本节手动注册。审批钩子用本节的一次性脚本注册。

1. 注册 MCP：先备份用户级 `%USERPROFILE%\.claude.json`；已有 `nijika-pet` 时先核对旧条目，不重复注册。PowerShell 使用 `$env:LOCALAPPDATA` 展开安装目录，不要照抄 CMD 的 `%LOCALAPPDATA%`：

   ```powershell
   $mcpExe = Join-Path $env:LOCALAPPDATA 'NijikaDesktopPet\app\dist\虹夏MCP-v2.exe'
   claude mcp add -s user nijika-pet -e 'NIJIKA_AGENT_NAME=Claude code' -- $mcpExe
   claude mcp list
   ```

   源码方式将 `$mcpExe` 改为项目 `dist\虹夏MCP-v2.exe` 的绝对路径。用户级配置写入上述 `.claude.json`；在新会话中确认四个工具可见：`show_completion`、`request_decision`、`wait_for_reply`、`get_reply`，以客户端实际工具前缀为准。
2. 提醒规则：把何时提醒、同一请求连续等待、恢复会话先 `get_reply` 的规则合并进 `%USERPROFILE%\.claude\CLAUDE.md`；仓库级 `AGENTS.md` 只覆盖本仓库。
3. 可选技能：把 `skills\nijika-desktop-dialog\SKILL.md` 复制到 `%USERPROFILE%\.claude\skills\nijika-desktop-dialog\`。

**Claude Code 命令审批提醒（可选）**：普通决策由 Agent 调 MCP，权限提示出现时的自动气泡则由 Claude Code 自己的权限事件钩子触发，两者是不同入口。运行仓库内的一次性脚本即可把两条 exec 形式钩子合并进用户级 `%USERPROFILE%\.claude\settings.json`（直接拉起打包程序、不经 shell，路径含空格或中文也安全）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\integrations\claude-code\install-hooks.ps1
```

脚本默认写入 `%USERPROFILE%\.claude\settings.json`、调用同一目录树中的 `dist\虹夏审批提醒.exe`，写入前备份到 `.claude\backups\settings.json.backup.nijika-<时间戳>`，只替换虹夏自己的条目并保留其他钩子，可重复执行；`-UserSettings` 与 `-ApprovalExe` 可覆盖这两处默认值。注册结果为 `PermissionRequest`（同步）与 `PostToolUse`（`async: true`，不阻塞任务）两个 `matcher: ".*"` 条目，`args` 为 `["--source", "claude-code"]`；JSON 必须合法，否则整个设置文件会被忽略。试用包安装脚本 `distribution\install.ps1` 带 `-ClaudeHooks` 开关，会在安装时调用同一脚本。与 Codex 不同，Claude Code 自有 hook 没有单独的信任步骤；会话运行中也会热加载新配置。测试时应在产生权限提示的任务中同时看到 Claude Code 权限提示与“命令需要授权”气泡；气泡“知道了”只记录收到提醒，**不授予权限**，授权仍在 Claude Code 权限提示中完成；命令完成后，尚未点击的匹配提醒由 `PostToolUse` 收起。

与 Codex 一样，`approval_hook.py` 用 `--source claude-code` 区分署名与文案，Codex 行为不受影响。2026-10-16 本机实测：合成事件经注册命令全链路通过、运行中会话热加载生效，预创建的匹配通知被一次真实 `PostToolUse` 自动收起；真实 `PermissionRequest` 的自然触发在低提示权限模式下仍待验收。钩子自 2026-10-16 深夜起调用安装目录中的 `虹夏审批提醒.exe`（冻结程序：改造 `approval_hook.py` 后需按构建步骤重建并重装才生效）。回退：删除上述两条 `hooks` 条目，或恢复 `.claude\backups\settings.json.backup.nijika-*` 备份。维护者可运行 `.\.venv\Scripts\python.exe tools\smoke_claude_hooks.py` 隔离检查合并、替换、备份、幂等与全新机器写入。

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
# 2026-10-26 分享前接入差异与冲突检查

接入方式继续沿用设置中心向导；程序路径和接入提示词在收件人电脑上生成，不需要沿用开发机的路径。不要把本机生成的整份接入目录发给别人当作通用配置。

| 客户端 | 普通完成/选择 | 原生权限提示 | 特别之处 |
| --- | --- | --- | --- |
| Codex | MCP + 已安装技能/规则 | 可选 PermissionRequest/PostToolUse 钩子；本人审阅信任 | Stop 等完成兜底另行配置；保留其他 MCP、notify 和权限 |
| 本机 ChatGPT Work | 插件 MCP + 插件技能 | 尚未接宿主原生权限事件 | 当前启动器依赖 Codex CLI 与 python.exe；不是云端 Work 或普通聊天 |
| DSH | desktop/web stdio MCP + DSH 技能 | 尚未接宿主原生权限事件 | 两个 profile 均需核对，重启后新建会话 |
| Claude Code | 依手册合并 MCP，使用通用规则 | 存在独立的可选安装脚本；真实 PermissionRequest 仍未完整验收 | 目前没有向导专属按钮，按“其他 MCP 客户端”生成资料；不把 Codex 钩子配置直接复用 |
| 其他客户端 | 导出 stdio JSON 和完整配置提示词 | 不作通用承诺 | 接收 AI 需识别自己的配置文件/作用域；普通网页聊天不能安装本机进程 |

同一用户下各 Agent 共用桌宠、SQLite 队列和四个 MCP 工具；通知有独立请求 ID，不按题目文字匹配回复。同名问题与同名来源也各自独立。客户端须保存自己创建的 ID，不要读取或操作别人的请求。显示来源不是认证；本机可信客户端之间的逻辑路由不等于不同系统用户之间的安全隔离。

向导检测配置变化后拒绝覆盖；重复接入复用已有档案并保留其他配置。Codex 同名服务若指向未知程序会要求先核对。已有窗口/旧 MCP 连接不保证热加载，文件写入、面板测试和 pending 都不证明外部客户端已经接通。本人 hook 信任仍在客户端完成，气泡绝不代替命令审批。

维护者只读检查：`python tools/audit_agent_integrations.py`；真实协议并发检查：`python tools/smoke_mcp_sources.py <虹夏MCP-v2.exe绝对路径>`。前者比较技能和依赖，不输出客户端配置或密钥；后者使用临时数据库，不向正式桌宠排测试问题。这两项不等于每款宿主的真实权限事件验收。
# VS Code 中的具体 Agent（2026-10-29）

点击“扫描本机”，找到 `VS Code · Codex`、`VS Code · Claude Code` 或其他已安装扩展，点击“接入此扩展”。来源会自动填好，预览后仅安装带编辑器条件的规则；已有 MCP 与命令行/后端共用时保留原配置。没有工具时，将生成的完整配置提示词发给对应扩展中的 AI。MAGPIE 管理时只核对与验证，不重复配置。

在该扩展中新建任务，调用示例：

```text
请调用虹夏 show_completion，task="编辑器验证"，summary="这条提醒来自 VS Code 的 Codex"，
agent_name="Codex"，software="VS Code"。使用你实际看到的工具前缀。
```

其他扩展把 agent_name 换成 Claude Code、DSH 或 CodeBuddy。来源参数只描述本次调用，气泡显示 `VS Code · Codex` 等。不要将 VS Code 固定来源覆盖到共用的全局配置。扩展是否提供 MCP、是否已启用、是否信任/已加载，仍需在真实宿主确认；CodeBuddy 的具体版本若不提供 MCP，应报告不支持，不能靠写一个 JSON 冒充连通。

当前仅扫描已知 Windows 用户级 stable/Insiders 目录；远程 SSH、WSL、容器、便携或自定义扩展目录不在自动检测范围。安装清单不代表连接成功。
