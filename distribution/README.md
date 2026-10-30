# 虹夏桌宠 · Windows 安装与进阶说明

单文件 Setup 用户先读安装目录下的 `00-安装后先看.txt`。双击 Setup EXE 即可安装，无需运行 PowerShell；安装后从“虹夏桌宠设置”接入 Agent。下面的 PowerShell 命令仅适用于旧 ZIP 包或维护者。

第一次使用请先看包根目录的 `00-解压后先看.txt`：包含安装命令、界面接入步骤和可直接复制的 AI 验证提示词。本文保留进阶选项和完整使用边界。

适用 Windows 10/11 x64。先把整个 ZIP 解压到普通文件夹；不要直接在 ZIP 预览窗口运行脚本。桌宠本体不需要管理员权限、Python 或联网；控制中心使用 Microsoft Edge WebView2，并仅开放本机回环管理端口。无需账号登录。

在解压文件夹打开 PowerShell，运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1
```

这会把桌宠（含设置中心）、MCP 和可选审批提醒程序复制到 `%LOCALAPPDATA%\NijikaDesktopPet\app`，在桌面创建“虹夏桌宠”与“虹夏桌宠设置”快捷方式，并启动桌宠。双击“虹夏桌宠设置”可添加 Agent、导入皮肤、调整动作和配置投喂入口；右键角色同样可以打开设置中心。想要桌宠开机启动，在安装命令末尾加 `-AutoStart`。

在设置中心进入“互动与养成”，保存“允许分区触摸”后可点击桌面角色的头顶、脸颊和身体，双击可触发坐姿小舞；右键可选择基础动作或“停止当前动作”。轻养成是独立开关，开启并保存后可投喂点心/喝水，两种操作分别冷却 30 秒。动作按钮属于面板试映，投喂才会保存数值并发送桌面反馈；工作提醒优先显示。若页面提示桌面互动未连接，先启动或更新这份完整试用包里的桌宠。

Agent 接入是可选的。新版设置中心的“扫描本机”会显示 Codex、ChatGPT Work、DSH、Claude Code、Gemini CLI、Copilot CLI 等适配器，并单独识别 VS Code 中已安装的 Codex、Claude Code、DSH、CodeBuddy 和 GitHub Copilot Chat 扩展。MAGPIE 已管理的客户端只登记归属，不在虹夏中重复写入。扫描只读取已知路径和扩展清单，不读取账号、聊天或密钥。

完整配置、源码安装方式和验证步骤见包内 `AGENT_SETUP.md`。电脑上已安装相应客户端后，关闭正在运行的旧任务和桌宠，再按需要重跑安装脚本并附加参数：

```powershell
# Codex：安装 MCP 与自动触发技能
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1 -Codex -NoLaunch

# 可选：同时准备 Codex 完成兜底与命令审批提醒（随后本人在 /hooks 审阅并信任）
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1 -Codex -CodexHooks -NoLaunch

# ChatGPT 桌面客户端的本机 Work：安装本地插件
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1 -Work -NoLaunch

# DeepSeek Harness：配置 desktop/web 与技能
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1 -Dsh -NoLaunch
```

Codex 和 Work 接入需要 `codex` 命令可从 PowerShell 找到；**现有 Work 插件还需要 `python.exe` 在 PATH 中**，安装脚本会提前检查。DSH 接入需要先在本机建立 `%USERPROFILE%\.dsh` 配置。三个参数可以合并使用。脚本不会删除别人的 Agent 配置；若 Codex 中已经存在 `nijika-pet` 服务，会提示核对路径，不会覆盖。配置后请重启相应客户端，用**新任务**发一条简短选择题，确认桌面显示、点击和聊天中的读回。Work 插件安装后还要重启 ChatGPT 桌面客户端。仅本机运行的 Work 可访问此 Windows 程序，普通聊天或云端 Work 不会自动连接。

默认安装到固定用户目录，因此解压出来的文件夹以后可以移走。搬动或更新正式安装目录后需重跑 Agent 接入步骤。消息记录保存在本机 `%USERPROFILE%\.nijika-desktop-pet\notifications.sqlite3`，避免 AppData 被打包客户端重定向成另一份队列；新版桌宠兼容旧会话的待处理消息。此试用包不含发送者的消息库或聊天历史。

`-CodexHooks` 安装 UserPromptSubmit、PermissionRequest、PostToolUse、Stop 四类定义，必须在 Codex CLI 的 `/hooks` 中本人审阅并信任，再开新任务才会执行；升级用户尤其需审阅新增的 UserPromptSubmit 与 Stop。实质任务漏调用桌宠时会从最终回复生成最多 120 字的安全结果摘要，不再只写“任务完成”；同轮已有有效桌宠通知则不重复，简短问答尽量保持安静。既有 Computer Use notify 原样保留。气泡只是提醒，点击“知道了”不等于命令授权；请在 Codex 原审批卡处理。若任务采用不请求审批的策略，就不会有审批事件。完整验收步骤见 `AGENT_SETUP.md`。

桌宠收到选择但 Agent 任务已经结束时，点击结果会保存，**不会自动唤醒已结束的任务**。回原会话发送“继续”，Agent 应先读取此前的回复。`pending` 只表示消息进入本机队列，不代表气泡已显示或用户已同意。

这是非官方同人试用包。角色图像和图标没有第三方再分发许可证；本包供收件人私下体验，不应公开发布、二次上架或将素材用于其他作品。公开发行前需单独解决角色与图像的使用权。软件包不包含 BOOTH 模型、抖音截图、个人配置或密钥。
# 多帧外观与作者赞助

- 角色衣橱支持旧 PNG / 九表情 ZIP，也支持连续透明 PNG 待机包；可复制 AI 提示词和下载模板。完整格式与逐步验收见包内 `SKIN_FORMAT.md`。
- Agent 页可展开各客户端差异；共享一个桌宠无需运行多个窗口。MCP 接通不代表原生权限事件已接通。不要把别人的用户配置/密钥导入自己的客户端。
- 如果维护者在包中附带公开赞助资料，投喂页会显示其链接或收款图；未配置时保持空状态。赞助自愿，不影响功能，本程序不处理支付或确认到账。


### 通知来源

头部显示 Agent · 软件，任务名另起一行；设置中心自动配置提示词含对应字段。同一作用域不要重复添加 nijika-pet/nijika_pet。编辑器模式需明确 VS Code/Obsidian，更新后分别重连旧 MCP。DSH/WorkBuddy 未知实际 Agent 时显示 Agent，详见 AGENT_SETUP.md。

## Agent 来源填写

通用客户端分别填写 Agent 和所在软件，不要把固定软件来源的配置共享给所有客户端。软件必填，未知模型用 Agent。旧别名或旧路径遇到无法核实/权限冲突时配置会停止，需要先核对原服务；已存在的其他服务不会被自动覆盖。详见 AGENT_SETUP.md。

## 本机发现入口（2026-10-29）

安装后打开 Agent 页的“扫描本机”，勾选软件、查看预览再应用。支持 Codex、ChatGPT Work、DSH、Claude Code、Gemini CLI、Copilot CLI；其他入口可生成指引。MAGPIE 管理项只登记，不改客户端或管理器。完成配置后在宿主新任务调用虹夏；本机测试不代表已接入宿主。旧连接和未带档案编号的共享配置不会自动显示该档案已验证。
