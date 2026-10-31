# 本机候选与发布检查单

## 2026-10-31 Codex 内部后台任务误提醒修复

- 本候选只修改 Codex Stop Hook 分类、通知安全摘要、持久规则和测试，不新增桌宠功能，不修改角色、皮肤、动画、前端或 MCP 工具。
- 目标验证：ambient-suggestions JSON 与 Codex 私有 helper 固定对象均静默；普通用户 JSON、简单问答和等待答复仍提醒；主动通知去重、重复 Stop、无有效轮次和显式子任务边界保持。
- 部署要求：先备份，再重建 `虹夏审批提醒.exe`；只同步工作区 `dist/` 与正式安装目录中的审批程序，保留消息库、Agent 配置、MAGPIE 服务、Hook 信任和其他两个 EXE。
- 发布边界：本轮完成源码修复和本机验证；是否制作新的 GitHub Release 版本另行按最终产物哈希记录，不覆盖已发布 `v0.1.6` / `v0.1.7`。
- 完成状态：26 项目标回归、全量 Python 168 项（1 项可选跳过）、JavaScript 20/20、冻结与正式安装 Hook、MCP、标准目录前端、Work 0.1.8、DSH 安装器及接入审计通过。工作区和正式安装 Hook 的 SHA-256 均为 `5CD44E9F738D96AE68E0ECCFE25AD9467EEA18C48FC882BE2D254198B8C8F717`；历史误提醒保留为诊断证据。证据见 `diagnostics/internal-task-guard-20261031-v2/`。

## 2026-10-31 每轮回复提醒修复安装器

- 新安装器应使用 `v0.1.7`：它基于提交 `bf4e324`，包含每个有效 Agent 轮次结束都发送虹夏提醒的修复，覆盖简单事实问答、无工具短答和等待用户回答的短句；同一轮已经主动发送 `show_completion` 或 `request_decision` 时仍保持去重。
- 构建命令：`powershell -ExecutionPolicy Bypass -File tools\build_installer.ps1 -Version 0.1.7 -OutputDirectory dist-release\installer-0.1.7`。旧 `v0.1.6` 保留作历史版本，不应继续作为最新下载入口。
- 当前候选：`dist-release/installer-0.1.7/虹夏桌宠-Setup-0.1.7.exe`，大小 72,630,210 字节，SHA-256 `9ee17469433a0ab97df2830a4f358423461521cd2d787c405d14b304fdd5fb31`；配套 `installer-manifest.json` 与隔离安装证据在 `diagnostics/installer-20261031/`。
- 发布前必须核对新 Setup EXE 的 `installer-manifest.json`、隔离安装/卸载证据和 GitHub Release 附件哈希；安装器不写收件人的外部 Agent 配置，首次接入仍从设置中心完成。

## 2026-10-31 朋友私下试用包

- 使用 `python tools/package_friend_trial.py` 生成四文件 ZIP：安装器、安装器清单、最新 `AGENT_SETUP.md` 和简明试用说明；不包含用户数据库、Agent 配置、备份、诊断或发送者路径。
- 当前包：`dist-release/friend-trial-0.1.7/虹夏桌宠-v0.1.7-朋友私下试用.zip`，大小 72,138,853 字节，SHA-256 `c34098b822b2d48ff6339d804b21dbf007e559bc135d94dd6d6ef434d0166ccc`。
- 这是私下测试包；收件人解压后双击 Setup，安装后从“虹夏桌宠设置 → Agent 接入”完成自己的客户端配置。角色和图标素材的公开再分发权仍未解决，不作为公开下载包。

## 2026-10-31 每轮回复提醒修复

