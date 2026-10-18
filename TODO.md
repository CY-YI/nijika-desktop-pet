# 当前待办

## 当前任务：Agent 接入教程与提示词复验（2026-10-18）

- 用户原话：“可以这些东西可以先代定然后你验收一下就是之前添加的比如说配置agent教程这这个东西它因为现在代码改变很多了嘛然后它那个提示词啊之类的需不需要改变”。动画工具与鲸鱼娘参考先待定，不等待此前的素材链接问题；本轮转为验收当前 Agent 向导、配置导出、自动配置提示词及安装说明。
- SOP Full 局部维护，保持现有客户端适配和 stdio 协议；单线进行。分支 `codex/interaction-settings-20261017`，基线 `dfecfad`，本轮初始工作区干净。
- 已知需复核处：普通 MCP 与审批/完成钩子边界、Codex 四事件和本人信任说明、Work 的晚到点击与自动等待、Claude Code 文档与向导实际选项的一致性。不开新客户端功能，不改变动画或扩大权限。
- [x] 正式路径只读核对：现有 Codex/Claude/DSH 虹夏配置均指向标准安装目录，工作区与安装版 MCP 虽摘要不同，但两份真实 stdio 四工具发现、推荐选项与选择回执均通过；不因此替换已正常工作的 MCP。
- [x] 69 项隔离源码回归、5 项前端控制器测试及 61 项正式构建源回归通过。新增测试覆盖各客户端完整路径/嵌入 JSON、可选钩子不安装、notify/配置原字节保留、旧导出刷新与幂等、入口参数转发。并行回归中一次非法无令牌请求发生 WinError 10053，保留失败日志；随后串行完整复跑 69 项 OK，未为此改鉴权或放宽校验。
- [x] 修正动态提示词：气泡短成果、字段限制/推荐说明、同 ID 连续等待、invalid 修正、实际工具前缀、Codex 四事件与本人信任、Work/DSH 原生桥接边界；计划预览不再对所有客户端展示 Codex 专属规则。手册补准确位置、Claude 专属向导尚缺及 PowerShell 环境变量写法。
- [x] 最小正式程序维护：已验收 `b172fbe` + `agent_setup.py`/`pet.py` 补丁，不含互动预览；修复已文档化的 `--control-panel --browser` 转发。新 `tools/smoke_agent_guidance.py` 在构建版与确切安装版通过 Codex/DSH/custom 隔离 plan→apply→prepare，不打开可视窗口。Work 安装仍为隔离 CLI 模拟，未重装真实插件或新增现场会话验收。
- [x] 更新固定安装目录与工作区 dist 的桌宠 EXE、备份并刷新真实三份接入文件，源码预览在原 53630 端口重新载入。8 个受保护对象（Codex 配置/hooks、Claude MCP/settings、DSH 两档案、MCP/Hook EXE）摘要保持原样；桌宠已无终端重启且心跳正常。更新首次复制遇到进程释放锁延迟，等待目标进程退出后复制成功。
- 交付边界：现有连接无需重配，钩子未改无需重信任。旧导出两份原先仍指工作区，已改为安装路径；无手动下载要求。内置浏览器已保存的权限拒绝未绕过，本轮没有页面点击/布局验收，也不把隔离 API/MCP 测试当外部 Agent 自主调用成功。构建/回归摘要在 `diagnostics/agent-guide-*-20261018*` 与 `build/agent-guide-hotfix-20261018/`；旧程序/文档/接入文件在 `backups/20261018-agent-guide-hotfix/`，均忽略不上传。
- [x] 工程文档与本轮改动纳入当前分支 Git 存档并推送；交付前通过虹夏发送一次成果提醒。生成程序、诊断、用户接入文件及本机备份均不上传。

## 待定任务：专业动画流程评估（2026-10-18）

- 2026-10-18 用户已要求这些方向先待定，当前不等待参考问题的回复、不继续选型或安装，回到 Agent 教程验收。下列为可恢复的研究记录。

- 最新方向：用户要求借鉴“Deep Sig Highness 的金鱼娘”作品。检索判断可能指 DSH 鲸鱼娘；已通过异步问题索要具体链接/作者，尚未收到，不能认定是哪一个版本。暂不发起 Blender/Live2D 选型投票，先按此参考澄清。
- [x] 参考源码检查（GitHub 连接只读读取，未安装/执行第三方插件）：`vlln/whale-girl/docs/sprites-spec.md` 明确为 AI 生图 → 切图/配准 → 帧图集 → 状态驱动播放，15 状态、若干 1–3 帧动作，并非 3D 或 Live2D；适合借鉴角色/动作资源契约，但低帧数不等于满足本项目丝滑目标。
- [x] `Andersen216/dsh-whale-girl-live2d` README/PROVENANCE 明确加载现成 `.moc3` 模型、物理、动作和表情资源，使用 Pixi 与 pixi-live2d-display；模型来自原作者氵六青的 VTube Studio 包。可以借鉴渲染接入、动作优先级及状态分层，不能把“能加载鲸鱼娘”说成“自动会制作同品质虹夏模型”。代码与美术资源许可独立，仅借鉴不等于复制素材进入本项目。来源：https://github.com/vlln/whale-girl/blob/main/docs/sprites-spec.md ，https://github.com/Andersen216/dsh-whale-girl-live2d/blob/main/README.md ，https://github.com/Andersen216/dsh-whale-girl-live2d/blob/main/PROVENANCE.md 。
- 用户反馈已打开的互动预览“动画效果都不是很好”，愿意由 Agent 直接调用专业工具，也愿意必要时学习配合。N30/N34 的视觉验收未通过；不继续把同一单图变形批量扩成正式桌面动作。
- 当前分支 `codex/interaction-settings-20261017`，基线 `7c11726`，开工工作区干净；保留已推送预览与稳定版，不改 MCP/提醒流程。继续 SOP Full 的受影响需求/选型阶段，单线实施。
- [x] 素材核对：工作区正式素材只有九张合成 PNG；未发现 PSD/ORA/CMO3/MOC3/BLEND/VRM/FBX 等分层或绑定源文件（排除私人备份/依赖/构建与诊断目录）。PATH、Windows 卸载注册项及常见安装位置未检测到 Blender/Live2D/Spine 等编辑器；不代表已全盘排除便携版。
- [x] 工具连接核对：插件目录精确搜索 Blender、Live2D/Cubism/Spine 均未返回匹配。较宽的动画搜索返回 Runway/Higgsfield 等未连接的视频服务，不是模型绑定编辑器，不冒称现成专业建模工具已可调用。
- [x] 官方资料核对：Live2D 需适配导入的分层 PSD 并建立 ArtMesh/参数；Spine 支持骨骼、权重、IK 与命令行导入/导出，保存和导出需相应许可；Blender 免费开源，提供骨骼/形态键、Python 接口与后台运行。文档依据：Live2D PSD 导入 https://docs.live2d.com/en/cubism-editor-manual/psd-import/ ；Spine https://esotericsoftware.com/spine-purchase 和 https://en.esotericsoftware.com/spine-command-line-interface ；Blender https://www.blender.org/features/animation/ 和 https://www.blender.org/features/ 。
- 所有路线先拆分并补齐被遮住的头发、脸、肢体等素材，再绑定与调曲线；换工具不等于单张 PNG 自动变为完整高质量模型。当前仅核对自动化接口，尚未安装、运行或证明本机 Blender 出图效果；不承诺与人工精修等同。
- 浏览器边界：按用户偏好尝试在内置浏览器查看 Live2D 官方 PSD 页面，https://docs.live2d.com 访问被本人权限拒绝，未通过其他浏览器或原始 UI 通道绕过；Live2D 依据为拒绝前已取得的官方检索正文。其他工具依官方来源检索，不改浏览器权限。
- [ ] 确定首个验证路径：早先 Blender 自动化样片与 Live2D 精修仅为候选；最新先等鲸鱼娘参考版本确认，再根据其真实资源流程建议首个样片。候选未选定，不先购买/上传素材至新服务，不替换正式程序。
- 下一步：用户提供作品链接/作者或演示后，核对具体仓库/模型与许可，明确可复用的工程机制与虹夏仍需制作的资产；再通过虹夏做真正需要的路线决定。若选择学习，只引导当前一步所需操作，不要求一次学完整套软件。

