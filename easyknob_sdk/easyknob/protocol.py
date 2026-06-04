"""Binary protocol encode/decode for FOC Gripper."""

import struct
from .models import Report, Command, MODE_IDLE, FLAG_CALIBRATED, FLAG_FORCE_ACTIVE

SYNC1 = 0xAA
SYNC2 = 0x55

CMD_REPORT  = 0x01
CMD_COMMAND = 0x02
CMD_PING    = 0x03
CMD_ACK     = 0x10


def crc16_ccitt(data: bytes) -> int:
    """CRC-16/CCITT: poly=0x1021, init=0xFFFF."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def encode_command(cmd: Command, seq: int = 0) -> bytes:
    """Encode a Command into a binary frame."""
    payload = struct.pack(
        '<hHHB',
        int(cmd.force * 100),
        int(cmd.force_threshold * 100),
        int(cmd.feedback_gain * 100),
        cmd.mode_cmd & 0xFF,
    )
    header = struct.pack('BBBB', SYNC1, SYNC2, len(payload), seq & 0xFF)
    # seq byte + cmd byte
    crc = crc16_ccitt(struct.pack('B', seq & 0xFF) + bytes([CMD_COMMAND]) + payload)
    return header + bytes([seq & 0xFF, CMD_COMMAND]) + payload + struct.pack('<H', crc)


def encode_ping(seq: int = 0) -> bytes:
    """Encode a ping frame."""
    header = struct.pack('BBBB', SYNC1, SYNC2, 0, seq & 0xFF)
    crc = crc16_ccitt(struct.pack('BB', seq & 0xFF, CMD_PING))
    return header + bytes([seq & 0xFF, CMD_PING]) + struct.pack('<H', crc)


def decode_report(frame: bytes) -> Report:
    """Decode a received frame into a Report.

    Args:
        frame: Raw binary frame starting from the byte after CMD.
               Payload + CRC (18 + 2 = 20 bytes).
    """
    if len(frame) < 20:
        raise ValueError(f"Frame too short: {len(frame)} bytes")
    payload = frame[:18]
    crc_bytes = frame[18:20]
    received_crc = struct.unpack('<H', crc_bytes)[0]
    computed_crc = crc16_ccitt(payload)

    rpt = Report(*struct.unpack('<ffffBB', payload))
    # Store flags internally
    rpt._flags = rpt._flags  # already set from unpack

    if received_crc != computed_crc:
        raise ValueError(f"CRC mismatch: got 0x{received_crc:04X}, expected 0x{computed_crc:04X}")
    return rpt


class ProtocolParser:
    """Stateful stream parser that extracts Report frames from a byte stream."""

    def __init__(self):
        self._buffer = bytearray()
        self._sync_pos = 0

    def feed(self, data: bytes) -> list[Report]:
        """Feed bytes and return list of successfully decoded Reports."""
        self._buffer.extend(data)
        reports = []

        while True:
            # Find sync
            if len(self._buffer) < 7:
                break

            idx = 0
            while idx < len(self._buffer) - 1:
                if self._buffer[idx] == SYNC1 and self._buffer[idx + 1] == SYNC2:
                    break
                idx += 1

            if idx > 0:
                del self._buffer[:idx]

            if len(self._buffer) < 7:
                break

            if self._buffer[0] != SYNC1 or self._buffer[1] != SYNC2:
                break

            payload_len = self._buffer[2]
            if payload_len > 64:
                del self._buffer[:1]
                continue

            frame_total = 5 + payload_len + 2  # header + payload + CRC
            if len(self._buffer) < frame_total:
                break

            cmd = self._buffer[4]
            if cmd == CMD_REPORT and payload_len == 18:
                payload = bytes(self._buffer[5:5 + 18])
                crc_bytes = bytes(self._buffer[5 + 18:5 + 20])
                received_crc = struct.unpack('<H', crc_bytes)[0]
                computed_crc = crc16_ccitt(payload)

                if received_crc == computed_crc:
                    angle, raw_angle, velocity, torque_cmd, mode, flags = \
                        struct.unpack('<ffffBB', payload)
                    rpt = Report(
                        angle=angle,
                        raw_angle=raw_angle,
                        velocity=velocity,
                        torque_cmd=torque_cmd,
                        mode=mode,
                    )
                    rpt._flags = flags
                    reports.append(rpt)

            del self._buffer[:frame_total]

        return reports
