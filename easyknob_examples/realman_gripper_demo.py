#!/usr/bin/env python3
"""
REALMAN Gripper Force-Feedback Demo
====================================
Integrates FOC force-feedback knob with REALMAN robotic arm gripper.

Control Logic:
  No force on gripper -> Knob angle (0-1) maps to gripper position (1-1000)
  Force detected       -> Knob provides torque feedback proportional to force

Requires:
  pip install Robotic_Arm
  pip install pyserial
"""

import sys
import time
import argparse
import threading
from collections import deque

from easyknob import EasyKnob, Report, Command

# ── REALMAN SDK ─────────────────────────────────────────────
try:
    from Robotic_Arm.rm_robot_interface import (
        RoboticArm, rm_thread_mode_e, rm_api_version
    )
    REALMAN_AVAILABLE = True
except ImportError:
    REALMAN_AVAILABLE = False

# ── Constants ───────────────────────────────────────────────
GRIPPER_MIN = 1
GRIPPER_MAX = 1000
DEFAULT_ARM_IP   = '192.168.0.19'
DEFAULT_ARM_PORT = 8080
DEFAULT_KNOB_PORT = 'COM12'
DEFAULT_KNOB_BAUD = 921600


# ═══════════════════════════════════════════════════════════
# REALMAN Gripper Wrapper
# ═══════════════════════════════════════════════════════════
class RealmanGripper:
    """Thin wrapper around REALMAN arm gripper API.

    REALMAN SDK gripper API reference:
      rm_set_gripper_route(min, max)     - set stroke range
      rm_set_gripper_position(pos, blk)  - position control (1-1000)
      rm_set_gripper_pick_on(spd, f, blk)- continuous force grip (50-1000)
      rm_set_gripper_release(spd, blk)   - open gripper
      rm_get_gripper_state()             - (ret, dict) state with position/force
    """

    def __init__(self, ip: str = DEFAULT_ARM_IP, port: int = DEFAULT_ARM_PORT):
        self._ip = ip
        self._port = port
        self._arm = None
        self._handle = None

    def connect(self):
        if not REALMAN_AVAILABLE:
            raise RuntimeError("Robotic_Arm not installed. pip install Robotic_Arm")
        self._arm = RoboticArm(rm_thread_mode_e.RM_TRIPLE_MODE_E)
        self._handle = self._arm.rm_create_robot_arm(self._ip, self._port)
        if self._handle is None or self._handle.id < 0:
            raise ConnectionError(f"Arm connect failed: {self._ip}:{self._port}")
        self._arm.rm_set_gripper_route(GRIPPER_MIN, GRIPPER_MAX)
        print(f"[Realman] Connected: {self._handle.id}")

    def disconnect(self):
        if self._arm:
            self._arm.rm_delete_robot_arm()
            print("[Realman] Disconnected")

    def get_state(self) -> dict:
        """Read gripper state. Returns dict with position/force/status fields."""
        if self._arm is None:
            return {}
        ret, state = self._arm.rm_get_gripper_state()
        return state if ret == 0 else {}

    def set_position(self, pos: int, speed: int = 500):
        """Move gripper to absolute position (1=closed, 1000=open)."""
        if self._arm is None:
            return
        pos = max(GRIPPER_MIN, min(GRIPPER_MAX, int(pos)))
        self._arm.rm_set_gripper_position(pos, False, 0)

    def grip_force(self, speed: int = 300, force: int = 150):
        """Continuous force-controlled grip (force: 50-1000)."""
        if self._arm is None:
            return
        self._arm.rm_set_gripper_pick_on(speed, force, False, 0)

    def release(self, speed: int = 500):
        """Open gripper."""
        if self._arm is None:
            return
        self._arm.rm_set_gripper_release(speed, False, 0)

    def __enter__(self): self.connect(); return self
    def __exit__(self, *a): self.disconnect()