## 当前任务：恢复互动设置与动作预览（2026-10-17）

- 用户原话：“那开始继续回归到那个桌面端的那个app设置界面内容优化那一块吧”。桌宠请求 `b7b332ec0e824980a8640e12ec51c902` 已答复“继续互动设置”；已在 Codex 聊天复述。沿用 N30/N32/N34，不加入未选的历史统计或来源筛选。
- SOP Full + Web 局部增量，沿用 Python / 原生 HTML、CSS、JS / SQLite / WebView2，仅本机回环，无账号与外部服务；单线实施。
- 基线：`codex/codex-stop-reminder` / `b172fbe`；初始未提交改动仅为上一轮 TODO 验收记录。旧互动工作树 `codex/interaction-preview` 有未完成改动，本轮只读参考，不覆盖或修改它。
- 交付边界：先提供“互动与养成”设置入口、连续局部变形预览及可关闭的本机养成。正式桌宠 EXE 与 Agent 接入配置保持现状；新触摸与彩蛋先在面板内试映，用户审阅后再进入桌面接入单元。
- [x] MVU1 代码与编码检查：选择性接回旧工作树的局部动作算法，新增 8 个动作试映、停止/重播、幅度与小特效试用。256×384 实际 WebP 均可解码，97–193 帧，单次循环；不宣称站立、背面转身或真实骨骼动画。浏览器目视与设备帧率未验证。
- [x] MVU2：养成开关、饱食/水分/心情、点心/喝水独立 30 秒冷却、离线最多 8 小时；并发与时钟回拨边界回归通过。预览不改数值，投喂才保存，没有旧桌宠无法消费的动作队列。
- [x] API/代码检查：64 项隔离 Python 回归通过（含既有提醒、Agent、专注和衣橱逻辑）；5 项无浏览器/无网络的 JS 控制器单元测试通过，覆盖停止后旧响应、动作响应乱序、保存时继续编辑、投喂成功而装饰动画失败、减少动画及关闭触摸。这些不是页面点击验收。两个 JS 的语法与 diff 空白检查通过。受限沙箱初跑因临时替换和本机套接字被拒失败，经原生授权、显式隔离库复跑取得最终 OK，不把初跑记为通过。
- [ ] MVU3 页面验收：内置浏览器打开 `http://127.0.0.1:53630/#interaction` 首次被拒。桌宠请求 `d0a1daa2dda54dfb84cb875aa8fccdbd` 已回答“继续页面验收”，已在聊天复述后重试；第二次仍被 saved permission/managed policy 阻断。未使用其他浏览器/无头浏览器等绕过，未宣称实际点击、复制、页面布局和帧率通过。需本人解除客户端保存的该地址访问拒绝后补验，后续不重复发送同一问题。
- [x] 源码与文档收口：本轮 16 个变更文件凭据特征扫描无命中；HTML 123 个 ID 无重复、两个脚本 103 个完整字面量 ID 引用均存在，语法及 diff 空白检查通过。需求状态、架构、接口、安装与变更记录已同步。这些静态检查不替代页面验收。
- Git 阶段存档使用独立分支 `codex/interaction-settings-20261017`，准确提交以该分支 Git 历史为准；不合并稳定 main、不替换正式 EXE。本任务仍有页面验收及桌面接入未完成，不输出 ALL_FINISH。
- 下一步：在已准备的互动页验收触摸分区、两种幅度/特效、重播/停止、切页取消和刷新后设置恢复，再按用户效果反馈继续桌面接入。首次生成实测约 2.35–5.15 秒（未测浏览器加载时间），重播缓存可复用；大动作与快速切换的体感仍待实测，不写成“已丝滑”。
- 工作区清点：`interaction_motion.py`、`interaction_store.py`、`control-ui/interaction.js` 与 `tests/test_interactions.py`、`tests/test_interaction_ui.cjs` 为正式源码/测试；`diagnostics/interaction-settings-preview/` 保留隔离数据库、样片 `dance.webp`、中间帧和 `animation-check.json`，用途为权限恢复后的现场补验与动作审阅，忽略入 Git/分享包。`diagnostics/interaction-settings-test/` 为协议测试专用队列，同样不打包。正式 EXE/用户数据、其他互动工作树均未修改。
- [ ] 桌面触摸、桌面动作播放和正式 EXE 替换在预览审阅后继续；当前不记为完成。

## 当前任务：Codex 完成提醒兜底（2026-10-17）

### 降权后的现场复验（2026-10-17）

- [x] 真实受限权限下，工作区外写入被拒绝；随后经 Codex 原生审批请求执行临时标记创建。PermissionRequest 自动生成虹夏请求 `62834892f46a4f8e992aed0be8855041`，用户点击“知道了”，MCP 只读查询返回 answered；助手已在聊天复述回执，原生命令另获授权后文件确实创建。该次验证没有手动模拟审批通知。
- [x] 用户随后要求“不主动调用 MCP 然后向我发送信息”：该轮没有主动调用桌宠发送工具，结束后用户回传“有”，确认自动气泡实际出现。结合只读事件与信任检查，完成本机 Codex Stop 兜底现场验收；记录见 `diagnostics/stop-fallback-current-turn.json`。
- [ ] 本次空测试标记 `C:\Users\CY\.nijika-desktop-pet\codex-approval-probe-20261017-f9137c62.txt` 仍存在；先前清理调用在中断后未取得完成结果，最新只读检查确认尚未删除。在受限权限下应另经允许清理该单一空文件，不绕过审批；当前先完成用户要求的无主动 MCP 自动提醒测试。

