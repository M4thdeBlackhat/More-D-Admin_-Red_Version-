"""
System Information Dashboard tab.
"""
import platform
import os
import threading
import customtkinter as ctk

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

from ..theme import *
from ..utils import logger as log


def _get_windows_version() -> str:
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
        product = winreg.QueryValueEx(key, "ProductName")[0]
        build   = winreg.QueryValueEx(key, "CurrentBuildNumber")[0]
        winreg.CloseKey(key)
        return f"{product} (Build {build})"
    except Exception:
        return platform.version()


def _bytes_to_gb(b: int) -> str:
    return f"{b / 1_073_741_824:.1f} GB"


class StatCard(ctk.CTkFrame):
    def __init__(self, parent, label: str, value: str = "—",
                 icon: str = "", color: str = TEXT_PRIMARY):
        super().__init__(parent, fg_color=BG_CARD,
                         corner_radius=CORNER_RADIUS, border_width=1,
                         border_color=BORDER)
        self.columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=icon + "  " + label, font=FONT_SMALL,
                     text_color=TEXT_SECONDARY, anchor="w").grid(
            row=0, column=0, padx=14, pady=(10, 0), sticky="w")

        self._val = ctk.CTkLabel(self, text=value, font=FONT_HEADING,
                                  text_color=color, anchor="w")
        self._val.grid(row=1, column=0, padx=14, pady=(2, 10), sticky="w")

    def update(self, value: str, color: str = None):
        self._val.configure(text=value)
        if color:
            self._val.configure(text_color=color)


class BarStat(ctk.CTkFrame):
    def __init__(self, parent, label: str):
        super().__init__(parent, fg_color=BG_CARD,
                         corner_radius=CORNER_RADIUS, border_width=1,
                         border_color=BORDER)
        self.columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, padx=14, pady=(10, 4), sticky="ew")
        hdr.columnconfigure(1, weight=1)
        ctk.CTkLabel(hdr, text=label, font=FONT_SMALL,
                     text_color=TEXT_SECONDARY).grid(row=0, column=0, sticky="w")
        self._pct_lbl = ctk.CTkLabel(hdr, text="—", font=FONT_SMALL,
                                      text_color=TEXT_PRIMARY)
        self._pct_lbl.grid(row=0, column=1, sticky="e")

        self._bar = ctk.CTkProgressBar(self, height=8,
                                        fg_color=BG_HOVER,
                                        progress_color=ACCENT,
                                        corner_radius=4)
        self._bar.set(0)
        self._bar.grid(row=1, column=0, padx=14, pady=(0, 10), sticky="ew")

    def update(self, pct: float, detail: str = ""):
        self._bar.set(max(0.0, min(1.0, pct / 100)))
        color = TEXT_GREEN if pct < 60 else TEXT_ORANGE if pct < 85 else TEXT_RED
        self._pct_lbl.configure(
            text=f"{pct:.1f}%  {detail}".strip(), text_color=color)
        bar_color = "#22aa22" if pct < 60 else "#cc8800" if pct < 85 else ACCENT
        self._bar.configure(progress_color=bar_color)


class DashboardTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.columnconfigure(0, weight=1)
        self._build_ui()
        self._refresh()
        self._schedule_refresh()

    def _build_ui(self):
        title = ctk.CTkLabel(self, text="System Information Dashboard",
                              font=FONT_TITLE, text_color=TEXT_PRIMARY, anchor="w")
        title.grid(row=0, column=0, padx=4, pady=(4, 12), sticky="w")

        sub = ctk.CTkLabel(self, text="Live system metrics — auto-refreshes every 5 s",
                            font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w")
        sub.grid(row=1, column=0, padx=4, pady=(0, 16), sticky="w")

        # ── Top info cards ───────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        for c in range(3):
            top.columnconfigure(c, weight=1)

        self._os_card   = StatCard(top, "Operating System", icon="🖥")
        self._cpu_card  = StatCard(top, "CPU",              icon="⚡", color=TEXT_BLUE)
        self._host_card = StatCard(top, "Computer Name",    icon="💻")
        self._os_card.grid  (row=0, column=0, padx=(0, 6), sticky="ew")
        self._cpu_card.grid (row=0, column=1, padx=6,      sticky="ew")
        self._host_card.grid(row=0, column=2, padx=(6, 0), sticky="ew")

        # ── Second row ───────────────────────────────────────────────
        row2 = ctk.CTkFrame(self, fg_color="transparent")
        row2.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        for c in range(3):
            row2.columnconfigure(c, weight=1)

        self._ram_total_card  = StatCard(row2, "Total RAM",   icon="🧠", color=TEXT_BLUE)
        self._disk_card       = StatCard(row2, "System Disk", icon="💾", color=TEXT_ORANGE)
        self._uptime_card     = StatCard(row2, "Uptime",      icon="⏱")
        self._ram_total_card.grid (row=0, column=0, padx=(0, 6), sticky="ew")
        self._disk_card.grid      (row=0, column=1, padx=6,      sticky="ew")
        self._uptime_card.grid    (row=0, column=2, padx=(6, 0), sticky="ew")

        # ── Progress bars ────────────────────────────────────────────
        bars_lbl = ctk.CTkLabel(self, text="Resource Usage",
                                 font=FONT_HEADING, text_color=TEXT_PRIMARY, anchor="w")
        bars_lbl.grid(row=4, column=0, padx=4, pady=(0, 8), sticky="w")

        bars = ctk.CTkFrame(self, fg_color="transparent")
        bars.grid(row=5, column=0, sticky="ew", pady=(0, 12))
        bars.columnconfigure(0, weight=1)
        bars.columnconfigure(1, weight=1)

        self._cpu_bar  = BarStat(bars, "CPU Usage")
        self._ram_bar  = BarStat(bars, "RAM Usage")
        self._disk_bar = BarStat(bars, "Disk Usage (C:)")
        self._cpu_bar.grid (row=0, column=0, padx=(0, 6), pady=(0, 8), sticky="ew")
        self._ram_bar.grid (row=0, column=1, padx=(6, 0), pady=(0, 8), sticky="ew")
        self._disk_bar.grid(row=1, column=0, columnspan=2, pady=(0, 8), sticky="ew")

        # ── Process list ─────────────────────────────────────────────
        procs_lbl = ctk.CTkLabel(self, text="Top Processes (by CPU)",
                                  font=FONT_HEADING, text_color=TEXT_PRIMARY, anchor="w")
        procs_lbl.grid(row=6, column=0, padx=4, pady=(0, 8), sticky="w")

        self._proc_box = ctk.CTkTextbox(self, height=160, font=FONT_MONO,
                                         fg_color=BG_CARD, text_color=TEXT_PRIMARY,
                                         corner_radius=CORNER_RADIUS,
                                         border_width=1, border_color=BORDER)
        self._proc_box.grid(row=7, column=0, sticky="ew", padx=0, pady=(0, 4))

        refresh_btn = ctk.CTkButton(
            self, text="↻  Refresh Now", font=FONT_BODY,
            fg_color=BG_CARD, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, corner_radius=CORNER_RADIUS,
            height=BTN_HEIGHT, command=self._refresh)
        refresh_btn.grid(row=8, column=0, sticky="w", pady=(8, 0))

    def _refresh(self):
        threading.Thread(target=self._collect, daemon=True).start()

    def _collect(self):
        data = {}
        data["os"]   = _get_windows_version() if HAS_WINREG else platform.version()
        data["host"] = platform.node()

        if HAS_PSUTIL:
            cpu_info  = platform.processor() or "Unknown CPU"
            data["cpu"]        = cpu_info[:48] + ("…" if len(cpu_info) > 48 else "")
            data["cpu_pct"]    = psutil.cpu_percent(interval=0.5)
            vm = psutil.virtual_memory()
            data["ram_total"]  = _bytes_to_gb(vm.total)
            data["ram_pct"]    = vm.percent
            data["ram_used"]   = _bytes_to_gb(vm.used)
            disk = psutil.disk_usage("C:\\")
            data["disk_pct"]   = disk.percent
            data["disk_free"]  = _bytes_to_gb(disk.free)
            data["disk_total"] = _bytes_to_gb(disk.total)
            bt = psutil.boot_time()
            import time
            secs = int(time.time() - bt)
            h, rem = divmod(secs, 3600)
            m = rem // 60
            data["uptime"] = f"{h}h {m}m"

            procs = []
            for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    procs.append(p.info)
                except Exception:
                    pass
            procs.sort(key=lambda x: x.get("cpu_percent") or 0, reverse=True)
            data["procs"] = procs[:12]
        else:
            data["cpu"]      = platform.processor() or "Unknown"
            data["ram_total"] = data["ram_pct"] = data["ram_used"] = "N/A"
            data["disk_pct"] = data["disk_free"] = data["disk_total"] = "N/A"
            data["uptime"]   = "N/A"
            data["procs"]    = []

        self.after(0, self._apply, data)

    def _apply(self, data):
        self._os_card.update(data.get("os", "—"))
        self._host_card.update(data.get("host", "—"))
        self._cpu_card.update(data.get("cpu", "—"))
        self._ram_total_card.update(data.get("ram_total", "—"))
        self._uptime_card.update(data.get("uptime", "—"))
        self._disk_card.update(
            f"{data.get('disk_free','?')} free / {data.get('disk_total','?')}")

        if HAS_PSUTIL:
            self._cpu_bar.update(data["cpu_pct"],
                                  f"{data['cpu_pct']:.1f}% of all cores")
            self._ram_bar.update(data["ram_pct"],
                                  f"{data['ram_used']} / {data['ram_total']}")
            self._disk_bar.update(data["disk_pct"],
                                   f"{data['disk_free']} free")

        procs = data.get("procs", [])
        self._proc_box.configure(state="normal")
        self._proc_box.delete("1.0", "end")
        hdr = f"{'PID':>7}  {'CPU%':>6}  {'MEM%':>6}  {'Name'}\n"
        self._proc_box.insert("end", hdr)
        self._proc_box.insert("end", "─" * 56 + "\n")
        for p in procs:
            line = (f"{p.get('pid',0):>7}  "
                    f"{p.get('cpu_percent',0):>5.1f}%  "
                    f"{p.get('memory_percent',0):>5.1f}%  "
                    f"{p.get('name','?')[:40]}\n")
            self._proc_box.insert("end", line)
        self._proc_box.configure(state="disabled")
        log.info("Dashboard refreshed")

    def _schedule_refresh(self):
        self.after(5000, self._auto_refresh)

    def _auto_refresh(self):
        self._refresh()
        self._schedule_refresh()
