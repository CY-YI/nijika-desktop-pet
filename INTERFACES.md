# 内部接口

## 本机管理接口（2026-10-15 设计）

所有 `/api/` 请求须携带 `X-Nijika-Token`；令牌只在管理服务运行期间有效，未知 Host、其他 Origin 与跨域预检均拒绝。JSON 错误使用 `{error: 可读原因}`，不返回堆栈或完整客户端配置。路径均为同源相对地址。

| 接口 | 输入 | 输出或效果 |
| --- | --- | --- |
| `GET /api/state` | 无 | 桌宠心跳摘要、已登记 Agent、设置、皮肤及投喂展示配置；不含现有客户端的密钥 |
| `POST /api/agents/plan` | 客户端、显示名、可选配置根目录 | 检测结果、计划 ID、具体文件与操作，尚不写配置 |
| `POST /api/agents/apply` | 计划 ID | 复核旧内容、备份后应用；返回已配置/需重启等实际状态 |
| `POST /api/agents/prepare` | 已登记档案 `id` | 补生成或更新专属接入文件，返回带完整自动配置提示词及真实文件路径的 `agent`；不修改外部客户端配置 |
| `POST /api/agents/test` | 档案 ID | 发带该来源名的本机测试通知；返回请求 ID，明确此步骤不证明外部 Agent 已调用 MCP |
| `GET /api/notices/{id}` | 请求 ID | 队列回执及当前渲染心跳是否正在显示此 ID |
| `POST /api/agents/remove` | 档案 ID | 移除管理面板档案；不擅自删除外部客户端配置 |
| `POST /api/settings` | 已知设置字段 | 原子保存设置；桌宠轮询应用，回传应用版本 |
| `POST /api/skins/import` | 有限大小的 PNG 或皮肤 ZIP | 校验并导入本机图片包；仅含图片及清单，不能含脚本 |
| `POST /api/support` | 作者名、说明、可选 HTTPS 支持链接 | 保存本机投喂展示配置，不发起支付 |
| `POST /api/support/image` | PNG/JPEG 图片 | 验证、转存收款展示图，尚无图片时显示未配置 |
| `POST /api/focus` | `action` = start/pause/resume/reset/skip；configure 时附 `focus_minutes`、`break_minutes` | 返回番茄钟视图（状态、模式、剩余秒数、今日完成数与专注秒数）；时长限 1–180 整数分钟 |
| `POST /api/reminders` | `enabled`、`sedentary_minutes`、`water_minutes`、`eye_minutes`（5–240）；或单独 `pause_minutes`（0–480） | 保存健康提醒配置或写入/取消免打扰，返回当前状态；改间隔会重置对应的起始时间 |
| `POST /api/notes` | `action` = add/toggle/remove，add 附 `text`，toggle/remove 附 `id` | 新增或更新当天便签；每天最多 20 条、每条约 1–120 字；打勾只在首次完成时加好感度 |

Agent 配置预览具有有效期；文件在预览后发生变化时拒绝覆盖并要求重新检测。`plan`、`apply` 的档案及 `state.agents[]` 包含 `guide`、`needed_files`、`bundle_directory`、`bundle_ready`；`guide.prompt` 为自包含安装提示词，`needed_files[].exists` 由实际文件检查得到。GET 状态只读；新档案在 apply、旧档案在明确调用 prepare 后生成接入文件。文件保留供后续接入，移除档案不清除外部配置或这些文件。新增字段与最终路由以实现和测试为准，未实现项不能记为已交付。

决策选项可为其中一项设置 recommended: true，并在简介中说明推荐理由。pending 只表示消息已进入本机队列，不能证明气泡可见；等待时复用原 request_id，避免重复问题。Agent 收到 answered 后应在原聊天中确认所选项，再继续任务。桌宠只保存点击结果，不会自行向 Codex 聊天发送一条新的用户消息。

更新触发：2026-09-26 改为 Win32 本地桌宠。

