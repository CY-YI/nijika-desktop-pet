# 源码开发与学习指南

更新于 2026-10-31：供收到完整工程包、准备自行修改的人使用。

## 先看哪几个文件

1. `README.md`：项目介绍与当前能力。
2. 本文：运行源码、修改位置和构建方法。
3. `ARCHITECTURE.md`、`INTERFACES.md`：模块关系与接口。
4. `AGENT_SETUP.md`、`NOTIFICATION_PROTOCOL.md`：Agent 接入及自动提醒边界。
5. `SKIN_FORMAT.md`：角色图片、多帧皮肤与导入格式。
6. `REQUIREMENTS.md`、`TODO.md`、`CHANGELOG.md`：需求选择、未完成项与历史变更。

文档里的历史本机路径、提交和诊断目录属于开发记录，不能直接复制为你的安装位置。以当前安装目录和向导实际生成的路径为准。

## 工程包里有什么

- 根目录 Python 文件：桌宠、设置服务、通知队列、Agent 接入等源码。
- `control-ui/`：设置界面的 HTML、CSS 和 JavaScript，没有 npm 构建步骤。
- `assets/`：当前角色图片和图标；`art/`、`web-demo/`：设计说明与预览。
- `integrations/`、`skills/`、`plugins/`、`.agents/`：客户端接入脚本、规则与本机 Work 插件。
- `tests/`、`tools/`：回归测试、构建辅助、动画准备及诊断工具源码。
- `build.ps1`、`installer/`：三个 EXE 的构建入口与 Windows 安装器配置。
- `dist/`：本次附带的三个已验证运行程序。修改源码后，这些 EXE 不会自动变化，需要重新构建。
- `SOURCE_MANIFEST.json`：源码提交、分支与每项文件的 SHA-256。

不包含原作者的 `.git/`、虚拟环境、消息库、客户端配置、登录信息、日志、备份或历史安装包。`.agents/` 是本项目的插件清单，和 `.git/` 是两个不同的目录。未纳入源码管理的本机视频原片和旧诊断截图也不属于此工程快照；当前桌宠所需图片均在 `assets/`。

## 先运行附带程序

完整解压后，直接打开 `dist/虹夏桌宠.exe`；设置界面可从角色右键菜单打开，或在工程目录运行：

```powershell
& ".\dist\虹夏桌宠.exe" --control-panel
```

程序默认使用你自己 Windows 用户目录中的数据。如果你已装过虹夏，希望开发时与日常版分开，请使用下面的隔离设置。

`虹夏MCP-v2/虹夏MCP-v2.exe` 和 `虹夏审批提醒.exe` 由客户端或事件模块调用，不是需要手动打开的桌宠窗口。MCP 自 `0.1.9` 起为 onedir，必须保留同级 `_internal/`。

## 运行源码

适用 Windows 10/11 x64；当前已测 Python 为 3.12。桌面设置窗口使用 WebView2；可用 `--browser` 在浏览器打开设置页。依赖安装通常需要联网，程序本体不要求模型 API 密钥。

在工程目录打开 PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe pet.py --self-test
```

`requirements-lock.txt` 是已测 Windows/Python 3.12 环境的完整版本；`requirements.txt` 列出四项直接依赖。无需激活虚拟环境，使用上面的解释器完整相对路径即可。

开发时先把数据库和 Agent 配置目标隔离在工程目录：

```powershell
$env:NIJIKA_PET_DB_PATH = Join-Path $PWD "diagnostics\local-development\notifications.sqlite3"
.\.venv\Scripts\python.exe control_panel.py --serve-only --agent-home ".\diagnostics\local-development\agent-home"
```

打开终端输出的 `http://127.0.0.1:端口/`，用 `Ctrl+C` 结束服务。`--agent-home` 将向导的配置目标放到测试目录；本机扫描和配置结果不代表真实客户端已连接。

另开一个 PowerShell，设置同一数据库后运行桌宠：

```powershell
$env:NIJIKA_PET_DB_PATH = Join-Path $PWD "diagnostics\local-development\notifications.sqlite3"
.\.venv\Scripts\python.exe pet.py
```

