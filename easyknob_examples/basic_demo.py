#!/usr/bin/env python3
"""Basic demo: read knob angle and apply force feedback."""

import time

from easyknob import EasyKnob, MODE_GRIPPER


def main():
    import argparse
    parser = argparse.ArgumentParser(description='FOC Gripper basic demo')
    parser.add_argument('--port', default='COM12', help='Serial port')
    parser.add_argument('--baud', type=int, default=921600, help='Baud rate')
    args = parser.parse_args()

    with EasyKnob(args.port, args.baud) as g:
        print(f"Connected to {args.port}")
        g.calibrate()
        time.sleep(0.5)

        print("Reading knob angle (Ctrl+C to stop)...")
        t0 = time.monotonic()
        try:
            while True:
                # Read latest report
                rpt = g.read_report(timeout=0.1)
                if rpt:
                    elapsed = time.monotonic() - t0
                    print(f"[{elapsed:6.1f}s] pos={rpt.angle:.3f} "
                          f"vel={rpt.velocity:+.2f} torque={rpt.torque_cmd:+.3f} "
                          f"mode={rpt.mode_name}")

                # Simulate: if position > 0.5, apply force feedback
                if rpt:
                    force = max(0, (rpt.angle - 0.5) * 10)
                    g.set_force(force)

        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == '__main__':
    main()