- 用户决定：“可以先做codex的”。本轮仅增加 Codex 完成提醒兜底，按 SOP Full 通道局部修复；Work、DSH、Claude Code 的完成事件接入仍在本轮范围外。
- 接手基线：`55e7096`，分支 `codex/codex-stop-reminder`；另一个互动工作树不参与修改。已有 39 项回归基线通过。
- 选型：采用官方 `UserPromptSubmit` / `PostToolUse` / `Stop` 生命周期 hook，复用安装版 `虹夏审批提醒.exe` 与消息库；保留现有 Computer Use 的 `notify` 原文。官方协议依据：<https://learn.chatgpt.com/docs/hooks>（2026-10-17 已检索并打开）。`Stop` 固定输出 `{}`，不输出续跑或授权决定。
- 验收目标：实质任务漏调用提醒时补发一次；成功调用过虹夏完成/选择工具则不补发；简短事实问答、内部标题和缺失轮次状态不提醒；关闭/点击后的重复 Stop 仍不重复；正文、命令与回复不存入轮次状态。
- [x] MVU1：`codex_completion.py` 在内存分类，轮次元数据仅存会话/轮次 SHA256、类别、计数、通知标记与时间；完成通知与标记同事务提交。已发送的无正文去重行保留，其他旧状态 30 天清理。隔离测试覆盖并发、关闭/回答后重放、消息保留期后重放、失败回滚、输入容错及无原文落盘。
- [x] MVU2：四事件安装器保留其他组与同组 handler、写前备份、重复安装不叠加；新增事件固定 --event 参数，畸形 Stop 仍返回 `{}`。新增 UserPromptSubmit / Stop 超时 15 秒，原审批两项定义（含 5 秒超时）保持原样。
- [x] 56 项完整回归通过；打包 `tools/smoke_approval_hook.py` 通过（实际 EXE、特殊字符路径、四事件、stdin、notify 不变、幂等、Claude Code 原审批来源与去重）。
- [x] `tools/smoke_codex_completion.py` 真实 CLI 验收：work 创建并读取临时文件后 1 条兜底；question 简短问答 0 条；notice 主动 MCP 1 条且兜底 0 条。均使用隔离队列，逐字节核对用户配置/notify/信任未变。并发首测曾漏掉 UserPromptSubmit 状态（原因未定位）；顺序复测通过，增加新增事件启动余量后并发两场景复测通过。分类为启发式，不把测试范围外的表达保证为绝无误判。
- [x] 最终 Hook 已重建并复制到 `%LOCALAPPDATA%\NijikaDesktopPet\app\dist\虹夏审批提醒.exe`，SHA256 `288489dcd5a7325fcbf367a0f99df927cbc68937234b8ae38a94bb89c7af1e30`，与源码 dist 相同；用确切安装路径启动、stdin→隔离完成队列验证通过。仅同步 Hook EXE 与 Codex 安装器/模板，桌宠/MCP 及前端未替换。
- [x] 正式 hooks.json 已合并；PermissionRequest / PostToolUse 原定义和 config.toml 原字节均未变，没有代写信任。原 Hook/脚本/模板/用户 hooks 备份在 `backups/20261017-codex-stop-183410/`，清单与回退见 ROLLBACK.md。
- [x] 需求、架构、接口、安装、接入、回退及变更记录已同步；新版试用包与文档包单独命名为 `2026-10-17-codex-stop.zip`，保留原分享包。20 项试用包白名单、SHA256 清单与三个 EXE 核对通过；Work 路径为 AUTO_LOCAL_MCP，占位配置不含本机队列/私人备份/真实客户端配置。文档包新增 ROLLBACK.md；19 个本轮修改文件的凭据特征扫描、打包模块检查与 git diff --check 通过。
- Git 归档：本轮只提交与推送 `codex/codex-stop-reminder`；`main` 与互动分支未改，提交与远端以该分支的 Git 历史为准。
- [x] 2026-10-17 用户明确回传“信任权限给了两个钩子”。只读 `hooks/list` 确认 UserPromptSubmit / Stop 以及原 PermissionRequest / PostToolUse 均为 enabled=true、trustStatus=trusted，无 warnings/errors。随后用真实安装定义启动独立 Codex CLI，不加信任跳过参数、不覆盖 hooks；在隔离目录创建并读回测试文件，正常结束后自动补发 1 条通知，用户配置原字节未变。新增两项的本人信任和正常模式自动触发已验收；本次隔离队列验证不额外向真实桌面发送测试气泡。
- 验收边界：本轮不改前端或 Agent 配置入口，全部 API/存储回归通过；Work/DSH/Claude Code 的完成兜底仍未实施。当前内置浏览器内核启动失败，不作新的页面目视通过声明。
- 工作区清点：`tools/smoke_codex_completion.py` 提升为可复用 CLI 验收工具；`build/codex-stop/` 保留为最终 Hook 的构建分析与 spec，`diagnostics/build-codex-stop.log` 为构建日志，`diagnostics/codex-stop-install.json` 为安装哈希及备份位置，`diagnostics/codex-trusted-verification.json` 为不含正文的正常信任验收摘要。均忽略入 Git、分享包不含这些目录。首次新测试因测试连接未关闭产生清理失败，现已修复并回归通过；清理其 10 个已知 `%TEMP%/tmp*` 目录的请求被自动审批审查拒绝，仅返回 blocked by policy，未给具体原因，未执行删除，待后续允许时处理；不清理来源不明目录。本次信任复验的临时目录均随验证结束正常清理。

## 当前任务：角色衣橱·自制角色引导（2026-10-17）

- 用户原话：“前端不是有一个导入皮肤的功能吗我希望这个皮肤可以由人家去制定一角色啊之类的这些东西但是你最好是给他一个比如说发给ai的提示词然后再在那边标注这个文件是什么样的类型格式的”。目标：让用户能拿一段提示词交给会画图的 AI，得到符合桌宠导入校验的角色素材，并在界面上直接看到两种文件格式的要求。
- [x] `control-ui/index.html` 在“角色衣橱”页新增“自制角色 · 让 AI 帮你画”卡片：两个复制按钮、方案一单张 PNG 与方案二 ZIP 表情包的格式标注、提示词预格式框、白底抠图提醒。
- [x] `control-ui/app.js` 新增 `SKIN_AI_PROMPT`（角色描述占位、Q 版全身、纯透明背景、PNG/RGBA、2:3、推荐 1024×1536、九张表情文件名与打包、成品自检）与 `renderSkinPrompt()`，两个按钮均调用现有 `copyText()` 并带失败回退。
- [x] `control-ui/styles.css` 新增 `.creator-card` 等样式与窄屏单列适配。
- [x] 与 `control_store.py` 实际校验逐条核对：PNG 必须 RGBA 且含全透明像素、四角透明、`0.62 ≤ w/h ≤ 0.72`、最小边 ≥32、≤800 万像素、≤32 MB；ZIP 只允许九张指定 PNG 与可选 `manifest.json`（≤4096B）、≤10 条目、解压 ≤64 MB、九张同尺寸。
- [x] 验证：`node --check control-ui/app.js` 通过；隔离服务 HTTP 实测新卡片、两个复制按钮与提示词注入均存在；87 个 JS 引用元素 ID 全部存在于 HTML；39 项回归通过。
- [x] 重建 `dist\虹夏桌宠.exe` 并替换安装版；从 PyInstaller 归档提取确认三份 control-ui 资源均含新卡片；重启桌宠与设置窗口，对运行中的设置服务用系统 Edge 无头模式真实渲染“角色衣橱”页，确认卡片、两块格式标注与提示词框排版正常。
- [x] 更新 2026-10-17 试用包与文档分享包；试用包内 EXE 哈希与仓库一致，分支已推送。
- 边界：cua 内置浏览器内核在本机无法启动（`windows sandbox failed: helper_unknown_error`），改用系统 Edge 无头渲染补验；桌面点击结果由用户本人决定。

## 当前任务：验证前端设置 UI 与各 Agent 接入步骤（2026-10-17）

