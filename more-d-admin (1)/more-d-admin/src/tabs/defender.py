"""
Advanced Windows Controls tab — Defender, Windows Update, Optimization,
Hidden Files, Cache cleanup.
"""
import threading
import customtkinter as ctk
from ..theme import *
from ..utils import logger as log
from ..utils.confirm import ask_confirm
from ..utils.admin import run_powershell, run_as_admin
from ..utils.restore import create_restore_point


def _toggle_defender(enable: bool) -> tuple[int, str]:
    val = "$false" if not enable else "$true"
    script = f"Set-MpPreference -DisableRealtimeMonitoring {not enable!s}"
    # PowerShell booleans are True/False → string
    script = ("Set-MpPreference -DisableRealtimeMonitoring $true"
              if not enable else
              "Set-MpPreference -DisableRealtimeMonitoring $false")
    return run_powershell(script)


def _defender_status() -> str:
    rc, out = run_powershell(
        "(Get-MpPreference).DisableRealtimeMonitoring")
    if rc != 0:
        return "Unknown"
    return "Disabled" if "True" in out else "Enabled"


def _toggle_windows_update(enable: bool) -> tuple[int, str]:
    services = ["wuauserv", "UsoSvc", "WaaSMedicSvc"]
    action = "auto" if enable else "disabled"
    start_action = "start" if enable else "stop"
    results = []
    for svc in services:
        rc, out = run_as_admin(f'sc config "{svc}" start= {action}')
        run_as_admin(f'sc {start_action} "{svc}"')
        results.append(f"{svc}: {'ok' if rc==0 else out}")
    return 0, "\n".join(results)


def _windows_update_status() -> str:
    rc, out = run_as_admin('sc query wuauserv')
    if "RUNNING" in out:
        return "Enabled (Running)"
    if "STOPPED" in out:
        return "Disabled (Stopped)"
    return "Unknown"


def _toggle_hidden_files(show: bool) -> tuple[int, str]:
    script = (
        f"Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced' "
        f"-Name Hidden -Value {1 if show else 2}"
    )
    rc, out = run_powershell(script)
    # Refresh Explorer
    run_powershell("Stop-Process -Name explorer -Force; Start-Process explorer")
    return rc, out


def _windows_optimize() -> tuple[int, str]:
    steps = [
        ('sc config "SysMain" start= disabled', "Disable Superfetch"),
        ('sc stop "SysMain"',                   "Stop Superfetch"),
        ('sc config "DiagTrack" start= disabled', "Disable Telemetry"),
        ('sc stop "DiagTrack"',                  "Stop Telemetry"),
        ("powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
         "Set High Performance power plan"),
    ]
    results = []
    for cmd, label in steps:
        rc, out = run_as_admin(cmd)
        results.append(f"{'✓' if rc==0 else '✗'} {label}")
    return 0, "\n".join(results)


def _one_click_cache() -> tuple[int, str]:
    script = """
    # DNS cache
    ipconfig /flushdns
    # ARP
    arp -d *
    # Windows Store cache
    wsreset.exe
    """
    return run_as_admin(f'cmd /c ipconfig /flushdns && arp -d *')


class ToggleCard(ctk.CTkFrame):
    """A status card with an enable/disable button pair."""
    def __init__(self, parent, title: str, description: str,
                 icon: str, on_enable, on_disable, status_fn=None):
        super().__init__(parent, fg_color=BG_CARD,
                         corner_radius=CORNER_RADIUS,
                         border_width=1, border_color=BORDER)
        self.columnconfigure(1, weight=1)
        self._status_fn = status_fn
        self._status_var = ctk.StringVar(value="Checking…")

        ctk.CTkLabel(self, text=icon, font=("Segoe UI", 28)).grid(
            row=0, column=0, rowspan=3, padx=(16, 10), pady=14)

        ctk.CTkLabel(self, text=title, font=FONT_HEADING,
                     text_color=TEXT_PRIMARY, anchor="w").grid(
            row=0, column=1, sticky="w", pady=(12, 0))

        ctk.CTkLabel(self, text=description, font=FONT_SMALL,
                     text_color=TEXT_SECONDARY, wraplength=320, anchor="w").grid(
            row=1, column=1, sticky="w")

        self._status_lbl = ctk.CTkLabel(
            self, textvariable=self._status_var,
            font=FONT_SMALL, text_color=TEXT_ORANGE, anchor="w")
        self._status_lbl.grid(row=2, column=1, sticky="w", pady=(0, 10))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=0, column=2, rowspan=3, padx=(10, 14), pady=14)

        ctk.CTkButton(
            btn_frame, text="Enable", width=90, height=BTN_HEIGHT,
            fg_color="#1a4a1a", hover_color="#256025",
            text_color=TEXT_GREEN, font=FONT_BODY,
            corner_radius=CORNER_RADIUS, command=on_enable).grid(
            row=0, column=0, pady=(0, 6))

        ctk.CTkButton(
            btn_frame, text="Disable", width=90, height=BTN_HEIGHT,
            fg_color=ACCENT_DIM, hover_color=ACCENT,
            text_color=TEXT_RED, font=FONT_BODY,
            corner_radius=CORNER_RADIUS, command=on_disable).grid(
            row=1, column=0)

        if status_fn:
            self._refresh_status()

    def _refresh_status(self):
        def do():
            val = self._status_fn()
            color = TEXT_GREEN if "Enabled" in val or "Running" in val else TEXT_RED
            self.after(0, self._status_var.set, val)
            self.after(0, lambda c=color: self._status_lbl.configure(text_color=c))
        threading.Thread(target=do, daemon=True).start()

    def update_status(self, text: str, color: str = TEXT_ORANGE):
        self._status_var.set(text)
        self._status_lbl.configure(text_color=color)


class DefenderTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.columnconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self, text="Advanced Windows Controls",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 4))
        ctk.CTkLabel(self,
                     text="System-level toggles — use with care. Restore points are created automatically.",
                     font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w").grid(
            row=1, column=0, sticky="w", pady=(0, 14))

        # ── Toggle cards ──────────────────────────────────────────────
        self._def_card = ToggleCard(
            self, "Windows Defender Real-Time Protection",
            "Enables/disables on-access malware scanning.",
            icon="🛡",
            on_enable=lambda: self._toggle("defender", True),
            on_disable=lambda: self._toggle("defender", False),
            status_fn=_defender_status)
        self._def_card.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        self._wu_card = ToggleCard(
            self, "Windows Update Service",
            "Starts or stops wuauserv / UsoSvc / WaaSMedicSvc.",
            icon="🔄",
            on_enable=lambda: self._toggle("wu", True),
            on_disable=lambda: self._toggle("wu", False),
            status_fn=_windows_update_status)
        self._wu_card.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        self._hf_card = ToggleCard(
            self, "Hidden File Visibility",
            "Shows or hides hidden files in Windows Explorer.",
            icon="👁",
            on_enable=lambda: self._toggle("hidden", True),
            on_disable=lambda: self._toggle("hidden", False))
        self._hf_card.grid(row=4, column=0, sticky="ew", pady=(0, 16))

        # ── One-shot actions ──────────────────────────────────────────
        actions_lbl = ctk.CTkLabel(self, text="Quick Actions",
                                    font=FONT_HEADING, text_color=TEXT_PRIMARY, anchor="w")
        actions_lbl.grid(row=5, column=0, sticky="w", pady=(0, 8))

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=6, column=0, sticky="ew", pady=(0, 14))

        ctk.CTkButton(
            btn_row, text="⚡ Windows Optimization Mode",
            width=220, height=BTN_HEIGHT,
            fg_color=ACCENT_DIM, hover_color=ACCENT,
            text_color=TEXT_PRIMARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS,
            command=self._optimize).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="🧹 One-Click Cache Cleanup",
            width=200, height=BTN_HEIGHT,
            fg_color="#1a3a5c", hover_color="#2460a0",
            text_color=TEXT_PRIMARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS,
            command=self._cache_cleanup).grid(row=0, column=1, padx=(0, 8))

        # ── Output log ────────────────────────────────────────────────
        self._out = ctk.CTkTextbox(
            self, height=160, font=FONT_MONO,
            fg_color=BG_CARD, text_color=TEXT_PRIMARY,
            corner_radius=CORNER_RADIUS, border_width=1, border_color=BORDER)
        self._out.grid(row=7, column=0, sticky="ew")
        self._out.configure(state="disabled")

    def _log(self, text: str):
        self._out.configure(state="normal")
        self._out.insert("end", text + "\n")
        self._out.see("end")
        self._out.configure(state="disabled")

    def _toggle(self, feature: str, enable: bool):
        parent = self.winfo_toplevel()
        action = "enable" if enable else "disable"
        labels = {
            "defender": "Windows Defender Real-Time Protection",
            "wu":       "Windows Update Service",
            "hidden":   "Hidden File Visibility",
        }
        if not ask_confirm(parent, f"{action.capitalize()} Feature",
                           f"{action.capitalize()} {labels[feature]}?",
                           danger=not enable):
            return

        if feature in ("defender", "wu"):
            create_restore_point(f"Before {action} {labels[feature]}")

        def do():
            if feature == "defender":
                rc, out = _toggle_defender(enable)
                card = self._def_card
            elif feature == "wu":
                rc, out = _toggle_windows_update(enable)
                card = self._wu_card
            else:
                rc, out = _toggle_hidden_files(enable)
                card = self._hf_card
            status_txt = ("Enabled" if enable else "Disabled") + (" ✓" if rc == 0 else " ✗")
            color = TEXT_GREEN if (enable and rc == 0) else TEXT_RED
            (log.success if rc == 0 else log.error)(
                f"{labels[feature]} {action}d: {out[:80]}")
            self.after(0, card.update_status, status_txt, color)
            self.after(0, self._log, f"{labels[feature]} {action}d\n{out}")
        threading.Thread(target=do, daemon=True).start()

    def _optimize(self):
        parent = self.winfo_toplevel()
        if not ask_confirm(parent, "Windows Optimization Mode",
                           "Apply Windows optimizations?\n\n"
                           "• Disable Superfetch (SysMain)\n"
                           "• Disable Telemetry (DiagTrack)\n"
                           "• Set High Performance power plan\n\n"
                           "A restore point will be created first."):
            return
        create_restore_point("Before Windows optimization")
        self._log("Running optimizations…")
        def do():
            rc, out = _windows_optimize()
            log.success(f"Optimization applied: {out}")
            self.after(0, self._log, out)
        threading.Thread(target=do, daemon=True).start()

    def _cache_cleanup(self):
        self._log("Flushing DNS cache and ARP table…")
        def do():
            rc, out = _one_click_cache()
            log.success(f"Cache cleanup: {out}")
            self.after(0, self._log, f"Cache flushed\n{out}")
        threading.Thread(target=do, daemon=True).start()
