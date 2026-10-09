# 虹夏桌宠 · 2D 坐姿版

桌面决策现在可为一个有明确理由的选项显示“推荐”。Agent 收到桌面点击后，应在原 Codex/Work 聊天中写明所选项，再按选择继续。这条聊天记录是 Agent 的确认消息，不会伪装成用户发送的新消息。如果 Agent 已结束等待，桌宠不会独立唤醒该任务，需要继续该聊天才能读取已保存的点击结果。

更新触发：2026-10-07 用户要求简单决策直接在桌宠完成，不必总回到聊天。

Windows 桌面上的 Q 版坐姿虹夏：完整双腿、透明背景、八种表情、自然眨眼。默认“活泼明显”动态：连续的待机呼吸、轻摆与偶尔弹跳；单击换表情并弹起，双击连续回应；按住角色拖动时倾斜，松手自然回正。右键可以选表情、大小、动态强度、手动说话、演示提醒或退出。日常气泡偶尔出现。Codex 可经本机 MCP 工具发送真实的完成提醒和选择题；简单选择及短成果审阅在气泡中显示完整决策信息和逐项简介，点击结果由当前 Agent 读取并继续任务，无需再回聊天确认。只有完整内容不适合气泡时，才使用单按钮完成提醒。菜单里的“演示”仍只在本地生效。

本机成品可双击 `dist/虹夏桌宠.exe` 启动；`dist/虹夏MCP-v2.exe` 是 Codex 自动启动的 stdio 服务，不需手动双击。当前电脑已注册 `nijika-pet` MCP 并安装 `skills/nijika-desktop-dialog/` 的全局副本；项目 `AGENTS.md` 规定何时主动发送提醒。独立 Codex CLI 会话已在普通审阅和选择任务中自主调用桌宠；Codex 桌面应用的新任务也已自动发出完成提醒并在桌面显示。Git 仓库只保存源码、素材、测试和文档，`dist/` 生成文件不入库；克隆后按 `INSTALL.md` 构建和注册。动画预览见 `art/motion-preview.gif`，气泡外观见 `art/bubble-preview.png`，角色帧在 `assets/sprites/`。

对外分享文档可运行 `.\.venv\Scripts\python.exe tools\package_docs.py` 从当前源码生成压缩包；旧压缩包不作为最新工程状态的依据。

桌面客户端 Work 的本机接入包在 `plugins/nijika-work-local/`，本机已通过 `.agents/plugins/marketplace.json` 安装并启用。它把同一 `虹夏MCP-v2.exe` 作为插件工具提供，并附带 Work 对话用的简短决策 skill。独立 Codex 会话关闭原有直连后仍通过插件实际调用成功；这证明插件工具链可用，但不等于 Work 会话已经连接。首次使用需重启桌面客户端、在**本机运行的 Work 新任务**中确认工具可见并完成一次桌面点击回传。云端 Work 对话不能直接运行这个 Windows 本机 stdio 程序；那种接入需要另行设计可安全访问的远程 MCP 服务。详见 `INSTALL.md`。

运行环境为 Windows 10/11 x64；源码使用 Python 3.12、Pillow 12.2、官方 MCP Python SDK 2.3，打包使用 PyInstaller 6.20。本机消息保存在用户目录的 SQLite 文件；已处理消息 7 天后清理，未处理消息 30 天后过期。MCP 只走本机 stdio，不开放网络端口。需求与验收见 `REQUIREMENTS.md`，待办见 `TODO.md`，架构与内部接口分别见 `ARCHITECTURE.md` 和 `INTERFACES.md`。这是非官方同人练习；仓库没有声明可供第三方复用角色素材的许可证。
