# 虹夏桌宠 · 2D 坐姿版

更新触发：2026-09-26 用户要求按 SOP_Core 管理文档并上传 Git。

Windows 桌面上的 Q 版坐姿虹夏：完整双腿、透明背景、八种表情、自然眨眼。默认“活泼明显”动态：连续的待机呼吸、轻摆与偶尔弹跳；单击换表情并弹起，双击连续回应；按住角色拖动时倾斜，松手自然回正。右键可以选表情、大小、动态强度或退出。当前只做外观和本地互动，尚未连接 AI/MCP 通知。

本机成品可双击 `dist/虹夏桌宠.exe` 启动。Git 仓库只保存源码、素材和文档，`dist/` 生成文件不入库；克隆后按 `INSTALL.md` 安装依赖并构建。动画预览见 `art/motion-preview.gif`，角色帧在 `assets/sprites/`，素材制作记录见 `art/PROMPTS.md`。

运行环境为 Windows 10/11 x64；源码使用 Python 3.12、Pillow 12.2，打包使用 PyInstaller 6.20。需求与验收见 `REQUIREMENTS.md`，待办见 `TODO.md`，架构与内部接口分别见 `ARCHITECTURE.md` 和 `INTERFACES.md`。这是非官方同人练习；仓库没有声明可供第三方复用角色素材的许可证。
