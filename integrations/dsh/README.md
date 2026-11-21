# DSH 本机接入

普通提醒通过 [MAGPIE Library](../../AGENT_SETUP.md) 分发共享 MCP 与统一提醒 Skill。若已有旧直连，先核对归属并迁移，避免两条连接同时生效。

## 实时结束事件（2026-10-31）

可选的 `-LifecycleOnly` 模式会在每个 profile 添加独立 `NIJIKA-DSH-LIFECYCLE` 块，通过 `lifecycle-bridge.mjs` 把宿主实时事件交给 `虹夏审批提醒.exe --lifecycle`。Codex 与 DSH 共用安全摘要和去重，无需靠模型记住调用来触发该补发入口。核对宿主接口版本为 `0.2.1-rc.2`（本机桌面）和 `0.2.1-rc.3`（CLI），其他版本需独立验收。

转接只处理本进程实时根会话的真实用户轮次正常结束，不扫描历史，不处理注入上下文或子任务。同轮收到成功的虹夏通知工具回执后不重复。DSH 重启、新会话后再验证；可用模块不等于用户当前配置已启用。MAGPIE 管理项由其维护者审阅，虹夏向导不擅自安装第二套服务或模块。

已有 MCP 由 MAGPIE 等工具管理时，维护者可审阅完整包中的脚本后，只添加/更新独立事件块：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\integrations\dsh\install.ps1 -LifecycleOnly
```

此模式保留 MCP、MAGPIE 管理项、全局规则与技能；默认检查两个 profile，也可加 `-Profiles desktop`。重复运行只替换同一标记块，不新增副本。先备份、拒绝损坏/重复标记，重启宿主后再验收。不要为了接事件再安装一份 MCP。

维护者测试：`node --test tests/dsh_lifecycle.test.mjs`（可通过 `NIJIKA_DSH_TEST_MODULES` 指向 DSH 内部模块目录验证真实 SessionStore）；`node tools/smoke_dsh_lifecycle.mjs <DSH内部模块目录> <审批程序.exe> <Python.exe>` 检查真实事件组件到冻结程序链路，仍不代替用户运行中的模型会话和气泡观察。

## 验证与来源

DSH 默认来源固定为 `Agent · DSH`，因为同一宿主可以切换多家模型。标准连接应省略 MCP 的单次 `agent_name` 和 `software` 参数；服务端也会把误传的 `Codex · DSH`、`DSH · DSH`、`WorkBuddy · DSH` 纠正为 `Agent · DSH`。明确知道真实模型时才使用具体名称，例如 `DeepSeek · DSH`。

项目移动后，在 MAGPIE Library 修改共享命令路径并同步。出现旧的 `NIJIKA-DSH-MCP` 标记或重复服务时，备份后核对实际加载项；不要重新运行旧直连接入流程。

安装后重启 DSH 桌面客户端或重开 DSH web 服务，并在**新 DSH 会话**中测试；已运行的会话未必热加载 MCP 工具和全局说明。保持 `dist/虹夏桌宠.exe` 运行，测试时让 DSH 发出一个真正需要选择的简短问题，检查桌面气泡、点击和 DSH 聊天中的读回。`pending` 只表示消息入队，不代表已显示或已确认。

DSH 的 MCP 客户端对单次工具调用默认设有 60 秒超时。技能因此要求以同一请求 ID 连续进行 45 秒等待，最多约九分钟；一次等待返回 `pending` 不应结束任务。如果 DSH 会话被中断，或等待上限后已经结束，桌宠仍会保存较晚的点击，但当前 stdio MCP **不能独立唤醒已结束的 DSH 任务**。在原 DSH 会话发送“继续”或“我回复了”，新的技能规则会先调用 `get_reply` 读取旧请求，再继续原任务；不要重发同一道选择题。要实现无时限、无需补发聊天消息的自动恢复，还需要 DSH 主机侧事件桥接，目前未实现。

可用 `dsh --profile web --dump-config` 检查合成配置是否含 `mcp-nijika-pet`。项目维护者可运行 `.\.venv\Scripts\python.exe tools\smoke_packaged_mcp.py` 在隔离消息库中验证 MCP 握手和点击回传；该测试本身不会触发正在运行的桌宠。当前 DSH 登录状态或模型权限仍由 DSH 自己管理。
