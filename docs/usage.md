# EasyKnob 使用文档

## 系统架构

```
┌──────────┐   USB Serial    ┌──────────────┐   Ethernet    ┌──────────┐
│ EasyKnob │ ◄──── 100Hz ──► │ 上位机/SDK   │ ◄───────────► │ 机械臂   │
│  (ESP32) │   921600 baud   │  (Python)    │               │ (REALMAN)│
└──────────┘                 └──────────────┘               └──────────┘
```

## 项目结构

```
easyknob/
├── easyknob_fw/              # ESP32 固件
│   ├── easyknob_fw.ino       #   主程序
│   ├── easyknob_protocol.*   #   串口协议
│   ├── easyknob_control.*    #   夹爪控制
│   └── motor_function.*      #   按钮+RGB
│
├── easyknob_sdk/easyknob/    # Python SDK
│   ├── gripper.py            #   EasyKnob 主类
│   ├── connection.py         #   串口管理
│   ├── protocol.py           #   协议编解码
│   └── models.py             #   数据模型
│
├── easyknob_gui/             # GUI 上位机
│   ├── app.py                #   tkinter 界面
│   └── i18n.py               #   中英文语言包
│
├── easyknob_examples/        # 示例脚本
│   ├── basic_demo.py         #   基础旋钮示例
│   └── realman_gripper_demo.py # REALMAN 夹爪示例
│
└── docs/                     # 文档
    ├── protocol.md           #   通信协议
    └── usage.md              #   使用文档
```

---

## 一、环境准备

### 1.1 Python 环境

```bash
# 安装 uv（Python 包管理器）
pip install uv

# 进入项目目录
cd easyknob

# 一键安装所有依赖（固件编译 + SDK + GUI + 示例）
uv sync
```

这会自动创建 `.venv` 虚拟环境并安装：
- `platformio` — ESP32 编译工具链
- `pyserial` — 串口通信
- `easyknob` — SDK 包（可编辑模式）
- `easyknob-gui` — GUI 包
- `easyknob-examples` — 示例脚本

### 1.2 固件编译环境

`uv sync` 已安装 PlatformIO，无需额外配置。首次编译会自动下载 ESP32 工具链。

---

## 二、固件编译与烧录

### 2.1 编译

```bash
uv run pio run
```

### 2.2 烧录

```bash
uv run pio run -t upload
```

烧录端口在 `platformio.ini` 中配置：

```ini
[env:esp32dev]
upload_port = COM12       # 修改为你的端口
monitor_speed = 921600    # 波特率
```

### 2.3 串口监视

```bash
uv run pio device monitor
```

---

## 三、GUI 上位机

### 3.1 启动

```bash
uv run easyknob-gui
```

### 3.2 界面说明

```
┌─────────────────────────────────────────────────────────┐
│ [端口: COM12 ▼] [刷新] [波特率: 921600 ▼] [连接]  [语言: zh ▼]│
├─────────────────────────────────────────────────────────┤
│ 模式: [空闲] [夹爪控制] [校准零点]              模式: 夹爪控制│
├──────────────────────────┬──────────────────────────────┤
│ 旋钮位置           [?]   │ 力反馈                  [?]   │
│ ┌────────────────────┐   │  ┌──┐                        │
│ │███████████         │   │  │  │  模拟外力: ───○───     │
│ └────────────────────┘   │  │  │  0.0 N                  │
│        0.520             │  │  │                         │
│ 速度: 1.23 rad/s        │  │  │  反馈增益: ───○───     │
│ 力矩: -0.500 V          │  │  │  5.0                     │
│                          │  │  │  力阈值:  ───○───     │
│                          │  │  │  0.50 N                  │
│                          │  └──┘                        │
├──────────────────────────┴──────────────────────────────┤
│ 数据包: 12345                       力反馈激活 (或: 无外力)│
└─────────────────────────────────────────────────────────┘
```

### 3.3 操作流程

1. **连接**：选择 COM 端口，点击「连接」
2. **校准**：点击「校准零点」设定当前角度为零位
3. **模式**：点击「夹爪控制」进入工作模式
4. **旋钮**：转动旋钮，观察位置条变化
5. **力反馈**：拖动「模拟外力」滑块测试力反馈效果

### 3.4 语言切换

右上角下拉框选择 `zh`（中文）或 `en`（English），界面即时切换。

### 3.5 提示说明

鼠标悬停在控件上会显示详细说明。点击 `?` 按钮查看完整帮助。

---

## 四、Python SDK

### 4.1 快速开始

```python
from easyknob import EasyKnob, Report, Command

# 连接旋钮
knob = EasyKnob('COM12')
knob.connect()

# 校准零点
knob.calibrate()

# 读取旋钮状态
rpt = knob.read_report(timeout=0.5)
if rpt:
    print(f"角度: {rpt.angle:.3f}")
    print(f"速度: {rpt.velocity:.2f} rad/s")
    print(f"力矩: {rpt.torque_cmd:.3f} V")
    print(f"模式: {rpt.mode_name}")

# 设置力反馈
knob.set_force(2.5)          # 2.5N 外力
knob.set_feedback_gain(8.0)  # 增益 8.0
knob.set_force_threshold(0.3) # 阈值 0.3N

# 切换模式
from easyknob import MODE_IDLE, MODE_GRIPPER
knob.set_mode(MODE_GRIPPER)

# 断开
knob.disconnect()
```

