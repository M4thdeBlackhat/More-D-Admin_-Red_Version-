"""
Windows Services manager tab.
Uses PowerShell Get-Service (much faster than sc query).
"""
import threading
import json
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from ..theme import *
from ..utils import logger as log
from ..utils.confirm import ask_confirm
from ..utils.restore import create_restore_point
from ..utils.admin import run_powershell, run_as_admin


def _get_services() -> list[dict]:
    script = (
        "Get-Service | Select-Object Name, DisplayName, Status | "
        "ConvertTo-Json -Compress"
    )
    rc, out = run_powershell(script)
    if rc != 0 or not out.strip():
        return []
    try:
        raw = json.loads(out)
        if isinstance(raw, dict):
            raw = [raw]
        result = []
        for s in raw:
            result.append({
                "name":    s.get("Name", ""),
                "display": s.get("DisplayName", s.get("Name", "")),
                "status":  str(s.get("Status", {}).get("Value__", s.get("Status", 0))),
                "running": str(s.get("Status", {}).get("Value__", 0)) == "4"
                           or str(s.get("Status", "")) == "Running",
            })
        return sorted(result, key=lambda x: x["name"].lower())
    except Exception as e:
        log.error(f"Service parse error: {e} | raw: {out[:200]}")
        return []


def _set_service(name: str, action: str) -> tuple[int, str]:
    if action == "start":
        rc, out = run_powershell(f'Start-Service -Name "{name}"')
    elif action == "stop":
        rc, out = run_powershell(f'Stop-Service -Name "{name}" -Force')
    elif action == "disable":
        rc, out = run_powershell(
            f'Set-Service -Name "{name}" -StartupType Disabled')
    elif action == "enable":
        rc, out = run_powershell(
            f'Set-Service -Name "{name}" -StartupType Automatic')
    elif action == "restart":
        rc, out = run_powershell(f'Restart-Service -Name "{name}" -Force')
    else:
        return 1, "Unknown action"
    return rc, out


def _style_tree(tree: ttk.Treeview):
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "Services.Treeview",
        background=BG_CARD,
        foreground=TEXT_PRIMARY,
        rowheight=32,
        fieldbackground=BG_CARD,
        borderwidth=0,
        relief="flat",
        font=("Segoe UI", 11),
    )
    style.configure(
        "Services.Treeview.Heading",
        background=BG_PANEL,
        foreground=TEXT_SECONDARY,
        font=("Segoe UI", 10, "bold"),
        borderwidth=0,
        relief="flat",
    )
    style.map(
        "Services.Treeview",
        background=[("selected", BG_SELECTED)],
        foreground=[("selected", ACCENT)],
    )
    style.map("Services.Treeview.Heading", background=[("active", BG_HOVER)])


class ServicesTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._all: list[dict] = []
        self._selected_name: str = ""
        self._selected_running: bool = False
        self._build_ui()
        self._load()

    # ── UI ─────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        hdr.columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="Windows Services",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).grid(
            row=0, column=0, sticky="w")

        self._search = ctk.CTkEntry(
            hdr, placeholder_text="🔍  Search services…",
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
            self, text="Loading services…",
            font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w")
        self._status.grid(row=1, column=0, sticky="w", pady=(0, 6))

        # ── Treeview ──────────────────────────────────────────────
        tree_frame = ctk.CTkFrame(self, fg_color=BG_CARD,
                                   corner_radius=CORNER_RADIUS,
                                   border_width=1, border_color=BORDER)
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        _style_tree(None)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=("status", "display"),
            show="headings",
            style="Services.Treeview",
            selectmode="browse",
        )
        self._tree.heading("status",  text="Status",       anchor="w")
        self._tree.heading("display", text="Service Name", anchor="w")
        self._tree.column("status",  width=90,  minwidth=70,  stretch=False, anchor="w")
        self._tree.column("display", width=500, minwidth=200, stretch=True,  anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew",
                        padx=(2, 0), pady=2)
        vsb.grid(row=0, column=1, sticky="ns", pady=2, padx=(0, 2))

        self._tree.tag_configure("running", foreground=TEXT_GREEN)
        self._tree.tag_configure("stopped", foreground=TEXT_DIM)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda e: self._on_action("start"))

        # ── Action buttons ────────────────────────────────────────
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))

        actions = [
            ("▶ Start",   "start",   "#1a4a1a", "#256025", TEXT_GREEN),
            ("■ Stop",    "stop",    ACCENT_DIM, ACCENT,   TEXT_RED),
            ("↺ Restart", "restart", "#1a3a5c", "#2460a0", TEXT_BLUE),
            ("✖ Disable", "disable", BG_HOVER,  "#3a1a1a", TEXT_SECONDARY),
            ("✔ Enable",  "enable",  BG_HOVER,  BG_HOVER,  TEXT_SECONDARY),
        ]
        for col, (label, action, bg, hv, fc) in enumerate(actions):
            ctk.CTkButton(
                btn_bar, text=label, width=100, height=BTN_HEIGHT,
                fg_color=bg, hover_color=hv, text_color=fc,
                font=FONT_BODY, corner_radius=CORNER_RADIUS,
                command=lambda a=action: self._on_action(a)
            ).grid(row=0, column=col, padx=(0 if col == 0 else 6, 0))

        self._sel_lbl = ctk.CTkLabel(
            btn_bar, text="Select a service above",
            font=FONT_SMALL, text_color=TEXT_DIM)
        self._sel_lbl.grid(row=0, column=len(actions), padx=12, sticky="w")

    # ── Data ───────────────────────────────────────────────────────
    def _load(self):
        self._status.configure(text="Loading services…", text_color=TEXT_SECONDARY)
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        svcs = _get_services()
        self.after(0, self._show, svcs)

    def _show(self, svcs: list[dict]):
        self._all = svcs
        self._filter()
        running = sum(1 for s in svcs if s["running"])
        self._status.configure(
            text=f"{len(svcs)} services  |  {running} running",
            text_color=TEXT_SECONDARY)

    def _filter(self):
        q = self._search.get().lower().strip()
        matched = (
            [s for s in self._all
             if q in s["name"].lower() or q in s["display"].lower()]
            if q else self._all
        )
        # Batch-update tree (much faster than delete/insert individually)
        self._tree.delete(*self._tree.get_children())
        for s in matched:
            tag  = "running" if s["running"] else "stopped"
            dot  = "● Running" if s["running"] else "○ Stopped"
            self._tree.insert("", "end", iid=s["name"],
                              values=(dot, s["display"] or s["name"]),
                              tags=(tag,))

    def _on_select(self, _event=None):
        sel = self._tree.selection()
        if not sel:
            return
        iid = sel[0]
        self._selected_name = iid
        # Find running state
        for s in self._all:
            if s["name"] == iid:
                self._selected_running = s["running"]
                self._sel_lbl.configure(
                    text=f"Selected: {s['display'] or iid}",
                    text_color=TEXT_PRIMARY)
                break

    def _on_action(self, action: str):
        name = self._selected_name
        if not name:
            return
        parent = self.winfo_toplevel()
        if action in ("stop", "disable"):
            if not ask_confirm(
                parent,
                f"{'Stop' if action == 'stop' else 'Disable'} Service",
                f"Are you sure you want to {action} the service:\n\n{name}?"
            ):
                return
            create_restore_point(f"Before {action} {name}")

        self._status.configure(
            text=f"Running '{action}' on {name}…", text_color=TEXT_ORANGE)

        def do():
            rc, out = _set_service(name, action)
            if rc == 0:
                log.success(f"Service {action}: {name}")
            else:
                log.error(f"Service {action} failed ({name}): {out}")
            self.after(0, self._load)

        threading.Thread(target=do, daemon=True).start()