- 用户原话：“把这个未完成的任务记录下来就行然后你验证一下是否会影响你做的那个前端ui的各个功能然后还有我如果部署各个agent揭露作虫的步骤有没有改变”。三件事：记录“Codex 结束事件接入虹夏”未完成项、实测设置中心各页、核对各客户端接入步骤是否变化。
- [x] 原待办“Codex 系统级结束通知兜底”已进入上方 N51 任务：改用官方 Stop 生命周期 Hook 接入，原 Computer Use notify 保留。代码、隔离测试与真实 CLI 已完成；正式安装和本人信任状态以本文件最上方任务为准，不再按未开始的 turn-ended 方案续作。
- [x] 前端 UI 实测（`codex/interaction-preview` 分支的 `control-ui/` 与 `main` 逐字节相同，判断不受影响，仍按用户要求实测）：`GET /` 注入令牌、无令牌 `GET /api/state` 返回 403（鉴权按预期拒绝）；`GET /api/state` 返回 renderer/agents/clients/skins/support/companion 全部字段；agents plan→apply→prepare→test 完整闭环通过（Codex 档案建立、接入目录与自动配置提示词生成、测试提醒入队）；focus configure/start/pause/reset 通过；notes add 通过；settings 更新通过；support 更新（name/message/url）通过；reminders 通过；skins 导入（非全透明 PNG）通过；support 收款图上传通过；未知路由按预期报错。
- 边界：本轮浏览器内核在当前沙箱下无法启动（`windows sandbox failed: helper_unknown_error`），因此 UI 验收走 API 级实测，未做页面像素级回归；接口与数据通路全部覆盖。
- [x] 接入步骤核对：Codex、Work、DSH 的向导/文档流程与 10-16 统一安装路径后一致，均指向 `%LOCALAPPDATA%\NijikaDesktopPet\app`，用户侧步骤（重载客户端、新任务验证、本人信任 hook）未变。Claude Code 为源码向导暂未覆盖的新客户端：`agent_setup.py` 的 `CLIENTS` 仍只有 codex/work/dsh/custom，设置中心不提供 Claude Code 选项，接入需按 `AGENT_SETUP.md` 手动执行 `claude mcp add` + `integrations\claude-code\install-hooks.ps1`；文档第 125 行误称“向导可为 Claude Code 档案生成配置”，与实际不符，待修正或补向导。
- [ ] 待用户参与：Codex 应用关闭后运行 `codex plugin add nijika-work-local@nijika-local` 刷新插件运行缓存；重启桌宠以使用安装版；如需 Claude Code 出现在设置中心向导，先补 `agent_setup.py` 客户端定义。
- 工作区清点：本轮只读核对 + 隔离临时环境（已清理 `%TEMP%\nijika-iso-*`、`nijika-ui-test-*` 与失效 `panel-status.json`）；一次性清理脚本用后即删；未改动真实消息库、皮肤、支持配置（写入测试均在隔离库）。

## 当前任务：统一安装路径并改指全部本机客户端（2026-10-16）

