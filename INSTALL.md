# 安装与运行

更新触发：2026-09-26 Git 源码交付需要可复现的运行与构建说明。

系统：Windows 10/11 x64。成品版双击 `dist/虹夏桌宠.exe`，无需安装 Python。右键角色可切换“活泼明显 / 轻柔自然 / 关闭”动态、开启或关闭偶发闲聊，也可手动触发说话或两种 Agent 演示提醒。演示中的按钮不会联系真实 Agent；退出时选“退出桌宠”。首次运行无需登录或配置。

从 Git 获取源码后，在项目根目录使用 Python 3.12 执行：

```powershell
python -m pip install -r requirements.txt
python pet.py --self-test
python pet.py
```

生成可双击的单文件版：

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

输出在 `dist/虹夏桌宠.exe`。单文件版首次启动需要解包资源，可能比源码运行略慢。`dist/` 与打包缓存不入 Git；源码包必须保留 `assets/sprites/`。项目没有 `.env`、密钥、网络连接或用户数据写入。

维护者可运行 `python tools/benchmark_motion.py` 测量绘制耗时、`python tools/probe_window_fps.py` 打开约 5 秒的窗口测实际帧间隔、`python tools/make_motion_preview.py` 与 `python tools/make_bubble_preview.py` 重建预览。`tools/inspect_window.py` 用于对正在运行的窗口做本地截图或交互检查；这些工具不会进入打包版。
