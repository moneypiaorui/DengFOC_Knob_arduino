"""Data models for FOC Gripper protocol."""

from dataclasses import dataclass

# Protocol constants
MODE_IDLE      = 0
MODE_GRIPPER   = 1
MODE_CALIBRATE = 2

FLAG_CALIBRATED   = 0x01
FLAG_FORCE_ACTIVE = 0x02

MODE_NAMES = {
    MODE_IDLE:      "idle",
    MODE_GRIPPER:   "gripper",
    MODE_CALIBRATE: "calibrate",
}

@dataclass
class Report:
    """Angle/position report from the knob (ESP32 -> Host)."""
    angle: float          # Normalized position 0.0 - 1.0
    raw_angle: float      # Raw encoder angle in radians
    velocity: float       # Angular velocity rad/s
    torque_cmd: float     # Torque voltage being applied
    mode: int             # 0=idle, 1=gripper, 2=calibrate

    @property
    def mode_name(self) -> str:
        """Return human-readable mode name."""
        return MODE_NAMES.get(self.mode, "unknown")

    @property
    def force_active(self) -> bool:
        """True if external force is being applied to the gripper."""
        return bool(self._flags & FLAG_FORCE_ACTIVE)

    @property
    def calibrated(self) -> bool:
        """True if the knob has been calibrated."""
        return bool(self._flags & FLAG_CALIBRATED)

@dataclass
class Command:
    """Force command to send to the knob (Host -> ESP32)."""
    force: float = 0.0              # Current force in Newtons
    force_threshold: float = 0.5    # Threshold to activate feedback (N)
    feedback_gain: float = 5.0      # Torque gain factor
    mode_cmd: int = 0               # 0=nop, 1=gripper, 2=calibrate, 3=idle
    damping: float = 0.0            # Damping factor 0.0~1.0 (0=free, 1=max)
