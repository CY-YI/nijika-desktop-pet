# 虹夏桌宠 · 2D 坐姿版

准备学习或修改源码，请先读 [源码开发指南](DEVELOPMENT.md)：包含环境搭建、隔离运行、模块地图、测试与构建步骤。完整工程包额外附带已验证程序和 `SOURCE_MANIFEST.json`，不包含个人配置或运行数据。

## MCP onedir 与临时目录治理（2026-11-03）

`虹夏MCP-v2` 已从 PyInstaller onefile 改为 onedir。新入口是 `dist\虹夏MCP-v2\虹夏MCP-v2.exe`，必须连同同目录的 `_internal\` 一起复制或安装；客户端不再在每次启动时把运行时解包到 `%TEMP%\_MEI*`。桌宠和审批提醒仍使用 onefile。

旧版 `dist\虹夏MCP-v2.exe` 仅作为精确迁移来源。`0.1.9` 安装器会在升级时删除该旧文件并安装完整 onedir 目录，不删除 `dist` 中其他文件。维护者若需回收旧运行时，可先运行 `python tools\cleanup_mcp_temp.py` 预演；只有同时匹配旧虹夏 MCP 的通用运行时文件和本次构建特有目录签名、超过 24 小时且未被运行进程引用的 `%TEMP%` 直属 `_MEI*` 才会在显式 `--apply` 时删除。本次两轮安全清理合计回收 50,132,361,143 字节，最终复查可清理项为 0；活动目录和非虹夏运行时均保留。

重启后的补充验收再次安全回收 37,785,966 字节旧残留，随后只读复查为 0 个可清理项。当前 5 个活动 MCP 进程全部从 onedir 目录启动，且没有任何 MCP 进程引用 `%TEMP%\_MEI*`。DSH 桌面客户端的自然短问答在没有额外提醒工具时仍自动产生具体气泡，来源显示为 `Agent · DSH`；其他外部宿主与干净 Windows 安装流程仍分别作为发布前验收项。

## 统一提醒核心（2026-10-31）

各客户端共用同一生命周期协议、安全摘要、来源解析和通知去重；详见 [NOTIFICATION_PROTOCOL.md](NOTIFICATION_PROTOCOL.md)。Codex 原生事件与 DSH 实时会话模块只负责转交事件。DSH 已核对 `0.2.1-rc.2 / 0.2.1-rc.3` 的接口；Work 等其他客户端目前仍只支持主动 MCP 调用，不承诺漏调时自动补发。

设置中心“Agent 接入”及导出的 `nijika-notification-capabilities.json` 会显示能力和独立验收要求。更新后重新打开接入步骤以刷新资料，预览应用并重载客户端；配置存在、主动测试成功与真实结束事件通过分开记录。旧下载包不会自动获得本次代码。

本机现用 DSH 已加载独立事件模块，用户确认两次自然会话的气泡与去重符合预期；两次均有主动工具调用，无工具补发已通过隔离真实事件组件到冻结程序测试，尚未完成自然会话视觉补验。原有服务、MAGPIE 归属和用户数据保留；安装指南见 [AGENT_SETUP.md](AGENT_SETUP.md)。

## 2026-10-31 内部后台任务误提醒修复

Codex 的 Stop Hook 现在只静默两类已确认的后台输出：同时具备 `currentSuggestionIds`、`generatedAtMs` 和带 `appId`/`appIds` 建议项的 `ambient-suggestions` 结构，以及私有 Codex helper 在版本化 `bin` 目录返回的固定排除对象。普通用户任务即使要求返回 JSON，仍会得到一条完成提醒；气泡只显示“已返回结构化结果，请查看任务。”，不再截断并显示原始 JSON。工作路径只在 Hook 内存中用于分类，不写入轮次表或通知正文；内部任务在同一轮也只落一条静默去重标记。正式安装 Hook 已更新为 SHA-256 `5CD44E9F738D96AE68E0ECCFE25AD9467EEA18C48FC882BE2D254198B8C8F717`。

## 2026-10-31 每轮回复提醒

已接入的 Agent 不需要用户在每次对话前再次提醒：每个有效轮次结束都会通过虹夏显示一次完成气泡，包含简单事实问答、无工具短答、等待用户回答的短句、用户主动要求返回的 JSON 和正文暂缺的短答。Agent 主动调用 `show_completion` 或 `request_decision` 时，同一轮不会再补发第二条；内部标题生成、已确认的 Codex helper／环境建议、显式子任务和没有有效轮次状态的事件保持安静。Codex 的 Stop Hook 已更新并同步到工作区与正式安装目录，候选和隔离 CLI 验收记录见 [PUBLISHING.md](PUBLISHING.md)。

## 当前正式安装状态（2026-10-30）

提醒可靠性、DSH 来源隔离、本机发现、冲突预览、分客户端接入和 VS Code 扩展识别均已纳入正式程序。正式安装路径仍为 `%LOCALAPPDATA%\NijikaDesktopPet\app\dist\虹夏桌宠.exe`；设置中心会显示 `VS Code · Codex`、`VS Code · Claude Code`、`VS Code · DSH`、`VS Code · CodeBuddy` 等具体扩展入口。

正式安装的三个程序已从本轮冻结构建同步更新，现有消息、设置、8 个 Agent 档案、MAGPIE 归属和客户端配置均保留。正式桌宠 SHA256 为 `DE3553927024511445E57D57B510249B77B1CF73B7D75872BB4D2FC7BA7E5F77`，MCP 为 `BA8A70AA0CB594B936917CCDD3AF01B9F45DC219B4DEAD1AD5C55B5765EFD9E5`，审批提醒为 `571DFD53D021814556071C352CF362829236719247614E50B7EDB20C5389BDA2`。

安装前程序、运行资源和 SQLite 一致性快照在 `backups/reminder-source-hardening-20261030/`。正式安装后，19 种 MCP 来源、4 个并发客户端、审批 Hook、DSH 安装器、Work 插件和接入指引冻结冒烟通过；真实桌面气泡分别验证了 `Agent · DSH`、`DeepSeek · DSH`，并实际显示了一次不授予权限的命令审批提醒。证据见 `diagnostics/reminder-source-hardening-20261030/`。扫描只读取已知扩展清单，不读取账号、聊天或密钥；MAGPIE 管理的目标不会由虹夏重复写入。`v0.1.7` 安装器已基于本轮每回复提醒修复重新构建，发布前仍需按 PUBLISHING.md 核对 Release 附件。

2026-10-30 的配置复审已清理旧 `.agents` 重复技能、旧技能备份和零字节审批探针，备份在 `backups/config-cleanup-20261030/safe-tool-apply/`。当前 Codex/DSH/Work 技能审计为 `clean`，5 个皮肤（含默认）和 8 个 Agent 档案可读且无完整键重复；具体命令与证据见 [AGENT_SETUP.md](AGENT_SETUP.md) 和 `diagnostics/config-cleanup-20261030/`。

## 本机发现候选（2026-10-29）

新增“扫描本机 → 勾选客户端 → 预览 → 分别应用”的便捷入口；Codex、Work、DSH 复用既有适配，Claude Code、Gemini CLI、Copilot CLI 新增用户级适配。MAGPIE 管理的目标保留原管理器，不重复写入。批量扫描时 Codex 与 ChatGPT Work 只能选一个，避免共用本机 Codex 环境时生成两套 MCP；应用前还会核对 `虹夏MCP-v2.exe` 与同级 `_internal\` 是否完整。编辑器等入口先生成指引；检测、配置、本机测试与真实宿主调用分别显示。见 [接入说明](AGENT_SETUP.md)。

本段保留 10 月 29 日候选开发时的状态记录；当前实际安装状态以上方 10 月 30 日正式安装段为准。

## 当前状态（2026-10-29）

本机正式程序已更新至本轮 Agent 接入修复版本：桌面提醒与选择、设置中心、基础互动、透明 PNG 多帧皮肤和公开赞助资料导出均已实现。Agent 配置区将管理昵称、Agent 身份和所在软件分开；配置迁移先预览、备份并校验，冲突或未知旧程序会停止写入。

当前源码完成 194 项 Python 回归（193 通过、1 项可选 PyYAML 跳过），20 项 JavaScript、4 项 DSH 事件测试通过（1 项真实 SessionStore 测试因未提供当前安装路径而跳过），冻结前端、接入指引、MCP、内置浏览器实际勾选、Setup 构建及朋友试用 ZIP 核对通过。最新结果见 [发布检查单](PUBLISHING.md) 和 `diagnostics/agent-config-guard-20261103/`；这些结果不表示每个外部宿主的新会话和原生权限事件均已实测，也不替代干净 Windows 上的安装/卸载全流程。

当前源码和 `v0.1.9` 安装器候选保存在现有开发分支的工作区；二进制是否作为 GitHub Release 下载，仍以 PUBLISHING.md 的附件哈希和私下试用授权为准。正式公开发行仍待真实赞助资料、自制角色试导入与角色/图标分发权利核对；尚未实现的完整动作及宿主桥接见 [TODO.md](TODO.md)。历史记录中的“未安装／暂不提交”仅描述对应日期的操作，以本节及最新检查点为准。

使用入口：[安装与运行](INSTALL.md) · [Agent 接入](AGENT_SETUP.md) · [自制皮肤格式](SKIN_FORMAT.md) · [架构](ARCHITECTURE.md) · [回退](ROLLBACK.md)。下方日期段落保留为历史记录。

## 2026-10-29 接入流程更新

Agent 接入区区分管理昵称、Agent 和所在软件，通用客户端必须填写软件；卡片和生成配置展示预期来源。Codex/DSH 安全迁移仅处理验证过的虹夏条目，遇到未知程序、配置冲突或不支持的布局停止。宿主能力及重连边界见 AGENT_SETUP.md。


## 2026-10-28：来源显示修复

通知头部改为“Agent · 软件”，任务名单列；MCP、Codex 完成兜底及 Codex/Claude 审批提醒使用一致结构。共享库和专属接入配置支持独立身份字段，兼容旧配置；详见 AGENT_SETUP.md。旧 stdio 连接需要在各宿主重新连接，编辑器外层软件需要明确元数据。多模型宿主未知身份显示 Agent，不猜测模型。


当前 MVP 已于 2026-10-26 更新到本机正式安装：用原桌面“虹夏桌宠 / 虹夏桌宠设置”快捷方式即可使用分区点击、基础彩蛋和养成投喂。Agent 档案和接入配置保留，无需重配。90 项 Python、20 项 JS 与隔离真实窗口验证通过，正式入口/设置页/真实提醒已复核；本轮备份与交付状态见 [TODO.md](TODO.md) 和 [PUBLISHING.md](PUBLISHING.md)。下方保留历次迭代记录，新旧状态以本段和当前待办为准。

2026-10-26 待机动画：增加独立的源片/透明样片同步对照页，支持暂停、逐帧、慢放和浅深背景；VP9-alpha 审阅副本保留 480 帧/24 fps，约 4.64 MB。81 项 Python、20 项 JS 回归通过，正式桌面程序仍未替换。维护者运行方法与美术验收边界见 [动作制作说明](art/animation/README.md)。

2026-10-25 两项补丁已自测：设置页动画先完成预解码再替换、静态与动态使用同一画框；MCP 识别明确调用方，纠正 Codex 的旧 DSH 标签。77 项 Python、20 项前端回归、真实页面八种动作、冻结程序和真实 Codex 来源检查通过。正式 MCP 已备份更新，旧会话须重启连接后生效；前端仍为独立候选，正式桌宠界面未替换，素材美术不因加载修复而视为通过。入口与生效说明见 [INSTALL.md](INSTALL.md)。

2026-10-25 两个会话工作已合并规划：前端候选先保留并完成隔离复核，当前主线继续“先修待机”，再处理挥手/思考与真实桌面触摸。现有区域清色和往返循环继续复用，本轮只修重复端点停顿并制作新 V4 审阅副本；动作美术仍待确认，不替换正式安装。当前优先级和未完成项见 [TODO.md](TODO.md)，样片及复现方式见 [动作制作说明](art/animation/README.md)。

2026-10-25 设置中心前端：七页导航、窄屏布局、表单草稿和保存反馈已完善，互动完整流程及三档宽度已用隔离数据检查，75 项 Python 与 17 项前端回归通过。独立候选已实际启动 WebView2 设置窗口并验证动画播放，尚未替换正式安装版；动作素材质量和桌面新动作仍待完成。详细改动与验收边界见 [当前待办](TODO.md)、[安装与运行](INSTALL.md) 和 [发布检查单](PUBLISHING.md)。

2026-10-19 动画素材试制：依据用户提供的鲸鱼娘视频，已制作一段 10 秒虹夏待机源片及透明 WebP 审阅副本；动作有真实帧间变化，但底色残留、首尾和角色一致性仍待精修，未安装到正式桌宠。独立素材工具、复现提示词与验收记录见 [动作制作说明](art/animation/README.md)；Agent 提醒和接入配置不因本次试制改变。

2026-10-26 MVP 互动闭环：允许分区触摸后，桌面点击、双击和右键可触发基础反馈；轻养成独立开启，投喂/喝水保存数值并发送短期反馈。设置中心提供试映、保存和冷却状态，动作沿用稳定渲染，不阻塞 Agent 提醒。90 项 Python、20 项 JavaScript 回归通过，正式安装已更新；当前交付与后续边界见 [PUBLISHING.md](PUBLISHING.md)。

2026-10-17 Codex 完成提醒兜底：可选生命周期 Hook 在实质工作结束、Agent 漏调用桌宠工具时补一条固定完成提醒；同轮已有有效完成/选择通知时不重复，尽量过滤简短事实问答。安装 `-CodexHooks` 后本人须在 `/hooks` 审阅新增的 UserPromptSubmit 和 Stop，再开新任务。原 Computer Use notify、其他客户端配置及设置界面用法保持不变。安装、验证与过滤边界见 [AGENT_SETUP.md](AGENT_SETUP.md)。

2026-10-15 桌宠与设置中心合并为单一程序：右键桌宠选择“设置中心 / 添加 Agent”，或双击桌面“虹夏桌宠设置”快捷方式（即 `虹夏桌宠.exe --control-panel`）。首页用向导接入 Codex、ChatGPT 本机 Work、DSH；自动填写常用路径，先预览、再备份写入，并提供桌面测试与 MCP 配置导出。其余页面管理角色皮肤、动作/大小/表情/闲聊和可配置的投喂入口。没有新时装素材时可以导入透明 PNG 或九帧图片包；投喂未配置时不会展示虚构收款码。

2026-10-15 第一版四项功能：专注与提醒页可开始/暂停/继续一轮番茄钟并显示今日完成数与分钟数，桌宠头顶同步倒计时徽章，结束时由气泡提示休息；久坐、喝水、护眼三个定时提醒可配置间隔并支持最长 480 分钟免打扰；今日便签每天最多 20 条，打勾完成；好感度按点击、专注、便签和桌面决策累积，分初识/熟悉/亲近/默契/挚友五阶段显示陪伴天数。数据与通知队列同在 `%USERPROFILE%\.nijika-desktop-pet` 的本机 SQLite，不联网。其余候选功能（N27–N50）只登记在 `REQUIREMENTS.md`，等待逐项选定后再进入版本。

![控制中心实际页面，隔离验收环境](art/control-panel-preview.jpg)

控制中心需要 Windows 上可用的 Microsoft Edge WebView2；仅打开本机管理服务，不开放局域网或公网。桌宠和 MCP 的通知链路继续使用原队列。面板里的“测试已点击”只证明本机气泡和回执可用，客户端是否主动调用仍须在新任务中验证。设置保存后由新版桌宠应用，退出管理窗口不会退出桌宠。

2026-10-11 提醒可靠性更新：统一桌面快捷方式与客户端启动程序的消息库，兼容旧会话的点击回传，独立轮询并恢复隐藏或位置错误的气泡。普通提醒现场点击已通过；本机两项 Codex hook 完成信任后，真实 Codex CLI 审批已自动触发虹夏提醒并保存“知道了”回执。安装到其他电脑仍需本人在 `/hooks` 审阅并信任，授权仍在 Codex 审批卡完成。步骤和验收边界见 [AGENT_SETUP.md](AGENT_SETUP.md)。

2026-10-16 Claude Code 审批提醒接入：Claude Code 用户级 `%USERPROFILE%\.claude\settings.json` 已注册与 Codex 同构的 PermissionRequest / PostToolUse 仅通知钩子，采用 exec 形式直接调用安装目录中的 `虹夏审批提醒.exe`，不经 shell；改动前自动备份原文件，注册由 `integrations\claude-code\install-hooks.ps1` 脚本维护（试用包安装带 `-ClaudeHooks` 开关）。气泡“知道了”只记录回执，授权仍在 Claude Code 自己的权限提示完成。实测已覆盖合成事件端到端、运行中热加载与真实 PostToolUse 自动收起；真实权限提示的自然触发尚未验收。步骤见 [AGENT_SETUP.md](AGENT_SETUP.md)。

桌面决策现在可为一个有明确理由的选项显示“推荐”。Agent 收到桌面点击后，应在原 Codex/Work 聊天中写明所选项，再按选择继续。这条聊天记录是 Agent 的确认消息，不会伪装成用户发送的新消息。如果 Agent 已结束等待，桌宠不会独立唤醒该任务，需要继续该聊天才能读取已保存的点击结果。

更新触发：2026-10-07 用户要求简单决策直接在桌宠完成，不必总回到聊天。

Windows 桌面上的 Q 版坐姿虹夏：完整双腿、透明背景、八种表情、自然眨眼。默认“活泼明显”动态：连续的待机呼吸、轻摆与偶尔弹跳；单击换表情并弹起，双击连续回应；按住角色拖动时倾斜，松手自然回正。右键可以选表情、大小、动态强度、手动说话、演示提醒或退出。Codex 可经本机 MCP 工具发送真实的完成提醒和选择题；简单选择及短成果审阅在气泡中显示完整决策信息和逐项简介，点击结果由当前 Agent 读取并继续任务，无需再回聊天确认。Agent 每个有效轮次的结束提醒由客户端规则和 Codex Stop 兜底共同保证。菜单里的“演示”仍只在本地生效。

本机成品可双击 `dist/虹夏桌宠.exe` 启动；`dist/虹夏MCP-v2/虹夏MCP-v2.exe` 是 Codex 自动启动的 stdio 服务，不需手动双击，且不能脱离同级 `_internal/` 单独复制。当前电脑已注册 `nijika-pet` MCP 并安装 `skills/nijika-desktop-dialog/` 的全局副本；项目 `AGENTS.md` 规定何时主动发送提醒。独立 Codex CLI 会话已在普通审阅和选择任务中自主调用桌宠；Codex 桌面应用的新任务也已自动发出完成提醒并在桌面显示。Git 仓库只保存源码、素材、测试和文档，`dist/` 生成文件不入库；克隆后按 `INSTALL.md` 构建和注册。动画预览见 `art/motion-preview.gif`，气泡外观见 `art/bubble-preview.png`，角色帧在 `assets/sprites/`。

对外分享文档可运行 `.\.venv\Scripts\python.exe tools\package_docs.py` 从当前源码生成压缩包；旧压缩包不作为最新工程状态的依据。

给熟人私下试用优先运行 `powershell -ExecutionPolicy Bypass -File tools\build_installer.ps1` 生成单个 Windows Setup EXE。收件人双击安装器即可选择安装目录、桌面快捷方式和开机自启，默认安装到 `%LOCALAPPDATA%\NijikaDesktopPet\app`，无需管理员权限或 PowerShell。安装、覆盖升级和卸载保留用户消息、皮肤与 Agent 档案，不自动改外部客户端配置。`tools\package_release.py` 保留为旧 ZIP/脚本安装通道。公开发布的素材权利仍需另行确认。

给朋友测试时可直接使用 `python tools\package_friend_trial.py` 生成小型私下试用 ZIP；当前脚本位于 `tools/package_friend_trial.py`，默认输出到 `dist-release/friend-trial-0.1.9-release/`。包内包含已加入自动接入防重复校验的 `v0.1.9` Setup、校验清单、最新 `AGENT_SETUP.md`、快速说明 `FRIEND_TRIAL_GUIDE.md` 和简明文本说明。旧 `dist-next` 候选和构建缓存属于可再生历史产物，清理前仍保留诊断与回退证据。

**Agent 接入配置集中见 [AGENT_SETUP.md](AGENT_SETUP.md)**：分别说明私下试用包、Codex、桌面客户端 Work、DSH、Claude Code，以及其他支持 stdio MCP 的本机客户端如何配置和验证。设置中心的“接入步骤”可直接复制自动配置提示词，内含本机 MCP 程序路径、完整 JSON 和提醒规则；发给有本机文件操作能力的 AI，由它配置与验证。接入文件自动保存至用户数据目录下 `integrations/agents/<档案ID>/`，界面显示准确路径，无需手动下载。客户端重载或本人权限确认仍按实际要求完成。

互动功能开发前的稳定存档为 `stable/pre-interactions-20261016`（`a876e18`）；源码与本机运行备份的恢复步骤见 [ROLLBACK.md](ROLLBACK.md)。本机私人备份不随源码或试用包分发。

桌面客户端 Work 的本机接入包在 `plugins/nijika-work-local/`，本机已通过 `.agents/plugins/marketplace.json` 安装并启用。它把同一 `虹夏MCP-v2.exe` 作为插件工具提供，并附带 Work 对话用的简短决策 skill。独立 Codex 会话关闭原有直连后仍通过插件实际调用成功；这证明插件工具链可用，但不等于 Work 会话已经连接。首次使用需重启桌面客户端、在**本机运行的 Work 新任务**中确认工具可见并完成一次桌面点击回传。云端 Work 对话不能直接运行这个 Windows 本机 stdio 程序；那种接入需要另行设计可安全访问的远程 MCP 服务。详见 `INSTALL.md`。

Codex 全局技能和本机 Work 插件 0.1.9 均要求最终回复前主动检查完成提醒，并加入“同一请求连续等待、恢复会话先读旧回复”的规则。较晚的点击会保存，但一旦 Agent 任务结束，现有 stdio MCP 无法单靠桌面点击重新唤醒任务；在原会话发送“继续”可触发读取。当前打开的会话不保证热更新，新的 Work 插件还需重启 ChatGPT 桌面客户端后在新任务中验收。

DSH 本机接入脚本在 `integrations/dsh/install.ps1`，默认注册 desktop 和 web 两个配置，安装专用技能及全局触发规则。本机已写入配置并通过 DSH web 合成配置检查、打包 MCP 握手及隔离选择回传测试。DSH 新会话已自主调用虹夏并显示带 DSH 来源的气泡；用户较晚点击后，回复保存在消息库，但 DSH 原任务已结束，未自动读回。技能现要求重复等待并在会话恢复时读取旧请求；无时限自动唤醒尚未实现。操作和限制见 `integrations/dsh/README.md`。

运行环境为 Windows 10/11 x64；源码使用 Python 3.12、Pillow 12.2、官方 MCP Python SDK 2.3，打包使用 PyInstaller 6.20。本机消息保存在用户目录的 SQLite 文件；已处理消息 7 天后清理，未处理消息 30 天后过期。MCP 只走本机 stdio，不开放网络端口。需求与验收见 `REQUIREMENTS.md`，待办见 `TODO.md`，架构与内部接口分别见 `ARCHITECTURE.md` 和 `INTERFACES.md`。这是非官方同人练习；仓库没有声明可供第三方复用角色素材的许可证。
# 2026-10-26 发布候选准备

本轮为既有 MVP 补充多 Agent 能力差异/冲突检查、透明 PNG 多帧待机皮肤，以及可随包携带的作者赞助资料。100 项 Python、20 项 JS、标准展开包冻结冒烟和实际浏览器流程通过；候选位于 `dist-next/release-readiness-20261026/release-candidate.zip`。未替换正式安装；准确范围及尚缺材料见 `TODO.md` 和 `PUBLISHING.md`。自制角色格式和试用步骤见 [SKIN_FORMAT.md](SKIN_FORMAT.md)。

设置中心的 Agent 页可展开查看 Codex/本机 Work/DSH/通用客户端的特别要求，原生权限提示不等于 MCP 通知。赞助页保存真实 HTTPS 链接或收款图后可“导出公开赞助资料”，维护者用 `python tools/package_release.py --support-bundle <该ZIP完整路径>` 打入包内；不需要发送个人数据目录。

公开分发前仍需补齐真实赞助资料、用户新角色试导入，以及默认角色/图标的公开再分发依据。本轮没有选择新许可证或上传公开下载。
