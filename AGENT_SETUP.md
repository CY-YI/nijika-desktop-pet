# 接入 Agent：Codex、ChatGPT Work、DSH 与其他本机客户端

虹夏由两个 Windows 程序组成：`虹夏桌宠.exe` 负责桌面显示，`虹夏MCP-v2.exe` 是 Agent 按需启动的 stdio MCP 服务。两者须在**同一台 Windows 10/11 x64 电脑、同一用户会话**中运行；只需手动启动桌宠，不要手动双击 MCP 程序。MCP 不开放网络端口，普通云端聊天无法直接调用本机 EXE。

## 已收到 Windows 私下试用 ZIP

完整解压 ZIP，在解压目录打开 PowerShell。先安装桌宠：

```powershell
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1
```

已有相应 Agent 客户端时，退出桌宠和旧任务，再按需运行以下命令；也可以把 `-Codex -Work -Dsh` 合并在同一次安装中：

```powershell
# Codex：注册 MCP、安装技能，并添加全局触发规则
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1 -Codex -NoLaunch

# ChatGPT 桌面客户端的本机 Work：安装本地插件和技能
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1 -Work -NoLaunch

# DeepSeek Harness：配置 desktop/web、安装技能与触发规则
powershell -ExecutionPolicy Bypass -File .\distribution\install.ps1 -Dsh -NoLaunch
```

`-Codex` 和 `-Work` 要求 PowerShell 能找到 `codex` 命令；`-Work` 还要求能找到 `python.exe`。`-Dsh` 要求该用户已经初始化 `%USERPROFILE%\.dsh`。安装脚本默认将程序放到 `%LOCALAPPDATA%\NijikaDesktopPet\app`，因此解压目录搬走后配置仍有效。想开机启动桌宠，可在首次安装命令后加 `-AutoStart`。

## 从 Git 源码构建

先按 [INSTALL.md](INSTALL.md) 安装 Python 依赖并运行 `build.ps1`，确认 `dist/` 中生成两个 EXE。桌宠仍需单独启动。

### Codex

在项目根目录运行：

```powershell
$mcpExe = (Resolve-Path -LiteralPath '.\dist\虹夏MCP-v2.exe').Path
codex mcp add nijika-pet -- $mcpExe
codex mcp get nijika-pet

$skillDir = Join-Path $env:USERPROFILE '.codex\skills\nijika-desktop-dialog'
New-Item -ItemType Directory -Path $skillDir -Force | Out-Null
Copy-Item -LiteralPath '.\skills\nijika-desktop-dialog\SKILL.md' -Destination $skillDir -Force
```

把 [Codex 全局触发规则](distribution/codex-global-instructions.txt) 合并到 `%USERPROFILE%\.codex\AGENTS.md`，可使其他工程的新 Codex 任务也知道何时使用桌宠；本仓库的 `AGENTS.md` 只覆盖本仓库。若已存在同名 `nijika-pet` 服务，先用 `codex mcp get nijika-pet` 核对旧路径，不要重复添加。新开 Codex 任务后再测试；旧任务不保证热加载工具和技能。

### ChatGPT 桌面客户端 Work（本机任务）

源码插件位于 `plugins/nijika-work-local/`，`mcp.json` 使用可移植标记，由启动脚本查找本项目的 `dist/虹夏MCP-v2.exe`、`NIJIKA_MCP_EXE` 指定的程序，或默认安装目录。确保 `python.exe` 和 `codex` 都能从 PowerShell 找到，再从项目根目录运行：

```powershell
codex plugin marketplace add . --json
codex plugin add nijika-work-local@nijika-local --json
codex plugin list --marketplace nijika-local --json
```

确认插件为 `installed: true`、`enabled: true`，重启 ChatGPT 桌面客户端，然后在**本机运行的新 Work 任务**中测试。普通聊天和云端 Work 不会自动获得本机 stdio MCP 工具。插件文件更新后也要刷新安装并重启客户端；当前已打开任务不保证热更新。

### DeepSeek Harness（DSH）

DSH 已在本机建立 `%USERPROFILE%\.dsh` 后，在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\integrations\dsh\install.ps1
```

安装脚本将 desktop/web 两个 profile 指向本机 MCP EXE，并复制 `nijika-dsh-dialog` 技能、写入全局触发规则。若只需要一个 profile，可传 `-Profiles desktop` 或 `-Profiles web`。重启 DSH 并新开会话；配置细节见 [DSH 接入说明](integrations/dsh/README.md)。

## 其他支持 stdio MCP 的本机 Agent

其配置格式由客户端决定。核心字段是以**绝对路径**启动 `虹夏MCP-v2.exe`，不传命令行参数；可设置 `NIJIKA_AGENT_NAME`，让桌面气泡标明来源。例如采用 `mcpServers` 格式的客户端可参考：

```json
{
  "mcpServers": {
    "nijika-pet": {
      "command": "C:/path/to/虹夏MCP-v2.exe",
      "args": [],
      "env": {"NIJIKA_AGENT_NAME": "MyAgent"}
    }
  }
}
```

把示例路径改成该电脑上 EXE 的真实绝对路径。为了让 Agent **主动**在需要审阅或选择时调用工具，还需给该客户端添加触发说明，可参考 [Codex 技能](skills/nijika-desktop-dialog/SKILL.md) 或 [DSH 技能](integrations/dsh/nijika-dsh-dialog/SKILL.md) 并适配其工具名称。仅注册 MCP 不保证模型每次都会主动调用。

## 验证与当前边界

1. 确认桌面能看到虹夏；在 Agent **新任务**里提出一个确实需要你二选一的简短问题。
2. Agent 应调用 `request_decision`，气泡显示来源、问题、各选项的一句影响说明；点击后 Agent 应通过 `wait_for_reply`/`get_reply` 读回，并在**原聊天**写明所选项。
3. 任务完成但内容太长时，Agent 可调用 `show_completion` 提醒你回聊天查看。`pending` 只表示本机排队，不代表气泡已显示或你已批准。

晚到的点击保存在本机消息库，但 Agent 任务若已经结束，当前 stdio MCP **不会自动唤醒该任务**；在原聊天发送“继续”，技能要求先读取旧请求。Codex、Work 和 DSH 的长期等待与晚到回复仍需各自在新任务中现场验收。
