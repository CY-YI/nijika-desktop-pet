# 通过 MAGPIE 接入虹夏桌宠

日常提醒、桌面选择及回执使用同一份 [nijika-agent-dialog](skills/nijika-agent-dialog/SKILL.md)。需要帮别的客户端做配置时，交给操作方 [nijika-magpie-setup](skills/nijika-magpie-setup/SKILL.md)。两者职责不同；每个客户端只启用一份日常提醒规则。

1. 打开 **虹夏桌宠设置 → Agent 接入 → 添加 Agent**，或扫描本机后选择目标。
2. 点 **检查 MAGPIE 分发**。未分发时选择 **查看 MAGPIE 步骤 → 复制 MAGPIE 配置提示词**，发给能操作同一台电脑的 AI，或按提示在 [MAGPIE Library](https://usemagpie.ai/docs/library) 操作。提示词包含当前安装路径和实际目标。已分发时可点 **登记并查看验证步骤**。
3. 在 Library 的 **MCP** 页复用唯一的 `nijika-pet`，命令是安装目录里的 `dist/虹夏MCP-v2/虹夏MCP-v2.exe`，同级 `_internal` 要保留。共享身份使用 `NIJIKA_AGENT_NAME=auto`，不在共享服务写死单个 Agent 的宿主标签或档案编号。
4. 在 **Skills** 分发 `nijika-agent-dialog`，宿主需要每轮自动加载时，在 **Instructions** 分发一句触发规则。多个目标可在同一个 Library 条目中勾选；以后改提醒行为时更新这一份 Skill。
5. 重载目标，在新任务校验显示和点击。回到向导登记已识别的分发；面板测试只验证本机桌宠。共享服务没有档案编号时，面板未认领不代表气泡没有到达。

已有直连时先确认业务、备份并迁移，避免同时启用两个入口。遇到 MAGPIE 未支持的宿主，报告所缺的 MCP、Skill 或触发指令能力；已有能用的路由暂停迁移。VS Code 中的具体扩展以实际宿主校验来源，不能把编辑器身份写进共享后端。原生权限钩子或结束事件另行验收，不因 Skill 分发而自动启用。若只切换同一客户端里的模型，沿用已有分发。

## 旧版本记录

以下带日期的段落用于回顾验收结果。当前安装、配置和升级一律使用上方步骤；历史直连命令及旧 Skill 不再随新包交付。

## 2026-11-18 Grok Build 自动来源

Grok 1.0.88 可继续通过通用 stdio MCP 配置接入。客户端实际握手名可能是 `grok-shell-<服务名>`，新版虹夏 MCP 会自动显示 `Grok · Grok Build`，无需在每次任务中手工传入 `agent_name` 或 `software`，也不需要在同一作用域再添加第二个虹夏服务。

更新 MCP 后，旧 Grok 任务仍运行已加载的旧进程。保存当前工作并在 Grok 中新建任务或重新连接 `nijika-pet`，再以一次普通任务核对头部。消息状态为 `pending` 只证明已进入本机队列，不能据此宣称气泡已经可见；实际点击和晚到回执仍按各客户端对话生命周期验证。设置中心的本机扫描若发现 `.grok/config.toml`，仍须预览后应用，不改写无关配置。

## 2026-11-03 自动配置防重复（旧版记录）

扫描结果只是入口证据。预览和批量应用前，设置中心现在会校验 MCP 的 onedir 运行时完整性：`dist\虹夏MCP-v2\虹夏MCP-v2.exe` 和同目录 `_internal\` 必须同时存在。只复制 EXE、缺失 `_internal\` 或安装路径不完整时，会停止配置并提示补齐完整程序，避免写出一份启动后立即失败的客户端配置。

批量扫描中，Codex 与 ChatGPT Work 只能选择一个。两者共用本机 Codex 环境，同时自动配置会产生两套 MCP 工具入口和重复提醒风险。界面从一项切换到另一项时会自动取消原来的选择并显示原因，后端 API 也会拒绝同时提交；如果需要两个宿主并存，应分别核对实际工具入口后使用单独向导明确配置，不能把它们当作“多重保险”。

## 2026-11-03 MCP onedir 路径

新配置统一指向 `<安装根>\dist\虹夏MCP-v2\虹夏MCP-v2.exe`。该 EXE 不能脱离同级 `_internal\` 单独复制；设置中心“所需文件”会显示当前机器的完整路径。旧版精确路径 `<安装根>\dist\虹夏MCP-v2.exe` 可在预览中安全迁移到新目录路径，未知目录中的同名程序仍会被拒绝。

升级不会结束正在运行的客户端或 MCP。已打开客户端需要重连 MCP 或新建任务，才会停止使用旧 onefile 进程并加载新路径。

## 2026-10-31 统一提醒核心接入（旧版记录）

1. 打开设置 → Agent 接入 → 扫描本机 → 预览并应用；已有档案打开“接入步骤”刷新导出资料。所有路径按当前安装目录生成，不复制作者电脑路径。
2. 阅读“通知能力与验收清单”：Codex 可接原生四事件，仍需本人审阅信任；DSH 可安装实时会话事件模块，接口核对版本 `0.2.1-rc.2 / 0.2.1-rc.3`。两者共用同一提醒算法。Work、其他客户端目前仅主动调用，不承诺漏调补发。
3. DSH 的自动计划更新 desktop/web 的两个独立虹夏块，安装模块路径为 `<安装目录>/integrations/dsh/lifecycle-bridge.mjs`，统一程序为 `<安装目录>/dist/虹夏审批提醒.exe`。移动安装位置后重新预览应用。MAGPIE 管理时不会代写服务或事件模块，应由配置所有者审阅合并，不能据档案已添加宣称已启用。
4. 重载客户端，在新任务分别验收“主动调用”“无主动调用的短答补发”“同轮去重”“后台与并行会话隔离”。结束事件须由宿主上报，禁止让模型生成会话/轮次 ID 执行模拟输入冒充真实验收。

当时的导出目录提供 `nijika-notification-capabilities.json`，列明程序位置、适配入口与验收清单。验证应分别记录工具发现、消息排队、桌面显示与用户点击。完整协议见 `NOTIFICATION_PROTOCOL.md`。

已由 MAGPIE 管理 MCP 的 DSH，不要重复添加服务。需要补齐结束事件时，可让配置维护者在实际安装目录审阅并运行 `integrations\dsh\install.ps1 -LifecycleOnly`，仅更新独立事件块；具体命令和边界见 `integrations/dsh/README.md`。若短答测试里模型仍主动调用了工具，只能证明主动提醒和去重，不能将其写成无工具补发通过。

## 2026-10-31 Codex 后台任务隔离

Codex 的 `Stop` Hook 会收到用户对话之外的后台任务。当前实现只在两种可核实特征下静默：最终回复同时包含 `currentSuggestionIds`、`generatedAtMs`、`suggestions`，且建议项带 `appId`/`appIds`；或工作路径位于 Codex 私有 `AppData\Local\OpenAI\Codex\bin\<版本>` 且最终回复精确为 `{"exclude":[]}`。其他 JSON 回复仍属于用户任务，会生成一条完成气泡，但正文使用安全摘要而不是原始 JSON。

分类所需的路径和回复只在 Hook 进程内存中读取；`codex_turn_state` 仍只保存哈希轮次标识、分类和去重标记。显式子任务事件、内部标题生成和缺少有效轮次状态继续静默。该修复不改变 MCP、权限 Hook 信任、消息库或外部客户端配置。

## 2026-10-30 配置一致性审计

Codex 的虹夏技能只保留源码与 `CODEX_HOME`（通常为 `%USERPROFILE%\.codex`）中的一份。不要把同名技能再复制到 `%USERPROFILE%\.agents\skills`；技能发现位置同时存在两份且内容不同时，不同任务可能读取旧规则。相同内容装两份也只算重复，不视为双保险。

维护者可运行：

```powershell
python tools\audit_agent_integrations.py
python tools\audit_local_state.py
```

两个工具都只读。第一项输出技能路径、摘要、缺失/匹配/冲突状态；第二项读取现有设置库与皮肤目录，检查当前皮肤、帧文件和完整 Agent 键。它们不读取会话或凭据，发现冲突时返回非零退出码。审计通过后，再分别重载客户端并做一次真实工具调用；文件一致不能证明旧连接已经加载。

2026-10-30 本机已先用 `tools\cleanup_legacy_nijika_integration.ps1` 预演目标，再以 `-Apply` 备份并删除旧 `.agents` 技能、旧技能 `.bak` 和零字节审批探针。清理工具只接受这三个精确路径，要求 `CODEX_HOME` 中的权威技能与源码摘要一致，并在删除前逐文件校验备份。重跑两项审计后状态均为 `clean`。

已有 Agent 档案继续保留。旧 `custom` 档案缺少 `agent_identity/software` 时，不根据名称猜测模型或宿主；需要明确来源时，从设置中心重新扫描并用当前路径生成一条新档案。相同客户端路径、Agent 与软件组合会被复用；仅 `custom + 同一用户目录` 但身份不同，不是重复档案。皮肤格式无需因本次审计改变。

## 2026-10-30 完成提醒与 DSH 来源加固

Codex、DSH 和本机 Work 的新版持久规则都要求在最终回复前检查完成提醒。每个有效轮次都必须主动调用一次 `show_completion`，`summary` 写具体结果，包括简单事实问答或正文暂缺的短答。Codex Stop 只在漏调用时生成最多 120 字的安全摘要，不能作为 Agent 不写结果详情的正常路径。

DSH 是可切换模型的工作台，不默认等于 DeepSeek 或 Codex。标准 DSH 连接省略 `agent_name/software`，通过官方配置和握手显示 `Agent · DSH`；明确模型时才传真实名称。共享 MCP 会拒绝把 Codex、ChatGPT、DSH 等宿主产品名当成 DSH 的 Agent，真实 `DeepSeek` 或自定义名称仍保留。自动接入会删除旧的孤立虹夏开始标记，但不会改由 MAGPIE 管理的实际服务。

2026-10-30 本机正式安装已更新三个 EXE、Codex 全局规则/技能、DSH desktop/web 配置和 Work 插件 0.1.7。2026-11-03 的 MCP onedir 更新将 Work 插件提升到 0.1.9，并把 Codex、DSH desktop/web 与 MAGPIE 的 `nijika-pet` 启动路径切到 onedir；Codex/DSH/Work 技能审计为 `clean`。正式用户库真实气泡已验证 `Agent · DSH` 与 `DeepSeek · DSH`；已打开客户端仍要重连 MCP 或新建任务，新的持久提示词和路径才会加载。服务端身份守卫不依赖客户端重连，旧参数也不会再显示 `Codex · DSH`。

## 2026-10-29 扫描本机与批量接入（旧版记录，已废止）

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

## 2026-10-29 旧版向导与配置迁移（历史）

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

维护审计：`python tools/repair_nijika_sources.py --output diagnostics/source-audit.json` 默认只读；本机 DSH YAML 审计需 PyYAML（工具依赖，不是桌宠运行依赖）。MAGPIE 已管理的客户端会标记 `skipped`，即使执行 `--apply` 也不会直接修改，必须回到 MAGPIE 处理。执行 `--apply --backup <本机目录>` 只会修正非 MAGPIE 的已识别虹夏条目；备份只保存虹夏片段，不复制完整账号配置。不要将本机备份或诊断上传。技能安装位另用 `tools/audit_agent_integrations.py` 检查；它不会替用户删除重复目录，发现冲突时按输出的绝对路径人工核对。


## 宿主原生事件（可选，与接入分开）

- Codex：在已安装目录运行 `distribution/install.ps1 -CodexHooks -NoLaunch`（从 ZIP 安装时），或运行 `integrations/codex/install-hooks.ps1`。核对 UserPromptSubmit、PermissionRequest、PostToolUse、Stop 四项；新增或改动须由本人在 Codex 的 `/hooks` 中审阅并信任。
- Claude Code：`integrations/claude-code/install-hooks.ps1` 对应 PermissionRequest 和 PostToolUse。权限仍在 Claude Code 请求中处理。
- DSH：有需要时审阅 `integrations/dsh/install.ps1 -LifecycleOnly`。此选项只更新会话事件转接，保留 MAGPIE 的 MCP 和提醒规则。
- 本机 Work：保留已工作的插件入口；Skill 正文由统一版本生成。未核实 MAGPIE 能分发给 Work 时，不把 Codex 列表项当成 Work，也不重复配置。云端 Work 或普通网页聊天不直接运行 Windows stdio 程序。

## 验证与当前边界

Codex、ChatGPT Work、DSH 与 DS Bot 默认共用 `%USERPROFILE%\.nijika-desktop-pet\notifications.sqlite3`。更新桌宠与 MCP 后重新启动桌宠；已有旧 MCP 进程的待处理消息由兼容桥接保留原 ID，点击仍会回传。新配置不要继续指定旧 AppData 路径；隔离测试可显式设置 `NIJIKA_PET_DB_PATH`。

1. 确认桌面能看到虹夏；在 Agent **新任务**里提出一个确实需要你二选一的简短问题。
2. Agent 应调用 `request_decision`，气泡显示来源、问题、各选项的一句影响说明；点击后 Agent 应通过 `wait_for_reply`/`get_reply` 读回，并在**原聊天**写明所选项。
3. 任务完成但内容太长时，Agent 可调用 `show_completion` 提醒你回聊天查看。`pending` 只表示本机排队，不代表气泡已显示或你已批准。
4. 使用支持文字回复的版本时，可让 Agent 提一个开放式问题。确认气泡显示“输入回复”，发送文字后，在原对话核对 Agent 读到的要点。该功能使用已有虹夏 MCP 连接，客户端重连后发现 `request_text_reply`。

晚到的点击保存在本机消息库，但 Agent 任务若已经结束，当前 stdio MCP **不会自动唤醒该任务**；在原聊天发送“继续”，技能要求先读取旧请求。Codex、Work、DSH 和 DS Bot 的长期等待与晚到回复仍需各自在新任务中现场验收。
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

## 在 MAGPIE 为新 Agent 复用虹夏

同一台电脑上的新 Agent 若支持由 MAGPIE 写入本机 stdio MCP，在「Library → MCP」找到现有 `nijika-pet`，勾选目标 Agent，然后重启该客户端或新建会话。保留已经生效的正式安装路径，并在新会话调用一次 `show_completion`，核对桌面气泡和来源。已由 MAGPIE 管理的目标沿用这个入口，避免在虹夏设置中心再次注册同名服务。

想让新客户端在日常任务结束时主动调用虹夏，还需为它分配适用的 Instructions 或 Skill，并实际测试自然任务。原生审批通知与结束事件兜底按宿主分别验证。若只是更换原客户端使用的模型，且它继续读取同一份客户端配置，已接入的虹夏可直接沿用。MAGPIE 的分配规则见 [Library 文档](https://usemagpie.ai/docs/library#mcp-servers)。

# 三客户端实际验收（2026-11-18）

本机 MAGPIE 同时管理 Codex、DSH 与 DS Bot，三个客户端最终都启动了安装目录中的同一 onedir `虹夏MCP-v2.exe`。实际自然短问答分别产生了独立的 SQLite 请求，正文没有串用：

| 客户端 | 唯一正文 | 气泡来源 | 回写状态 |
| --- | --- | --- | --- |
| Codex | `Codex Magpie 验收 C-1118-07...` | `ChatGPT · Codex` | `answered` |
| DSH | DSH 结果，包含 `2+2=4` | `Agent · DSH` | `answered` |
| DS Bot | `3+3=6`、`4+4=8`、`5+5=10` | `Agent · DS Bot` | 均经桌面点击后为 `answered` |

DS Bot 的 `5+5=10` 是在重启客户端、加载 `%USERPROFILE%\.ds-bot\integrations\nijika-dsbot-mcp` 稳定 bundle 后再次验证；请求 ID 为 `5474440dbce44c3e887561fe797b5d99`。`tests/test_dsbot_installer.py` 另外覆盖首次安装、占位路径改写、稳定 junction、单份技能/全局规则和幂等重跑。MAGPIE 页脚仍可能显示与虹夏无关的旧 Claude Desktop 路径错误；该提示没有阻止三客户端路由或本机气泡显示，未作跨产品无关配置修改。
