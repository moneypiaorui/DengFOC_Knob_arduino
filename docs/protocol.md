# EasyKnob 通信协议

## 概述

EasyKnob 旋钮与上位机通过 **USB 串口** 进行双向二进制通信。

| 参数 | 值 |
|------|-----|
| 波特率 | 921600 |
| 数据位 | 8 |
| 停止位 | 1 |
| 校验 | 无（帧级 CRC-16/CCITT） |
| 帧率 | 100Hz（每 10ms 一帧） |
| 字节序 | 小端 (Little-Endian) |

## 帧格式

```
┌────────┬────────┬────────┬────────┬────────┬─────────────────┬───────────┐
│ SYNC1  │ SYNC2  │ Length │  Seq   │  Cmd   │    Payload      │  CRC16    │
│  0xAA  │  0x55  │ 1 byte │ 1 byte │ 1 byte │ 0~32 bytes      │ 2 bytes   │
└────────┴────────┴────────┴────────┴────────┴─────────────────┴───────────┘
```

| 偏移 | 字段 | 大小 | 说明 |
|------|------|------|------|
| 0 | SYNC1 | 1 | 固定 `0xAA` |
| 1 | SYNC2 | 1 | 固定 `0x55` |
| 2 | Length | 1 | Payload 长度 (0~32) |
| 3 | Seq | 1 | 序列号 (0~255, 自增回绕) |
| 4 | Cmd | 1 | 命令类型 |
| 5..N | Payload | Length | 负载数据 |
| N+1 | CRC_LO | 1 | CRC-16 低字节 |
| N+2 | CRC_HI | 1 | CRC-16 高字节 |

帧总长 = 5 + Length + 2 bytes。最大 39 bytes。

## CRC-16/CCITT

```
多项式: 0x1021 (x^16 + x^12 + x^5 + 1)
初始值: 0xFFFF
输入: Payload 数据（不含 sync/length/seq/cmd）
输出: 不取反
```

### Python 参考实现

```python
def crc16_ccitt(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return crc
```

### C++ 参考实现

```cpp
uint16_t crc16_ccitt(const uint8_t* data, size_t len) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (uint8_t bit = 0; bit < 8; bit++) {
            crc = (crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1;
        }
    }
    return crc;
}
```

## 命令定义

### CMD 0x01 — 上行报告 (ESP32 → Host)

旋钮以 100Hz 固定频率向上位机发送状态报告。

**Payload (18 bytes):**

| 偏移 | 字段 | 类型 | 说明 |
|------|------|------|------|
| 0 | angle | float32 | 归一化角度 0.0~1.0 |
| 4 | raw_angle | float32 | 编码器原始角度 (rad) |
| 8 | velocity | float32 | 角速度 (rad/s) |
| 12 | torque_cmd | float32 | 当前力矩指令 (V) |
| 16 | mode | uint8 | 模式: 0=空闲, 1=夹爪, 2=校准 |
| 17 | flags | uint8 | Bit0=已校准, Bit1=力反馈激活 |

**帧总长: 25 bytes**

### CMD 0x02 — 下行命令 (Host → ESP32)

上位机向旋钮发送控制指令。

**Payload (7 bytes):**

| 偏移 | 字段 | 类型 | 说明 |
|------|------|------|------|
| 0 | force | int16 | 外力值 ×100 (-327.68~327.67 N) |
| 2 | threshold | uint16 | 力阈值 ×100 (0~655.35 N) |
| 4 | gain | uint16 | 反馈增益 ×100 (0~655.35) |
| 6 | mode_cmd | uint8 | 0=无操作, 1=夹爪模式, 2=校准, 3=空闲 |

**帧总长: 14 bytes**

### CMD 0x03 — Ping (双向)

心跳包，Payload 长度 0。

### CMD 0x10 — 应答

| 偏移 | 字段 | 类型 | 说明 |
|------|------|------|------|
| 0 | ack_cmd | uint8 | 被应答的命令 |
| 1 | result | uint8 | 0=成功, 1=错误 |

## 控制逻辑

```
if |force| < threshold:
    旋钮自由旋转（低阻尼）
    旋钮角度 → 夹爪位置 (0→1 映射到 关闭→打开)

if |force| >= threshold:
    旋钮力矩 = -gain × force（限幅 ±6V）
    夹爪持续力控夹持
```

## 解析状态机

接收端逐字节解析，状态转移：

```
SYNC1 → SYNC2 → LEN → SEQ → CMD → PAYLOAD → CRC_LO → CRC_HI
  ↑                                                      │
  └──────────────── 匹配失败/超时回退 ←────────────────────┘
```

- 收到 `0xAA` 后等待 `0x55`
- 读取 Length 后等待对应字节数
- CRC 校验通过则交付上层
- 任意字节间超过 100ms 无数据则复位

## 示例数据包

### 上行报告示例

```
AA 55 12 01 01 00 00 80 3F 00 00 00 00 00 00 00 00 00 00 00 00 01 01 C3 8C
│     │  │  │  │  └───────────── Payload (18 bytes) ──────────────┘  └─ CRC
│     │  │  │  └─ Cmd=0x01 (报告)
│     │  │  └─ Seq=1
│     │  └─ Len=18
│     └─ Sync
```

解析：angle=1.0, raw=0.0, vel=0.0, torque=0.0, mode=1(夹爪), flags=1(已校准)

### 下行命令示例

```
AA 55 07 02 02 90 01 40 00 88 13 01 36 2B
│     │  │  │  │  └───────── Payload ─────┘  └─ CRC
│     │  │  │  └─ Cmd=0x02 (命令)
│     │  │  └─ Seq=2
│     │  └─ Len=7
│     └─ Sync
```

解析：force=4.0N, threshold=0.64N, gain=50.0, mode_cmd=1(夹爪模式)
