"""Internationalization module for EasyKnob GUI."""

import json

LANGUAGES = {
    "zh": "中文",
    "en": "English",
}

_current_lang = "zh"


def set_language(lang: str):
    """Switch language. Raises ValueError if lang not supported."""
    if lang not in LANGUAGES:
        raise ValueError(f"Unsupported language: {lang}")
    global _current_lang
    _current_lang = lang


def get_language() -> str:
    return _current_lang


def tr(key: str, **kwargs) -> str:
    """Translate a key to the current language.

    Usage:
        tr("window.title")         -> "EasyKnob - 力反馈旋钮上位机"
        tr("pos.value", val=0.52)  -> "0.52"
    """
    text = _STRINGS.get(_current_lang, {}).get(key)
    if text is None:
        text = _STRINGS["en"].get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text


def tr_help(key: str) -> str:
    """Get detailed help text for a key in the current language."""
    text = _HELP.get(_current_lang, {}).get(key)
    if text is None:
        text = _HELP.get("en", {}).get(key, "")
    return text


# ═══════════════════════════════════════════════════════════
# UI strings
# ═══════════════════════════════════════════════════════════
_STRINGS = {
    "zh": {
        # ── Window ──
        "window.title": "EasyKnob - 力反馈旋钮上位机",

        # ── Connection bar ──
        "conn.port": "端口:",
        "conn.refresh": "刷新",
        "conn.baud": "波特率:",
        "conn.connect": "连接",
        "conn.disconnect": "断开",
        "conn.connected": "已连接",
        "conn.disconnected": "未连接",
        "conn.help": "从下拉列表选择串口，点击「连接」建立与旋钮的通信。\n波特率需与固件一致（默认 921600）。",

        # ── Mode ──
        "mode.label": "模式:",
        "mode.idle": "空闲",
        "mode.gripper": "夹爪控制",
        "mode.calibrate": "校准零点",
        "mode.help": "空闲模式：旋钮自由旋转，低阻尼。\n夹爪控制模式：旋钮角度映射夹爪位置，夹爪受力时旋钮反馈力矩。\n校准零点：将当前位置设为零点参考。",

        # ── Position ──
        "pos.title": "旋钮位置",
        "pos.value": "{val:.3f}",
        "pos.velocity": "速度:",
        "pos.torque": "力矩:",
        "pos.rad_s": "{val:.2f} rad/s",
        "pos.voltage": "{val:.3f} V",
        "pos.help": "旋钮当前角度（归一化 0.0~1.0）。\n0.0 = 全关位置，1.0 = 全开位置。\n转动旋钮时该值会变化。",

        # ── Force ──
        "force.title": "力反馈",
        "force.value": "{val:.2f} N",
        "force.simulate": "模拟外力:",
        "force.help": "力反馈状态显示。\n模拟外力滑块用于测试：拖动滑块模拟夹爪受力，旋钮会感受到反力矩。",

        # ── Settings ──
        "settings.gain": "反馈增益:",
        "settings.gain.help": "增益越高，相同外力下旋钮的反力矩越大。\n范围 0~50，默认 5.0。",
        "settings.threshold": "力阈值 (N):",
        "settings.threshold.help": "外力低于此阈值时不触发力反馈，旋钮低摩擦自由旋转。\n范围 0~10N，默认 0.5N。",
        "settings.damping": "阻尼:",
        "settings.damping.help": "速度阻尼系数。0=完全自由旋转（无阻力），1=最大阻尼。\n默认 0，值越大转动阻力越大。",

        # ── Status bar ──
        "status.packets": "数据包: {count}",
        "status.force_active": "力反馈激活",
        "status.force_idle": "无外力",
        "status.mode.gripper": "夹爪控制",
        "status.mode.idle": "空闲",

        # ── Language ──
        "lang.label": "语言:",
        "lang.help": "切换界面语言。",

        # ── Mode label (status) ──
        "indicator.mode": "模式: {name}",
    },

    "en": {
        # ── Window ──
        "window.title": "EasyKnob - Force Feedback Controller",

        # ── Connection bar ──
        "conn.port": "Port:",
        "conn.refresh": "Refresh",
        "conn.baud": "Baud:",
        "conn.connect": "Connect",
        "conn.disconnect": "Disconnect",
        "conn.connected": "Connected",
        "conn.disconnected": "Disconnected",
        "conn.help": "Select the COM port for the EasyKnob device and click Connect.\nBaud rate must match the firmware (default 921600).",

        # ── Mode ──
        "mode.label": "Mode:",
        "mode.idle": "IDLE",
        "mode.gripper": "GRIPPER",
        "mode.calibrate": "Calibrate Zero",
        "mode.help": "IDLE: Knob spins freely with light damping.\nGRIPPER: Knob angle maps to gripper position; external force triggers torque feedback.\nCalibrate: Sets the current position as the zero reference.",

        # ── Position ──
        "pos.title": "Knob Position",
        "pos.value": "{val:.3f}",
        "pos.velocity": "Velocity:",
        "pos.torque": "Torque:",
        "pos.rad_s": "{val:.2f} rad/s",
        "pos.voltage": "{val:.3f} V",
        "pos.help": "Current normalized knob angle (0.0 to 1.0).\n0.0 = fully closed, 1.0 = fully open.\nTurning the knob changes this value.",

        # ── Force ──
        "force.title": "Force Feedback",
        "force.value": "{val:.2f} N",
        "force.simulate": "Simulate Force:",
        "force.help": "Force feedback status display.\nDrag the slider to simulate external gripper force — the knob will respond with counter-torque.",

        # ── Settings ──
        "settings.gain": "Feedback Gain:",
        "settings.gain.help": "Higher gain = stronger counter-torque for the same external force.\nRange: 0~50, default: 5.0.",
        "settings.threshold": "Force Threshold (N):",
        "settings.threshold.help": "Forces below this value do not activate feedback — the knob spins freely.\nRange: 0~10 N, default: 0.5 N.",
        "settings.damping": "Damping:",
        "settings.damping.help": "Velocity damping factor. 0 = completely free spin (no resistance), 1 = max damping.\nDefault: 0. Higher values = more resistance when turning.",

        # ── Status bar ──
        "status.packets": "Packets: {count}",
        "status.force_active": "FORCE ACTIVE",
        "status.force_idle": "force: idle",
        "status.mode.gripper": "GRIPPER",
        "status.mode.idle": "IDLE",

        # ── Language ──
        "lang.label": "Language:",
        "lang.help": "Switch the interface language.",

        # ── Mode label (status) ──
        "indicator.mode": "Mode: {name}",
    },
}


