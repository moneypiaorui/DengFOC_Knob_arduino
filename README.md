# EasyKnob

力反馈旋钮 — EasyTeleop 遥操作体系的物理交互设备。

> 旋钮角度 ↔ 夹爪位置 · 夹爪受力 → 旋钮力矩反馈

## 架构

```
┌──────────┐   USB Serial    ┌──────────────┐   Ethernet    ┌──────────┐
│ EasyKnob │ ◄──── 100Hz ──► │ 上位机/SDK   │ ◄───────────► │ 机械臂   │
│  (ESP32) │   921600 baud   │  (Python)    │               │ (REALMAN)│
└──────────┘                 └──────────────┘               └──────────┘
     │                              │
     ├─ AS5600 磁编码器              ├─ tkinter GUI
     ├─ BLDC 电机 (FOC)             ├─ Python SDK
     ├─ 按钮 + RGB LED              └─ REALMAN 集成
     └─ USB CDC 串口
```

## 快速开始

```bash
# 1. 安装环境
pip install uv
git clone https://github.com/moneypiaorui/EasyKnob.git
cd EasyKnob
uv sync

# 2. 编译烧录固件
uv run pio run -t upload

# 3. 启动 GUI
uv run easyknob-gui

# 4. 运行 REALMAN 夹爪 demo
pip install Robotic_Arm
uv run easyknob-demo --knob COM12 --arm 192.168.1.18
```

## 项目结构

```
easyknob/
├── easyknob_fw/              # ESP32 固件
│   ├── easyknob_fw.ino       #   主程序 (921600, 100Hz)
│   ├── easyknob_protocol.*   #   串口协议 (CRC-CCITT)
│   ├── easyknob_control.*    #   夹爪控制 (IDLE/ACTIVE/CALIBRATE)
│   └── motor_function.*      #   按钮 + RGB
│
├── easyknob_sdk/easyknob/    # Python SDK
│   ├── gripper.py            #   EasyKnob 主类
│   ├── connection.py         #   串口管理
│   ├── protocol.py           #   协议编解码
│   └── models.py             #   Report / Command 数据类
│
├── easyknob_gui/             # GUI 上位机
│   ├── app.py                #   tkinter 界面 (30Hz)
│   └── i18n.py               #   中/English 语言包
│
├── easyknob_examples/        # 示例脚本
│   ├── basic_demo.py         #   基础旋钮读取
│   └── realman_gripper_demo.py # REALMAN 力位混合控制
│
└── docs/                     # 文档
    ├── protocol.md           #   通信协议规范
    └── usage.md              #   使用手册
```

## Python SDK 快速使用

```python
from easyknob import EasyKnob

# 连接
knob = EasyKnob('COM12')
knob.connect()
knob.calibrate()

# 读取
rpt = knob.read_report()
print(f"角度: {rpt.angle:.3f}, 速度: {rpt.velocity:.2f} rad/s")

# 力反馈
knob.set_force(2.5)           # 2.5N 外力 → 旋钮反力矩
knob.set_feedback_gain(8.0)   # 增益 8.0

knob.disconnect()
```

## 控制逻辑

| 场景 | 旋钮 | 夹爪 |
|------|------|------|
| 无力 (force < threshold) | 低摩擦自由旋转 | 位置跟随旋钮角度 |
| 有力 (force ≥ threshold) | 力矩 = -gain × force | 力控保持 |

## 文档

| 文档 | 内容 |
|------|------|
| [通信协议](docs/protocol.md) | 帧格式、CRC、命令定义、示例数据包 |
| [使用手册](docs/usage.md) | 环境搭建、固件烧录、GUI、SDK、REALMAN |

## 硬件

| 组件 | 型号 |
|------|------|
| MCU | ESP32 WROOM 32E |
| 编码器 | AS5600 (12-bit 磁编码器) |
| 电机 | BLDC 云台电机 (7 对极) |
| 驱动 | 3 相 PWM (30kHz) |
| 供电 | 12.6V (3S LiPo) |

## License

GPL-3.0
