# 版本回退与本机备份

## 2026-11-21 Codex 审批气泡过滤

- `%LOCALAPPDATA%\NijikaDesktopPet\local-upgrade-approval-event-scope-20261121-212756` 保存 `before.exe` 和部署校验清单。确认审批程序未运行后，可按清单把该副本恢复到正式安装目录的 `dist\虹夏审批提醒.exe`。

## 2026-11-21 所有 Agent 气泡的文字回复

- `%LOCALAPPDATA%\NijikaDesktopPet\local-upgrade-agent-replies-20261121-211552` 保存更新前的桌宠、MCP、审批程序和技能。按 `deployment.json` 中的路径及校验值恢复对应文件。保留现有通知库中的回复、原快捷方式及 Codex Hook 定义和信任状态。
- 选择题自填回复的上一个快照为 `%LOCALAPPDATA%\NijikaDesktopPet\local-upgrade-decision-text-20261121-145612`。

## 2026-11-21 活动 MCP 连接的文字回复兼容

- `%LOCALAPPDATA%\NijikaDesktopPet\local-upgrade-reply-compat-20261121-144735` 保存原桌宠、原 MCP 及技能副本。按 `deployment.json` 对单个组件回退。已提交的兼容回复留在原通知 ID 下，本机消息库继续沿用。

## 2026-11-21 气泡内回复与衣橱删除

- 正式更新备份在 `%LOCALAPPDATA%\NijikaDesktopPet\local-upgrade-inline-reply-20261121-143558`，`deployment.json` 列出桌宠、MCP、三个设置资源与技能的路径和校验值。退出桌宠并让使用虹夏的客户端重连前，按需恢复对应组件。正式目录继续使用同一份用户数据与快捷方式。
- 衣橱删除将导入目录移到用户数据目录的 `removed-skins/`，并在必要时切到默认皮肤。需要手工恢复某套皮肤时，将对应编号目录移回 `skins/`，刷新衣橱后重新应用。

## 2026-11-21 设置中心白屏修复

- `%LOCALAPPDATA%\NijikaDesktopPet\local-upgrade-webview-20261121-141625` 保存修复前的桌宠程序与 `deployment.json` 摘要。需要回退时退出桌宠，从该目录将 `虹夏桌宠-before.exe` 恢复至正式安装的 `dist/虹夏桌宠.exe`。运行资源、桌面快捷方式和启动项沿用既有路径。

## 2026-11-21 单一入口及文字回复本机升级

- 回退目录为 `%LOCALAPPDATA%\NijikaDesktopPet\local-upgrade-desktop-reply-20261121-140302`。`deployment.json` 记录桌宠、MCP、审批程序、接入指引与技能的原路径及摘要。`before/shortcuts/` 保存旧设置快捷方式。`notifications-before.sqlite3` 是升级前一致性快照。
- 需要回退时，退出虹夏并让当前 Agent 断开虹夏 MCP，按清单恢复对应文件。日常回退继续使用现有消息与设置库。只有需要恢复桌面独立设置入口时才取回旧快捷方式。
- 旧程序已移出正式运行目录。仍在内存中的旧 MCP 会话随宿主断开退出，下一次启动使用正式路径上的新程序。运行时标准库 ZIP 的成员内容逐个一致，保留原容器。
- 桌面主快捷方式在同一归档中另存为“虹夏桌宠-打开设置前.lnk”。现用桌面图标在原快捷方式上增加 `--control-panel`，Windows 启动项沿用无参数入口。

## 2026-11-21 停用旧配置归档

- 本机归档位于 `%USERPROFILE%\.nijika-desktop-pet\backups\legacy-retirement-20261121`。`app-exports-complete.json` 列出从正式目录和旧导出目录移出的 15 项及原路径，回退时只恢复确有需要的单项，不恢复旧配置到已由 MAGPIE 管理的活动客户端。
- 重复程序副本已清理：归档原 `app/` 的 161 个文件已逐个与 `%LOCALAPPDATA%\NijikaDesktopPet\local-upgrade-agent-guide-20261119-191524\app` 的相对路径和 SHA-256 核对一致，随后删除约 62.53 MiB。需要恢复清单中的 `app/` 项时，从上述完整快照取对应副本；`redundant-app-purge.json` 记录实际删除及保留路径。
- `dsbot/` 保留移除前的三份依赖清单、旧 bundle 与引用它的 junction；`magpie/` 保留两项旧技能的退役记录与清理前库快照。DS Bot 日常仍使用 MAGPIE 生成的单一 MCP；如确需恢复旧 bundle，先按下节取消该单项分发，再恢复旧 bundle、junction 和对应的三份清单。库快照用于核对，不整份覆盖当前配置。