# ═══════════════════════════════════════════════════════════
# Help / detailed descriptions
# ═══════════════════════════════════════════════════════════
_HELP = {
    "zh": {
        "overview": (
            "EasyKnob 力反馈旋钮上位机\n\n"
            "本软件用于连接 EasyKnob 力反馈旋钮，通过串口实时显示旋钮角度、\n"
            "速度和力矩状态，并支持模拟外力进行力反馈测试。\n\n"
            "典型用法：\n"
            "1. 选择串口，点击「连接」\n"
            "2. 进入「夹爪控制」模式\n"
            "3. 转动旋钮，观察位置变化\n"
            "4. 拖动「模拟外力」滑块，感受旋钮力反馈\n\n"
            "配合 REALMAN 机械臂：运行 easyknob-demo 脚本实现夹爪力位混合控制。"
        ),
        "protocol": (
            "通信协议说明\n\n"
            "波特率：921600\n"
            "帧率：100Hz（每 10ms 一帧）\n"
            "帧格式：AA 55 Len Seq Cmd Payload CRC16\n\n"
            "上行（旋钮→上位机）：Cmd=0x01\n"
            "  angle(f32) raw_angle(f32) velocity(f32) torque(f32) mode(u8) flags(u8)\n\n"
            "下行（上位机→旋钮）：Cmd=0x02\n"
            "  force(i16×100) threshold(u16×100) gain(u16×100) mode_cmd(u8)"
        ),
    },
    "en": {
        "overview": (
            "EasyKnob Force Feedback Controller\n\n"
            "Connect to the EasyKnob device via serial to display real-time\n"
            "knob angle, velocity, and torque. Supports simulated force testing.\n\n"
            "Typical workflow:\n"
            "1. Select COM port and click 'Connect'\n"
            "2. Switch to 'GRIPPER' mode\n"
            "3. Turn the knob to see position changes\n"
            "4. Drag the 'Simulate Force' slider to feel force feedback\n\n"
            "For REALMAN arm control: run the easyknob-demo script for\n"
            "force-position hybrid gripper control."
        ),
        "protocol": (
            "Protocol Specification\n\n"
            "Baud rate: 921600\n"
            "Frame rate: 100 Hz (every 10 ms)\n"
            "Frame format: AA 55 Len Seq Cmd Payload CRC16\n\n"
            "Uplink (Knob -> Host): Cmd=0x01\n"
            "  angle(f32) raw_angle(f32) velocity(f32) torque(f32) mode(u8) flags(u8)\n\n"
            "Downlink (Host -> Knob): Cmd=0x02\n"
            "  force(i16x100) threshold(u16x100) gain(u16x100) mode_cmd(u8)"
        ),
    },
}