# ═══════════════════════════════════════════════════════════
# Force-Position Hybrid Controller
# ═══════════════════════════════════════════════════════════
class ForcePositionController:
    """Bridges FOC Knob <-> REALMAN Gripper with force-position hybrid control.

    Two modes:
      POSITION MODE (no external force):
        Knob angle (0-1)  -->  Gripper position (1-1000)
        Direct mapping: turn knob = move gripper

      FORCE MODE (gripper senses force):
        Knob provides torque feedback proportional to force
        Gripper holds with force-controlled grip
    """

    def __init__(self,
                 knob: EasyKnob,
                 gripper: RealmanGripper,
                 force_threshold: float = 0.5,
                 feedback_gain: float = 5.0,
                 grip_force: int = 150):
        self.knob = knob
        self.gripper = gripper
        self.force_threshold = force_threshold
        self.feedback_gain = feedback_gain
        self.grip_force_val = grip_force

        self._running = False
        self._latest: Report | None = None
        self._lock = threading.Lock()
        self._tick = 0

    def _on_report(self, rpt: Report):
        with self._lock:
            self._latest = rpt

    def start(self):
        self.knob.on_report = self._on_report
        self.knob.start()
        self._running = True
        print("[Ctrl] Force-Position Hybrid Control started")
        print(f"[Ctrl]   threshold={self.force_threshold}N, "
              f"gain={self.feedback_gain}, grip_force={self.grip_force_val}")

    def stop(self):
        self._running = False
        self.knob.stop()

    def tick(self):
        """One control iteration. Call at ~100Hz (every 10ms)."""
        self._tick += 1

        # Read gripper state
        state = self.gripper.get_state()

        # Read latest knob angle
        with self._lock:
            rpt = self._latest
        if rpt is None:
            return

        # Detect force from gripper state
        force_val = self._extract_force(state)
        force_active = force_val > self.force_threshold

        if force_active:
            # ── FORCE MODE ──
            # Send force feedback to knob
            cmd = Command(
                force=force_val,
                force_threshold=self.force_threshold,
                feedback_gain=self.feedback_gain,
            )
            self.knob.send_command(cmd)

            # Gripper holds with force control (refresh every 100ms)
            if self._tick % 10 == 0:
                self.gripper.grip_force(speed=300, force=self.grip_force_val)

        else:
            # ── POSITION MODE ──
            # Clear force on knob
            cmd = Command(force=0.0,
                          force_threshold=self.force_threshold,
                          feedback_gain=self.feedback_gain)
            self.knob.send_command(cmd)

            # Knob angle (0-1) -> Gripper position (1-1000)
            target = GRIPPER_MIN + int(rpt.angle * (GRIPPER_MAX - GRIPPER_MIN))
            if self._tick % 5 == 0:  # every 50ms
                self.gripper.set_position(target)

        # Status log every 2 seconds
        if self._tick % 200 == 0:
            mode = "FORCE" if force_active else "POS"
            print(f"[{mode}] knob={rpt.angle:.3f} "
                  f"vel={rpt.velocity:+.2f} "
                  f"force={force_val:.2f}N "
                  f"state_keys={list(state.keys()) if state else 'N/A'}")

    def run(self, duration: float = 0):
        """Run control loop for N seconds (0=forever)."""
        self.start()
        t0 = time.monotonic()
        try:
            while self._running:
                if duration > 0 and (time.monotonic() - t0) > duration:
                    break
                self.tick()
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("\n[Ctrl] Stopped by user")
        finally:
            self.stop()

    def _extract_force(self, state: dict) -> float:
        """Extract force value from REALMAN gripper state dict.

        The state dict structure depends on the arm firmware version.
        Common fields (REALMAN EG2-4C2 gripper):
          - 'force' or 'current': gripper motor current/force (0-1000)
          - 'position': current opening (0-1000)
          - 'status': motion status flags

        Adjust this method based on actual state dict fields.
        To see available fields, the code prints state.keys() in status log.
        """
        if not state:
            return 0.0
        # REALMAN gripper returns 'current_force' (0-1000) and 'actpos'
        if 'current_force' in state:
            return float(state['current_force']) / 100.0  # normalize to ~N
        for key in ('force', 'current', 'torque', 'load', 'gripper_force'):
            if key in state:
                val = state[key]
                if isinstance(val, (int, float)):
                    return float(val) / 1000.0 * 10.0
        return 0.0


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description='REALMAN Gripper Force-Feedback Demo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python realman_gripper_demo.py
  python realman_gripper_demo.py --knob COM12 --arm 192.168.1.18
  python realman_gripper_demo.py -d 30 -t 0.3 -g 8.0 --grip-force 200
        """
    )
    parser.add_argument('--knob', '-k', default=DEFAULT_KNOB_PORT,
                        help='Knob serial port')
    parser.add_argument('--arm', '-a', default=DEFAULT_ARM_IP,
                        help='REALMAN arm IP')
    parser.add_argument('--arm-port', '-p', type=int, default=DEFAULT_ARM_PORT)
    parser.add_argument('--duration', '-d', type=float, default=0,
                        help='Duration in seconds (0=forever)')
    parser.add_argument('--threshold', '-t', type=float, default=0.5,
                        help='Force threshold (N)')
    parser.add_argument('--gain', '-g', type=float, default=5.0,
                        help='Feedback torque gain')
    parser.add_argument('--grip-force', '-f', type=int, default=150,
                        help='Gripper holding force (50-1000)')
    args = parser.parse_args()

    if not REALMAN_AVAILABLE:
        print("ERROR: pip install Robotic_Arm")
        print("Repo: https://github.com/RealManRobot/RM_API2")
        sys.exit(1)

    # Connect
    knob = EasyKnob(args.knob, DEFAULT_KNOB_BAUD)
    gripper = RealmanGripper(args.arm, args.arm_port)

    knob.connect()
    gripper.connect()

    ctrl = ForcePositionController(
        knob=knob,
        gripper=gripper,
        force_threshold=args.threshold,
        feedback_gain=args.gain,
        grip_force=args.grip_force,
    )

    try:
        ctrl.run(duration=args.duration)
    finally:
        knob.disconnect()
        gripper.disconnect()


if __name__ == '__main__':
    main()