## 2026-11-21 MAGPIE 单一接入回退点

- 程序、指引和 Work 技能的原件在 `%LOCALAPPDATA%\NijikaDesktopPet\local-upgrade-magpie-only-20261121`，`deployment.json` 列出更新项及摘要。若只回退设置中心，先关闭虹夏窗口，再按清单恢复程序和相应运行库；保留当前数据库、快捷方式和 MCP 服务。
- DS Bot 的切换前快照在 `%USERPROFILE%\.nijika-desktop-pet\backups\magpie-only-20261121`。仅在确需回退时退出 DS Bot，在 MAGPIE 取消 DS Bot 对虹夏 MCP 的单项分发，核对生成的条目已退，再从备份的 `package.json` 恢复旧 bundle 加载项。不要覆盖完整 MAGPIE 库或其他 Agent 的后来改动，避免重新启用两条虹夏连接。

## 2026-11-19 本机统一提醒升级回退点

- `%LOCALAPPDATA%\NijikaDesktopPet\local-upgrade-unified-20261119-223856` 保存本轮回退。`deployment.json` 列出更新的桌宠 EXE、`dist/_nijika_pet_runtime/base_library.zip` 与 `AGENT_SETUP.md` 及新摘要，`app/` 保存原文件，`verification.json` 保存原摘要、配置摘要和清理核对清单。
- 如需回退，先正常关闭虹夏桌宠与设置中心，再按清单恢复这三个文件并使用原桌面快捷方式启动。SQLite 快照用于核对升级前的设置和档案，日常回退程序时继续使用当前消息库。
- 2026-11-21 复查确认 10 个 `.running-*` 旧副本和 1 个升级暂存文件已从正式目录移除。10 个旧副本在上一个完整旧安装快照中逐个校验一致。旧平铺 MCP 仍有历史导出引用，继续保留。技能迁移前的备份位于 `%USERPROFILE%\.nijika-desktop-pet\backups\unified-skill-20261119-215815`。

## 2026-11-19 本机 MAGPIE 向导升级回退点

- 旧安装和数据快照保存在 `%LOCALAPPDATA%\NijikaDesktopPet\local-upgrade-agent-guide-20261119-191524`。`app/` 是完整旧安装，`state/` 包含 SQLite 一致性快照、皮肤和支持素材，`deployment.json` 记录正式安装的改动文件。
- 如需回退，先退出桌宠与设置中心，并让受影响的 Agent 断开 MCP。按 `deployment.json` 从备份的 `app/` 恢复升级改动。当前数据和客户端配置应继续沿用。`retired/` 保存切换时移出的文件，既有 MCP 连接可能仍在使用旧映像。
- 新程序启动时按现有七天保留规则清理了超期的已答通知。需要查看旧记录时使用只读快照，避免覆盖当前数据库中的新通知和设置。

## 2026-11-18 本机 0.1.11 升级回退点

- 旧安装完整文件备份位于 `backups/local-upgrade-0.1.11-20261118/app/`。`before-sha256.json` 保存 343 个文件的摘要，`deployment.json` 列出本次写入的文件，`config-digests.json` 只保存 6 项接入配置的校验值。
- `shortcuts/` 保存修复前的两条桌面链接。它们曾指向过期测试目录。若仅回退程序文件，可继续使用已修正指向正式安装目录的桌面链接。
- 需要回退时，先正常退出桌宠并让受影响的 MCP 客户端主动断开连接。验证备份摘要后，针对 `deployment.json` 的文件清单恢复原文件。对本次新增项，只有确认仍与升级产物一致且确需移除时才处理。保留用户目录的数据和用户后来修改的客户端配置。
- 仍在用的旧 MCP 映像在同盘回退目录里保留供原连接退出，不应手动调用。应用回退以已核验的工作区备份为准。

## 2026-11-03 MCP onedir 迁移

在替换正式安装前，三个当前程序和必要的客户端路径摘要会备份到 `backups/mcp-onedir-20261103/`。回退需要恢复 `虹夏桌宠.exe`、`虹夏审批提醒.exe` 以及旧 onefile 的 `虹夏MCP-v2.exe`；只恢复 onedir 目录中的 EXE 而遗漏 `_internal/` 不能构成可运行程序。

正式升级后若要回退 MCP，应按备份恢复旧 onefile EXE，并把客户端配置明确改回 `<安装根>\dist\虹夏MCP-v2.exe`。默认保留最新消息库、设置、Agent 档案与 Hook 信任，不整份覆盖用户数据。`0.1.9` 安装器只删除精确旧 MCP 文件，不删除桌宠、审批程序、文档或 `dist` 其他内容。

