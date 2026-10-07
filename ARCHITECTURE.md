# 架构

更新触发：2026-09-26 清空旧版后，按 2D Windows 桌宠重建。

`pet.py` 是唯一运行入口。Pillow 从 `assets/sprites/` 读取九张同尺寸 RGBA 角色帧，启动时缩放到窗口尺寸。每次刷新按实际时间计算呼吸、摇摆、弹跳和拖动倾角，并对原图做亚像素仿射采样；转换为 Win32 所需的预乘 alpha 后写入复用的 DIB。Win32 分层置顶窗口显示位图，处理鼠标拖动、单击、双击、右键菜单和眨眼。10 毫秒的窗口定时请求在当前测试机器上产生约 16 毫秒的实际帧间隔；动作按单调时钟计算，丢帧也不会拖慢动作时长。动画不改写原始图片。没有 Web 前端、后端、数据库或外部网络。资源路径在源码与 PyInstaller 冻结环境下均由 `__file__`/`_MEIPASS` 定位。接口见 `INTERFACES.md`。

气泡由同一进程内的第二个分层置顶窗口绘制，文字和按钮仅在消息变化时重画；它跟随角色移动。角色定时器负责低频日常话语和气泡自动收起。菜单中的演示提醒只回显本地选择。真实 MCP 提醒带请求 ID，选项卡同时显示短名称和一句说明，点击后将选择写入本地队列供对应 Agent 读取。

2026-10-07 接入层：`mcp_server.py` 用官方 Python MCP SDK 的 stdio 传输供 Codex 启动，提供完成提醒、请求选择和查询/等待回复工具。`notification_store.py` 以用户本机 `%LOCALAPPDATA%/NijikaDesktopPet/notifications.sqlite3` 作为进程间队列；Agent 工具写入，桌宠每约 350 毫秒读取最早待处理消息，点击或关闭时写回结果。简单决策及短成果审阅使用 `request_decision`，气泡显示足够的正文和选项简介，Agent 读取选择后在原任务中继续；`show_completion` 仅表示收到较复杂成果的提醒，不代表批准。通知先于日常闲聊显示；桌宠未运行时消息保留。消息只在本机，不开放 HTTP 端口。已处理记录 7 天后清理，待处理超过 30 天失效。Codex 多个任务可分别启动 stdio 子进程，SQLite 事务负责串行化写入。

2026-10-07 Work 本机插件层：`.agents/plugins/marketplace.json` 暴露 `plugins/nijika-work-local/`，其 `mcp.json` 以 `nijika-work-pet` 名称通过插件内的 Python 启动脚本运行同一个本机 EXE，避免与已有 Codex 直接配置的 `nijika-pet` 同名；插件 skill 约束简短决策、等待回执与回退行为。这层只在可启动本机 stdio MCP 的本地执行环境有效；托管 Work 需另有远程 HTTPS MCP 与身份验证。当前验证边界是插件安装、清单启用、插件启动入口及本机 MCP 协议，Work 会话端到端检查仍单列为待办。

Windows 本机负责绘制和消息循环；图像生成只负责制作静态素材，不进入运行时。`build.ps1` 用 PyInstaller 分别打包桌宠窗口版和 MCP 标准输入输出服务版，图像作为桌宠只读资源嵌入。通知记录位于用户本机目录；角色位置和动态偏好仍未持久化。
