# 安装与运行

本机 2026-10-09 核对：桌面和开机自启的“虹夏桌宠”快捷方式都指向本项目 `dist/虹夏桌宠.exe`；该文件已重新打包，包含气泡隐藏后重显及窗口重建修复。Codex 全局入口和 Work 插件 0.1.5 都指向 `dist/虹夏MCP-v2.exe`。修改 `pet.py` 后必须重新运行 `build.ps1` 并重新启动桌宠，Git 中的源码变化不会自动更新 `dist/` 的 EXE。

给其他 Windows 用户私下试用时，运行 `.\.venv\Scripts\python.exe tools\package_release.py` 生成不含个人配置和消息库的安装 ZIP。收件人解压后按 `distribution/README.md` 运行安装脚本；脚本复制程序到其本机用户目录，并可选接入 Codex、Work 或 DSH。试用包内的 Work MCP 路径由安装脚本按收件人路径写入，不直接复制本机硬编码路径。角色素材没有公开再分发许可证，不应将此试用包公开发布。

更新触发：2026-10-07 增加 Codex 本机 MCP 服务和带简介的选择题。

系统：Windows 10/11 x64。成品版双击 `dist/虹夏桌宠.exe`，无需安装 Python。右键角色可切换动态、闲聊、手动说话和两种本地演示提醒；演示按钮不会联系真实 Agent。真实 Codex 消息由 `虹夏MCP-v2.exe` 接收，桌宠运行时自动显示，未运行时保留待处理消息。退出时右键选“退出桌宠”。无登录或网络端口。

从 Git 获取源码后，在项目根目录使用 Python 3.12 执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe pet.py --self-test
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe pet.py
```

生成两个单文件程序：

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

输出在 `dist/虹夏桌宠.exe` 和 `dist/虹夏MCP-v2.exe`。当前电脑已配置 Codex；其他电脑构建后可在项目根目录运行：

```powershell
$mcpExe = (Resolve-Path -LiteralPath 'dist\虹夏MCP-v2.exe').Path
codex mcp add nijika-pet -- $mcpExe
codex mcp get nijika-pet
```

把 `skills/nijika-desktop-dialog/SKILL.md` 安装到 Codex 用户技能目录，并在 Codex 的全局 `AGENTS.md` 中引用它，可让新任务把简单决策和短成果审阅整理成“完整短正文＋有简介的选择”。工程根目录也带有 `AGENTS.md`，说明成果待审阅和需要选择时的桌面提醒规则。当前电脑已完成安装；独立 Codex CLI 会话已在普通审阅与选择任务中自主发出提醒。安装或配置变化通常由新开的 Codex 任务读取；已经打开的任务不保证即时刷新工具列表。桌宠程序仍需打开以便立即看见提醒。

Codex 的审批策略可能要求先确认 MCP 工具调用。经用户明确授权，当前电脑只对 `nijika-pet` 的 `show_completion`、`request_decision`、`get_reply`、`wait_for_reply` 设置了逐工具 `approval_mode = "approve"`；服务器默认规则和其他工具未改。独立 Codex CLI 会话在未附加临时放行参数时已成功发送提醒。其他电脑沿用自身审批策略，遇到提示时应核对要发送的内容。桌宠上的选择仍由用户亲自点击，`pending` 或关闭不算同意。

单文件版首次启动需要解包资源，可能比源码运行略慢。`dist/`、`.venv/` 与构建缓存不入 Git；源码包必须保留 `assets/sprites/`。通知数据库默认在 `%LOCALAPPDATA%\NijikaDesktopPet\notifications.sqlite3`；可用 `env.example` 中的可选变量在隔离测试时改路径。消息含任务摘要，请只在受信任的本机用户会话中使用。本项目不要求真实 API 密钥或联网。

维护者可运行 `.\.venv\Scripts\python.exe tools\smoke_packaged_mcp.py` 测试打包服务，或运行 `.\.venv\Scripts\python.exe tools\smoke_pet_ipc.py` 在隔离消息库下测试真实桌面气泡与点击回传。`tools/benchmark_motion.py`、`tools/probe_window_fps.py` 和 `tools/make_bubble_preview.py` 分别用于动画性能及气泡预览；这些工具不会进入打包版。

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

当前电脑已把同一 `dist/虹夏MCP-v2.exe` 注册到 DSH 的 desktop 与 web 配置，并安装 `nijika-dsh-dialog` 技能和全局触发说明。其他电脑先构建两个 EXE，再执行 `powershell -ExecutionPolicy Bypass -File .\integrations\dsh\install.ps1`。安装不会替换 DSH 原有的桌宠插件；配置、重启和测试步骤见 `integrations/dsh/README.md`。
