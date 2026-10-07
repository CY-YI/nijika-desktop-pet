# 安装与运行

更新触发：2026-10-07 增加 Codex 本机 MCP 服务和带简介的选择题。

系统：Windows 10/11 x64。成品版双击 `dist/虹夏桌宠.exe`，无需安装 Python。右键角色可切换动态、闲聊、手动说话和两种本地演示提醒；演示按钮不会联系真实 Agent。真实 Codex 消息由 `虹夏MCP.exe` 接收，桌宠运行时自动显示，未运行时保留待处理消息。退出时右键选“退出桌宠”。无登录或网络端口。

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

输出在 `dist/虹夏桌宠.exe` 和 `dist/虹夏MCP.exe`。当前电脑已配置 Codex；其他电脑构建后可在项目根目录运行：

```powershell
$mcpExe = (Resolve-Path -LiteralPath 'dist\虹夏MCP.exe').Path
codex mcp add nijika-pet -- $mcpExe
codex mcp get nijika-pet
```

把 `skills/nijika-desktop-dialog/SKILL.md` 安装到 Codex 用户技能目录，并在 Codex 的全局 `AGENTS.md` 中引用它，可让新任务把选择题整理成“名称＋一句说明”。当前电脑已完成这一步。安装或配置变化通常由新开的 Codex 任务读取；已经打开的任务不保证即时刷新工具列表。桌宠程序仍需打开以便立即看见提醒。

Codex 的审批策略可能要求先确认 MCP 工具调用。当前电脑保留默认审批设置；交互式 Codex 任务遇到提示时，需要按实际要发送的内容批准。无交互且禁止审批的 CLI 会话会拒绝该调用。通知工具获准运行之后，桌宠上的选择仍由用户亲自点击，`pending` 或关闭不算同意。

单文件版首次启动需要解包资源，可能比源码运行略慢。`dist/`、`.venv/` 与构建缓存不入 Git；源码包必须保留 `assets/sprites/`。通知数据库默认在 `%LOCALAPPDATA%\NijikaDesktopPet\notifications.sqlite3`；可用 `env.example` 中的可选变量在隔离测试时改路径。消息含任务摘要，请只在受信任的本机用户会话中使用。本项目不要求真实 API 密钥或联网。

维护者可运行 `.\.venv\Scripts\python.exe tools\smoke_packaged_mcp.py` 测试打包服务，或运行 `.\.venv\Scripts\python.exe tools\smoke_pet_ipc.py` 在隔离消息库下测试真实桌面气泡与点击回传。`tools/benchmark_motion.py`、`tools/probe_window_fps.py` 和 `tools/make_bubble_preview.py` 分别用于动画性能及气泡预览；这些工具不会进入打包版。
