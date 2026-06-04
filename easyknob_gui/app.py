#!/usr/bin/env python3
"""FOC Gripper GUI - Force feedback knob upper computer."""

import time
import threading
from collections import deque
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox
import serial.tools.list_ports

from easyknob import EasyKnob, Report, Command, MODE_IDLE, MODE_GRIPPER

# ── Constants ───────────────────────────────────────────────
BAUD_RATES = ['115200', '230400', '460800', '921600']
DEFAULT_BAUD = '921600'
HISTORY_SIZE = 500

# ── Gripper GUI ─────────────────────────────────────────────
class GripperGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("FOC Gripper - Force Feedback Controller")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        self.gripper: Optional[EasyKnob] = None
        self._connected = False
        self._history = deque(maxlen=HISTORY_SIZE)
        self._lock = threading.Lock()

        # Settings
        self._baud_var = tk.StringVar(value=DEFAULT_BAUD)
        self._port_var = tk.StringVar(value='COM12')
        self._gain_var = tk.DoubleVar(value=5.0)
        self._threshold_var = tk.DoubleVar(value=0.5)
        self._simulate_force = tk.DoubleVar(value=0.0)

        self._build_ui()
        self._refresh_ports()

        # Update display at 30Hz
        self._update_display()

    # ── UI Construction ──────────────────────────────────
    def _build_ui(self):
        # Top bar: connection
        top = ttk.Frame(self.root, padding=5)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Port:").pack(side=tk.LEFT, padx=2)
        self._port_cb = ttk.Combobox(top, textvariable=self._port_var, width=10, values=[])
        self._port_cb.pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Refresh", command=self._refresh_ports).pack(side=tk.LEFT, padx=2)

        ttk.Label(top, text="Baud:").pack(side=tk.LEFT, padx=(10, 2))
        ttk.Combobox(top, textvariable=self._baud_var, width=8, values=BAUD_RATES).pack(side=tk.LEFT, padx=2)

        self._btn_connect = ttk.Button(top, text="Connect", command=self._toggle_connect)
        self._btn_connect.pack(side=tk.LEFT, padx=10)

        self._status_label = ttk.Label(top, text="Disconnected", foreground="red")
        self._status_label.pack(side=tk.LEFT, padx=10)

        # Mode buttons
        modes = ttk.Frame(self.root, padding=5)
        modes.pack(fill=tk.X)
        ttk.Label(modes, text="Mode:").pack(side=tk.LEFT, padx=2)
        self._btn_idle = ttk.Button(modes, text="IDLE", command=lambda: self._set_mode(MODE_IDLE))
        self._btn_idle.pack(side=tk.LEFT, padx=2)
        self._btn_grip = ttk.Button(modes, text="GRIPPER", command=lambda: self._set_mode(MODE_GRIPPER))
        self._btn_grip.pack(side=tk.LEFT, padx=2)
        ttk.Button(modes, text="Calibrate Zero", command=self._calibrate).pack(side=tk.LEFT, padx=10)

        self._mode_label = ttk.Label(modes, text="Mode: --", font=('', 10, 'bold'))
        self._mode_label.pack(side=tk.RIGHT, padx=10)

        # Main display area
        main = ttk.Frame(self.root, padding=5)
        main.pack(fill=tk.BOTH, expand=True)

        # Left: position gauge
        left = ttk.LabelFrame(main, text="Knob Position", padding=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self._pos_canvas = tk.Canvas(left, width=300, height=80, bg='#1a1a2e')
        self._pos_canvas.pack(fill=tk.X, pady=5)
        self._pos_bar = self._pos_canvas.create_rectangle(0, 0, 0, 80, fill='#4ecca3', outline='')

        self._pos_label = ttk.Label(left, text="0.000", font=('Consolas', 24))
        self._pos_label.pack()

        pos_grid = ttk.Frame(left)
        pos_grid.pack(fill=tk.X, pady=5)
        ttk.Label(pos_grid, text="Velocity:").grid(row=0, column=0, sticky='w')
        self._vel_label = ttk.Label(pos_grid, text="0.00 rad/s", font=('Consolas', 10))
        self._vel_label.grid(row=0, column=1, padx=10)
        ttk.Label(pos_grid, text="Torque:").grid(row=0, column=2, sticky='w')
        self._torque_label = ttk.Label(pos_grid, text="0.00 V", font=('Consolas', 10))
        self._torque_label.grid(row=0, column=3, padx=10)

        # Right: force display + controls
        right = ttk.Frame(main)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        force_frame = ttk.LabelFrame(right, text="Force Feedback", padding=10)
        force_frame.pack(fill=tk.BOTH, expand=True)

        self._force_canvas = tk.Canvas(force_frame, width=80, height=200, bg='#1a1a2e')
        self._force_canvas.pack(side=tk.LEFT, padx=(0, 10))
        self._force_bar = self._force_canvas.create_rectangle(10, 200, 70, 200, fill='#e84545', outline='')
        self._force_canvas.create_line(5, 100, 75, 100, fill='#555555')
        self._force_label = ttk.Label(force_frame, text="0.00 N", font=('Consolas', 14))
        self._force_label.pack(side=tk.LEFT)

        # Controls
        ctrl = ttk.Frame(force_frame)
        ctrl.pack(side=tk.TOP, fill=tk.X, expand=True, padx=10)

        ttk.Label(ctrl, text="Simulate Force:").pack(anchor='w')
        ttk.Scale(ctrl, from_=20, to=0, variable=self._simulate_force,
                  command=self._on_force_slider).pack(fill=tk.X)
        self._force_slider_label = ttk.Label(ctrl, text="0.0 N")
        self._force_slider_label.pack()

        ttk.Separator(ctrl, orient='horizontal').pack(fill=tk.X, pady=10)

        ttk.Label(ctrl, text="Feedback Gain:").pack(anchor='w')
        ttk.Scale(ctrl, from_=0, to=50, variable=self._gain_var,
                  command=lambda v: self._on_gain_change()).pack(fill=tk.X)
        self._gain_label = ttk.Label(ctrl, text="5.0")
        self._gain_label.pack()

        ttk.Label(ctrl, text="Force Threshold (N):").pack(anchor='w')
        ttk.Scale(ctrl, from_=0, to=10, variable=self._threshold_var,
                  command=lambda v: self._on_threshold_change()).pack(fill=tk.X)
        self._threshold_label = ttk.Label(ctrl, text="0.50")
        self._threshold_label.pack()

        # Bottom: status bar
        bottom = ttk.Frame(self.root, padding=2)
        bottom.pack(fill=tk.X, side=tk.BOTTOM)
        self._packet_label = ttk.Label(bottom, text="Packets: 0 | Drops: 0")
        self._packet_label.pack(side=tk.LEFT)
        self._force_active_label = ttk.Label(bottom, text="force: OFF", foreground="gray")
        self._force_active_label.pack(side=tk.RIGHT, padx=10)

    # ── Connection ───────────────────────────────────────
    def _refresh_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self._port_cb['values'] = ports
        if ports and not self._port_var.get():
            self._port_var.set(ports[0])

    def _toggle_connect(self):
        if self._connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        port = self._port_var.get()
        baud = int(self._baud_var.get())
        try:
            self.gripper = EasyKnob(port, baud)
            self.gripper.connect()
            self._connected = True
            self._btn_connect.config(text="Disconnect")
            self._status_label.config(text=f"Connected {port}", foreground="green")

            # Start background reading
            self.gripper.on_report = self._on_report
            self.gripper.start()

            # Start TX timer at 50Hz
            self._tx_loop()
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))

    def _disconnect(self):
        if self.gripper:
            self.gripper.stop()
            self.gripper.disconnect()
            self.gripper = None
        self._connected = False
        self._btn_connect.config(text="Connect")
        self._status_label.config(text="Disconnected", foreground="red")

    # ── Callbacks ────────────────────────────────────────
    def _on_report(self, rpt: Report):
        with self._lock:
            self._history.append((time.monotonic(), rpt.angle,
                                  rpt.velocity, rpt.torque_cmd,
                                  rpt.mode, rpt.force_active))

    _packet_count = 0

    def _tx_loop(self):
        """Send force commands at 50Hz."""
        if not self._connected or not self.gripper:
            return
        try:
            force = self._simulate_force.get()
            gain = self._gain_var.get()
            threshold = self._threshold_var.get()
            cmd = Command(
                force=force,
                feedback_gain=gain,
                force_threshold=threshold,
            )
            self.gripper.send_command(cmd)
        except Exception:
            pass
        self.root.after(20, self._tx_loop)  # 50Hz

    def _on_force_slider(self, val):
        self._force_slider_label.config(text=f"{float(val):.1f} N")

    def _on_gain_change(self):
        self._gain_label.config(text=f"{self._gain_var.get():.1f}")

    def _on_threshold_change(self):
        self._threshold_label.config(text=f"{self._threshold_var.get():.2f}")

    def _set_mode(self, mode: int):
        if self.gripper:
            self.gripper.set_mode(mode)

    def _calibrate(self):
        if self.gripper:
            self.gripper.calibrate()

    # ── Display update (30Hz) ────────────────────────────
    def _update_display(self):
        with self._lock:
            if self._history:
                last = self._history[-1]
                angle = last[1]
                velocity = last[2]
                torque = last[3]
                mode = last[4]
                force_active = last[5]

                # Position gauge
                w = self._pos_canvas.winfo_width()
                bar_w = max(4, int(angle * w))
                self._pos_canvas.coords(self._pos_bar, 0, 0, bar_w, 80)

                # Position label
                self._pos_label.config(text=f"{angle:.3f}")

                # Velocity and torque
                self._vel_label.config(text=f"{velocity:.2f} rad/s")
                self._torque_label.config(text=f"{torque:.3f} V")

                # Mode
                self._mode_label.config(
                    text=f"Mode: {'GRIPPER' if mode == MODE_GRIPPER else 'IDLE'}",
                    foreground='#4ecca3' if mode == MODE_GRIPPER else 'gray'
                )

                # Force bar
                force = self._simulate_force.get()
                ch = self._force_canvas.winfo_height()
                fh = min(int((force / 20.0) * ch), ch)
                self._force_canvas.coords(self._force_bar, 10, ch, 70, ch - fh)
                self._force_label.config(text=f"{force:.2f} N")

                # Force active indicator
                if force_active:
                    self._force_active_label.config(text="FORCE ACTIVE", foreground="red")
                else:
                    self._force_active_label.config(text="force: idle", foreground="gray")

                self._packet_count += 1
                self._packet_label.config(text=f"Packets: {self._packet_count}")

        self.root.after(33, self._update_display)

    def on_close(self):
        self._disconnect()
        self.root.destroy()


# ── Main ────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    app = GripperGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == '__main__':
    main()