- 用户原话：“不要让他们只在这一个工作区生效让他们跟正常的那些嗯路径都统一不然的话以后我想找都找不到”。目标：桌宠与各客户端不再依赖开发目录 `D:\deepseekharnes work\提示功能作用的桌宠`，统一到标准安装位置 `%LOCALAPPDATA%\NijikaDesktopPet\app`（安装根目录下的 `notifications.sqlite3` 只是旧版迁移候选，运行时数据仍统一在 `%USERPROFILE%\.nijika-desktop-pet\`）。
- [x] 重建 `dist\虹夏审批提醒.exe`（含去重修复与 `--source claude-code` 支持），经 `tools\package_release.py` 生成试用包并运行 `distribution\install.ps1 -Dsh -CodexHooks -AutoStart -NoLaunch` 安装。
- [x] 快捷方式（桌面“虹夏桌宠”“虹夏桌宠设置”、开机自启）、Work 插件 manifest、DSH desktop/web 配置与技能、Codex 审批钩子全部改指安装目录；DSH 原文件以 `.bak-nijika-*` 备份，聚合快照在 `%USERPROFILE%\.nijika-desktop-pet\backup-before-unify-20261016\`。
- [x] Claude Code：MCP 用户级注册改指安装版（`claude mcp remove/add -s user`）；审批钩子改用新脚本 `integrations/claude-code/install-hooks.ps1`（exec 形式、合并保留其他钩子、备份到 `.claude\backups\`、重复执行幂等、全新机器可直接建文件），调用安装版 EXE。
- [x] Codex：`install.ps1 -Codex` 对既有注册只警告不覆盖，改为备份后直接改写 `~/.codex/config.toml` 的 MCP 命令路径（保留四个工具的 approval_mode）；marketplace `nijika-local` 经 Codex CLI 移除重加，`plugin list` 显示来源为安装目录且插件 installed+enabled。
- [x] 新增 `distribution\install.ps1` 的 `-ClaudeHooks` 开关与两个正式冒烟测试 `tools\smoke_claude_hooks.py`、`tools\smoke_dsh_installer.py`；修复 `integrations/dsh/install.ps1` 缺 UTF-8 BOM 的隐患。
- [x] 验证：三款 EXE 与仓库 `dist/` 哈希逐一相同；安装版 MCP 冒烟（stdio 握手、四工具、隔离消息库气泡回执）通过；DSH web 配置解析、desktop 配置文件、快捷方式目标、CC 与 Codex 钩子命令均为安装路径；39 项回归通过。
- [ ] 待用户参与的三步：关闭 Codex 应用后运行 `codex plugin add nijika-work-local@nijika-local` 刷新插件运行缓存（缓存仍锁定旧路径；官方 CLI 刷新尝试被本机权限策略拦下，未代跑）；在 Codex `/hooks` 重新审阅信任两条虹夏钩子（路径已变）；重启桌宠以使用安装版（当前运行的仍是旧目录进程）。
- 验收边界：不宣称客户端重新信任后的自然触发已现场复验；钩子自本轮起调用冻结的安装版 EXE，改造 `approval_hook.py` 后需重建+重装；`~/.claude.json` 与 `~/.codex/config.toml` 中残留的开发目录字样只是项目历史/信任记录，不是运行依赖；旧的接入快照（`%USERPROFILE%\.nijika-desktop-pet\integrations\agents\<档案ID>\`）为过期导出，重启桌宠后新导出会使用安装路径。
- 工作区清点：一次性探针 `diagnostics/check_cc_hooks_install.py`、`check_dsh_installer_encoding.py` 已提升为 `tools/smoke_claude_hooks.py`、`tools/smoke_dsh_installer.py`，`diagnostics/patch_codex_config.py` 为一次性机器改动脚本。

## 当前任务：Claude Code 审批提醒接入（2026-10-16）

- 用户在气泡选择“现在接上”后实施 Claude Code 侧审批提醒；随后追问“我想确认的是为什么codex里面可以有这个功能……DSH里面也要再次添加……但是它能够实现”，并要求“请按照我的SOP落盘并提交吧”。已核实三条链路：Codex 走 `hooks.json` 权限钩子（10-11 已真实验收）；Claude Code 走用户级 `settings.json` 钩子（本轮接入）；DSH 目前只有 MCP 工具通道，主机侧权限事件桥接未实现（见 `integrations/dsh/README.md` 与 N19 边界），现有 DSH 效果不需要重复添加。
- [x] `approval_hook.py` 增加 `--source claude-code`：气泡署名“Claude code”、文案指向 Claude Code 权限提示；Codex 默认路径逐字保持。
- [x] `notification_store.py`：已完成的旧通知不再吞掉同 key 的新提醒；审批优先级 100 与“resolve 只作用于 pending、不伪造点击”保持不变。
- [x] `%USERPROFILE%\.claude\settings.json` 注册 `PermissionRequest` + `PostToolUse`（async）两条 exec 钩子（项目 venv 的 python 直接拉起，不经 shell），改动前备份 `settings.json.backup.nijika-20261016-222118`。
- [x] 验证：来源文案与空输出/退出码 0 的隔离检查、仓库冒烟测试通过；合成 CC 事件端到端气泡 → 用户点击回执 answered、PostToolUse 不覆盖点击、重复请求生成新通知并自动收起；运行中会话热加载生效，预创建通知被一次真实 `PostToolUse` 自动收起 resolved。
- [x] 用户以气泡选定“新建 claude 分支”；源码与文档已提交到 `claude/cc-approval-reminder`（基于互动分支顶端）并推送，`main` 与 `codex/interaction-30-32-34` 保持原样。（2026-10-16 深夜更新：审批钩子已改指安装版 `%LOCALAPPDATA%\NijikaDesktopPet\app\dist\虹夏审批提醒.exe`，不再依赖工作树所在分支；详见上方“统一安装路径”任务。）
- 验收边界：真实 `PermissionRequest` 自然触发（低提示权限模式下几乎不弹）尚未验收；气泡只提醒，不授予或绕过任何权限；Claude Code 侧当前运行源码，`dist\虹夏审批提醒.exe` 未重建，Codex 打包路径仍为旧代码。
- 工作区清点：临时测试脚本 `_tmp_cc_hook_test.py` 已删除；本轮改动为 `approval_hook.py`、`notification_store.py` 与 CHANGELOG/README/AGENT_SETUP/REQUIREMENTS/TODO 文档；上一任务“并行写入提示”所指的未核实改动即本工作，归属已明确。
- 后续可选：核实 DSH 是否提供等价的权限事件钩子；若有，可照 Codex / Claude Code 的模式再接审批自动气泡（未开始，等用户确认）。

## 当前任务：互动功能前建立可恢复存档（2026-10-16）

- 用户选定 N30 分区触摸互动、N32 数值养成与投喂、N34 彩蛋动作，要求“在此之前先做好git存档”，担心 2D 动画效果不满意时需要恢复。
- 本轮先完成存档，不修改动画、运行程序、用户偏好或消息库结构。第一版及安装教程维持当前效果；N43/N44 等候选本轮不实现。
- [x] 核对存档前工作区干净，稳定基线为 `a876e181335029f81d8f1b6c81363ff6f4cfc6f0`。
- [x] 创建注释标签 `stable/pre-interactions-20261016` 并推送 GitHub；远程 peeled commit 已核对为上述基线。
- [x] 切换至独立开发分支 `codex/interaction-30-32-34`，`main` 保持稳定版。
- [x] `backups/20261016-pre-interactions-a876e18/` 已包含 `source.bundle`、`runtime.zip`、`userdata/notifications.sqlite3`、`RESTORE.md` 与 `MANIFEST.json`；当前没有额外自定义皮肤/支持图片需要备份。Git bundle 完整历史校验、ZIP 与三款 EXE/图标逐项哈希、SQLite integrity_check 均通过。
- [x] `.gitignore` 与本仓库 `.git/info/exclude` 同时忽略本机 `backups/`，防止切回旧标签后误纳入私人快照。恢复说明见 `ROLLBACK.md`。
- [x] 存档说明、忽略规则及 N30/N32/N34 选定范围已提交为 `c73e813` 并推送 `origin/codex/interaction-30-32-34`；稳定 `main` 与标签仍指向 `a876e18`。
- [ ] 下一阶段先制作小范围互动预览并验收动画效果，再递增实现 N30/N32/N34；不得以整张图片的简单晃动冒充完整新动作。
- 验证边界：本轮为存档与范围记录，没有改动生产 Python/前端代码，也没有重建、替换或启动任何 EXE；沿用之前验收结果，不宣称新互动已实现。
- 工作区清点：仅生成上述正式恢复资料，无一次性探针或测试目录；本机私人备份不推送、不打入分享包。运行程序与用户数据库未修改，SQLite 使用只读源连接及 backup API 获取一致性快照。
- 并行写入提示：完成基线标签和本地备份后，工作区出现非本轮产生的审批/通知模块修改与临时测试文件（已观察到 `approval_hook.py`、`notification_store.py`、`_tmp_cc_hook_test.py`）；所有者未核实，原样保留、不执行、不加入本次提交。当前工作区因此不以干净作结；后续动画开发前须再次核对全部差异，必要时在隔离工作区继续，避免混入存档或误覆盖。（2026-10-16 晚核实：上述改动与临时文件属 Claude Code 审批提醒接入工作，已由上方任务记录并提交 `claude/cc-approval-reminder`；临时测试文件已删除，改动归属已明确；互动开发继续前先切回 `codex/interaction-30-32-34`。）

## 当前任务：第二版范围收敛（2026-10-16）

- 用户已确认：“ok这个安装教程这一块是搞定了”；N20 本轮安装教程与自动配置提示词按当前界面验收，未知客户端真实接入验证边界仍保留。
- 用户继续要求：“接下来看根据我的SOP继续执行吧”。已核对 `main` 与 `origin/main` 同步，基线 `bafd7c5`，接手时工作区干净。
- 沿用 Full 通道、本机管理 Web 架构及单线开发。第一版 N24/N25/N26/N31 已有完成与验收记录；“第二档大概率 D 组”仍是倾向，未逐项选定。
- [x] 恢复需求、待办、变更、架构与接口；确认 N43–N47 尚未进入实现。
- 选择历史：虹夏请求 `56f537d532b74ef6ac8dd2696833f177` 已回答“历史与来源”（N43/N44），助手已在原聊天复述；随后用户要求“我现在有些忘记那些功能选择是哪些了重新让我再筛选一下吧不用那么快做决定”。以此最新要求为准，原选择改为待重选，未进行 N43/N44 代码开发。
- [x] 重新整理原有 N24–N50 清单，区分第一版已完成四项与其余 23 项候选，保留原编号及工作量说明；先供聊天中比较，不再立即发出限时桌面选择。
- [x] 用户重新选定 N30/N32/N34，先完成稳定版 Git 与本地运行备份，再进入互动方案；其余未选候选保持 Could。
- [ ] 选定后记录 Must/Should、更新架构与接口，按最小可验证单元实现、隔离测试、内置浏览器验收、正式打包和 Git 收尾。

## 当前任务：复制提示词直接配置 MCP（2026-10-16）

- 用户要求：配置先实际保存到本机并显示准确位置；提示词带齐程序路径、配置内容和规则，复制给有本机文件操作能力的 AI 后由其完成接入，不再要求手动下载、填字段。
- 沿用 Full 通道及 Web 扩展，修复 N20 的接入流程；范围仅本机，不增加新的客户端适配或远程服务。
- [x] 按 Agent 档案生成独立接入文件，旧档案可补生成；GET 状态不写文件。
- [x] 动态生成包含真实路径、完整 MCP JSON 与规则的安装提示词；明确重载、权限和实际验证边界。
- [x] 修复清单空路径与 Work 插件实际位置；实际内置浏览器走通隔离新建和正式旧档案“接入步骤”，验证两处复制内容。
- [x] 隔离测试：39 项回归通过；实际生成的 `nijika-mcp.json` 启动正式 MCP EXE，stdio 握手与四工具发现通过，没有改动外部客户端配置。
- [x] 正式 EXE 已替换（2026-10-16 21:16，40,113,973 字节），桌宠与原生设置窗口重启成功；内置浏览器打开其实际端口验证已有 Claude code 档案补生成、真实路径与完整提示词复制（2127 字符）。
- [x] 接入指南、安装、架构、接口、需求与本轮记录已同步；本机运行及数据边界保持不变。
- [x] 两份 2026-10-16 分享包重建并检查 20 项白名单条目、安装包文件哈希和 Work 路径占位符；未含消息库、真实接入档案或临时诊断数据。源码凭据特征扫描与差异空白检查通过。
- [x] 实现与文档提交 `84c1e37` 已推送 `origin/main`；本条交付记录随收尾提交同步。
- 验收边界：接收方 AI 在未知客户端执行安装、新会话主动调用尚未代测，不把上述验证写成 Claude Code 已接通；需重载或本人授权时由接收方如实报告。
- 工作区清点：本轮隔离测试服务已停止；`diagnostics/auto-setup-acceptance/` 保留为新建档案/保存提示词的复现样本，`diagnostics/agent-auto-setup-production.png` 为正式 UI 验收截图，`diagnostics/build-auto-setup.log` 为构建记录，均忽略入 Git。`build/auto-setup-release/` 保留为与正式 EXE 核对的构建样本；自动审批审查拒绝了清理删除操作，仅返回策略阻止，未提供具体原因，实际文件未删除，不进入分享包。真实用户接入文件留在用户数据目录供后续复制，不进入分享包。

## 当前任务：向导列出 MCP 所需文件位置（2026-10-15）

- 用户原话：“MCP配置所需要的那些文件在哪个位置啊你得让他知道啊”。
- [x] `agent_setup.py` 新增 `client_files()`，按客户端列出 MCP 程序、客户端配置、主动提醒规则与可选技能的绝对路径，并标注已有/待写入/可选。
- [x] `plan()`、`apply()` 与 `/api/state` 返回 `needed_files`，已添加的伙伴卡片点“接入步骤”也能看到完整文件位置。
- [x] 向导第三步在示例提示词下新增“这套配置用到的文件和位置”清单：逐条显示类别、说明、完整路径与已有状态，每条可单独复制，另有“复制全部路径”。
- [x] `AGENT_SETUP.md` 增加 Codex / Work / DSH / 其他 MCP 客户端的文件位置对照表与服务名说明。
- [x] 验证：38 项回归通过；重建并替换 `dist/虹夏桌宠.exe`（2026-10-15 17:56，约 40 MB），重启后实测页面含文件清单容器与复制按钮、脚本含渲染函数、`/api/state` 对 Codex 档案返回 4 条真实绝对路径且状态正确；静态渲染确认排版清晰。

## 当前任务：Agent 向导步骤与示例提示词（2026-10-15）

- 用户原话：“Agent配置导入步骤是什么呀在这个软件的界面显示的并不清晰啊像我都没法跟着这个去操作”“如果有需要给AI客户端的提示词也最好是直接给一个例子让他能照搬去用”。
- 问题定位：旧向导只显示“应用并添加 / 导出配置”，没有说明应用之后在客户端要做什么，也没有可直接复制的验证提示词。
- [x] `agent_setup.py` 新增 `GUIDES` 与 `client_guide()`，为 Codex、Work、DSH、其他 MCP 客户端分别提供标题、编号步骤、示例提示词与注意事项；`plan()`、`apply()` 及 `/api/state` 的 Agent 档案都返回该指南。
- [x] 向导第三步新增“接下来请照这 N 步做”卡片：编号步骤、示例提示词代码块、“复制提示词”按钮与一条注意事项；提示词明确 `show_completion`、`request_decision` 的用法与“等待我点击”。
- [x] 每个已添加 Agent 卡片新增“接入步骤”按钮，随时重看该客户端步骤与提示词；打开时仅展示说明，不重复写配置。
- [x] 复制按钮在新版 WebView2 中直接用剪贴板 API，失败时回退到隐藏文本框复制；复制成功后按钮短暂显示“已复制 ✓”。
- [x] `AGENT_SETUP.md` 补充 Codex/DSH 通用提示词、Work 提示词与其他 MCP 客户端提示词，可直接粘贴给 AI。
- [x] 验证：13 项控制面板测试与 38 项全量回归通过；重建并替换 `dist/虹夏桌宠.exe`（2026-10-15 17:44，约 40 MB）后重启桌宠与设置窗口，实测页面含步骤容器与复制按钮、脚本含渲染函数与卡片入口、`/api/state` 对三个已添加 Agent 均返回指南；静态渲染确认排版清晰可读。

## 当前任务：第一版四项功能（N24/N25/N26/N31，2026-10-15）

- 用户原话：“咱这个是出版嘛咱分阶段去添加功能 现在我们第一版先添加24，25，26，31，从而让界面不再单调，后续我感兴趣的就还我后面再进行选择你把其他的需求填入文档就行 第二档大概率是把地主功能加入将它的主要功能加强”。
- 范围判定：本轮只做 N24 番茄钟、N25 久坐/喝水/护眼提醒、N26 今日便签、N31 好感度/陪伴天数；N27–N30、N32–N50 仅登记，不实现。
- [x] 新增 `companion_store.py`，与本机通知队列共用 SQLite；建立番茄钟、健康提醒、便签、好感度四组数据与校验。
- [x] `pet.py` 接入每秒陪伴轮询、到期气泡、头顶倒计时徽章、右键“开始/暂停专注”“结束这一轮”，点击角色记录好感度。
- [x] `control_panel.py` 新增 `/api/focus`、`/api/reminders`、`/api/notes` 三个本机接口，只绑定 `127.0.0.1`，沿用会话令牌与同源校验。
- [x] 设置中心新增“专注与提醒”“今日便签与陪伴”两页，导航、圆环倒计时、统计、提醒表单、免打扰、便签列表与陪伴阶段卡均已接真实数据。
- [x] 运行 `.venv\Scripts\python.exe -m unittest discover -s tests -q`：`Ran 38 tests ... OK`。
- [x] 实机验收：`tools/accept_companion.py` 驱动运行中的设置窗口，14 项检查全部通过（专注运行/暂停/继续/结束、非法时长拒绝、免打扰写入与还原、提醒间隔还原、便签新建/打勾/删除、好感度 +2 与完成计数 +1、陪伴天数与阶段可读）。
- [x] 界面实渲染：无头 Edge 输出 `diagnostics/page-focus.png` 与 `diagnostics/page-notes.png`，两页布局与真实数据正常（诊断图不入 Git）。
- [x] 复用构建产物：`dist/虹夏桌宠.exe`（2026-10-15 16:55，约 40 MB）随后与设置中心启动、心跳及本机 API 均正常。
- [x] 更新 `REQUIREMENTS.md`（第一版范围与四项验收记录）、`CHANGELOG.md`，并把“第二档大概率 D 组”记为待用户最终勾选的倾向，不是已确认范围。
- [x] `tools/accept_companion.py` 保留为可复用的实机验收脚本；一次性验收脚本与临时便签已清理。
- [x] 重新生成分享包：`tools/package_docs.py` 与 `tools/package_release.py` 均以 2026-10-15 重新输出；试用包清单核对后只含 `虹夏桌宠.exe`、`虹夏MCP-v2.exe`、`虹夏审批提醒.exe`，不再包含旧控制中心 EXE；试用包 SHA256 为 `1039096c3fe98bd3144def0d432aa90317838e8a4f988df193cc6978c3f0f04d`。
- [x] 敏感数据扫描：源码、脚本、配置模板与文档未发现真实密钥、私钥或令牌，命中的仅为 `YOUR_API_KEY_HERE` 占位符。
- [x] 提交并推送 `main`：`d76c915 Add phase 1 focus timer, break reminders, daily notes and companionship`。待用户为第二档勾选具体功能后再开新范围。

## 当前任务：单程序合并与功能对比选型（2026-10-15）

- 用户原话：“为什么要把红夏捉宠跟捉宠控制器独立成两个软件呢……这个控制器为什么功能这么少啊根据我的sop你应该去横向对比其他的桌虫界面还有哪些功能然后让我选择性添加呀”。
- [x] 合并为单一程序：`control_panel.py` 抽出 `run_panel()`，`虹夏桌宠.exe --control-panel` 打开设置窗口；`pet.py` 右键“设置中心 / 添加 Agent”改为启动自身；`build.ps1` 只产出一个桌宠 EXE（内置控制 UI 与 webview 数据）。
- [x] 删除废弃的 `dist/虹夏控制中心.exe`，桌面快捷方式改为“虹夏桌宠”+“虹夏桌宠设置”，开机自启仍指向 `dist/虹夏桌宠.exe`。
- [x] 实测：单文件 EXE 启动桌宠心跳正常（`supports_control=true`、`applied_revision=2`），`--control-panel` 窗口以同一 EXE 打开并完整渲染设置界面；29 项回归通过。
- [x] 按 SOP 阶段 1 横向对比 10 个同类桌宠，登记 N24–N50 候选功能（见 `REQUIREMENTS.md`）。
- [ ] 等待用户从 N24–N50 中勾选要做的项；勾选后分配 Must/Should/Could 并进入实现。
- [ ] 合并后的分享包需重新生成（试用包文件清单已去掉控制中心 EXE）；安装脚本隔离验收待补。

## 当前任务：管理界面与快捷添加 Agent（2026-10-15）

- 目标：新增 Agent 接入向导、皮肤替换、动作设置和投喂入口；优先完成 Agent 的便捷接入闭环。
- 已恢复：工作区为 `D:\deepseekharnes work\提示功能作用的桌宠`，分支 `main`，基线提交 `5e52fa5`，开工前工作区干净；此前普通通知与 Codex CLI 权限提醒的验收记录保留。
- [x] 读取需求、待办、最新变更、架构、接口及现有安装脚本；加载用户指定 SOP、虹夏交互 skill 与 Web 扩展。
- [x] 核对成熟桌宠 VPet 官方仓库的动画、模组、主题与设置模块，登记增量需求 N20–N23。
- [x] 用户在虹夏选择“独立设置窗口”；采用 pywebview/WebView2 + 本机管理服务，登记模块和接口。
- [x] MVU1 初版：管理面板、本机管理 API、WebView2 独立窗口及真实心跳状态。
- [x] MVU2 初版：Agent 选择、检测、预览、备份写入、测试提醒与配置导出；Codex/DSH 的隔离目录真实浏览器操作通过。
- [x] MVU3 初版：透明 PNG / 九帧 ZIP 导入、切换与默认恢复，动作设置持久化和桌宠轮询应用；可配置投喂展示。
- [x] 内置浏览器实际测试导航、Codex/DSH 表单、错误目录拦截、设置保存与刷新、皮肤导入切换和支持链接保存；面板发送 → 原生气泡显示 → 自动化实际点击 → 面板显示“本机测试已点击”通过。
- [x] 最终打包验收与正式入口整理：正式 `dist/虹夏控制中心.exe` 已启动复验（PrintWindow 实际渲染出完整 Agent 接入界面），正式 `dist/虹夏桌宠.exe` 已用含设置降级与缺失皮肤检查的源码重建、启动，心跳上报 `supports_control=true`，并通过本机 API 验证设置实时同步（角色宽 320→380→320，`applied_revision` 0→1→2）。
- [x] 同步工程文档、敏感信息检查及本轮产物清点；两份分享 ZIP 已按最终产物重建。
- [x] 桌面入口：`虹夏桌宠.lnk`、`虹夏控制中心.lnk` 均指向 `dist` 正式产物，开机启动项指向同一桌宠 EXE。
- [x] Git 保存：本轮增量提交到 `codex/control-panel` 并推送，随后快进合并到 `main` 并推送 `926a329`。
- 未提供：真实投喂图片与新的时装素材；产品提供导入与配置入口，不伪造这些素材。

### 中断接手检查点（2026-10-15，用户提示额度不足）

- 当前分支 `main`，起点为 `5e52fa5`；本轮增量已提交为 `fa62cd9`、`926a329` 并推送到 `origin/main`。下一轮直接基于 `main` 继续即可。
- 用户已确认：虹夏请求 `ee422de2d45a4bb293ee139f76bb2b3c` 选择“独立设置窗口”，已在原聊天复述；没有未解决的方案选择，不要重新询问架构。
- SOP：需求、架构、开发、质检与交付均已完成本轮增量；新增编号 N20–N23，原角色/MCP/审批链路保留。
- 主要新增：`control_panel.py`（本机 API / 独立窗口）、`agent_setup.py`（接入适配器）、`control_store.py`（设置和皮肤）、`control-ui/`、`tests/test_control_panel.py`、`requirements-lock.txt`。`pet.py` 接入设置轮询与右键控制中心；构建及试用包脚本已纳入第四个 EXE。
- 最新源码验证：中断后补跑 29 项 unittest 全部通过，`git diff --check` 通过；此前 `pip check` 通过。Work 适配器的 CLI 调用已用 mock 检查隔离 home、参数及插件清单，**未在新真实 Work 任务中验收**。不得把本机面板测试当外部 Agent 的自主调用验收。
- 视觉证据：`art/control-panel-preview.jpg` 是内置浏览器对实际页面的完整截图，使用隔离验收数据。浏览器测试服务为 `http://127.0.0.1:53180`，目录 `diagnostics/control-panel-20261015/`，该目录不入 Git；另有源代码独立窗口及 `dist-next/虹夏控制中心.exe` 的隔离窗口被启动，下一轮先核对是否仍存活。
- 构建状态：最终 `dist/虹夏控制中心.exe` 已构建并启动复验通过，日志 `diagnostics/control-panel-final-build.log`；正式 `dist/虹夏桌宠.exe` 已用最后源码重建并复验，心跳含 `supports_control=true` 与正确 `applied_revision`。MCP 与审批程序源码本轮未修改，正在运行的旧 MCP 会话保持不动。
- 收尾完成项：桌面“虹夏控制中心”快捷方式已建立并指向正式产物；`dist-next/` 暂存 EXE 的残留进程已关闭、目录已清理；过期检查点中的“暂存窗口可能仍存活”不再适用。
- 本轮未覆盖：真实 Work 任务中的自主调用，以及公开分发所需素材授权，分别记录在下方待办。
- 环境约束：只绑定 `127.0.0.1`，不加公网、不读模型密钥、不替用户信任 hook。用户已明确希望用虹夏通知；长成果最终回话前只发一次完成提醒。

