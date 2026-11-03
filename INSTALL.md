# 安装与运行

## 2026-11-03 MCP onedir 升级

`0.1.9` 起，MCP 的正式路径为 `%LOCALAPPDATA%\NijikaDesktopPet\app\dist\虹夏MCP-v2\虹夏MCP-v2.exe`，并依赖同级 `_internal\`。不要把目录内的 EXE 单独复制到别处。升级安装器只删除精确旧文件 `...\dist\虹夏MCP-v2.exe`，再安装完整 onedir 目录；消息库、皮肤、设置、Agent 档案、客户端配置、MAGPIE 管理项和 Hook 信任均保留。

新版本不再产生 onefile 的 `_MEI` 解包目录。已有残留可用仓库工具先做只读预演：

```powershell
.\.venv\Scripts\python.exe tools\cleanup_mcp_temp.py --summary-only
.\.venv\Scripts\python.exe tools\cleanup_mcp_temp.py --min-age-hours 24 --apply --summary-only
```

第二条命令会删除 `%TEMP%` 中同时匹配旧虹夏运行时指纹、超过最小年龄且没有被任何运行进程使用的直属 `_MEI*` 目录；不会处理其他软件、重解析点或活动目录。运行中的旧客户端不会被强制结束，重连后才会使用新路径。

本机迁移已完成：正式安装、工作区 `dist`、Codex/DSH 配置、MAGPIE 的 `nijika-pet` 和 Work 插件 0.1.9 均使用 onedir；最终 Python 192 项、JavaScript 20/20、冻结前端的 173 文件暂存区、冻结 MCP 与 Setup 编译通过。`0.1.9` 尚待在一台可丢弃的干净 Windows 环境完成实际安装、升级、桌面启动和卸载；不在日常账户用测试绕过该隔离边界。

## 本轮统一提醒更新

使用本轮完整新版包，保留 `dist` 和 `integrations` 的相对结构。安装后在“Agent 接入”重新预览并应用 DSH，可同时更新 MCP 和独立的 `NIJIKA-DSH-LIFECYCLE` 块；实际模块及程序路径按接收方安装位置生成。缺少模块、标记冲突或预览后配置变化会停止写入，其他服务与权限保留。MAGPIE 管理的连接只登记，不会自动安装此模块，须由维护该配置的人审阅合并。

Codex 已信任的原有四事件命令保持兼容，不需要重复重配 MCP。DSH 重启后在新会话验收；核对版本为 `0.2.1-rc.2 / 0.2.1-rc.3`，其他版本须另验。Work、其他客户端仍须主动调用，不因安装 skill 获得自动补发。桌宠本体不需要 Python；DSH 模块使用宿主自带 Node 能力，Work 插件继续要求 PATH 中的 `python.exe` 和 Codex CLI。

每个客户端分开检查：主动通知和点击回传；不提示使用虹夏的短问答；主动通知后同轮无重复；并行任务不串线。面板测试不能替代外部宿主实测。协议与故障语义见 `NOTIFICATION_PROTOCOL.md`。

## 2026-10-31 Codex 内部后台任务误提醒修复

正式安装的 `%LOCALAPPDATA%\NijikaDesktopPet\app\dist\虹夏审批提醒.exe` 已替换为 SHA-256 `5CD44E9F738D96AE68E0ECCFE25AD9467EEA18C48FC882BE2D254198B8C8F717`。新 Hook 不再把 Codex `ambient-suggestions` 或私有 helper 的 `{"exclude":[]}` 后台结果写入虹夏气泡；普通用户回复、简单问答和用户主动要求的 JSON 仍每轮提醒，JSON 使用固定安全摘要。桌宠、MCP、消息库、MAGPIE 服务与 Hook 信任未改变。Codex/DSH/Work 的持久规则已同步，Work 插件已升级并启用 0.1.9；已打开的客户端需要新任务或重连以加载新版规则。

## 2026-10-30 路径可移植性与配置审计

安装脚本默认写入 `%LOCALAPPDATA%\NijikaDesktopPet\app`，也可用 `-InstallRoot` 指定其他本机绝对路径。它会使用收件人的实际安装位置重写 Work `mcp.json`，不会沿用在原作者电脑上的路径；Codex 配置目录由 `-CodexHome`（默认 `%USERPROFILE%\.codex`）生成，DSH 目录由 `-DshRoot`（默认 `%USERPROFILE%\.dsh`）生成。设置中心的接入向导使用当前实际用户目录和当前 MCP 可执行文件位置，不写死项目目录。

已用带空格和中文的自定义安装目录验证：完整解压包安装后，Work 的 MCP 参数等于该安装目录下的 `dist\虹夏MCP-v2\虹夏MCP-v2.exe`，且不包含原解压目录；收件人传入的 `-CodexHome` 也会同步到实际 Codex CLI 进程，不能再出现技能写在自定义目录、MCP 却注册到默认目录的分裂状态。安装/向导继续采用备份、预览后变化检查和同名冲突停止；不要为了“修好”而同时保留两个管理同一个客户端的虹夏服务。

维护者检查技能、当前皮肤和 Agent 档案：

```powershell
python tools\audit_agent_integrations.py
python tools\audit_local_state.py
```

若输出内容不一致、重复、当前皮肤缺失或完整 Agent 键重复，命令返回非零；按 `issues` 中的准确路径人工核对。Codex 的权威用户技能位置是 `%USERPROFILE%\.codex\skills\nijika-desktop-dialog`，不要再向 `%USERPROFILE%\.agents\skills` 安装同名副本。维护者可用 `tools\cleanup_legacy_nijika_integration.ps1` 先做默认预演，再决定是否以 `-Apply` 备份并清理三个已知旧文件。当前皮肤目录仍按原 PNG/ZIP 格式读取，不需要迁移；旧 Agent 档案也不批量删除，重新扫描后由当前向导补全新配置。

## 2026-10-30 提醒可靠性与 DSH 来源正式版

当前正式安装的桌宠、MCP 和审批提醒已更新到提醒可靠性加固构建。三个程序位于 `%LOCALAPPDATA%\NijikaDesktopPet\app\dist\`，桌面与开机自启快捷方式继续使用同一路径；现有消息库、设置、Agent 档案和 Hook 信任未被初始化或覆盖。更新前程序、实际运行资源和 SQLite 一致性快照在 `backups/reminder-source-hardening-20261030/`。

已打开的外部 Agent 会话需要重连 `nijika-pet` 或新建任务，才能加载新版“主动发送具体完成摘要”的持久规则。DSH 来源隔离由共享 MCP 服务端执行，因此即使旧连接仍发送 `agent_name=Codex` 也会规范为 `Agent · DSH`；只有明确的 DeepSeek 等真实模型名会保留。

## 2026-10-30 本机发现与 VS Code Agent 正式版

当前正式程序已更新到 `%LOCALAPPDATA%\NijikaDesktopPet\app\dist\`，桌面与开机自启快捷方式继续使用同一路径。打开“虹夏桌宠设置”→“Agent 接入”→“扫描本机”，可查看六种可自动接入客户端、五种指引入口，以及已安装的 VS Code Codex、Claude Code、DSH、CodeBuddy 和 GitHub Copilot Chat 扩展。

VS Code 扩展只在明确条件成立时使用 `VS Code · Agent` 来源；共享 Codex/DSH 后端不会因为曾从编辑器启动就全局改成 VS Code。MAGPIE 已管理的客户端只登记档案，不在虹夏里重复写配置。扫描只读取已知路径和扩展清单，不读取账号、聊天或密钥。

更新前程序和数据库快照在 `backups/vscode-agents-formal-20261030/`。旧 MCP 文件仍可能被已打开会话占用，因此以 `虹夏MCP-v2.running-formal-20261030.bak` 保留；它不是启动入口。要激活新版来源识别，请保存任务后在客户端重连 `nijika-pet` 或新建会话。

## 2026-10-29 接入配置修复版本

通用向导的“所在软件”必填，例如 VS Code/Obsidian；Agent 不确定时留空为 Agent。无需模型密钥。旧 Codex 同名程序无法验证或别名权限冲突时，向导会停止并说明原因，避免继续使用旧程序或覆盖无关服务。旧自定义档案可以读取，但要获得明确来源需按新向导重新生成对应软件配置。旧宿主连接需要重载，面板本机测试不能代替外部新会话验收。


## 2026-10-28 来源更新后重连

本次头部修复需要匹配的桌宠、MCP 和审批提醒程序。保持标准 `app/dist` 路径，更新前备份程序与数据库；更换 MCP 文件不会更新正在运行的连接，保存任务后分别重新连接客户端。VS Code/Obsidian 通过相同引擎启动时需明确软件字段，不能保证引擎自动识别外层编辑器。不要将同一个虹夏程序以两个别名同时配置到同一作用域。


## 本机已安装的 MVP（2026-10-26）

正式程序已更新至 `%LOCALAPPDATA%\NijikaDesktopPet\app\dist\虹夏桌宠.exe`，桌面与开机自启沿用该路径。双击“虹夏桌宠设置”进入“互动与养成”：分区触摸独立于轻养成；保存开启轻养成后可投喂点心/喝水。右键角色可选基础动作及“停止当前动作”，工作提醒优先显示。既有 Agent 配置与钩子无需重新安装或信任。

本轮旧桌宠及一致性数据快照保存在项目 `backups/mvp-formal-20261026/`，回退时仅恢复需要的程序，默认保留最新消息与养成数据。原视频样片没有进入正式安装；完整转身、抓取抛掷和进一步美术效果仍为后续。

## 维护者：待机动画对照（2026-10-26）

可选 `tools/requirements-animation.txt` 仅供维护者导出素材。`tools/review_animation.py export` 从已验证源片/WebP 生成独立新目录，`serve <目录>` 在系统分配的空闲回环端口提供只读对照；打开终端输出的 URL 即可。准确命令、实际样片与检查记录见 [动作制作说明](art/animation/README.md)。这不安装皮肤或启动第二套桌宠，用户安装包/Agent 接入不增加步骤，不把源片或维护页收入正式安装包。

## 点击闪烁与来源复发修复（2026-10-25）

独立候选位于 `dist-next/source-flash-20261025/`，同时包含无闪烁切换的设置程序和来源校正 MCP；标准展开目录用于候选测试，旧前端候选保留。源码隔离预览 `http://127.0.0.1:64005/#interaction` 已读取新控制器；不要用旧候选 EXE 验收新切换逻辑。界面素材仍为旧的局部变形试映，不等同于 AN01 视频动画。