- 新审批 Hook 候选：`dist-next/every-reply-reminder-20261031/虹夏审批提醒.exe`，SHA-256 `59934E1A38A0207F18FB1D3A5EB80D6A9145F655A9FC034D64595E1DA277439A`。
- 已备份旧 Hook 到 `backups/every-reply-reminder-20261031/`，并同步工作区 `dist/` 与正式安装目录 `%LOCALAPPDATA%\NijikaDesktopPet\app\dist\`；桌宠、MCP、消息库、MAGPIE 和用户客户端配置未覆盖。
- 隔离验证：21 项提醒单元、打包 Hook 冒烟、Codex `question`/`work`/主动 `notice` 三场景通过；真实 CLI 的用户 `config.toml`、notify 和 Hook 信任摘要保持不变。
- 详细哈希与检查记录：`diagnostics/every-reply-reminder-20261031/verification.json`。
- Work 插件源、Codex/DSH 技能和设置中心文案已同步；当前客户端进程占用插件缓存，卸载重装未强制执行，重启客户端后按新规则加载。外部宿主自然任务的可见性仍需新会话观察。

## 2026-10-31 标准 Windows 安装器

- 已发布私有仓库 Release `v0.1.6`：https://github.com/CY-YI/nijika-desktop-pet/releases/tag/v0.1.6 。实际附件名为 `NijikaDesktopPet-Setup-0.1.6.exe`；GitHub CLI 上传中文文件名时丢失了前缀，因此使用 ASCII 附件名保证链接可识别。下载复核为 72,630,838 字节，SHA-256 `15cce50ff95ae6dd24460abef5460f0597c615480a0f5833a74aa0bcff91cc15`，与本地完全一致。
- 构建：`powershell -ExecutionPolicy Bypass -File tools\build_installer.ps1`。产物 `dist-release\installer\虹夏桌宠-Setup-0.1.6.exe`，配套 `installer-manifest.json` 记录字节数和 SHA-256。生成物不提交 Git。
- Inno Setup 6.7.3 便携编译器从官方 GitHub Release 下载，数字签名验证有效。简体中文语言文件来自官方 `jrsoftware/issrc` 的 `Files/Languages/ChineseSimplified.isl`，随 `installer/` 保存来源说明。
- 真实 Setup EXE 在临时中文空格目录完成安装、覆盖升级和卸载，23 项白名单文件、Work MCP 路径、快捷方式、用户数据保留和卸载进程退出全部通过。证据在 `diagnostics\installer-20261031\install-checks.json`。
- 默认只安装程序，不自动写 Codex/Work/DSH 等客户端；用户从设置中心预览并确认接入。卸载不删除消息库、皮肤、Agent 档案或外部配置。
- 本安装器没有代码签名证书，发布时提供 SHA-256，并如实说明 Windows SmartScreen 可能显示未知发布者；不要求关闭安全防护。角色/图标再分发权仍未解决，当前二进制只供私下试用，不作为公开上架许可。

## 配置一致性与可移植性审计（2026-10-30）

- 维护审计工具把技能内容不一致、同一客户端重复副本、选中皮肤缺失、皮肤帧损坏和完整 Agent 键重复判为阻塞，CLI 非零退出。旧来源修复工具会跳过 MAGPIE 管理的客户端，且不再把纯序列化格式变化列为待修改。
- 安装测试同时覆盖空格、中文和自定义 `CodexHome`：Work MCP 路径、Codex CLI 的配置根和收件人安装目录都由实际参数生成，不沿用发送者路径。
- 本机只读检查未发现皮肤损坏或皮肤 ID 重复；当前默认皮肤和 4 个自制皮肤有效，8 个 Agent 档案可读且没有完整键重复。两个身份字段缺失的旧 `custom` 档案保留，避免把名称猜测成模型或软件。
- 本机三个已确认无用目标已由安全清理工具实际删除，回退副本在 `backups/config-cleanup-20261030/safe-tool-apply/`。清理后 `agent-integrations-after-cleanup.json` 与本机状态审计均为 `clean`，证据在 `diagnostics/config-cleanup-20261030/`。
- 最新完整回归为 Python 159 项（158 通过、1 项可选 PyYAML 跳过）；补跑系统 Python 的完整来源修复测试 8/8 通过；JavaScript 20/20 通过；Python/JavaScript/PowerShell 语法与 `git diff --check` 通过。合并证据见 `diagnostics/config-cleanup-20261030/final-verification.json`。
- 本轮没有替换正式 EXE、没有改真实客户端 MCP、MAGPIE、Hook 信任、消息库或皮肤数据；因此既有候选 SHA256 不变。

## 提醒可靠性与 DSH 来源加固（2026-10-30，正式安装）

- 本轮修复针对自动配置后复发的两类回归：Codex 只剩无信息量 Stop 兜底，以及 DSH 出现 `Codex · DSH`。源码范围包括安全结果摘要、服务端多模型来源守卫、DSH 孤立标记修复、三个宿主持久规则与 Work 插件 0.1.7。
- 冻结构建位于 `build/reminder-source-hardening-20261030/`。正式桌宠 SHA256 `DE3553927024511445E57D57B510249B77B1CF73B7D75872BB4D2FC7BA7E5F77`，MCP `BA8A70AA0CB594B936917CCDD3AF01B9F45DC219B4DEAD1AD5C55B5765EFD9E5`，审批提醒 `571DFD53D021814556071C352CF362829236719247614E50B7EDB20C5389BDA2`；工作区 `dist` 与标准安装目录逐字节一致。
- 更新前三个 EXE、SQLite 一致性快照、Codex 规则/技能、正式 Work 插件源、DSH 实际配置和正式运行资源均已备份到 `backups/reminder-source-hardening-20261030/`。正式目录不存在 `AGENTS.md` 的旧错误假设已移除，运行资源按实际存在文件单独记录摘要。
- 全量验证为 Python 147 项通过、1 项可选 PyYAML 跳过，JavaScript 20 项通过；Python/JavaScript 语法和 `git diff --check` 通过。正式安装版另通过 19 种 MCP 来源、显式编辑器元数据与 4 个并发客户端独立回执、审批 Hook、DSH 安装器、Work 插件和接入指引隔离冒烟。
- 正式用户库真实气泡验收：故意提交 `Codex/DSH` 时落库显示 `Agent/DSH`，真实 `DeepSeek/DSH` 保持原身份；两次均确认窗口实际可见后才清理测试通知。证据在 `diagnostics/reminder-source-hardening-20261030/live-bubble-acceptance.json`。
- 正式用户库模拟 `PermissionRequest` 后，命令审批提醒气泡实际可见，随后以 `PostToolUse` 收起测试项；整个过程不授予或拒绝权限。`config.toml` 中四个虹夏 Hook 的 `trusted_hash` 仍在且路径未变。证据在 `diagnostics/reminder-source-hardening-20261030/approval-bubble-acceptance.json`。
- Codex 全局规则与技能、DSH desktop/web 实际配置和 Work 插件 0.1.7 已同步；MAGPIE 的 `magpie-mcp-nijika-pet` 服务、Hook 信任、消息和设置保持不变。服务端来源守卫会保护仍在发送旧参数的新连接；已打开客户端要加载新的主动提醒规则，仍需重连 MCP 或新建任务。
- 本轮仍为 Windows 本机回环试用范围，不自动提交、推送、合并 `main` 或创建公开 Release。真实 DSH/Work 宿主自然任务、公开发布素材权利和干净 Windows 验收继续作为独立边界。

## VS Code 具体 Agent 正式纳入（2026-10-30）

- 正式安装已更新：`%LOCALAPPDATA%\NijikaDesktopPet\app\dist\虹夏桌宠.exe`、`虹夏MCP-v2.exe`、`虹夏审批提醒.exe` 与冻结候选对应文件一致。工作区 `dist` 已同步。
- 正式 EXE SHA256：桌宠 `F40E2313671CC582B43DCE8C4694DCD0BF47BAA31A14EB8AD28F8A5DB7E5CA21`；MCP `CA327906509B941464043719465DA8B379A229183E1BD47E5CA479E0C7B29EBD`；审批提醒 `3FE39FA6FB46EA74ED7D83808731E8ABDD440F1B5A0BE221D170CB4FEBD70083`。
- 更新前三个程序和 SQLite 一致性快照保存在 `backups/vscode-agents-formal-20261030/`。默认回退只恢复所需程序，保留更新后的用户消息和设置；旧 MCP 映像仅供仍持有旧文件的进程，不是启动入口。
- 正式安装页真实扫描识别 VS Code 中 Codex、Claude Code、DSH、CodeBuddy 四个具体扩展。正式安装冻结冒烟通过；MCP 验证通过 16 种来源、显式编辑器元数据及 4 个并发客户端独立回执。
- 最新私下试用包：`dist-next/vscode-agents-formal-20261030/虹夏桌宠-VS-Code-Agent正式试用-20261030.zip`，SHA256 `314d8c2589278e30b721366fc9aa3dc7b886e438f559ebb7a440abd07f8145d2`。包内 22 项文件清单全部匹配，解压后的精确 EXE 冻结冒烟通过，不包含测试数据库、回退映像或发送者路径。
- 安全边界：安装脚本未启用任何 `-Codex/-Work/-Dsh/-*Hooks` 配置开关，扫描为只读，未接管 MAGPIE、未覆盖真实客户端配置。新增或重载真实会话后才能激活新版 MCP 来源识别。
- 公开发行仍待实际多宿主自然任务验收、真实赞助资料、自制角色试导入、角色/图标再分发依据及干净 Windows 机器验收。本次安装不合并 `main`、不创建公开 Release。

## VS Code 具体 Agent 候选（2026-10-30）

- 候选 ZIP：`dist-next/vscode-agents-20261030/vscode-agents-candidate.zip`，SHA256 `112e7d8309c8bde27660b5b3917a7d9f210b9878ce645a5d79ec3b8a934626e2`。22 项清单哈希通过；无用户数据库、备份文件、`C:\\Users\\CY` 路径或测试赞助资料。
- 本轮新增：扫描 VS Code stable/Insiders 已知扩展并按 `VS Code · Codex`、`VS Code · Claude Code`、`VS Code · DSH`、`VS Code · CodeBuddy` 分开显示；接入向导预填 Agent/扩展，生成条件来源规则和完整验证提示词。
- 冻结验证：142 项 Python（141 通过、1 可选 YAML 跳过）、系统 YAML 6 项、20 项 JavaScript；候选 App/MCP、来源回执并发、浏览器 360/1280 检查通过，控制台无错误。证据见 `diagnostics/vscode-agents-20261029/`。
- 上述候选现已正式纳入本机安装；真实客户端配置仍未由该流程写入，扩展是否启用、是否具备 MCP、宿主自然任务和原生权限事件仍需在实际客户端单独验证。

## 本机发现候选（2026-10-29，本轮最新）

- 独立候选：`dist-next/discovery-20261029/discovery-candidate.zip`，SHA256 `cc834c47682bb95e57a6543c429b74521a7c90d0fc1c8f0ac9f39c81c15d3443`。22 项显式文件清单及 ZIP 完整性通过，包含新版 App/MCP、既有 Hook、安装脚本、简明上手与接入文档；不含真实用户库、配置、赞助测试资料或本机发送者路径文本。
- 134 项 Python：133 通过、1 项可选 YAML 跳过；系统对应 YAML 组 6 项通过；20 项 JavaScript 和语法检查通过。最终 EXE 接口冒烟覆盖扫描、批量配置、管理归属、来源导出，以及既有皮肤/赞助/互动；MCP 冻结验证覆盖16种来源、编辑器显式参数和4客户端独立回执。自然宿主登录、新会话及所有原生事件未全部实测，不能把协议用例当成实际宿主验收。
- 浏览器隔离验收覆盖正常/冲突/管理器保留三种结果及1280/360像素布局；最终冻结候选已打开隔离预览，源预览服务关闭。证据与测试日志在 `diagnostics/discovery-20261029/`。最终包仅重新整理了文档，运行程序逐字节等同于通过最终冒烟的文件。
- 正式安装 App/MCP/Hook 未替换，真实客户端仅只读扫描，没有自动接管 MAGPIE 或关闭现有任务。该候选不等同于已安装、已推送、已公开发布；尚待的发行素材与权利核对沿用下文，不标记项目 ALL_FINISH。

## 当前交付快照（2026-10-29）

- 历史分享压缩包已按用户授权精简：当前候选和 10 月 28 日 DSH 修复候选保留，其余旧试用/审阅 ZIP 已删除；文末旧路径只作历史记录。详细清单见 TODO.md 压缩包清理检查点及本地 `diagnostics/archive-cleanup-20261029/`。
- 最新本机候选：`dist-next/setup-fix-20261029/setup-fix-candidate.zip`，补入根目录 `00-解压后先看.txt` 后的 SHA256 为 `15fca73a6e4a9b09b7688106e0fd3147b81fdc831c4b86307669ae1e83df7f94`；22 项文件清单及 ZIP 完整性通过。此次只新增简明说明并更新包内 distribution/README.md，所有程序、脚本和其他旧条目逐字节不变，程序仍与正式安装一致。其余文档为打包时快照。
- 正式桌宠 EXE SHA256：`075179a005c686831e2d0c9b051b989ec772c4489a56379cd095d9d0b3aa3c2a`。本次只清理和归档源码，不替换已运行的程序或客户端配置。
- 候选和精确安装程序已通过冻结接口冒烟；最终源码 119 项 Python（118 通过、1 项可选 YAML 跳过）、系统 YAML 组 6 项、20 项 JavaScript 通过。前端接入与来源的详细验收边界见 TODO.md 最新记录。
- 用户已授权将当前源码分组提交、推送到既有开发分支；不等同于合并 main 或发布可下载 EXE。二进制和用户数据不入 Git。
- 公开发行仍待：真实赞助链接/收款图、自制角色按教程试导入、默认角色和图标的再分发依据或替换素材、另一台干净 Windows 机器试用。未新增许可，也不将合成握手/隔离测试算作所有宿主自然任务已验收。

以下按日期保留历史记录；“未安装／暂不上传”等表述仅适用于对应的历史轮次。

更新触发：形成新候选、复测失败、动作范围变化或准备替换正式安装时。

## 分享发布准备：当前候选（2026-10-26）

- [x] 候选 `dist-next/release-readiness-20261026/release-candidate.zip`：标准结构、21 项 SHA256 清单；本轮正式安装不变，候选沿用私下试用名称，尚不能作为公开下载成品。
- [x] 100 项 Python、20 项 JS；真实已安装 MCP 的 7 个来源和 4 个独立进程共库并发测试通过。技能差异审计不读取私密配置，也不代表所有客户端的原生审批事件均通过。
- [x] 扩展冻结冒烟覆盖资源一致、鉴权、养成、Agent 导出/能力矩阵、模板导入/应用、多帧预览、赞助白名单导出；实际浏览器走通下载/上传/保存/导出，360/1280 宽度无整页溢出，控制台错误 0。独立真实桌宠窗口加载已导入多帧皮肤。
- [x] 多帧/赞助相关接口、接入差异、教程与格式手册同步；包中增加 `SKIN_FORMAT.md`。详细证据保留在 `diagnostics/release-readiness-20261026/`。
- [ ] 收到真实赞助材料：作者在赞助页保存并导出 ZIP，再运行 `python tools/package_release.py --app-exe <已测候选EXE> --support-bundle <真实公开资料ZIP> --output <新分享ZIP>`。只纳入公开 JSON/可选 PNG；演示 example.com 资料不得用于真实发布。
- [ ] 用户按衣橱提示词试制自己的角色并试导入；核对素材可公开分发，尤其默认角色与桌面图标。未擅自添加许可证。
- [ ] 按实际改动组整理 Git 存档、审阅最终公开说明和发布附件；本轮不批量提交历史混合工作树，也不自动上传。

上述软件验证不代替新角色美术验收、收款图归属确认或另一台干净 Windows 机器测试。完整 N34 和动画精修继续后置，不阻塞已测 MVP，但也不宣称这些目标已完成。

## MVP 功能优先级（2026-10-26）

- [x] 用户确认动画以“不闪烁、不阻塞操作”为本期门槛；设置页切换修复通过后不再因 AN01 美术质量阻塞功能开发。
- [x] 源码接入 N30/N32/N34 的最小桌面闭环：分区点击、基础右键/双击动作、投喂短期事件消费、开关和异常降级；90 项 Python 与 20 项 JavaScript 回归通过。
- [x] 隔离候选 `dist-next/mvp-functional-20261026/` 已重建并验证：桌面分区点击、双击、右键动作/停止、点心/喝水顺序消费、设置页状态和 Agent 气泡优先级均在真实窗口检查；90 项 Python 与 20 项 JavaScript 回归通过。候选 ZIP 为 `mvp-review.zip`，20 项清单摘要一致。
- [x] 同源码正式构建已备份更新至本机标准安装目录和工作区 dist；默认数据启动心跳确认互动已连接，设置页试映及真实外部 Agent 气泡通过。原设置、3 个 Agent 档案和桌面/自启入口保留，MCP/Hook/客户端配置未修改；备份在 `backups/mvp-formal-20261026/`。
- [ ] 动作美术精修、AN02/AN03、完整转身、抓取摇晃/抛掷和专业绑定放到后续阶段；本次正式更新使用稳定的 PNG 渲染，未安装视频样片。
- 收尾证据：`diagnostics/mvp-formal-20261026/`。首次冻结冒烟因与解压错误并行而找不到文件，顺序重跑通过；原生设置窗口截图捕获异常未被记为通过，实际页面验收使用同一正式服务的内置浏览器。原 90 项 Python/20 项 JS 结果继续适用于本轮未改动的运行源码。

## 2026-10-26 待机审阅单元

- [x] 复用 V4 和原始源片，新建独立 VP9-alpha/源片对照及只读维护页；不更改正式安装或已有两份 EXE 候选。两边 480 帧/24 fps/20 秒，平台标识保留；4 项真实视频/HTTP、81 项完整 Python 与 20 项 JS 回归通过。
- [x] 内置浏览器检查播放、暂停、重播、逐帧、慢放、往返转向/循环、三种背景及 360 宽度，未观察到整页横向溢出或控制台错误；原生视频零丢帧样本只属于本机浏览器审阅，不是正式桌面性能承诺。
- [ ] AN01 美术一致性仍待用户集中审阅，源片脸型/姿态漂移不因转码而消失。新样片、对照视频与诊断目录均不进入安装包或 Git，工具源码与维护页面可入库。

## 2026-10-25 点击闪烁 / 来源复发候选

- 增量：预加载解码后替换图片、统一静态/动态几何框；MCP 按明确请求客户端纠正内置旧标签，不改工具输入与队列结构。素材美术改进仍独立待验收。
- [x] 77 项 Python、20 项 JavaScript、语法与空白检查；真实页面八种动作、快速切换、重播/停止、离页返回均加载完整图片，尺寸及 padding 一致，控制台错误为零。
- [x] 七个冻结 MCP stdio 场景：Codex 现代/legacy、DSH、Claude code、Work、自定义、未知客户端；完成/选择和回执均正确。真实 Codex CLI 在故意错误 DSH 环境下分别调用源码与确切安装版，均写入 Codex，真实配置摘要不变。
- [x] 新前端冻结程序的资源、鉴权、养成/冷却、动画与 Agent 导出冒烟通过，ZIP 20 项白名单清单校验通过。应用首轮构建因相对资源路径失败，改绝对资源路径后构建和运行检查通过，失败日志保留。
- 本机仅更新已验证 MCP，正式桌宠/Hook 与来源配置未改；旧服务映像有备份。已打开旧会话的 Restart 仍需客户端操作，不把磁盘更新写成全会话已热加载。
- 新旧候选均保留于忽略的 `dist-next/`；不公开发布、不自动提交当前混合工作区。最终文件名和摘要见 `diagnostics/source-flash-20261025/acceptance.json`。

## 2026-10-25 前端候选

- 范围：既有七页设置中心、草稿保护、互动设置/试映与本机养成；保持本机回环服务，不增加网络部署。用户授权能自行验收的步骤自主推进。
- 候选：`dist-next/frontend-20261025/frontend-review.zip`；展开目录为旁边的 `review/虹夏桌宠-Windows私下试用/`。EXE 在标准 `dist/` 下，必须保留同包脚本、插件和说明供 Agent 向导使用。
- 复现：按 `build.ps1` 的桌宠打包参数使用独立输出目录，数据参数使用绝对资源路径；然后 `python tools/package_release.py --app-exe <候选EXE> --output <候选ZIP>`。该选项只替换包内桌宠来源，MCP/审批程序继续取既有 `dist/`，不重配真实客户端。
- 候选来自当前工作树，包含先前 Agent 来源修复；动画准备工具、源视频和新动画样片不入包。未以混合未提交改动冒充独立版本提交。

## 已通过

- [x] 75 项 Python 回归、17 项前端控制器回归与 JS 语法检查。
- [x] 七页在 360/768/1280 宽度无页面横向溢出；实际浏览器互动点击、保存、冷却及刷新恢复。
- [x] 五个内嵌 UI 文件逐字节等于源码；20 项私下试用包清单摘要一致。
- [x] 本机 WebView2 窗口实际打开，角色与脚本正常加载并完成摸头播放。
- [x] `tools/smoke_frontend_candidate.py <标准展开目录/dist/虹夏桌宠.exe>` 通过：隔离启动、无令牌拒绝、设置与冷却恢复、动画解码、通用 Agent 配置导出。测试目录自动清理。
- [x] 源码仍使用同源令牌、Host/Origin 检查、CSP、禁止跨域、参数化数据库查询；新增前端不使用动态 HTML 注入或外部 CDN。候选不携带真实配置、消息库、私钥或动画诊断素材。

本轮 85 个源文件常见凭据模式扫描为 0，证据见 `diagnostics/frontend-20261025/acceptance.json`；模式扫描不代表任意秘密格式都可被识别。删除本轮 `build/frontend-20261025/` 的组合命令被自动审批审查拦截，仅返回 `blocked by policy`；中间目录仍保留供构建复核，不绕过限制，正式交付前清理项未勾选。

## 完整互动版本仍须完成

- [ ] AN01 美术审阅：V4 已复用区域清色并去掉往返端点长停顿，但脸部/姿态一致性及反向感仍待确认；保留原片与平台标识，不能靠编码指标宣称视觉达标。先验收这一段，再处理已有 AN02 与尚未取回核实的 AN03。
- [ ] N30/N34 的完整转身、桌面分区触摸/抓取/摇晃/抛出等目标没有全部实现。旧变形试映只用于操作预览。
- [ ] 完整动作资源预算、真实桌面输入、通知优先级和桌面播放性能验收。
- [ ] 选择性整理仍待提交的动画准备、Agent 来源和前端改动，核对版本、回退点后再形成正式安装更新；构建产物不入 Git。

项目当前为私下试用；未新增开源许可证或第三方素材授权。此候选没有安装到 `%LOCALAPPDATA%\NijikaDesktopPet\app`，也没有改变 MCP、审批信任或生产消息库。上述功能欠项未完成前，不标记整体 `ALL_FINISH`。

## 2026-10-29 接入修复候选

候选位于 dist-next/setup-fix-20261029/setup-fix-candidate.zip，正式安装已更新本轮桌宠程序。候选和安装 EXE 均通过冻结接口冒烟，21 项文件白名单与摘要检查通过；没有真实赞助资料或用户数据库。公开发布仍待赞助材料、原创角色试导入与分发权利核对，各外部宿主自然任务不等于合成测试已通过。未公开上传。