## 2026-10-30 配置旧文件清理

安全清理工具把三个旧目标备份到 `backups/config-cleanup-20261030/safe-tool-apply/`，`manifest.json` 记录原路径、类型、文件大小和 SHA-256。需要回退时按清单恢复：`01-nijika-desktop-dialog/` 回到 `%USERPROFILE%\.agents\skills\nijika-desktop-dialog`，另外两个单文件恢复原文件名；默认不要恢复旧技能副本，否则审计会再次判为冲突或重复。

## 2026-10-30 提醒可靠性与 DSH 来源加固

正式安装前备份位于 `backups/reminder-source-hardening-20261030/`：`formal-dist/` 保存三个旧 EXE，`formal-app-runtime/` 保存更新前文档、DSH/Work/Codex 运行资源及摘要，`notifications-snapshot.sqlite3` 是更新前 SQLite 一致性快照。`manifest.json` 记录来源提交、分支、程序和数据库摘要。

回退时先关闭路径为 `%LOCALAPPDATA%\NijikaDesktopPet\app\dist\虹夏桌宠.exe` 的正式桌宠与设置窗口，再按需恢复三个旧程序；默认保留更新后的消息、回执、皮肤、设置、Agent 档案和 Hook 信任，不整份覆盖用户数据库。正式目录里的 `*.running-reminder-source-hardening-20261030.bak` 只是更新时占用中的旧映像，不是启动入口；等对应旧连接退出后再清理。

## 2026-10-30 VS Code 具体 Agent 正式安装

更新前三个程序与 SQLite 一致性快照位于 `backups/vscode-agents-formal-20261030/`。需要回退时先关闭桌面角色与设置窗口，再恢复所需旧程序；默认保留更新后的消息、回执、皮肤、设置和 Agent 档案，不整份恢复旧数据库。

正式安装目录中的 `虹夏MCP-v2.running-formal-20261030.bak` 是仍被旧会话持有的替换前映像，不要从客户端配置指向它，也不要在旧进程退出前删除。旧会话重连后会使用标准 `虹夏MCP-v2.exe`。

## 2026-10-29 本机发现候选

本轮仅源码及独立候选，没有覆盖正式安装；回退试用只需关闭候选面板并使用原桌面快捷方式，不恢复真实消息库。候选的合成配置/数据库位于 diagnostics/discovery-20261029，不与正式数据共用。将来真实接入后，按向导保存的逐文件 `.bak-nijika-*` 核对恢复，先确认没有后续用户改动，不能整份覆盖其他服务；MAGPIE 管理目标继续由其管理器处理。activity 辅助表保持旧通知表兼容，无需为运行旧程序删除数据。

## 2026-10-29 前端接入修复回退

备份在 backups/setup-fix-20261029，包含前一安装程序、替换前的手册/安装脚本与 SQLite 一致性快照。默认只恢复程序与必要安装脚本，保留此后用户消息和设置，不默认恢复旧数据库。8 项现有客户端配置/MCP/Hook 摘要在本轮保持。旧设置窗口仍使用被改名保留的旧映像；关闭旧窗口、重开设置可使用新版。占用旧映像不是新的启动入口，不能在进程仍使用时清理。


## 2026-10-28 来源修复回退

本机备份 `backups/source-identity-20261028/installed/` 包含更新前的三个程序及一致性数据库快照；workspace 子目录保存更新前 dist 程序。默认只回退程序，保留最新数据库与回执。新 notice_sources 附属表不改变旧 notifications 表列，旧程序可共用，勿为回退程序覆盖新数据。

客户端/共享库备份只保存虹夏条目与技能片段；合并恢复相应片段，不整体覆盖客户端配置。安装目录的 `虹夏MCP-v2.running-20261028.bak` 是尚在运行的旧进程映像，保留到旧会话重连后再清理；不是新的启动入口。不要结束所有 MCP 进程或回退无关未提交改动。


## 2026-10-26 MVP 正式更新的恢复点

本轮备份在项目 `backups/mvp-formal-20261026/`：`虹夏桌宠-before.exe` 为更新前正式桌宠，`notifications-before.sqlite3` 为 SQLite 一致性快照，`manifest.json` 记录程序和受保护配置摘要。若工作区原 dist 与旧安装版不同，另保留 `虹夏桌宠-workspace-before.exe`。本机备份不加入分享包或 Git。