来源修复的 MCP 已备份后更新至本机标准 `app/dist/虹夏MCP-v2.exe` 和工作区 dist；正式桌宠/审批 EXE、客户端配置与信任未改。正在运行的旧 MCP 仍需在客户端的 MCP 服务器列表对 `nijika-pet` 点 Restart 才能释放旧连接；这一步不是重新安装。旧映像临时保留为标准 dist 内的 `.running-old-<标记>.exe`，不被任何新配置引用，退出旧进程后再清理；回退副本在忽略的 `backups/source-flash-20261025/`。

维护者可运行 `tools/smoke_mcp_sources.py <MCP绝对路径>`：使用隔离库验证七个真实 stdio 场景的来源、完成、选择和回执，覆盖现代/legacy 协议、错误环境标签、Work、自定义名与未知客户端。打包可同时指定 `tools/package_release.py --app-exe <候选桌宠> --mcp-exe <候选MCP> --output <新ZIP>`，避免把旧 MCP 混入新候选。

## 设置中心前端源码验收（2026-10-25）

本轮修改当前分支的 `control-ui/` 和静态资源白名单，已构建独立前端候选，尚未替换正式安装版。不要通过更新 MCP、重装技能或重新信任钩子获取界面变化；正式界面需要随桌宠程序更新。

