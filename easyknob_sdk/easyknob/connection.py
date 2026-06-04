"""Serial connection management for FOC Gripper."""

import serial
import serial.tools.list_ports
import time
from typing import Optional

DEFAULT_BAUD = 921600


class SerialManager:
    """Manages serial connection to the FOC Gripper knob.

    Usage:
        with SerialManager('COM12') as sm:
            sm.send(cmd_bytes)
            data = sm.read_available()
    """

    def __init__(self, port: str, baud: int = DEFAULT_BAUD, timeout: float = 0.1):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self._ser: Optional[serial.Serial] = None

    # ── Context manager ─────────────────────────────────
    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    # ── Connection ──────────────────────────────────────
    def open(self) -> bool:
        """Open the serial port. Returns True on success."""
        try:
            self._ser = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
            time.sleep(0.1)  # Let Arduino reset complete
            return True
        except serial.SerialException as e:
            raise ConnectionError(f"Failed to open {self.port}: {e}")

    def close(self):
        """Close the serial port."""
        if self._ser and self._ser.is_open:
            self._ser.close()
            self._ser = None

    @property
    def is_connected(self) -> bool:
        """Check if the serial port is open."""
        return self._ser is not None and self._ser.is_open

    # ── I/O ─────────────────────────────────────────────
    def send(self, data: bytes):
        """Send raw bytes over the serial port."""
        if not self.is_connected:
            raise ConnectionError("Not connected")
        self._ser.write(data)

    def read_available(self) -> bytes:
        """Read all currently available bytes."""
        if not self.is_connected:
            raise ConnectionError("Not connected")
        count = self._ser.in_waiting
        if count > 0:
            return self._ser.read(count)
        return b''

    def read(self, size: int, timeout: Optional[float] = None) -> bytes:
        """Read exactly `size` bytes, blocking with optional timeout."""
        if not self.is_connected:
            raise ConnectionError("Not connected")
        if timeout is not None:
            self._ser.timeout = timeout
        data = self._ser.read(size)
        if timeout is not None:
            self._ser.timeout = self.timeout
        return data

    def flush(self):
        """Flush the input buffer."""
        if self.is_connected:
            self._ser.reset_input_buffer()

    @staticmethod
    def list_ports() -> list[str]:
        """List available serial port names."""
        return [p.device for p in serial.tools.list_ports.comports()]