### 4.2 上下文管理器

```python
with EasyKnob('COM12') as knob:
    rpt = knob.read_report()
    print(rpt.angle)
# 自动断开
```

### 4.3 回调模式

```python
def on_report(rpt: Report):
    print(f"位置: {rpt.angle:.3f}")

knob = EasyKnob('COM12')
knob.on_report = on_report
knob.connect()
knob.start()   # 后台线程持续读取

# ... 主程序做其他事 ...

knob.stop()
knob.disconnect()
```

### 4.4 API 参考

#### EasyKnob 类

| 方法 | 说明 |
|------|------|
| `__init__(port, baud=921600)` | 创建实例 |
| `connect()` | 打开串口 |
| `disconnect()` | 关闭串口 |
| `is_connected` | 连接状态 (property) |
| `read_report(timeout=0.5)` | 读取最新报告 |
| `latest` | 最新报告 (property) |
| `set_force(force: float)` | 设置外力 (N) |
| `set_feedback_gain(gain: float)` | 设置反馈增益 |
| `set_force_threshold(threshold: float)` | 设置力阈值 (N) |
| `set_mode(mode: int)` | 设置模式 (0/1) |
| `calibrate()` | 校准零点 |
| `send_command(cmd: Command)` | 发送完整命令 |
| `start()` | 启动后台读取 |
| `stop()` | 停止后台读取 |

#### Report 数据类

| 字段 | 类型 | 说明 |
|------|------|------|
| `angle` | float | 归一化角度 0~1 |
| `raw_angle` | float | 原始角度 (rad) |
| `velocity` | float | 角速度 (rad/s) |
| `torque_cmd` | float | 力矩指令 (V) |
| `mode` | int | 0=空闲, 1=夹爪, 2=校准 |
| `mode_name` | str | 模式名称 (property) |
| `force_active` | bool | 力反馈是否激活 (property) |

#### Command 数据类

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `force` | float | 0.0 | 外力 (N) |
| `force_threshold` | float | 0.5 | 力阈值 (N) |
| `feedback_gain` | float | 5.0 | 反馈增益 |
| `mode_cmd` | int | 0 | 0=无操作, 1=夹爪, 2=校准, 3=空闲 |

---

## 五、REALMAN 夹爪控制

### 5.1 安装 REALMAN SDK

```bash
pip install Robotic_Arm
```

### 5.2 运行 Demo

```bash
uv run easyknob-demo --knob COM12 --arm 192.168.1.18
```

### 5.3 参数说明

```bash
uv run easyknob-demo --help
```

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--knob` / `-k` | COM12 | 旋钮串口 |
| `--arm` / `-a` | 192.168.0.19 | 机械臂 IP |
| `--arm-port` / `-p` | 8080 | 机械臂端口 |
| `--duration` / `-d` | 0 | 运行时长 (秒, 0=永久) |
| `--threshold` / `-t` | 0.5 | 力反馈阈值 (N) |
| `--gain` / `-g` | 5.0 | 力矩反馈增益 |
| `--grip-force` / `-f` | 150 | 夹持力 (50-1000) |

### 5.4 控制逻辑

```
┌─ 位置模式（无外力）─────────────────────┐
│  旋钮角度 0.0~1.0                        │
│      ↓                                   │
│  夹爪位置 GRIPPER_MIN~GRIPPER_MAX        │
│      ↓                                   │
│  rm_set_gripper_position(target)         │
└──────────────────────────────────────────┘

┌─ 力反馈模式（检测到外力）───────────────┐
│  夹爪力 sensor                           │
│      ↓                                   │
│  旋钮力矩 = -gain × force                │
│      ↓                                   │
│  夹爪力控保持                            │
│  rm_set_gripper_pick_on(speed, force)    │
└──────────────────────────────────────────┘
```

### 5.5 基础旋钮 Demo

```bash
uv run easyknob-basic --port COM12
```

---

## 六、硬件连接

```
ESP32 WROOM 32E

GPIO 32 ──► A 相 PWM   ┐
GPIO 33 ──► B 相 PWM   ├─ BLDC 电机驱动器
GPIO 25 ──► C 相 PWM   ┘
GPIO 19 ──► I2C SDA    ┐
GPIO 18 ──► I2C SCL    ├─ AS5600 磁编码器
GPIO 12 ──► 使能引脚    (HIGH=使能)
GPIO 4  ──► 按钮       (LOW=按下)
GPIO 39 ──► 电流 A     (ADC)
GPIO 36 ──► 电流 B     (ADC)

USB ────► 串口通信 + 供电
```

关键参数：
- 供电电压：12.6V（3S 锂电池）
- 电机极对数：7
- PWM 频率：30kHz
- 编码器分辨率：12-bit (4096)
