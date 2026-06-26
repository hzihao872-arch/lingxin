# L10 灵巧手 Python 控制

Linker Hand **L10 左手** 的 Python 控制与开发环境，支持：

- **命令行控制**（Dashboard HTTP 或官方 SDK）
- **Web 控制台**（浏览器调关节、保存姿态）
- **摄像头遥操作**（MediaPipe 识别手掌，实时驱动 L10）

---

## 快速开始（SDK 模式控制真机）

环境装好后（见 [环境准备](#环境准备)），**关闭官方 Dashboard 和 Web UI**（CAN 总线同一时刻只能一个程序占用），然后运行：

```cmd
cd /d D:\LLLLLLL\robothand\lingxin
py examples\l10_camera_teleop.py --backend sdk --sdk-path vendor\linkerhand-python-sdk --mirror --max-joint-delta 0 --close-ratio 0.4
```

- `--max-joint-delta 0`：关闭每关节速度上限，**跟手不滞后**
- `--close-ratio 0.4`：保留抓握闭合方向的柔化系数（仅在限速开启时生效，这里留作可选旋钮）
- `--mirror`：画面水平镜像，更符合左右手直觉

预览窗口按 **Q** 或 **Esc** 退出，退出时手会自动缓回到张开姿态。

> 仅预览、不连硬件：加 `--dry-run`。完整参数见 [摄像头遥操作](#摄像头遥操作推荐)。

---

## 目录

1. [环境准备](#环境准备)
2. [摄像头遥操作（推荐）](#摄像头遥操作推荐)
3. [命令行控制](#命令行控制)
4. [Web 控制台](#web-控制台)
5. [关节说明](#关节说明)
6. [常见问题](#常见问题)

---

## 环境准备

### 要求

- Windows 10/11
- Python 3.10+（建议用 **`py`** 启动器，不要用可能无效的 `python` 命令）
- L10 已接电、PCAN-USB 已连接

### 一键安装（PowerShell）

```powershell
cd D:\LLLLLLL\robothand\lingxin
.\scripts\setup_env.ps1
```

可选：克隆官方 SDK 并安装 CAN 依赖：

```powershell
.\scripts\install_official_sdk.ps1
```

### 手动安装（CMD / PowerShell 均可）

```cmd
cd /d D:\LLLLLLL\robothand\lingxin
py -m pip install -e ".[sdk,vision,test]"
```

| 依赖组 | 用途 |
|--------|------|
| `sdk` | 直连 CAN / 官方 SDK |
| `vision` | 摄像头 + MediaPipe |
| `test` | 运行 pytest |

### 运行测试（无需硬件）

```cmd
py -m pytest -q
py -m l10_hand_control --help
```

---

## 摄像头遥操作（推荐）

用摄像头识别你的手掌，把弯曲、张开、拇指侧摆等动作映射到 L10。

### 工作原理

```text
摄像头 -> MediaPipe 21 关键点 -> 映射为 10 关节值 -> PoseSmoother(EMA 去抖) -> L10 move_pose()
```

程序：`examples/l10_camera_teleop.py`

柔和感来自**高频率、低延迟的无抖动跟随**，而不是把动作调慢。默认 `--update-hz 30` + 较高的 EMA 系数让手即时跟随你的动作，同时滤掉 MediaPipe 的帧间抖动。`--max-joint-delta`（默认关闭）是一个**速度上限**，只在你想刻意放慢时打开；`--ease`（默认关闭）让拇指屈曲起手更柔但会牺牲部分抓握的跟手度。退出时自动从当前姿态缓回张开姿态。

### 使用前注意

1. **同一时刻只能有一个程序占用 CAN 总线**
   - 若用 SDK 模式：先关闭官方 Dashboard、本项目的 Web UI（`l10-web` / 8765 端口）
2. **不要加 `--dry-run`** 若要让真机动作（该参数只预览、不驱动手）
3. Windows 上请用 **`py`**，不要用可能无响应的 `python`
4. 建议加 **`--mirror`**，镜像画面通常更符合左右手直觉

### 用 CMD 启动

打开 **命令提示符（cmd）**：

```cmd
cd /d D:\LLLLLLL\robothand\lingxin
```

**1. 仅预览（不连接硬件，测试摄像头）**

```cmd
py examples\l10_camera_teleop.py --dry-run --mirror
```

**2. SDK 模式控制真机（需先关闭 Dashboard / Web UI）**

```cmd
py examples\l10_camera_teleop.py --backend sdk --sdk-path vendor\linkerhand-python-sdk --mirror --verbose
```

**3. Dashboard 模式（需先打开官方 Dashboard 并识别到 L10）**

```cmd
py examples\l10_camera_teleop.py --backend dashboard --mirror
```

预览窗口中按 **Q** 或 **Esc** 退出。

### 用 PowerShell 快捷脚本

```powershell
cd D:\LLLLLLL\robothand\lingxin
.\scripts\run_camera_teleop.ps1 -Backend sdk
.\scripts\run_camera_teleop.ps1 -DryRun
```

### 常用参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--backend` | `dashboard` | `sdk` 或 `dashboard` |
| `--sdk-path` | `vendor\linkerhand-python-sdk` | SDK 目录 |
| `--camera` | `0` | 摄像头编号 |
| `--mirror` | 关 | 水平镜像画面 |
| `--tracked-hand` | `Right` | 跟踪 `Left` / `Right` |
| `--smoothing` | `0.45` | 整体 EMA 系数，越大越跟手、越小越稳 |
| `--finger-smoothing` | `0.22` | 四指专用 EMA，越小越不抖（下限 0.06） |
| `--sensitivity` | `1.2` | 动作放大倍数 |
| `--update-hz` | `30` | 向 L10 发送指令频率上限，越高越跟手 |
| `--speed` | `120` | 关节运动速度 0-255 |
| `--ease` / `--no-ease` | 关 | 拇指屈曲走 ease 曲线（牺牲跟手度换柔和起手） |
| `--max-joint-delta` | `0` | 每帧每关节变化上限（**速度限制**，非柔和度），`0` 关闭 |
| `--close-ratio` | `1.0` | 仅当限速开启时，闭合方向的额外减速系数 |
| `--verbose` | 关 | 打印每帧下发的 pose |
| `--dry-run` | 关 | 只识别手，不驱动 L10 |

**四指抖动时可试：**

```cmd
py examples\l10_camera_teleop.py --backend sdk --sdk-path vendor\linkerhand-python-sdk --mirror --finger-smoothing 0.06
```

**动作幅度不够时可试：**

```cmd
py examples\l10_camera_teleop.py --backend sdk --sdk-path vendor\linkerhand-python-sdk --mirror --sensitivity 1.5
```

**觉得跟手不够、想更灵敏：**

```cmd
py examples\l10_camera_teleop.py --backend sdk --sdk-path vendor\linkerhand-python-sdk --mirror --update-hz 45 --smoothing 0.6
```

**确实想刻意放慢抓握（限速，非默认）：**

```cmd
py examples\l10_camera_teleop.py --backend sdk --sdk-path vendor\linkerhand-python-sdk --mirror --max-joint-delta 8 --close-ratio 0.4
```

退出时会自动从当前姿态缓回到张开姿态，无需手动归位。

### 首次运行

MediaPipe 模型首次运行可能下载约 10 MB，属正常现象。终端应出现 `LIVE: controlling L10`；若只有 `DRY-RUN`，说明未连接硬件。

---

## 命令行控制

### 安全提示

- 测试前固定好灵巧手，避免夹伤
- **不要同时**运行 Dashboard、Web UI、SDK 遥操作等多个 CAN 客户端

### Dashboard 后端

官方 Dashboard 已打开且识别 `can1 / L10 / ball_joint / left` 时：

```cmd
py -m l10_hand_control --backend dashboard doctor
py -m l10_hand_control --backend dashboard list-devices
py -m l10_hand_control --backend dashboard gesture 握拳_Fist
py -m l10_hand_control --backend dashboard speed 120
```

若提示 `7080` 不可达，请先启动 `dashboard.exe`。

### SDK 后端

Dashboard **已关闭**，且已执行 `install_official_sdk`：

```cmd
py -m l10_hand_control --backend sdk --sdk-path vendor\linkerhand-python-sdk list-devices
py -m l10_hand_control --backend sdk --sdk-path vendor\linkerhand-python-sdk gesture fist
py -m l10_hand_control --backend sdk --sdk-path vendor\linkerhand-python-sdk pose 80,80,80,80,80,80,80,80,80,80
```

单关节调试示例：

```cmd
py -m l10_hand_control --backend sdk --sdk-path vendor\linkerhand-python-sdk joint index_root=0
py -m l10_hand_control --backend sdk --sdk-path vendor\linkerhand-python-sdk joint thumb_rotation=30
```

配置模板：`config/l10_left.example.yaml`

---

## Web 控制台

浏览器里手动拖滑块、保存姿态：

```cmd
py -m l10_hand_control.web_server --backend sdk --sdk-path vendor\linkerhand-python-sdk
```

或：

```cmd
scripts\run_web_ui.cmd
```

打开 http://127.0.0.1:8765/ 。**Web UI 运行时无法同时跑 SDK 遥操作**（CAN 冲突）。

---

## 关节说明

L10 一次控制 **10 个关节**，数值 **0-255**（越大通常越张开）：

| 索引 | 名称 | 说明 |
|------|------|------|
| 0 | `thumb_root` | 拇指根部弯曲 |
| 1 | `thumb_swing` | 拇指侧摆 |
| 2 | `index_root` | 食指根部 |
| 3 | `middle_root` | 中指根部 |
| 4 | `ring_root` | 无名指根部 |
| 5 | `pinky_root` | 小指根部 |
| 6 | `index_swing` | 食指侧摆 |
| 7 | `ring_swing` | 无名指侧摆 |
| 8 | `pinky_swing` | 小指侧摆 |
| 9 | `thumb_rotation` | 拇指旋转 |

自定义逻辑示例：`examples/custom_l10_control.py`

---

## 常见问题

| 现象 | 处理 |
|------|------|
| 输入 `python` 没反应 | 改用 **`py`** |
| `--dry-run` 时手不动 | 正常；去掉该参数并用 `sdk`/`dashboard` |
| `PCAN Channel has not been initialized` | 关闭 Dashboard / Web UI / 其他占 CAN 的程序后重试 |
| 端口 8765 被占用 | `taskkill` 结束占用进程，或先关 Web UI |
| 摄像头打不开 | 换 `--camera 1`，或关闭占用摄像头的其他软件 |
| 四指一直轻微弯曲、抖动 | 降低 `--finger-smoothing`（如 `0.06`） |
| 拇指/手指幅度不够 | 提高 `--sensitivity`（如 `1.5`） |
| 跟手不够、动作滞后 | 提高 `--update-hz`（如 `45`）和 `--smoothing`（如 `0.6`） |
| 抓握太急、想放慢 | 设 `--max-joint-delta 8 --close-ratio 0.4`（限速，默认关） |
| 抓握太慢、跟不上 | 确认未设 `--max-joint-delta`，或显式设为 `0` |
| 退出时手突然松开 | 已修复：现在退出会缓回到张开姿态；若仍异常检查 CAN 连接 |
| 预览卡顿 | 默认已是异步下发；勿随意加 `--sync-hand` |

---

## 项目结构（简要）

```text
lingxin/
  l10_hand_control/          核心库（映射、SDK 封装、Web）
  examples/
    l10_camera_teleop.py     摄像头遥操作
    custom_l10_control.py    自定义控制示例
  scripts/                   安装与启动脚本
  tests/                     单元测试
  config/                    配置示例
  vendor/                    官方 SDK（可选克隆）
```

---

## Web 控制台详细说明

本节补充 [Web 控制台](#web-控制台) 的完整用法。实现代码在 `l10_hand_control/web_server.py` 与 `l10_hand_control/static/`。

### 功能概览

| 功能 | 说明 |
|------|------|
| 十个关节滑块 | 调节 L10 全部自由度（0–255） |
| 实时调节 | 勾选后拖动滑块即下发到机械手 |
| 张开手掌 | 载入官方推荐张开姿态 |
| 示教读取 | 扭矩置零后用手拨动，滑块同步显示读数 |
| 保存姿态 | 将当前十个关节值命名保存 |
| 姿态列表 | 应用 / 载入滑块 / 删除已保存姿态 |

### 启动前准备

1. 已安装本项目：`py -m pip install -e ".[sdk]"`
2. 已克隆官方 SDK：`scripts\install_official_sdk.cmd`（或 `install_official_sdk.ps1`）
3. L10 已接电，PCAN-USB 已连接
4. **关闭**官方 Dashboard（若用 SDK 后端）
5. **不要**与摄像头遥操作、其他 SDK 程序同时占用 CAN

### 启动方式

**推荐（CMD，不受 PowerShell 脚本策略限制）：**

```cmd
cd /d D:\LLLLLLL\robothand\lingxin
scripts\run_web_ui.cmd
```

**或直接运行模块（默认 SDK 后端）：**

```cmd
py -m l10_hand_control.web_server --backend sdk --sdk-path vendor\linkerhand-python-sdk
```

**若官方 Dashboard 已运行且识别到 L10，可改用：**

```cmd
py -m l10_hand_control.web_server --backend dashboard
```

**可选参数：**

| 参数 | 默认 | 说明 |
|------|------|------|
| `--host` | `127.0.0.1` | 监听地址 |
| `--port` | `8765` | 端口 |
| `--config` | 无 | YAML 配置，如 `config\l10_left.yaml` |
| `--backend` | `sdk` | `sdk` / `dashboard` / `auto` |
| `--sdk-path` | `vendor\linkerhand-python-sdk` | SDK 路径 |
| `--presets` | `data\saved_poses.json` | 姿态保存文件 |

浏览器打开：**http://127.0.0.1:8765/**

若页面异常，请 **Ctrl+F5** 强制刷新，避免浏览器缓存旧版 `app.js`。

### 界面操作

#### 1. 关节调节

- 页面显示十个滑块，对应 [关节说明](#关节说明) 中的索引 0–9
- 勾选 **「实时调节」**：拖动滑块时机械手跟随动作（约 30 次/秒）
- 取消勾选后，需点 **「发送到机械手」** 才会下发
- **「设置速度」**：修改关节运动速度（0–255，默认 120）
- **「张开手掌」**：载入官方张开姿态（见下文）

#### 2. 示教读取（仅 SDK 后端）

L10 **没有** L25 那样的硬件失能指令；示教模式通过 **扭矩置零** 实现，便于用手拨动关节。

1. 点 **「失能并读取」**：扭矩置 0，开始轮询关节反馈
2. 用手轻轻拨动灵巧手，滑块实时显示十个关节读数
3. 满意后点 **「保存当前姿态」** 命名保存
4. 点 **「恢复使能」**：恢复扭矩，可继续实时调节

示教期间不会向机械手发送控制指令。

#### 3. 保存与应用姿态

- 输入名称（如「握拳」「OK手势」）→ **「保存当前姿态」**
- 右侧列表中：
  - **应用**：下发该姿态到机械手并更新滑块
  - **载入滑块**：只更新界面，不发送
  - **删除**：从列表移除

姿态保存在 `data/saved_poses.json`，重启 Web 服务后仍保留。

### 官方张开姿态参考

Web 中 **「张开手掌」** 与代码常量 `OPEN_PALM_POSE` 均来自官方 SDK 示例：

- 文件：`vendor/linkerhand-python-sdk/example/L10/gesture/linker_hand_open_palm.py`
- 姿态：`[255, 70, 255, 255, 255, 255, 255, 255, 255, 255]`

其中 **拇指侧摆 = 70** 是官方推荐的张开位置，**不是** 读数上限；示教读取时该关节仍可能显示到 255。

本仓库对应定义：`l10_hand_control/l10_pose.py` 中的 `OPEN_PALM_POSE`。

### 连接状态

页面右上角显示：

- **机械手已连接**：后端正常，可操作
- **机械手未连接**：检查 PCAN、是否关闭 Dashboard（SDK 模式）、是否被其他程序占用 CAN

### 常见问题（Web）

| 现象 | 处理 |
|------|------|
| 页面一直「检查连接中」、无滑块 | 强制刷新（Ctrl+F5）；确认 8765 端口服务已启动 |
| `l10-web` 命令找不到 | 使用 `py -m l10_hand_control.web_server` |
| PowerShell 脚本无法运行 | 改用 `scripts\run_web_ui.cmd` |
| 显示未连接 / 7080 错误 | SDK 模式需关闭 Dashboard；或改用 `--backend sdk` |
| 改代码后页面无变化 | 终端 Ctrl+C 停掉旧服务后重新启动 |
| 与遥操作冲突 | Web UI 与 `l10_camera_teleop.py` 不要同时运行 |
| 示教模式不可用 | 需 SDK 后端，Dashboard 后端不支持 |

### 停止服务

在运行 Web 服务的终端按 **Ctrl+C** 即可退出。
