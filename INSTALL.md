# 安装与运行

## 互动设置预览（2026-10-17，尚未替换正式 EXE）

本阶段只在源码设置中心提供“互动与养成”入口。沿用下方已有 Python 环境后运行 `.\.venv\Scripts\python.exe control_panel.py`，在左侧进入“互动与养成”。动作卡片和角色头顶/脸颊用于试映；可停止、重播，并选择轻柔或活泼幅度。试映幅度不改变正式桌宠设置，减少动画的系统偏好会使用静态表情。

需要养成时，在下方开启“轻养成”并点“保存互动设置”，再点击点心或喝水。数值自动保存在消息库，两个投喂分别冷却 30 秒；关闭养成后暂停，离线最多计算 8 小时，没有死亡或惩罚。“试映吃点心/喝水”只看动画，不改数值。触摸/特效开关可先在试映室试用，再保存偏好。

新动作目前只在面板内播放，不会排入旧桌宠队列。正式桌面 EXE、快捷方式、启动项与各 Agent 的接入步骤维持当前版本；待页面和动画效果验收后才接入桌面动作、重建并安装。不要把本阶段代码提交视为已安装升级。

隔离开发预览可先设置 `NIJIKA_PET_DB_PATH` 为工作区 `diagnostics\interaction-settings-preview\notifications.sqlite3`，再运行 `control_panel.py --serve-only --agent-home <工作区内的隔离用户目录>`；服务只监听 `127.0.0.1`，打开输出地址并进入 `#interaction`。本机浏览器访问权限门禁当前拒绝了该地址，需要本人在客户端允许本地地址访问后补做页面操作验收，不能据 API 测试认定页面已实测通过。

回归命令为 `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`；测试前也应设隔离的 `NIJIKA_PET_DB_PATH`，避免协议测试导入服务时初始化真实消息库。受限沙箱可能拦截临时文件替换和本机套接字，需经原生权限申请在隔离环境复验，不能把这些拒绝当成功。

互动控制器还可运行 `node --test tests/test_interaction_ui.cjs`；使用 Node 内置测试运行器，无浏览器、网络或第三方前端依赖，仅验证异步响应、保存竞态和开关逻辑，不能替代真实页面点击/布局验收。