- [x] 制作 Windows 私下试用安装包，去除发送者路径与本地消息库；隔离测试桌宠、DSH、Codex/Work 安装流程与 Work MCP 握手。
- [ ] 若计划公开发行，先取得或替换角色与图标素材的再分发权，并补充明确的软件/素材许可证。

2026-10-09 收尾验收：用户确认当前桌宠效果可以接受；本轮进入文档归档与本地提交。下列未勾选项仍是后续工作，不因本次验收自动视为完成。

更新触发：2026-10-07 用户要求按 SOP_Core 回顾进度并展示当前桌宠。

- [x] 核对工作区路径、旧进程及内容，关闭旧桌宠，清空旧工程和缓存。
- [x] 恢复旧需求与否决记录，选定 2D 立绘方案及本轮范围。
- [x] 生成完整坐姿角色图、八种表情及眨眼帧；实际窗口截图已审阅。
- [x] 建立透明桌面程序；上一轮打包版已实际启动，点击、拖动和右键菜单可用。
- [x] 打包便携版，实际启动并检查窗口。
- [x] 加入待机呼吸/摇摆、点击弹跳、拖动倾斜，以及动态强度菜单。
- [x] 将离散动作帧改为连续变形；当前机器默认/大号帧间隔中位数分别为 15.8/15.6 毫秒。
- [x] 重新打包并实测点击、拖动、双击、动态强度、大小切换、退出与重新启动。
- [x] 清点交付内容、扫描敏感信息，完成安装说明。