两个进程使用同一数据库才能互相接收消息。需要测试真实 Agent 时，按 `AGENT_SETUP.md` 在真实客户端预览并确认接入；不要把测试目录配置当成已完成真实接入。

## 想改什么，找哪里

| 修改目标 | 主要位置 |
| --- | --- |
| 桌面角色、窗口、拖动、气泡与点击 | `pet.py` |
| 设置界面布局和交互 | `control-ui/` |
| 设置 HTTP 接口 | `control_panel.py` |
| 设置、皮肤和 Agent 档案 | `control_store.py`、`skin_animation.py` |
| 互动动作、养成、专注与便签 | `interaction_motion.py`、`interaction_store.py`、`companion_store.py` |
| MCP 工具与通知存储 | `mcp_server.py`、`notification_store.py` |
| 通知分类、安全摘要及统一生命周期 | `notification_policy.py`、`notification_lifecycle.py` |
| 来源标签、宿主和编辑器识别 | `notice_source.py`、`host_process.py`、`vscode_agents.py` |
| 本机发现、自动配置和配置保护 | `agent_discovery.py`、`agent_setup.py`、`setup_config.py` |
| Codex 原生事件适配 | `approval_hook.py`、`integrations/codex/` |
| DSH 实时事件适配 | `integrations/dsh/lifecycle-bridge.mjs` |
| 换皮肤、动画制作 | `SKIN_FORMAT.md`、`art/animation/README.md`、`tools/prepare_animation.py` |

建议先改设置页面的一段文案或样式，用源码设置服务观察变化；再从一个小模块开始学习。改完 Python 代码通常需要重启对应进程。

## 验证改动

```powershell
$env:NIJIKA_PET_DB_PATH = Join-Path $PWD "diagnostics\local-development\notifications.sqlite3"
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

前端测试需 Node.js；本机已测 Node 24，不需要运行 `npm install`：

```powershell
node --test tests/test_form_state.cjs tests/test_interaction_ui.cjs
node --test tests/dsh_lifecycle.test.mjs
```

DSH 的真实 SessionStore 测试需要本机已安装 DSH 的内部模块路径，未提供时会跳过该项。动画准备工具的可选依赖在 `tools/requirements-animation.txt`；它们不属于普通桌宠的必需依赖。

`tools/smoke_windows_installer.py` 只能在可丢弃 Windows Sandbox/虚拟机里运行，不要在日常电脑账户执行安装/卸载冒烟。其他写客户端配置或修复工具也应先读说明，不要批量执行 `tools/` 下的所有脚本。

## 把修改打成 EXE

在装好依赖的工程目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1 -OutputDirectory dist-dev
```

三个程序生成在 `dist-dev/`。桌宠、MCP 和事件提醒程序应来自同一份已验证源码。打包分发可使用：

```powershell
.\.venv\Scripts\python.exe tools/package_release.py --app-exe ".\dist-dev\虹夏桌宠.exe" --mcp-exe ".\dist-dev\虹夏MCP-v2\虹夏MCP-v2.exe" --approval-exe ".\dist-dev\虹夏审批提醒.exe" --output ".\dist-release\my-trial.zip"
```

Windows Setup 另需本机 Inno Setup 6 编译器，见 `installer/README.md` 和 `PUBLISHING.md`。源码包不附带第三方编译器安装文件。

## 接入和分享边界

Codex 和 DSH 共用通知核心，但各自需要宿主事件入口。DSH 当前核对版本为 `0.2.1-rc.2 / 0.2.1-rc.3`；Work 等未接结束事件的入口仍依赖主动调用。不能因为安装了 skill 就宣称所有客户端每轮一定会提醒。

工程包提供给熟人私下学习和修改，不代表角色、图标或其他第三方素材获得了新的公开分发许可。仓库未提供统一的开源许可证，不在本次打包中替作者新增授权；需要公开发布或商用时应先核对代码与素材的使用范围。

源码包不带 Git 历史。要保留自己的修改，可以在解压目录新建 Git 仓库；要沿用原仓库分支和历史，请使用有访问权限的 GitHub 账号克隆仓库。