需要回退程序时，先退出桌宠和设置窗口，将 `虹夏桌宠-before.exe` 复制到 `%LOCALAPPDATA%\NijikaDesktopPet\app\dist\虹夏桌宠.exe` 后重新启动；桌面及开机自启路径不变。开发预览也要回退时，再同步对应的工作区 dist。默认继续使用最新的消息和设置数据库，不自动用旧快照覆盖后续消息。MCP、审批程序、客户端配置与信任没有因本次更新改变。

本次只更新基础互动与设置中心，视频样片未进入正式安装。下面的 2026-10-16 记录仍保留，作为更早的完整源码/运行备份。

更新触发：2026-10-16 用户选定 N30/N32/N34，要求先保存当前效果，便于新动画不满意时恢复。

## 已保留的版本

- 稳定源码提交：`a876e181335029f81d8f1b6c81363ff6f4cfc6f0`。
- Git 注释标签：`stable/pre-interactions-20261016`，已推送远程。
- 原 `main` 保持稳定版；后续互动功能在 `codex/interaction-30-32-34` 分支开发。
- 本机备份目录：项目根目录下 `backups/20261016-pre-interactions-a876e18/`。
- `source.bundle`：带历史的离线 Git 存档，可用 Git bundle verify 检查。
- `runtime.zip`：当时正式的三个 EXE 与快捷方式图标，按原项目相对路径保存；不包含用户消息或设置。
- `userdata/`：当时本机 SQLite 的一致性快照，以及已有自定义皮肤、支持图片；属于私人数据，只保存在本机。
- `MANIFEST.json`：以上文件的 SHA256、基线与备份时刻。备份目录忽略入库，不作为对外试用包。

## 需要恢复时

用户可以直接要求：“恢复到互动功能开发前的存档”。执行恢复的 Agent 应：

1. 先核对工作区差异，保存后续工作，不使用 `reset --hard` 或 `clean` 丢弃新内容。
2. 核对标签指向上述提交，并检查本机备份的 SHA256、Git bundle 和数据库完整性。
3. 从该标签建立新的 `codex/restore-…` 分支；源码与角色 PNG 随源码恢复。确保本仓库 `.git/info/exclude` 中仍有 `/backups/`，避免旧标签的忽略规则遗漏私人备份目录；新克隆的仓库也先加此排除再放入私人快照。
4. 退出本项目的设置窗口与桌宠，再将 `runtime.zip` 中的 EXE 和图标恢复至当前项目对应目录。确认桌面及开机启动快捷方式仍指向项目的 `dist/虹夏桌宠.exe`。只恢复源码不会自动替换已运行的 EXE。
5. 默认保留最新用户数据。若还需恢复设置或养成数据，先另存恢复前的数据；确认所有共享此消息库的桌宠、面板及 MCP 进程已退出，再处理数据库与其 WAL/SHM。不要在数据库仍被打开时直接覆盖文件。
6. 私人数据恢复会回到备份时刻，之后的新消息和选择可能不在旧快照中，应先说明并让用户选择是否恢复数据。客户端 MCP 配置与 hook 信任不在本存档的恢复范围内，不自动修改。
7. 重启恢复的正式程序，复验角色显示、原动画、气泡和一次 MCP 点击回传，再标记恢复完成。

本文件是恢复说明，本轮没有执行回退、替换正式程序或修改本机数据。

## Codex 完成兜底的独立回退点（2026-10-17）

完成兜底开发基线为 `55e7096`，新实现位于 `codex/codex-stop-reminder`。正式安装前的备份在本机 `backups/20261017-codex-stop-183410/`：包括原 `dist/虹夏审批提醒.exe`、原 Codex 安装器/模板、`hooks.before.json` 与 `MANIFEST.json`。这些资料用于本次增量的恢复，不含 config.toml 或模型凭据；不上传。

仅关闭完成兜底时，在 Codex `/hooks` 停用本项目的 UserPromptSubmit 与 Stop；保留原审批两项和 Computer Use notify。需回退程序时，核对清单哈希，待没有正在执行的 Hook 后把备份 EXE 及脚本/模板恢复至 `%LOCALAPPDATA%\NijikaDesktopPet\app`。若 hooks.json 自备份后未新增其他内容，可先备份当前文件再恢复 hooks.before.json；有其他新改动时仅移除本项目新增两事件 handler，保留它们和既有审批。不要回写信任记录。

本次只新增 `codex_turn_state` 表，没有改原通知结构。回退旧 Hook 后该表可留在库中，旧桌宠/MCP 会忽略它；不需还原或删除消息库，也不影响设置、皮肤、便签与其他 Agent。仅切换 Git 分支不会回退安装目录中的 EXE。