## 本轮 Git 交付

- [x] 核对需求、待办、变更、架构、接口、运行说明；修正实际完成状态和源码仓库的构建步骤。
- [x] 初始化本地 Git 仓库；源码、九张角色图、预览和文档入库，`dist/` 与构建缓存忽略。
- [x] 获取远程仓库地址与公开范围，核对远程已有内容后推送至私有 `CY-YI/nijika-desktop-pet`。

## 后续范围

- [ ] N5：如用户需要，再增加本地状态记忆并在其他桌面缩放设置下实测。
- [x] 用户选择 Codex 作为首个真实 MCP 客户端；其他 Agent 后续再做。
- [x] DSH desktop/web 本机配置安装虹夏 MCP 与技能；合成配置及隔离 MCP 回传通过。
- [x] 重启 DSH 桌面客户端，确认 DSH host 启动虹夏 MCP 子进程。
- [x] 新 DSH 会话自主调用虹夏并显示带 DSH 来源的选择气泡；较晚点击已写入消息库。
- [ ] 在新 DSH 会话中复测连续 45 秒等待及原聊天中的点击读回；本轮用户操作窗口时停止了界面接管。
- [ ] 若要求超出等待上限后仍无需发聊天消息就自动恢复，实现 DSH 主机侧事件桥接；现有 stdio MCP 只保存晚到回复，不能唤醒已结束任务。