2026-10-15：设置中心与桌宠合并为同一个 `dist/虹夏桌宠.exe`。右键角色选择“设置中心 / 添加 Agent”，或双击桌面的“虹夏桌宠设置”快捷方式（等价于 `虹夏桌宠.exe --control-panel`），即可打开设置窗口。设置窗口使用系统 Microsoft Edge WebView2；其他电脑若缺少该运行时，请从 [Microsoft 官方页面](https://developer.microsoft.com/microsoft-edge/webview2/)安装，或用 `虹夏桌宠.exe --control-panel --browser` 在浏览器打开同一管理面板。所有方式都仅绑定本机回环地址，窗口关闭后停止其服务。

控制中心首页点击“添加 Agent”，选择 Codex、ChatGPT 本机 Work 或 DSH，确认自动检测的位置和计划改动后应用。已有文件会保留备份，其他客户端条目不会被清空。其他客户端选择“其他 MCP 客户端”并生成接入文件，再“复制自动配置提示词”给能操作本机文件的 AI；提示词含完整路径、JSON 与持久提醒规则，无需手动下载或填字段。文件默认保存至 `%USERPROFILE%\.nijika-desktop-pet\integrations\agents\<档案ID>\`，准确位置在“接入步骤”显示。重载及本人权限确认如有必要仍须完成。面板不收集模型 API 密钥，不会替用户信任审批 hook。具体范围见 `AGENT_SETUP.md`。

动作、大小、常驻表情、闲聊开关与所选皮肤保存在同一用户消息库的独立设置表；导入皮肤放在消息库旁的 `skins/`，投喂图片放在 `support/`。默认目录仍为 `%USERPROFILE%\.nijika-desktop-pet`。新表不改变已有通知表协议；旧 Agent 会话继续通过同一队列通信。收款图与真实设置不进入 Git 或试用包。

第一版四项功能的操作位置：设置中心左侧“专注与提醒”页开始/暂停/继续番茄钟、修改专注与休息分钟数、开启三类健康提醒或设置免打扰；“今日便签与陪伴”页添加当天便签、打勾完成并查看好感度、陪伴天数与当前阶段。桌宠右键也能“开始专注 / 暂停专注”和“结束这一轮”，倒计时显示在角色头顶。数据表 `companion_*` 与通知队列共用同一个 SQLite 文件，删除该文件会同时重置提醒历史与陪伴数据。可复用验收脚本为 `.\.venv\Scripts\python.exe tools\accept_companion.py`（需要设置中心正在运行）。

本机 2026-10-16 核对：桌宠已按标准流程统一安装到 `%LOCALAPPDATA%\NijikaDesktopPet\app`，桌面与开机自启快捷方式、Codex 审批钩子、Work 插件清单、DSH desktop/web 配置、Claude Code 的 MCP 注册与审批钩子均指向安装目录中的程序；三款 EXE 与仓库 `dist/` 逐字节相同。修改 `pet.py` 等源码后必须重新运行 `build.ps1` 重建，再按 `distribution/install.ps1` 重新安装到上述目录并重启桌宠；Git 中的源码变化不会自动更新运行中的程序，各客户端配置里的开发目录字样只属历史记录。

给其他 Windows 用户私下试用时，运行 `.\.venv\Scripts\python.exe tools\package_release.py` 生成不含个人配置和消息库的安装 ZIP。收件人解压后按 `distribution/README.md` 运行安装脚本；脚本复制程序到其本机用户目录（默认 `%LOCALAPPDATA%\NijikaDesktopPet\app`），并可选接入 Codex、Work、DSH 或 Claude Code（`-Codex -Work -CodexHooks -ClaudeHooks -Dsh -AutoStart` 开关）。试用包内的 Work MCP 路径由安装脚本按收件人路径写入，不直接复制本机硬编码路径。角色素材没有公开再分发许可证，不应将此试用包公开发布。

更新触发：2026-10-07 增加 Codex 本机 MCP 服务和带简介的选择题。

系统：Windows 10/11 x64。成品版双击 `dist/虹夏桌宠.exe`，无需安装 Python。右键角色可切换动态、闲聊、打开控制中心、手动说话和两种本地演示提醒；演示按钮不会联系真实 Agent。真实 Codex 消息由 `虹夏MCP-v2.exe` 接收，桌宠运行时自动显示，未运行时保留待处理消息。退出时右键选“退出桌宠”。无账号登录；只有控制中心运行时开放本机管理端口。

从 Git 获取源码后，在项目根目录使用 Python 3.12 执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe pet.py --self-test
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe pet.py
```

源码开发还可运行 `.\.venv\Scripts\python.exe control_panel.py` 打开独立窗口，或附加 `--browser` / `--serve-only` 进行浏览器验证。`requirements.txt` 固定直接依赖，`requirements-lock.txt` 保存本轮 Python 3.12 Windows 环境的完整版本，可用后者复现已测环境。没有前端 npm 或 CDN 依赖。

生成三个单文件程序（更新前先退出对应的运行中程序）：

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

输出在 `dist/虹夏桌宠.exe`（桌宠与设置中心）、`dist/虹夏MCP-v2.exe` 和 `dist/虹夏审批提醒.exe`。第三个程序供可选的 Codex 命令审批与完成兜底提醒使用，安装与审阅步骤见 `AGENT_SETUP.md`。当前电脑已配置 Codex；其他电脑也可使用设置中心向导，或在项目根目录运行：

```powershell
$mcpExe = (Resolve-Path -LiteralPath 'dist\虹夏MCP-v2.exe').Path
codex mcp add nijika-pet -- $mcpExe
codex mcp get nijika-pet
```

把 `skills/nijika-desktop-dialog/SKILL.md` 安装到 Codex 用户技能目录，并在 Codex 的全局 `AGENTS.md` 中引用它，可让新任务把简单决策和短成果审阅整理成“完整短正文＋有简介的选择”。工程根目录也带有 `AGENTS.md`，说明成果待审阅和需要选择时的桌面提醒规则。当前电脑已完成安装；独立 Codex CLI 会话已在普通审阅与选择任务中自主发出提醒。安装或配置变化通常由新开的 Codex 任务读取；已经打开的任务不保证即时刷新工具列表。桌宠程序仍需打开以便立即看见提醒。

Codex 的审批策略可能要求先确认 MCP 工具调用。经用户明确授权，当前电脑只对 `nijika-pet` 的 `show_completion`、`request_decision`、`get_reply`、`wait_for_reply` 设置了逐工具 `approval_mode = "approve"`；服务器默认规则和其他工具未改。独立 Codex CLI 会话在未附加临时放行参数时已成功发送提醒。其他电脑沿用自身审批策略，遇到提示时应核对要发送的内容。桌宠上的选择仍由用户亲自点击，`pending` 或关闭不算同意。

Codex 完成兜底（2026-10-17）：重建 Hook 后运行 `integrations\codex\install-hooks.ps1`，或安装试用包时加 `-CodexHooks`；本人在 Codex `/hooks` 审阅新增 UserPromptSubmit / Stop，保留原 PermissionRequest / PostToolUse，然后新开任务。该功能不需要改变 Agent 的 MCP JSON、全局技能或前端设置；现有 Computer Use notify 保持原样。只有成功调用过桌宠通知的同轮会抑制兜底，输入无效不算已发送。消息库仅新增无正文的轮次表，旧桌宠/MCP 能直接显示它生成的普通完成通知。

单文件版首次启动需要解包资源，可能比源码运行略慢。`dist/`、`.venv/` 与构建缓存不入 Git；源码包必须保留 `assets/sprites/`。通知数据库默认在 `%USERPROFILE%\.nijika-desktop-pet\notifications.sqlite3`，避免桌面客户端的 AppData 重定向造成两份队列；旧运行中会话的待处理消息与回复由桌宠桥接。可用 `env.example` 中的可选变量在隔离测试时改路径。消息含任务摘要，请只在受信任的本机用户会话中使用。本项目不要求真实 API 密钥或联网。

维护者可运行 `.\.venv\Scripts\python.exe tools\smoke_packaged_mcp.py` 测试打包服务，或运行 `.\.venv\Scripts\python.exe tools\smoke_pet_ipc.py` 在隔离消息库下测试真实桌面气泡与点击回传；`tools\smoke_claude_hooks.py` 与 `tools\smoke_dsh_installer.py` 分别隔离验证 Claude Code 钩子安装器与 DSH 安装脚本。`tools/benchmark_motion.py`、`tools/probe_window_fps.py` 和 `tools/make_bubble_preview.py` 分别用于动画性能及气泡预览；这些工具不会进入打包版。

## 桌面客户端 Work 本机接入

本机插件目录为 `plugins/nijika-work-local/`，项目插件清单为 `.agents/plugins/marketplace.json`。源码中的 `mcp.json` 不再包含开发者电脑路径；Python 启动脚本优先查找同一项目根目录的 `dist/虹夏MCP-v2.exe`，也可读取 `NIJIKA_MCP_EXE` 或正式安装目录。插件运行仍需要能从 PATH 找到 `python.exe`。私下试用包的安装脚本会按收件人目录写入确定的 EXE 路径。当前电脑已安装并启用 0.1.5 版，技能要求短决策连续等待、恢复会话时先读取旧请求。安装命令为：

```powershell
codex plugin marketplace add . --json
codex plugin add nijika-work-local@nijika-local --json
codex plugin list --marketplace nijika-local --json
```

确认插件显示 `installed: true`、`enabled: true` 后，保持 `虹夏桌宠.exe` 运行，**重启 ChatGPT 桌面客户端**，从本机运行的 Work 新任务发起一条简短测试选择题，检查气泡能显示、点击后 Work 能读回选择。普通聊天或云端 Work 不会因为本机 Codex 配置而自动拥有这个 stdio 工具。插件说明仅指导 Agent 何时调用；模型是否主动调用仍需以新任务实测，不能由安装状态推断。需要将云端 Work 接入时，必须提供经过鉴权的远程 HTTPS MCP 端点，本机插件不能代替公网连接。请勿把本机消息库直接暴露到网络。

Codex 全局技能和 Work 插件技能均要求在一次 45 秒等待返回 `pending` 后复用原请求 ID 继续等待，最多约九分钟；若任务已结束，较晚的点击仍保存在消息库，但不会自动唤醒 Agent。在原会话发送“继续”后，技能要求先调用 `get_reply` 读取该请求。此规则已安装，当前打开的 Codex/Work 任务不保证热更新；Work 0.1.5 版的隔离 MCP 启动测试通过，真实 Work 会话中的长等待和晚到回复仍待验收。

可用 `.\.venv\Scripts\python.exe tools\smoke_work_plugin.py` 在隔离消息库下验证插件启动入口及四个 MCP 工具，不会给正在运行的桌宠发送测试通知。

## DeepSeek Harness（DSH）本机接入

当前电脑已把同一 `dist/虹夏MCP-v2.exe` 注册到 DSH 的 desktop 与 web 配置，并安装 `nijika-dsh-dialog` 技能和全局触发说明。其他电脑先构建 EXE，再执行 `powershell -ExecutionPolicy Bypass -File .\integrations\dsh\install.ps1`。安装不会替换 DSH 原有的桌宠插件；配置、重启和测试步骤见 `integrations/dsh/README.md`。
