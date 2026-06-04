# EasyKnob 文档

## 文档索引

| 文档 | 说明 |
|------|------|
| [protocol.md](protocol.md) | 通信协议规范 — 帧格式、CRC、命令定义、示例数据包 |
| [usage.md](usage.md) | 使用文档 — 环境搭建、固件烧录、GUI、SDK、REALMAN 集成 |

## 快速链接

- **固件编译**: `uv run pio run -t upload`
- **启动 GUI**: `uv run easyknob-gui`
- **夹爪 Demo**: `uv run easyknob-demo --knob COM12 --arm 192.168.1.18`
- **基础 Demo**: `uv run easyknob-basic --port COM12`
- **SDK 导入**: `from easyknob import EasyKnob`

## 架构图

```
┌──────────┐   USB Serial    ┌──────────────┐   Ethernet    ┌──────────┐
│ EasyKnob │ ◄──── 100Hz ──► │ 上位机/SDK   │ ◄───────────► │ 机械臂   │
│  (ESP32) │   921600 baud   │  (Python)    │               │ (REALMAN)│
└──────────┘                 └──────────────┘               └──────────┘
     │                              │
     ├─ AS5600 磁编码器              ├─ tkinter GUI
     ├─ BLDC 电机 (FOC)             ├─ Python SDK
     ├─ 按钮 + RGB                  └─ REALMAN 集成
     └─ USB CDC 串口
```