| 接口 | 输入 | 输出或效果 |
| --- | --- | --- |
| `SpriteSet(width, height)` | `assets/sprites/` 下八种表情及 `blink.png` | 缩放后的角色图、复用的透明内存位图 |
| `PetWindow.show_pose(name, **pose)` | 表情名与连续位移、角度、缩放、星光强度 | 更新同一桌面窗口，不启动新窗口 |
| 左键单击 | 可见角色像素 | 循环切换八种常驻表情 |
| 左键拖动 | 可见角色像素 | 移动桌宠窗口 |
| 双击 | 可见角色像素 | 切到加油表情并连续弹跳 |
| 右键菜单 | 可见角色像素 | 选择表情、大小、动态强度、闲聊开关、手动说话、两种演示提醒或退出 |
| 定时器 | 好奇表情与随机时间 | 短暂显示 `blink` 帧；其他常驻表情暂无自动眨眼 |
| 动画定时器 | 当前表情、单调时钟、动态强度、交互状态 | 连续计算待机呼吸/摇摆、偶尔自主弹跳、点击弹跳或拖动倾斜并绘制透明位图 |
| 动态菜单 | 轻柔、活泼、关闭 | 立即调整动画幅度与频率，不写入用户配置 |
| `BubbleNotice` / `BubbleOverlay.show` | 标题、正文、按钮、显示时长、角色位置 | 在角色上方绘制独立透明气泡 |
| 日常话语 | 点击角色、菜单手动触发或低频定时 | 显示短句；约数秒后自动收起，也可点击关闭 |
| 演示 Agent 提醒 | 菜单中的完成提醒或选择请求 | 显示 Agent 名称、待办和两项操作；一直保留到关闭或选择 |
| 演示按钮回调 | 所选按钮 | 仅显示本地结果，不向任何 Agent 发送或保存 |

原本只有本地演示按钮；2026-10-07 新增以下真实 MCP 接口。仍无 HTTP、WebSocket 或第三方账号。

## Codex MCP 接口（2026-10-07 已接入）

| 工具 | 输入 | 结果 |
| --- | --- | --- |
| `show_completion` | 任务标题、简短结果 | 生成单按钮“知道了”的完成提醒；仅表示收到，不表示批准，返回 `request_id` |
| `request_decision` | 任务标题、最多 80 字且最多三段的问题、2–3 个 `label` + `description` 选项 | 生成可在桌宠直接完成的选择，短成果可连正文一同呈现；返回 `request_id`，输入无效时返回 `status=invalid` 与修正提示 |
| `get_reply` | `request_id` | 返回 `pending` / `answered` / `dismissed` / `expired` / `not_found` 与所选名称、简介 |
| `wait_for_reply` | `request_id`、最长 60 秒 | 等待桌面点击；超时仍返回 `pending`，可再次调用 |

本阶段在同一用户机器上通过 stdio 和 SQLite 交换，不提供 HTTP/WebSocket、账户或第三方传输。Agent 来源名称由 MCP 服务启动环境决定，输入内容限制长度并作为纯文本绘制。`request_decision` 不接受只有 A/B 名称的字符串列表；每个选项名称最多占 20 个显示列，且必须有 6–48 字的一句话简介。短结果能放入问题正文时，Agent 应调用 `request_decision`、等候选择并在同一任务中继续，不重复要求聊天确认；复杂审阅才调用 `show_completion`。`show_completion` 与 `request_decision` 的输入无效时返回 `status=invalid`、空 `request_id` 和可修正的错误说明。示例按钮仍只影响本地演示；带 `request_id` 的真实提醒才写回队列。MCP 客户端是否继续等待取决于该客户端的调用流程；桌宠不会独立唤醒已经结束的 Agent 会话。

## 本机运行与审批事件（2026-10-11）

- 默认数据库：`%USERPROFILE%\.nijika-desktop-pet\notifications.sqlite3`。`NIJIKA_PET_DB_PATH` 仍可显式覆盖；覆盖时禁用旧库桥接。
- `LegacyQueueBridge.sync()`：旧库待处理请求复制到新库并保留 ID；新库的点击或关闭结果写回对应旧库。桥接记录单独存在 `legacy_origins` 表，不改变原通知的九列表结构。
- `renderer-status.json`：桌宠每约三秒原子更新进程 ID、时间、实际数据库路径/文件标识、当前通知 ID、气泡可见性和矩形。供本机诊断使用，不是 MCP 显示回执或用户确认。
- 审批程序 stdin：Codex JSON 事件，最多 1 MiB；`PermissionRequest` 创建 `kind=approval` 的优先通知，`PostToolUse` 收起匹配的未处理通知并标记 `resolved`。`notice_tags` 保存事件摘要哈希、种类和优先级，不存储原始命令。
- 审批程序 stdout：始终为空，退出码 0，不输出授权决定。格式错误仅在 stderr 写固定错误提示，不阻断 Codex 原审批流程。“知道了”只产生通知回执。

审批 hook 要求本人审阅并信任；当前任务不请求审批时不会有该事件。真实平台审批验收与模拟输入测试分开记录，配置步骤见 `AGENT_SETUP.md`。
