# 虹夏桌宠 · Windows 私下试用包

适用 Windows 10/11 x64。先把整个 ZIP 解压到普通文件夹；不要直接在 ZIP 预览窗口运行脚本。桌宠本体不需要管理员权限、Python 或联网；控制中心使用 Microsoft Edge WebView2，并仅开放本机回环管理端口。无需账号登录。

在解压文件夹打开 PowerShell，运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1
```

这会把桌宠、MCP、可选审批提醒程序和控制中心复制到 `%LOCALAPPDATA%\NijikaDesktopPet\app`，在桌面创建“虹夏桌宠”与“虹夏控制中心”快捷方式，并启动桌宠。双击控制中心可添加 Agent、导入皮肤、调整动作和配置投喂入口；右键角色也可打开控制中心。想要桌宠开机启动，在安装命令末尾加 `-AutoStart`。

Agent 接入是可选的。完整配置、源码安装方式和验证步骤见包内 `AGENT_SETUP.md`。电脑上已安装相应客户端后，关闭正在运行的旧任务和桌宠，再按需要重跑安装脚本并附加参数：

```powershell
# Codex：安装 MCP 与自动触发技能
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1 -Codex -NoLaunch

# 可选：同时准备 Codex 命令审批提醒（随后本人在 /hooks 审阅并信任）
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1 -Codex -CodexHooks -NoLaunch

# ChatGPT 桌面客户端的本机 Work：安装本地插件
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1 -Work -NoLaunch

# DeepSeek Harness：配置 desktop/web 与技能
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1 -Dsh -NoLaunch
```

Codex 和 Work 接入需要 `codex` 命令可从 PowerShell 找到；**现有 Work 插件还需要 `python.exe` 在 PATH 中**，安装脚本会提前检查。DSH 接入需要先在本机建立 `%USERPROFILE%\.dsh` 配置。三个参数可以合并使用。脚本不会删除别人的 Agent 配置；若 Codex 中已经存在 `nijika-pet` 服务，会提示核对路径，不会覆盖。配置后请重启相应客户端，用**新任务**发一条简短选择题，确认桌面显示、点击和聊天中的读回。Work 插件安装后还要重启 ChatGPT 桌面客户端。仅本机运行的 Work 可访问此 Windows 程序，普通聊天或云端 Work 不会自动连接。

默认安装到固定用户目录，因此解压出来的文件夹以后可以移走。搬动或更新正式安装目录后需重跑 Agent 接入步骤。消息记录保存在本机 `%USERPROFILE%\.nijika-desktop-pet\notifications.sqlite3`，避免 AppData 被打包客户端重定向成另一份队列；新版桌宠兼容旧会话的待处理消息。此试用包不含发送者的消息库或聊天历史。

`-CodexHooks` 只安装事件定义，必须在 Codex CLI 的 `/hooks` 中本人审阅并信任，再开新任务才会执行。气泡只是提醒，点击“知道了”不等于命令授权；请在 Codex 原审批卡处理。若任务采用不请求审批的策略，就不会有审批事件。完整验收步骤见 `AGENT_SETUP.md`。

桌宠收到选择但 Agent 任务已经结束时，点击结果会保存，**不会自动唤醒已结束的任务**。回原会话发送“继续”，Agent 应先读取此前的回复。`pending` 只表示消息进入本机队列，不代表气泡已显示或用户已同意。

这是非官方同人试用包。角色图像和图标没有第三方再分发许可证；本包供收件人私下体验，不应公开发布、二次上架或将素材用于其他作品。公开发行前需单独解决角色与图像的使用权。软件包不包含 BOOTH 模型、抖音截图、个人配置或密钥。
