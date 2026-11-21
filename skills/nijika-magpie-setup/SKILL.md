---
name: nijika-magpie-setup
description: Use MAGPIE Library to add or verify an explicitly requested local Agent's Nijika desktop pet connection and distribute its reminder rules or Skill. Use for setup, not for routine reminders.
---

# 通过 MAGPIE 接入虹夏

1. 确认用户要接入的客户端、所在软件和作用域。负责操作的 AI 可以运行在另一个客户端。读取虹夏设置中心的接入提示词以获取安装路径、通用提醒规则和统一提醒技能路径。确认是同一台 Windows 电脑；必要时核对当前安装根目录下的 `dist/虹夏MCP-v2/虹夏MCP-v2.exe` 及同级 `_internal`。
2. 在 MAGPIE Library 核对目标分发，同时核对实际生效的 MCP 和规则。已有相同分发则复用。对于用户已批准的迁移，备份并确认旧条目确属虹夏，确保宿主重载时只启用一条连接。归属不明或目标不支持时保留可用入口并报告。仅更换同一客户端内的模型时，沿用现有分发。
3. 对未接入且受支持的目标，用已安装的 MAGPIE Library 界面或该版本明确支持的管理命令操作。复用唯一的 `nijika-pet` stdio 条目，新增目标分发，保留现有目标。只有明确缺少虹夏条目时才新增一份，指向当前本机 onedir 程序，使用 `NIJIKA_AGENT_NAME=auto`。不要在共享条目中填入单个客户端的 `NIJIKA_HOST_NAME` 或 `NIJIKA_PROFILE_ID`。管理入口不可用或目标不支持时，说明能确认的状态和具体所缺动作；用户指定 MAGPIE 时不要改走直连。
4. 在 Library 的 Skills 中分发同一份 `nijika-agent-dialog`。宿主需要持久指令才能每轮加载技能时，在 Instructions 中只分发触发规则。MCP、Skills 和 Instructions 的目标可能不同；有技能不等于已接通 MCP。MAGPIE 无法写入的宿主保留它现有的入口，提醒正文沿用统一技能。不要为此添加新的直连配置。此接入 Skill 和整段提示词只交给负责配置的 AI。
5. 让目标通过其支持的方式加载变更，在目标的新任务中发现工具并尝试一次 `show_completion`，核对软件和 Agent 标签。工具支持来源参数且自动来源不充分时填实际身份和宿主，多模型宿主不猜模型。报告分发、工具发现、消息排队和桌面显示这几个实际到达的状态。没有看到桌面时只报告排队。权限审批与结束事件由宿主单独验收；只有用户要求时才核对相关集成，信任交由本人。

MAGPIE 管理入口以本机版本与 [Library 文档](https://usemagpie.ai/docs/library) 为准。缺少可用管理入口时提供具体的 Library 条目和目标，不手改库文件模拟同步。