维护者运行 `node --test tests/test_form_state.cjs tests/test_interaction_ui.cjs` 与 `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`，本轮分别 17/75 项通过。本机当前预览为 `http://127.0.0.1:64005/#interaction`，数据在忽略目录 `diagnostics/frontend-20261025/`，不读取正式消息库；服务结束后此临时地址失效。真实浏览器已验收七页 360/768/1280 宽度、互动完整流程和手机添加向导，截图/布局数据同目录。

候选 ZIP 位于 `dist-next/frontend-20261025/frontend-review.zip`，展开在其旁边的 `review/虹夏桌宠-Windows私下试用/`，保持 `dist/`、集成脚本与说明的标准相对路径。通过 `tools/package_release.py --app-exe <候选EXE> --output <新ZIP>` 打包，无需覆盖 `dist/` 或正式安装文件。运行 `.\.venv\Scripts\python.exe tools/smoke_frontend_candidate.py "<展开目录>\dist\虹夏桌宠.exe"`，工具会使用自动清理的隔离库/用户目录检查资源、鉴权、养成、动画和通用向导导出，不写真实客户端。真实 WebView2 设置窗口打开/播放已验收，宿主关闭前草稿弹窗仍不作可靠持久化承诺。完整发布边界见 `PUBLISHING.md`。