## 工作区清点

`tools/benchmark_motion.py` 与 `tools/probe_window_fps.py` 保留为持续性能回归工具；`tools/inspect_window.py` 保留用于实际窗口检查；`tools/make_motion_preview.py` 和 `tools/make_bubble_preview.py` 分别重建动画与气泡预览。`art/motion-preview.gif` 与 `art/bubble-preview.png` 是可审阅的交付材料。`dist/` 仅供本机运行，Git 忽略它；构建缓存和一次性对比图已清理。未发现需要保留的临时日志或草稿目录。

## 气泡与桌面提醒（2026-09-26）

- [x] 绘制可读的透明气泡，随桌宠移动，支持关闭与自动收起日常话语。
- [x] 加入少量日常台词及菜单开关，保留原有表情和动态。
- [x] 加入明确标注为演示的 Agent 待确认/选择提醒，桌面可点击操作但不向真实 Agent 发送。
- [x] 更新架构、接口、运行说明并重新打包；实测气泡、按钮、拖动、退出及性能。
- [x] 记录用户决定：本轮只做气泡与本地演示，日常话语偶尔出现、以安静为主。
- [x] Git 远程仓库已配置并完成推送。

## 提醒与权限验收（2026-10-11）

- [x] 普通提醒现场显示与 MCP 点击回传；用户选择“显示正常”。
- [x] 定位 AppData 重定向造成不同队列，统一默认路径并兼容旧会话回复。
- [x] 独立通知轮询、气泡显示与位置恢复、错误重试及本机运行诊断。
- [x] 实现 Codex 审批事件通知、去重与完成后收起；气泡回执不授予命令权限。
- [x] 本人审阅并信任两项 hook；只读接口确认均已信任、启用。独立 Codex CLI 在 `on-request` / `read-only` 下产生真实审批卡，虹夏自动提醒，用户点击“知道了”并记录回执；原审批仍等待授权，随后取消申请，未创建测试文件。本项验收覆盖本机 Codex CLI，不请求审批的任务不会触发该事件。

## 进度复核（2026-10-07）

- [x] 核对需求、待办、变更记录、源码、可执行文件与 Git 状态；在当前电脑重新启动打包版。
- [ ] 在可用的桌面操作通道中复测本次重启后的全部按钮；本轮桌面操作内核未能启动，历史交互测试记录保留在变更记录中。

## 真实 Codex MCP 提醒（2026-10-07）

- [x] 查出桌面实际运行的 EXE 早于气泡重显源码，并修复窗口类重复注册错误；2026-10-09 替换 EXE 后在真实桌面进程中验证气泡被隐藏或关闭均能自动恢复。
- [ ] 为 MCP 增加桌宠实际显示回执，使调用者能区分“队列已接收”和“桌面已显示”；当前 `pending` 仍只表示排队。

- [x] 推荐选项的 MCP 字段、消息库保存和气泡显示通过隔离测试及预览。
- [x] Codex/Work skill 要求点击后在原聊天记录中写明选择；待处理请求复用 ID，避免重复题。
- [x] 气泡被隐藏但问题仍待处理时自动恢复显示；新版桌宠已重启并确认主窗口可见。
- [ ] 用一条新的真实 Codex 任务验收“桌面点击后原聊天出现选择记录”；该行为依赖 Agent 保持等待并继续输出。

- [x] 用本机队列连接 Codex MCP 工具与桌宠，显示来源、任务与选项简介。
- [x] 验证点击回传、关闭状态、排队和重启后的消息可读性。
- [x] 配置 Codex 本机 MCP；独立 Codex CLI 会话已调用，桌面应用的新任务也已自主发出真实完成提醒。
- [x] 重建桌宠与 MCP 双程序；打包版桌面显示、点击回传和退出通过隔离测试。
- [x] 编写并安装 `nijika-desktop-dialog` skill，强制整理选择题的名称和一句说明。
- [x] 经用户明确授权，为本机四个桌宠 MCP 工具设置逐工具免审批；无临时放行参数的 Codex CLI 调用已通过。
- [x] 独立 Codex CLI 会话把含糊 A/B 改写成有名称和简介的选项；`request_decision` 与 `get_reply` 实测通过。
- [x] 普通决策与成果待审阅任务均在独立 Codex CLI 会话中自主触发桌面提醒；用户在桌面点击后，Agent 读回所选内容。
- [x] 新开的 Codex 桌面应用任务已自主触发 `show_completion`，桌宠气泡实际显示；该测试任务已归档。
- [x] 用户在真实桌宠气泡中选择“效果满意”；打包版 MCP 的 `wait_for_reply` 读回选项及说明，待处理队列清空。
- [ ] 用新的 Codex 桌面应用任务实测短成果全文在气泡中“接受／修改”的自主调用与继续执行；当前聊天的 MCP 工具列表没有热刷新。
- [x] 为桌面客户端 Work 准备并安装本机插件，提供独立命名的 MCP 服务与决策 skill；确认插件在项目外仍显示已安装、已启用，安装缓存副本可实际启动并列出四个工具，独立 Codex 会话仅经插件调用成功。
- [x] 当前 Codex 会话仅经已安装插件向真实桌宠发送选择题；用户在桌面点击，插件工具读回 `answered` 与选项简介。
- [x] Codex 全局技能和 Work 插件 0.1.5 同步连续等待与会话恢复规则；Work 安装缓存及隔离 MCP 启动检查通过。
- [ ] 在新 Codex 与本机 Work 会话中分别验收超过一次等待后仍继续等待，以及晚到点击在恢复会话时读回。
- [ ] 重启桌面客户端，在本机运行的 Work 新任务中确认插件工具可见，并实测桌面选择点击后 Work 读回结果；当前会话无法热刷新或自动验证另一会话的工具列表。
- [ ] 若以后要让云端 Work 使用桌宠，设计经过鉴权的远程 HTTPS MCP 桥接及网络安全边界；本轮仅接本机 Work。
- [x] 更新安装与使用说明、扫描本机数据与构建产物，完成本地 Git 提交。
