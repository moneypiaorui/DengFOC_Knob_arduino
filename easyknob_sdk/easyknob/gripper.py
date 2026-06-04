"""Main SDK class for the FOC Gripper force-feedback knob."""

import struct
import threading
import time
from typing import Optional, Callable
from collections import deque

from .connection import SerialManager, DEFAULT_BAUD
from .protocol import (
    ProtocolParser, encode_command, encode_ping,
    CMD_ACK, CMD_PING, SYNC1, SYNC2, crc16_ccitt,
)
from .models import Report, Command, MODE_IDLE, MODE_GRIPPER, MODE_CALIBRATE


class EasyKnob:
    """High-level SDK for the FOC Gripper force-feedback knob.

    Usage:
        gripper = EasyKnob('COM12')

        # Option 1: manual polling
        gripper.connect()
        gripper.set_force(2.5)
        rpt = gripper.read_report(timeout=0.5)
        if rpt:
            print(f"Angle: {rpt.angle:.2f}, Velocity: {rpt.velocity:.1f}")

        # Option 2: background reading with callbacks
        def on_report(rpt: Report):
            print(f"Position: {rpt.angle:.3f}")

        gripper.on_report = on_report
        gripper.start()
        time.sleep(10)
        gripper.stop()

        # Option 3: context manager
        with EasyKnob('COM12') as g:
            rpt = g.read_report()
    """

    def __init__(
        self,
        port: str,
        baud: int = DEFAULT_BAUD,
        on_report: Optional[Callable[[Report], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
    ):
        self._serial = SerialManager(port, baud)
        self._parser = ProtocolParser()
        self._seq = 0
        self._latest: Optional[Report] = None
        self._lock = threading.Lock()

        # Callbacks
        self.on_report = on_report
        self.on_disconnect = on_disconnect

        # Background reading
        self._running = False
        self._rx_thread: Optional[threading.Thread] = None

    # ── Context manager ─────────────────────────────────
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.stop()
        self.disconnect()

    # ── Connection ──────────────────────────────────────
    def connect(self):
        """Open serial connection to the knob."""
        self._serial.open()

    def disconnect(self):
        """Close serial connection."""
        self._serial.close()

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._serial.is_connected

    # ── Data ────────────────────────────────────────────
    @property
    def latest(self) -> Optional[Report]:
        """The most recently received report."""
        with self._lock:
            return self._latest

    def read_report(self, timeout: float = 0.5) -> Optional[Report]:
        """Block until a valid report is received or timeout.

        Returns None if no report was received within the timeout.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            data = self._serial.read_available()
            if data:
                reports = self._parser.feed(data)
                if reports:
                    with self._lock:
                        self._latest = reports[-1]
                    return self._latest
            time.sleep(0.001)
        return None

    # ── Control ─────────────────────────────────────────
    def _send_cmd(self, cmd: Command):
        """Send a command frame."""
        frame = encode_command(cmd, self._seq)
        self._seq = (self._seq + 1) & 0xFF
        self._serial.send(frame)

    def set_force(self, force: float):
        """Set the gripper force feedback value (Newtons).

        - force = 0: no feedback, knob controls position freely
        - force > threshold: knob provides proportional torque feedback
        """
        cmd = Command(force=force)
        self._send_cmd(cmd)

    def set_feedback_gain(self, gain: float):
        """Set the torque feedback gain (0.0 - 655.35).

        Higher gain = stronger resistance for the same force.
        """
        cmd = Command(feedback_gain=gain)
        self._send_cmd(cmd)

    def set_force_threshold(self, threshold: float):
        """Set the force threshold to activate feedback (Newtons).

        Forces below this threshold are treated as "no force".
        """
        cmd = Command(force_threshold=threshold)
        self._send_cmd(cmd)

    def set_mode(self, mode: int):
        """Set operating mode (MODE_IDLE=0, MODE_GRIPPER=1)."""
        cmd = Command(mode_cmd=mode)
        self._send_cmd(cmd)

    def calibrate(self):
        """Send calibrate command (sets zero angle from current position)."""
        cmd = Command(mode_cmd=2)
        self._send_cmd(cmd)

    def send_command(self, cmd: Command):
        """Send a fully specified command."""
        self._send_cmd(cmd)

    # ── Background reading ──────────────────────────────
    def start(self):
        """Start background report reading thread.

        Calls self.on_report for each received Report.
        """
        if self._running:
            return
        self._running = True
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._rx_thread.start()

    def stop(self):
        """Stop the background reading thread."""
        self._running = False
        if self._rx_thread and self._rx_thread.is_alive():
            self._rx_thread.join(timeout=1.0)
        self._rx_thread = None

    def _rx_loop(self):
        """Background thread: continuously read and parse reports."""
        while self._running:
            try:
                if not self._serial.is_connected:
                    if self.on_disconnect:
                        self.on_disconnect()
                    break

                data = self._serial.read_available()
                if data:
                    reports = self._parser.feed(data)
                    for rpt in reports:
                        with self._lock:
                            self._latest = rpt
                        if self.on_report:
                            self.on_report(rpt)
                else:
                    time.sleep(0.001)
            except Exception:
                time.sleep(0.01)