## 可选动画素材准备（2026-10-19）

维护者在源码环境运行 `.\.venv\Scripts\python.exe -m pip install -r tools\requirements-animation.txt`，再用 `tools\prepare_animation.py` 将本地短片转为独立 WebP 审阅副本，具体参数与当前样片问题见 [动作制作说明](art/animation/README.md)。依赖 `imageio-ffmpeg==0.6.0` 不进入正式桌宠运行依赖或试用包。此次没有重建或替换正式程序，不需要用户调整 Agent 配置、钩子信任或导入教程；当前皮肤导入仍不能接收这段视频。

## Agent 教程维护（2026-10-18）

本机正式 `虹夏桌宠.exe` 已更新自动配置教程并修正管理参数转发，三份旧接入快照已备份刷新。既有客户端 MCP 配置、Codex notify/hooks 信任及 MCP/审批程序保持不变，无需重配；从“设置中心 → Agent 接入 → 接入步骤”重新复制即可取得新版提示词。正式程序基于已验收 `b172fbe` 加 `agent_setup.py` / `pet.py` 维护补丁，未带入下方未验收的互动预览。

维护者可运行 `.\.venv\Scripts\python.exe tools\smoke_agent_guidance.py <实际桌宠EXE绝对路径>`：程序以 `--control-panel --serve-only --agent-home <临时目录>` 隔离验证冻结管理 API，检查完整提示词、真实路径、旧配置保留及 Codex 可选钩子未被自动安装；不启动可视窗口，不向真实消息库发测试。构建来源与摘要在本机忽略目录 `build/agent-guide-hotfix-20261018/manifest.json`，备份在 `backups/20261018-agent-guide-hotfix/`。这是程序/API 验证，不能替代用户页面点击或真实 Agent 自主调用验收。

## 互动设置预览（2026-10-17，尚未替换正式 EXE）

设置中心的“互动与养成”页同时管理试映和桌面 MVP。开启并保存后，桌面点击头部/脸颊/身体会触发分区反馈，双击触发坐姿小舞，右键菜单可调用摇头、坐姿小舞、提起晃晃；试映仍可停止、重播并选择轻柔或活泼幅度。若桌宠状态页显示 `desktop_playback=false`，先重启已安装的桌宠 EXE，再重新打开设置中心。

需要养成时，在下方开启“轻养成”并点“保存互动设置”，再点击点心或喝水。数值自动保存在消息库，两个投喂分别冷却 30 秒；关闭养成后暂停，离线最多计算 8 小时，没有死亡或惩罚。成功投喂会由桌宠心跳消费一次并播放基础动作；页面试映仍不改数值。触摸/特效开关可先在试映室试用，再保存偏好。

新动作目前只在源码面板内播放，不会排入正式桌宠队列。互动功能没有随正式程序更新；2026-10-18 的正式版只维护接入教程。待页面和动画效果验收后才接入桌面动作、重建并安装，不要把互动预览的代码提交视为已安装升级。

隔离开发预览可先设置 `NIJIKA_PET_DB_PATH` 为工作区 `diagnostics\interaction-settings-preview\notifications.sqlite3`，再运行 `control_panel.py --serve-only --agent-home <工作区内的隔离用户目录>`；服务只监听 `127.0.0.1`，打开输出地址并进入 `#interaction`。本机浏览器访问权限门禁当前拒绝了该地址，需要本人在客户端允许本地地址访问后补做页面操作验收，不能据 API 测试认定页面已实测通过。

回归命令为 `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`；测试前也应设隔离的 `NIJIKA_PET_DB_PATH`，避免协议测试导入服务时初始化真实消息库。受限沙箱可能拦截临时文件替换和本机套接字，需经原生权限申请在隔离环境复验，不能把这些拒绝当成功。

互动控制器还可运行 `node --test tests/test_interaction_ui.cjs`；使用 Node 内置测试运行器，无浏览器、网络或第三方前端依赖，仅验证异步响应、保存竞态和开关逻辑，不能替代真实页面点击/布局验收。

