"""
Process Manager — uses ttk.Treeview for fast rendering of hundreds of rows.
Auto-refreshes in place (updates values, doesn't rebuild widgets).
"""
import threading
import time
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

from ..theme import *
from ..utils import logger as log
from ..utils.confirm import ask_confirm


def _get_processes() -> list[dict]:
    if not HAS_PSUTIL:
        return []
    procs = []
    for p in psutil.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent", "status"]):
        try:
            info = p.info
            procs.append({
                "pid":    info["pid"],
                "name":   info["name"] or "?",
                "cpu":    info["cpu_percent"] or 0.0,
                "mem":    info["memory_percent"] or 0.0,
                "status": info["status"] or "?",
            })
        except Exception:
            pass
    procs.sort(key=lambda x: x["cpu"], reverse=True)
    return procs


def _kill_pid(pid: int, force: bool) -> tuple[int, str]:
    if not HAS_PSUTIL:
        return 1, "psutil not available"
    try:
        p = psutil.Process(pid)
        p.kill() if force else p.terminate()
        return 0, "ok"
    except Exception as e:
        return 1, str(e)


def _style_proc_tree():
    s = ttk.Style()
    s.theme_use("default")
    s.configure(
        "Proc.Treeview",
        background=BG_CARD,
        foreground=TEXT_PRIMARY,
        rowheight=28,
        fieldbackground=BG_CARD,
        borderwidth=0,
        relief="flat",
        font=("Consolas", 10),
    )
    s.configure(
        "Proc.Treeview.Heading",
        background=BG_PANEL,
        foreground=TEXT_SECONDARY,
        font=("Segoe UI", 10, "bold"),
        borderwidth=0,
        relief="flat",
    )
    s.map(
        "Proc.Treeview",
        background=[("selected", BG_SELECTED)],
        foreground=[("selected", ACCENT)],
    )
    s.map("Proc.Treeview.Heading",
          background=[("active", BG_HOVER)])


class ProcessesTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._procs:         list[dict] = []
        self._selected_pid:  int | None = None
        self._selected_name: str        = ""
        self._refresh_running           = False
        self._build_ui()
        self._load()
        self._schedule_refresh()

    # ── UI ──────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        hdr.columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="Process Manager",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).grid(
            row=0, column=0, sticky="w")

        self._search = ctk.CTkEntry(
            hdr, placeholder_text="🔍  Filter by name or PID…",
            width=240, height=34, fg_color=BG_CARD,
            border_color=BORDER, text_color=TEXT_PRIMARY,
            font=FONT_BODY, corner_radius=CORNER_RADIUS)
        self._search.grid(row=0, column=1, sticky="e", padx=(10, 0))
        self._search.bind("<KeyRelease>", lambda e: self._filter())

        ctk.CTkButton(
            hdr, text="↻ Refresh", width=90, height=34,
            fg_color=BG_CARD, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS, command=self._load
        ).grid(row=0, column=2, padx=(8, 0))

        self._status = ctk.CTkLabel(
            self, text="Loading…",
            font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w")
        self._status.grid(row=1, column=0, sticky="w", pady=(0, 6))

        # ── Treeview ───────────────────────────────────────────────
        _style_proc_tree()

        tree_frame = ctk.CTkFrame(
            self, fg_color=BG_CARD,
            corner_radius=CORNER_RADIUS,
            border_width=1, border_color=BORDER)
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        cols = ("pid", "cpu", "mem", "status", "name")
        self._tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings",
            style="Proc.Treeview", selectmode="browse")

        for col, heading, w, stretch in [
            ("pid",    "PID",      70,  False),
            ("cpu",    "CPU %",    70,  False),
            ("mem",    "MEM %",    70,  False),
            ("status", "Status",   80,  False),
            ("name",   "Name",     400, True),
        ]:
            self._tree.heading(col, text=heading, anchor="w",
                               command=lambda c=col: self._sort(c))
            self._tree.column(col, width=w, minwidth=40,
                               stretch=stretch, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew", padx=(2, 0), pady=2)
        vsb.grid(row=0, column=1, sticky="ns", pady=2, padx=(0, 2))

        self._tree.tag_configure("hi_cpu", foreground=TEXT_ORANGE)
        self._tree.tag_configure("hi_mem", foreground=TEXT_BLUE)
        self._tree.tag_configure("normal", foreground=TEXT_PRIMARY)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        self._sort_col = "cpu"
        self._sort_rev = True

        # ── Buttons ────────────────────────────────────────────────
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))

        ctk.CTkButton(
            btn_bar, text="⚡ Force Kill", width=140, height=BTN_HEIGHT,
            fg_color=ACCENT_DIM, hover_color=ACCENT,
            text_color=TEXT_PRIMARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS,
            command=self._kill_selected
        ).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            btn_bar, text="Terminate Gracefully", width=170, height=BTN_HEIGHT,
            fg_color=BG_CARD, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS,
            command=self._terminate_selected
        ).grid(row=0, column=1, padx=(0, 8))

        self._sel_lbl = ctk.CTkLabel(
            btn_bar, text="Click a process to select it",
            font=FONT_SMALL, text_color=TEXT_DIM)
        self._sel_lbl.grid(row=0, column=2, sticky="w")

    # ── Data loading ────────────────────────────────────────────────
    def _load(self):
        if self._refresh_running:
            return
        self._refresh_running = True
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        procs = _get_processes()
        self.after(0, self._show, procs)

    def _show(self, procs: list[dict]):
        self._procs = procs
        self._refresh_running = False
        self._filter()
        running = sum(1 for p in procs if p["status"] == "running")
        self._status.configure(
            text=f"{len(procs)} processes  |  {running} running",
            text_color=TEXT_SECONDARY)

    def _filter(self):
        q = self._search.get().lower().strip()
        if q:
            matched = [p for p in self._procs
                       if q in p["name"].lower() or q in str(p["pid"])]
        else:
            matched = self._procs

        # Sort
        matched = sorted(matched, key=lambda x: x.get(self._sort_col, 0),
                          reverse=self._sort_rev)

        # Fast in-place update: update existing iids, insert new, remove old
        existing = set(self._tree.get_children())
        seen = set()

        for p in matched:
            iid = str(p["pid"])
            seen.add(iid)
            tag = "hi_cpu" if p["cpu"] > 15 else ("hi_mem" if p["mem"] > 5 else "normal")
            vals = (
                str(p["pid"]),
                f"{p['cpu']:5.1f}",
                f"{p['mem']:5.1f}",
                p["status"],
                p["name"],
            )
            if iid in existing:
                self._tree.item(iid, values=vals, tags=(tag,))
            else:
                self._tree.insert("", "end", iid=iid, values=vals, tags=(tag,))

        for iid in existing - seen:
            self._tree.delete(iid)

    def _sort(self, col: str):
        if self._sort_col == col:
            self._sort_rev = not self._sort_rev
        else:
            self._sort_col = col
            self._sort_rev = col in ("cpu", "mem", "pid")
        self._filter()

    def _on_select(self, _=None):
        sel = self._tree.selection()
        if not sel:
            return
        try:
            pid = int(sel[0])
            self._selected_pid = pid
            for p in self._procs:
                if p["pid"] == pid:
                    self._selected_name = p["name"]
                    self._sel_lbl.configure(
                        text=f"Selected: {p['name']} (PID {pid})",
                        text_color=TEXT_PRIMARY)
                    break
        except Exception:
            pass

    # ── Actions ─────────────────────────────────────────────────────
    def _kill_selected(self):
        if not self._selected_pid:
            return
        parent = self.winfo_toplevel()
        if ask_confirm(
            parent, "Force Kill Process",
            f"Force-kill '{self._selected_name}' (PID {self._selected_pid})?\n\n"
            "Unsaved data in that process will be lost."
        ):
            def do():
                rc, out = _kill_pid(self._selected_pid, force=True)
                (log.success if rc == 0 else log.error)(
                    f"Force-killed {self._selected_name} ({self._selected_pid})"
                    if rc == 0 else f"Kill failed: {out}")
                time.sleep(0.4)
                self.after(0, self._load)
            threading.Thread(target=do, daemon=True).start()

    def _terminate_selected(self):
        if not self._selected_pid:
            return
        parent = self.winfo_toplevel()
        if ask_confirm(
            parent, "Terminate Process",
            f"Terminate '{self._selected_name}' (PID {self._selected_pid})?",
            confirm_text="Terminate", danger=False
        ):
            def do():
                rc, out = _kill_pid(self._selected_pid, force=False)
                (log.success if rc == 0 else log.error)(
                    f"Terminated {self._selected_name}"
                    if rc == 0 else f"Terminate failed: {out}")
                time.sleep(0.4)
                self.after(0, self._load)
            threading.Thread(target=do, daemon=True).start()

    # ── Auto-refresh ────────────────────────────────────────────────
    def _schedule_refresh(self):
        self._load()
        self.after(6000, self._schedule_refresh)
