#!/usr/bin/env python3
"""EasyKnob GUI - Force feedback knob upper computer. Supports zh/en."""

import time
import threading
from collections import deque
from typing import Optional

import tkinter as tk
from tkinter import ttk, messagebox
import serial.tools.list_ports

from easyknob import EasyKnob, Report, Command, MODE_IDLE, MODE_GRIPPER
from i18n import tr, tr_help, set_language, get_language, LANGUAGES

# ── Constants ───────────────────────────────────────────────
BAUD_RATES = ['115200', '230400', '460800', '921600']
DEFAULT_BAUD = '921600'
HISTORY_SIZE = 500


class ToolTip:
    """Hover tooltip for tkinter widgets."""
    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip_window: Optional[tk.Toplevel] = None
        widget.bind('<Enter>', self._show)
        widget.bind('<Leave>', self._hide)

    def _show(self, event=None):
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "9", "normal"), wraplength=350)
        label.pack()

    def _hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class EasyKnobGUI:
    """EasyKnob force-feedback knob upper computer with i18n support."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(tr("window.title"))
        self.root.geometry("850x640")
        self.root.resizable(True, True)

        self.knob: Optional[EasyKnob] = None
        self._connected = False
        self._history = deque(maxlen=HISTORY_SIZE)
        self._lock = threading.Lock()
        self._packet_count = 0

        # Settings
        self._baud_var = tk.StringVar(value=DEFAULT_BAUD)
        self._port_var = tk.StringVar(value='COM12')
        self._gain_var = tk.DoubleVar(value=5.0)
        self._threshold_var = tk.DoubleVar(value=0.5)
        self._damping_var = tk.DoubleVar(value=0.0)
        self._simulate_force = tk.DoubleVar(value=0.0)
        self._lang_var = tk.StringVar(value=get_language())

        self._build_ui()
        self._refresh_ports()
        self._update_display()

    # ═══════════════════════════════════════════════════════
    # UI Construction
    # ═══════════════════════════════════════════════════════
    def _build_ui(self):
        # ── Top bar: connection + language ──
        top = ttk.Frame(self.root, padding=5)
        top.pack(fill=tk.X)

        frm = ttk.Frame(top)
        frm.pack(side=tk.LEFT)

        port_lbl = ttk.Label(frm, text=tr("conn.port"))
        port_lbl.pack(side=tk.LEFT, padx=2)
        ToolTip(port_lbl, tr_help("conn.help"))

        self._port_cb = ttk.Combobox(frm, textvariable=self._port_var, width=10, values=[])
        self._port_cb.pack(side=tk.LEFT, padx=2)

        btn_refresh = ttk.Button(frm, text=tr("conn.refresh"), command=self._refresh_ports)
        btn_refresh.pack(side=tk.LEFT, padx=2)

        baud_lbl = ttk.Label(frm, text=tr("conn.baud"))
        baud_lbl.pack(side=tk.LEFT, padx=(10, 2))
        ttk.Combobox(frm, textvariable=self._baud_var, width=8, values=BAUD_RATES).pack(
            side=tk.LEFT, padx=2)

        self._btn_connect = ttk.Button(frm, text=tr("conn.connect"), command=self._toggle_connect)
        self._btn_connect.pack(side=tk.LEFT, padx=10)

        self._status_label = ttk.Label(frm, text=tr("conn.disconnected"), foreground="red")
        self._status_label.pack(side=tk.LEFT, padx=10)

        # Language selector (right side of top bar)
        lang_frm = ttk.Frame(top)
        lang_frm.pack(side=tk.RIGHT, padx=5)
        lang_lbl = ttk.Label(lang_frm, text=tr("lang.label"))
        lang_lbl.pack(side=tk.LEFT, padx=2)
        ToolTip(lang_lbl, tr_help("lang.help"))
        self._lang_cb = ttk.Combobox(lang_frm, textvariable=self._lang_var,
                                     values=list(LANGUAGES.keys()), width=4,
                                     state='readonly')
        self._lang_cb.pack(side=tk.LEFT, padx=2)
        self._lang_cb.bind('<<ComboboxSelected>>', lambda e: self._switch_language())

        # ── Mode bar ──
        modes = ttk.Frame(self.root, padding=5)
        modes.pack(fill=tk.X)

        mode_lbl = ttk.Label(modes, text=tr("mode.label"))
        mode_lbl.pack(side=tk.LEFT, padx=2)
        ToolTip(mode_lbl, tr_help("mode.help"))

        self._btn_idle = ttk.Button(modes, text=tr("mode.idle"),
                                     command=lambda: self._set_mode(MODE_IDLE))
        self._btn_idle.pack(side=tk.LEFT, padx=2)

        self._btn_grip = ttk.Button(modes, text=tr("mode.gripper"),
                                      command=lambda: self._set_mode(MODE_GRIPPER))
        self._btn_grip.pack(side=tk.LEFT, padx=2)

        btn_cal = ttk.Button(modes, text=tr("mode.calibrate"), command=self._calibrate)
        btn_cal.pack(side=tk.LEFT, padx=10)
        ToolTip(btn_cal, tr_help("mode.help"))

        self._mode_label = ttk.Label(modes, text="--", font=('', 10, 'bold'))
        self._mode_label.pack(side=tk.RIGHT, padx=10)

        # ── Main display ──
        main = ttk.Frame(self.root, padding=5)
        main.pack(fill=tk.BOTH, expand=True)

        # Left: position gauge
        left = ttk.LabelFrame(main, text=tr("pos.title"), padding=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        pos_help = ttk.Label(left, text="?", foreground="gray", cursor="hand2",
                             font=('', 8, 'bold'))
        pos_help.pack(anchor='ne')
        pos_help.bind('<Button-1>', lambda e: self._show_help("overview"))
        ToolTip(pos_help, tr_help("pos.help"))

        self._pos_canvas = tk.Canvas(left, width=300, height=80, bg='#1a1a2e')
        self._pos_canvas.pack(fill=tk.X, pady=5)
        self._pos_bar = self._pos_canvas.create_rectangle(0, 0, 0, 80, fill='#4ecca3', outline='')

        self._pos_label = ttk.Label(left, text="0.000", font=('Consolas', 24))
        self._pos_label.pack()

        pos_grid = ttk.Frame(left)
        pos_grid.pack(fill=tk.X, pady=5)

        vel_lbl = ttk.Label(pos_grid, text=tr("pos.velocity"))
        vel_lbl.grid(row=0, column=0, sticky='w')
        ToolTip(vel_lbl, tr_help("pos.help"))
        self._vel_label = ttk.Label(pos_grid, text="0.00 rad/s", font=('Consolas', 10))
        self._vel_label.grid(row=0, column=1, padx=10)

        trq_lbl = ttk.Label(pos_grid, text=tr("pos.torque"))
        trq_lbl.grid(row=0, column=2, sticky='w')
        ToolTip(trq_lbl, tr_help("pos.help"))
        self._torque_label = ttk.Label(pos_grid, text="0.00 V", font=('Consolas', 10))
        self._torque_label.grid(row=0, column=3, padx=10)

        # Right: force + settings
        right = ttk.Frame(main)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        force_frame = ttk.LabelFrame(right, text=tr("force.title"), padding=10)
        force_frame.pack(fill=tk.BOTH, expand=True)

        force_help = ttk.Label(force_frame, text="?", foreground="gray", cursor="hand2",
                               font=('', 8, 'bold'))
        force_help.pack(anchor='ne')
        ToolTip(force_help, tr_help("force.help"))
        force_help.bind('<Button-1>', lambda e: self._show_help("protocol"))

        self._force_canvas = tk.Canvas(force_frame, width=80, height=200, bg='#1a1a2e')
        self._force_canvas.pack(side=tk.LEFT, padx=(0, 10))
        self._force_bar = self._force_canvas.create_rectangle(10, 200, 70, 200, fill='#e84545', outline='')
        self._force_canvas.create_line(5, 100, 75, 100, fill='#555555')
        self._force_label = ttk.Label(force_frame, text="0.00 N", font=('Consolas', 14))
        self._force_label.pack(side=tk.LEFT)

        # Controls
        ctrl = ttk.Frame(force_frame)
        ctrl.pack(side=tk.TOP, fill=tk.X, expand=True, padx=10)

        sim_lbl = ttk.Label(ctrl, text=tr("force.simulate"))
        sim_lbl.pack(anchor='w')
        ToolTip(sim_lbl, tr_help("force.help"))
        ttk.Scale(ctrl, from_=20, to=0, variable=self._simulate_force,
                  command=self._on_force_slider).pack(fill=tk.X)
        self._force_slider_label = ttk.Label(ctrl, text="0.0 N")
        self._force_slider_label.pack()

        ttk.Separator(ctrl, orient='horizontal').pack(fill=tk.X, pady=10)

        gain_lbl = ttk.Label(ctrl, text=tr("settings.gain"))
        gain_lbl.pack(anchor='w')
        ToolTip(gain_lbl, tr_help("settings.gain.help"))
        ttk.Scale(ctrl, from_=0, to=50, variable=self._gain_var,
                  command=lambda v: self._on_gain_change()).pack(fill=tk.X)
        self._gain_label = ttk.Label(ctrl, text="5.0")
        self._gain_label.pack()

        thresh_lbl = ttk.Label(ctrl, text=tr("settings.threshold"))
        thresh_lbl.pack(anchor='w')
        ToolTip(thresh_lbl, tr_help("settings.threshold.help"))
        ttk.Scale(ctrl, from_=0, to=10, variable=self._threshold_var,
                  command=lambda v: self._on_threshold_change()).pack(fill=tk.X)
        self._threshold_label = ttk.Label(ctrl, text="0.50")
        self._threshold_label.pack()

        damp_lbl = ttk.Label(ctrl, text=tr("settings.damping"))
        damp_lbl.pack(anchor='w')
        ToolTip(damp_lbl, tr_help("settings.damping.help"))
        ttk.Scale(ctrl, from_=0, to=100, variable=self._damping_var,
                  command=lambda v: self._on_damping_change()).pack(fill=tk.X)
        self._damping_label = ttk.Label(ctrl, text="0.00")
        self._damping_label.pack()

        # ── Bottom status bar ──
        bottom = ttk.Frame(self.root, padding=2)
        bottom.pack(fill=tk.X, side=tk.BOTTOM)
        self._packet_label = ttk.Label(bottom, text=tr("status.packets", count=0))
        self._packet_label.pack(side=tk.LEFT)
        self._force_active_label = ttk.Label(bottom, text=tr("status.force_idle"), foreground="gray")
        self._force_active_label.pack(side=tk.RIGHT, padx=10)

    # ═══════════════════════════════════════════════════════
    # Language
    # ═══════════════════════════════════════════════════════
    def _switch_language(self):
        lang = self._lang_var.get()
        try:
            set_language(lang)
        except ValueError:
            return
        # Rebuild UI with new language
        for widget in self.root.winfo_children():
            widget.destroy()
        self._build_ui()
        self._refresh_ports()
        if self._connected:
            self._update_after_reconnect()

    def _update_after_reconnect(self):
        """Restore UI state after language switch while connected."""
        self._btn_connect.config(text=tr("conn.disconnect"))
        self._status_label.config(
            text=f"{tr('conn.connected')} {self._port_var.get()}", foreground="green")

    def _refresh_texts(self):
        """Refresh all dynamic UI texts (called after language switch)."""
        self._btn_idle.config(text=tr("mode.idle"))
        self._btn_grip.config(text=tr("mode.gripper"))

    # ═══════════════════════════════════════════════════════
    # Connection
    # ═══════════════════════════════════════════════════════
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
            self.knob = EasyKnob(port, baud)
            self.knob.connect()
            self._connected = True
            self._btn_connect.config(text=tr("conn.disconnect"))
            self._status_label.config(
                text=f"{tr('conn.connected')} {port}", foreground="green")
            self.knob.on_report = self._on_report
            self.knob.start()
            self._tx_loop()
        except Exception as e:
            messagebox.showerror(
                tr("conn.connect") + " Error", str(e))

    def _disconnect(self):
        if self.knob:
            self.knob.stop()
            self.knob.disconnect()
            self.knob = None
        self._connected = False
        self._btn_connect.config(text=tr("conn.connect"))
        self._status_label.config(text=tr("conn.disconnected"), foreground="red")

    # ═══════════════════════════════════════════════════════
    # Callbacks
    # ═══════════════════════════════════════════════════════
    def _on_report(self, rpt: Report):
        with self._lock:
            self._history.append((time.monotonic(), rpt.angle,
                                  rpt.velocity, rpt.torque_cmd,
                                  rpt.mode, rpt.force_active))

    def _tx_loop(self):
        if not self._connected or not self.knob:
            return
        try:
            cmd = Command(
                force=self._simulate_force.get(),
                feedback_gain=self._gain_var.get(),
                force_threshold=self._threshold_var.get(),
                damping=self._damping_var.get() / 100.0,
            )
            self.knob.send_command(cmd)
        except Exception:
            pass
        self.root.after(20, self._tx_loop)

    def _on_force_slider(self, val):
        self._force_slider_label.config(text=tr("force.value", val=float(val)))

    def _on_gain_change(self):
        self._gain_label.config(text=f"{self._gain_var.get():.1f}")

    def _on_threshold_change(self):
        self._threshold_label.config(text=f"{self._threshold_var.get():.2f}")

    def _on_damping_change(self):
        self._damping_label.config(text=f"{self._damping_var.get() / 100.0:.2f}")

    def _set_mode(self, mode: int):
        if self.knob:
            self.knob.set_mode(mode)

    def _calibrate(self):
        if self.knob:
            self.knob.calibrate()

    # ═══════════════════════════════════════════════════════
    # Display update (30Hz)
    # ═══════════════════════════════════════════════════════
    def _update_display(self):
        with self._lock:
            if self._history:
                last = self._history[-1]
                angle, velocity, torque, mode, force_active = last[1:]

                w = self._pos_canvas.winfo_width()
                bar_w = max(4, int(angle * w))
                self._pos_canvas.coords(self._pos_bar, 0, 0, bar_w, 80)

                self._pos_label.config(text=tr("pos.value", val=angle))
                self._vel_label.config(text=tr("pos.rad_s", val=velocity))
                self._torque_label.config(text=tr("pos.voltage", val=torque))

                mode_name = tr("status.mode.gripper") if mode == MODE_GRIPPER \
                    else tr("status.mode.idle")
                self._mode_label.config(
                    text=tr("indicator.mode", name=mode_name),
                    foreground='#4ecca3' if mode == MODE_GRIPPER else 'gray')

                force = self._simulate_force.get()
                ch = self._force_canvas.winfo_height()
                fh = min(int((force / 20.0) * ch), ch)
                self._force_canvas.coords(self._force_bar, 10, ch, 70, ch - fh)
                self._force_label.config(text=tr("force.value", val=force))

                if force_active:
                    self._force_active_label.config(
                        text=tr("status.force_active"), foreground="red")
                else:
                    self._force_active_label.config(
                        text=tr("status.force_idle"), foreground="gray")

                self._packet_count += 1
                self._packet_label.config(
                    text=tr("status.packets", count=self._packet_count))

        self.root.after(33, self._update_display)

    # ═══════════════════════════════════════════════════════
    # Help dialog
    # ═══════════════════════════════════════════════════════
    def _show_help(self, topic: str):
        text = tr_help(topic)
        dialog = tk.Toplevel(self.root)
        dialog.title("EasyKnob Help")
        dialog.geometry("500x350")
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_widget = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                              font=('TkDefaultFont', 10), relief=tk.FLAT,
                              padx=5, pady=5)
        text_widget.insert('1.0', text)
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)

        ttk.Button(dialog, text="OK", command=dialog.destroy).pack(pady=5)

    def on_close(self):
        self._disconnect()
        self.root.destroy()


# ── Main ────────────────────────────────────────────────────
def main():
    root = tk.Tk()
    app = EasyKnobGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == '__main__':
    main()