2026-10-15：设置中心与桌宠合并为同一个 `dist/虹夏桌宠.exe`。右键角色选择“设置中心 / 添加 Agent”，或双击桌面的“虹夏桌宠设置”快捷方式（等价于 `虹夏桌宠.exe --control-panel`），即可打开设置窗口。设置窗口使用系统 Microsoft Edge WebView2；其他电脑若缺少该运行时，请从 [Microsoft 官方页面](https://developer.microsoft.com/microsoft-edge/webview2/)安装，或用 `虹夏桌宠.exe --control-panel --browser` 在浏览器打开同一管理面板。所有方式都仅绑定本机回环地址，窗口关闭后停止其服务。

控制中心首页点击“添加 Agent”，选择 Codex、ChatGPT 本机 Work 或 DSH，确认自动检测的位置和计划改动后应用。已有文件会保留备份，其他客户端条目不会被清空。其他客户端选择“其他 MCP 客户端”并生成接入文件，再“复制自动配置提示词”给能操作本机文件的 AI；提示词含完整路径、JSON 与持久提醒规则，无需手动下载或填字段。文件默认保存至 `%USERPROFILE%\.nijika-desktop-pet\integrations\agents\<档案ID>\`，准确位置在“接入步骤”显示。重载及本人权限确认如有必要仍须完成。面板不收集模型 API 密钥，不会替用户信任审批 hook。具体范围见 `AGENT_SETUP.md`。

动作、大小、常驻表情、闲聊开关与所选皮肤保存在同一用户消息库的独立设置表；导入皮肤放在消息库旁的 `skins/`，投喂图片放在 `support/`。默认目录仍为 `%USERPROFILE%\.nijika-desktop-pet`。新表不改变已有通知表协议；旧 Agent 会话继续通过同一队列通信。收款图与真实设置不进入 Git 或试用包。

第一版四项功能的操作位置：设置中心左侧“专注与提醒”页开始/暂停/继续番茄钟、修改专注与休息分钟数、开启三类健康提醒或设置免打扰；“今日便签与陪伴”页添加当天便签、打勾完成并查看好感度、陪伴天数与当前阶段。桌宠右键也能“开始专注 / 暂停专注”和“结束这一轮”，倒计时显示在角色头顶。数据表 `companion_*` 与通知队列共用同一个 SQLite 文件，删除该文件会同时重置提醒历史与陪伴数据。可复用验收脚本为 `.\.venv\Scripts\python.exe tools\accept_companion.py`（需要设置中心正在运行）。

本机 2026-10-16 核对：桌宠已按标准流程统一安装到 `%LOCALAPPDATA%\NijikaDesktopPet\app`，桌面与开机自启快捷方式、Codex 审批钩子、Work 插件清单、DSH desktop/web 配置、Claude Code 的 MCP 注册与审批钩子均指向安装目录中的程序；三款 EXE 与仓库 `dist/` 逐字节相同。修改 `pet.py` 等源码后必须重新运行 `build.ps1` 重建，再按 `distribution/install.ps1` 重新安装到上述目录并重启桌宠；Git 中的源码变化不会自动更新运行中的程序，各客户端配置里的开发目录字样只属历史记录。

给其他 Windows 用户私下试用时，优先运行 `powershell -ExecutionPolicy Bypass -File tools\build_installer.ps1`。需要同时重建三个应用时加 `-BuildApplications`；版本可用 `-Version 0.1.7`，已有 Inno Setup 不在默认位置时用 `-Compiler <ISCC.exe>`。工具先从白名单生成独立暂存区，再在 `dist-release\installer` 输出单个中文 Setup EXE 与 SHA-256 清单。该 EXE 不提交 Git。

收件人双击 Setup EXE，按向导选择安装目录、桌面快捷方式和可选开机自启，默认安装到 `%LOCALAPPDATA%\NijikaDesktopPet\app`，不需要管理员权限、Python 或 PowerShell。首次启动后打开“虹夏桌宠设置”配置 Agent。覆盖安装会更新 Work MCP 路径，但不会改外部客户端；升级和卸载保留 `%USERPROFILE%\.nijika-desktop-pet` 的消息、皮肤和 Agent 档案。通过 Windows“已安装的应用”卸载，外部 Agent 配置需另行管理。

维护者仅在可丢弃的 Windows Sandbox 或虚拟机内执行 `python tools\smoke_windows_installer.py <Setup EXE> --disposable-windows-session`，验证中文安装目录、升级、Work 路径、数据保留和卸载。测试默认拒绝执行；即使加参数，只要检测到已有虹夏安装、卸载登记或快捷方式，也会拒绝。测试不再改写 Windows 桌面、开始菜单或启动目录的注册表路径，不能在日常使用账户中运行。静默安装支持 `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER /DIR=<目录>`；卸载器同样支持这些静默参数。当前安装器未签名，Windows 可能显示 SmartScreen 发布者提示，应通过来源和 SHA-256 核对，不要求关闭安全防护。

旧 `tools\package_release.py` ZIP 通道继续保留；脚本可选接入 Codex、Work、DSH 或 Claude Code（`-Codex -Work -CodexHooks -ClaudeHooks -Dsh -AutoStart`）。角色素材没有公开再分发许可证，不应将包含这些素材的试用包公开上架。

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

输出在 `dist/虹夏桌宠.exe`（桌宠与设置中心）、完整 `dist/虹夏MCP-v2/` 目录和 `dist/虹夏审批提醒.exe`。MCP 目录内的 EXE 与 `_internal/` 必须一起保留；第三个程序供可选的 Codex 命令审批与完成兜底提醒使用，安装与审阅步骤见 `AGENT_SETUP.md`。当前电脑已配置 Codex；其他电脑也可使用设置中心向导，或在项目根目录运行：

```powershell
$mcpExe = (Resolve-Path -LiteralPath 'dist\虹夏MCP-v2\虹夏MCP-v2.exe').Path
codex mcp add nijika-pet -- $mcpExe
codex mcp get nijika-pet
```

把 `skills/nijika-desktop-dialog/SKILL.md` 安装到 Codex 用户技能目录，并在 Codex 的全局 `AGENTS.md` 中引用它，可让新任务把简单决策和短成果审阅整理成“完整短正文＋有简介的选择”。工程根目录也带有 `AGENTS.md`，说明成果待审阅和需要选择时的桌面提醒规则。当前电脑已完成安装；独立 Codex CLI 会话已在普通审阅与选择任务中自主发出提醒。安装或配置变化通常由新开的 Codex 任务读取；已经打开的任务不保证即时刷新工具列表。桌宠程序仍需打开以便立即看见提醒。

Codex 的审批策略可能要求先确认 MCP 工具调用。经用户明确授权，当前电脑只对 `nijika-pet` 的 `show_completion`、`request_decision`、`get_reply`、`wait_for_reply` 设置了逐工具 `approval_mode = "approve"`；服务器默认规则和其他工具未改。独立 Codex CLI 会话在未附加临时放行参数时已成功发送提醒。其他电脑沿用自身审批策略，遇到提示时应核对要发送的内容。桌宠上的选择仍由用户亲自点击，`pending` 或关闭不算同意。

Codex 完成兜底（2026-10-17）：重建 Hook 后运行 `integrations\codex\install-hooks.ps1`，或安装试用包时加 `-CodexHooks`；本人在 Codex `/hooks` 审阅新增 UserPromptSubmit / Stop，保留原 PermissionRequest / PostToolUse，然后新开任务。该功能不需要改变 Agent 的 MCP JSON、全局技能或前端设置；现有 Computer Use notify 保持原样。只有成功调用过桌宠通知的同轮会抑制兜底，输入无效不算已发送。消息库仅新增无正文的轮次表，旧桌宠/MCP 能直接显示它生成的普通完成通知。

桌宠与审批提醒仍为单文件程序；MCP 自 `0.1.9` 起为目录程序，启动时不再向 `%TEMP%` 解包。`dist/`、`.venv/` 与构建缓存不入 Git；源码包必须保留 `assets/sprites/`。通知数据库默认在 `%USERPROFILE%\.nijika-desktop-pet\notifications.sqlite3`，避免桌面客户端的 AppData 重定向造成两份队列；旧运行中会话的待处理消息与回复由桌宠桥接。可用 `env.example` 中的可选变量在隔离测试时改路径。消息含任务摘要，请只在受信任的本机用户会话中使用。本项目不要求真实 API 密钥或联网。

维护者可运行 `.\.venv\Scripts\python.exe tools\smoke_packaged_mcp.py` 测试打包服务，或运行 `.\.venv\Scripts\python.exe tools\smoke_pet_ipc.py` 在隔离消息库下测试真实桌面气泡与点击回传；`tools\smoke_claude_hooks.py` 与 `tools\smoke_dsh_installer.py` 分别隔离验证 Claude Code 钩子安装器与 DSH 安装脚本。`tools/benchmark_motion.py`、`tools/probe_window_fps.py` 和 `tools/make_bubble_preview.py` 分别用于动画性能及气泡预览；这些工具不会进入打包版。

## 桌面客户端 Work 本机接入

本机插件目录为 `plugins/nijika-work-local/`，项目插件清单为 `.agents/plugins/marketplace.json`。源码中的 `mcp.json` 不再包含开发者电脑路径；Python 启动脚本优先查找同一项目根目录的 `dist/虹夏MCP-v2/虹夏MCP-v2.exe`，也可读取 `NIJIKA_MCP_EXE` 或正式安装目录。插件运行仍需要能从 PATH 找到 `python.exe`。私下试用包的安装脚本会按收件人目录写入确定的 EXE 路径。当前源码为 0.1.9 版，技能要求每轮主动检查完成提醒、短决策连续等待、恢复会话时先读取旧请求。安装命令为：

```powershell
codex plugin marketplace add . --json
codex plugin add nijika-work-local@nijika-local --json
codex plugin list --marketplace nijika-local --json
```

确认插件显示 `installed: true`、`enabled: true` 后，保持 `虹夏桌宠.exe` 运行，**重启 ChatGPT 桌面客户端**，从本机运行的 Work 新任务发起一条简短测试选择题，检查气泡能显示、点击后 Work 能读回选择。普通聊天或云端 Work 不会因为本机 Codex 配置而自动拥有这个 stdio 工具。插件说明仅指导 Agent 何时调用；模型是否主动调用仍需以新任务实测，不能由安装状态推断。需要将云端 Work 接入时，必须提供经过鉴权的远程 HTTPS MCP 端点，本机插件不能代替公网连接。请勿把本机消息库直接暴露到网络。

Codex 全局技能和 Work 0.1.9 插件技能均要求在最终回复前主动检查完成提醒，并在一次 45 秒等待返回 `pending` 后复用原请求 ID 继续等待，最多约九分钟；若任务已结束，较晚的点击仍保存在消息库，但不会自动唤醒 Agent。在原会话发送“继续”后，技能要求先调用 `get_reply` 读取该请求。当前打开的 Codex/Work 任务不保证热更新；真实 Work 会话中的主动提醒、长等待和晚到回复仍按现场调用验收。

可用 `.\.venv\Scripts\python.exe tools\smoke_work_plugin.py` 在隔离消息库下验证插件启动入口及四个 MCP 工具，不会给正在运行的桌宠发送测试通知。

## DeepSeek Harness（DSH）本机接入

当前电脑已把同一 `dist/虹夏MCP-v2/虹夏MCP-v2.exe` 注册到 DSH 的 desktop 与 web 配置，并安装 `nijika-dsh-dialog` 技能和全局触发说明。其他电脑先构建完整 onedir 目录，再执行 `powershell -ExecutionPolicy Bypass -File .\integrations\dsh\install.ps1`。安装不会替换 DSH 原有的桌宠插件；配置、重启和测试步骤见 `integrations/dsh/README.md`。
# 2026-10-26 多帧皮肤与赞助随包

接收者保持安装目录完整，Agent 向导仍按收件人本机位置生成配置；普通接入流程不变。自制皮肤见 `SKIN_FORMAT.md`，不需要安装额外绘图软件才能导入 PNG/ZIP。

维护者在投喂支持页保存并导出 `nijika-public-support.zip` 后，使用 `python tools/package_release.py --app-exe <候选桌宠EXE> --support-bundle <公开赞助ZIP> --output <输出ZIP>`。该开关只带公开作者说明/链接/可选收款图，收件人首次启动自动显示。无此开关时不读取维护者本机赞助配置。公开图的摘要与配置配对，旧图片不会被当成新配置自动展示。真实支付和到账校验仍由收款平台承担。

## 2026-10-29 本机发现候选

新版 Agent 页入口为“扫描本机 → 勾选 → 预览勾选项 → 应用可接入项”，支持六个专属客户端；其他入口生成指引。MAGPIE 已管理目标只登记，继续在原管理器同步。首次配置仍需宿主重载及真实工具调用；不自动授予命令权限或信任钩子。简明步骤见根目录 `00-解压后先看.txt`，详细限制见 AGENT_SETUP.md。

本轮仅本机隔离验证及候选打包，正式安装程序与真实客户端配置保持原状。候选从 `dist-next/discovery-20261029/` 取用，替换程序时应使用完整包并保留用户数据。下文既有安装脚本和 Windows 运行要求不变。
