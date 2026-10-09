# DSH 本机接入

本目录把现有 `dist/虹夏MCP-v2.exe` 注册为 DeepSeek Harness（DSH）的 stdio MCP 工具，并安装 `nijika-dsh-dialog` 技能。DSH Agent 需要用户做短决策或审阅成果时，可调用 `mcp__nijika_pet__request_decision`；长成果用 `mcp__nijika_pet__show_completion` 提醒。选择由桌宠气泡回传给发起请求的 DSH 会话。桌宠与 DSH 必须在同一台 Windows 用户会话中运行；无需新服务或网络端口。

在本机完成构建后运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\integrations\dsh\install.ps1
```

默认写入 `%USERPROFILE%\.dsh\profiles\desktop\cordis.patch.yml` 和 `web\cordis.patch.yml`，同时复制技能到 `%USERPROFILE%\.dsh\skills\nijika-dsh-dialog\SKILL.md`，并在 `%USERPROFILE%\.dsh\AGENTS.md` 中加入触发规则。已有配置保留；修改过的配置会先生成 `.bak-nijika-时间戳` 备份。重复运行不会复制同一配置块。若只需一个配置，可用 `-Profiles desktop` 或 `-Profiles web`。项目路径改变或 MCP EXE 重建后，请重跑安装脚本。

安装后重启 DSH 桌面客户端或重开 DSH web 服务，并在**新 DSH 会话**中测试；已运行的会话未必热加载 MCP 工具和全局说明。保持 `dist/虹夏桌宠.exe` 运行，测试时让 DSH 发出一个真正需要选择的简短问题，检查桌面气泡、点击和 DSH 聊天中的读回。`pending` 只表示消息入队，不代表已显示或已确认。

DSH 的 MCP 客户端对单次工具调用默认设有 60 秒超时。技能因此要求以同一请求 ID 连续进行 45 秒等待，最多约九分钟；一次等待返回 `pending` 不应结束任务。如果 DSH 会话被中断，或等待上限后已经结束，桌宠仍会保存较晚的点击，但当前 stdio MCP **不能独立唤醒已结束的 DSH 任务**。在原 DSH 会话发送“继续”或“我回复了”，新的技能规则会先调用 `get_reply` 读取旧请求，再继续原任务；不要重发同一道选择题。要实现无时限、无需补发聊天消息的自动恢复，还需要 DSH 主机侧事件桥接，目前未实现。

可用 `dsh --profile web --dump-config` 检查合成配置是否含 `mcp-nijika-pet`。项目维护者可运行 `.\.venv\Scripts\python.exe tools\smoke_packaged_mcp.py` 在隔离消息库中验证 MCP 握手和点击回传；该测试本身不会触发正在运行的桌宠。当前 DSH 登录状态或模型权限仍由 DSH 自己管理。
