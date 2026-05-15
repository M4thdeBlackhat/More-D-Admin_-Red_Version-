"""
Installed Applications manager — ttk.Treeview for fast rendering.
Fixes the self.after(0, widget.configure, dict) crash bug.
"""
import threading
import subprocess
import customtkinter as ctk
import tkinter as tk
from tkinter import ttk

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

from ..theme import *
from ..utils import logger as log
from ..utils.confirm import ask_confirm
from ..utils.restore import create_restore_point

_UNINSTALL_KEYS = []
if HAS_WINREG:
    _UNINSTALL_KEYS = [
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]


def _get_installed() -> list[dict]:
    if not HAS_WINREG:
        return []
    apps, seen = [], set()
    for hive, path in _UNINSTALL_KEYS:
        try:
            key = winreg.OpenKey(hive, path)
        except Exception:
            continue
        i = 0
        while True:
            try:
                sub_name = winreg.EnumKey(key, i)
            except OSError:
                break
            i += 1
            try:
                sub = winreg.OpenKey(key, sub_name)
            except Exception:
                continue
            try:
                name = winreg.QueryValueEx(sub, "DisplayName")[0].strip()
            except Exception:
                winreg.CloseKey(sub)
                continue
            if not name or name in seen:
                winreg.CloseKey(sub)
                continue
            seen.add(name)

            def _qv(k, field, default=""):
                try:
                    return winreg.QueryValueEx(k, field)[0]
                except Exception:
                    return default

            apps.append({
                "name":         name,
                "version":      _qv(sub, "DisplayVersion"),
                "publisher":    _qv(sub, "Publisher"),
                "uninstall_cmd":_qv(sub, "UninstallString"),
                "silent_cmd":   _qv(sub, "QuietUninstallString"),
            })
            winreg.CloseKey(sub)
        winreg.CloseKey(key)
    return sorted(apps, key=lambda x: x["name"].lower())


def _run_uninstall(app: dict) -> tuple[int, str]:
    cmd = app.get("silent_cmd") or app.get("uninstall_cmd")
    if not cmd:
        return 1, "No uninstall command found"
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=120)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 1, str(e)


def _style_apps_tree():
    s = ttk.Style()
    s.theme_use("default")
    s.configure(
        "Apps.Treeview",
        background=BG_CARD,
        foreground=TEXT_PRIMARY,
        rowheight=30,
        fieldbackground=BG_CARD,
        borderwidth=0,
        relief="flat",
        font=("Segoe UI", 11),
    )
    s.configure(
        "Apps.Treeview.Heading",
        background=BG_PANEL,
        foreground=TEXT_SECONDARY,
        font=("Segoe UI", 10, "bold"),
        borderwidth=0,
        relief="flat",
    )
    s.map(
        "Apps.Treeview",
        background=[("selected", BG_SELECTED)],
        foreground=[("selected", ACCENT)],
    )
    s.map("Apps.Treeview.Heading",
          background=[("active", BG_HOVER)])


class AppsTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._apps:     list[dict] = []
        self._selected: dict | None = None
        self._build_ui()
        self._load()

    # ── UI ──────────────────────────────────────────────────────────
    def _build_ui(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        hdr.columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="Installed Applications",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).grid(
            row=0, column=0, sticky="w")

        self._search = ctk.CTkEntry(
            hdr, placeholder_text="🔍  Search applications…",
            width=260, height=34, fg_color=BG_CARD,
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
            self, text="Scanning installed applications…",
            font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w")
        self._status.grid(row=1, column=0, sticky="w", pady=(0, 6))

        # ── Treeview ───────────────────────────────────────────────
        _style_apps_tree()

        tree_frame = ctk.CTkFrame(
            self, fg_color=BG_CARD,
            corner_radius=CORNER_RADIUS,
            border_width=1, border_color=BORDER)
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        cols = ("name", "version", "publisher")
        self._tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings",
            style="Apps.Treeview", selectmode="browse")

        for col, heading, w, stretch in [
            ("name",      "Application Name", 380, True),
            ("version",   "Version",          110, False),
            ("publisher", "Publisher",        240, False),
        ]:
            self._tree.heading(col, text=heading, anchor="w",
                               command=lambda c=col: self._sort(c))
            self._tree.column(col, width=w, minwidth=80,
                               stretch=stretch, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew", padx=(2, 0), pady=2)
        vsb.grid(row=0, column=1, sticky="ns", pady=2, padx=(0, 2))

        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        self._sort_col = "name"
        self._sort_rev = False

        # ── Buttons ────────────────────────────────────────────────
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))

        ctk.CTkButton(
            btn_bar, text="🗑 Uninstall Selected",
            width=180, height=BTN_HEIGHT,
            fg_color=ACCENT_DIM, hover_color=ACCENT,
            text_color=TEXT_PRIMARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS,
            command=self._uninstall_selected
        ).grid(row=0, column=0, padx=(0, 8))

        self._sel_lbl = ctk.CTkLabel(
            btn_bar, text="Select an application above",
            font=FONT_SMALL, text_color=TEXT_DIM)
        self._sel_lbl.grid(row=0, column=1, sticky="w")

    # ── Data ────────────────────────────────────────────────────────
    def _load(self):
        self._status.configure(text="Scanning registry…", text_color=TEXT_SECONDARY)
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        apps = _get_installed()
        self.after(0, self._show, apps)

    def _show(self, apps: list[dict]):
        self._apps = apps
        self._filter()
        self._status.configure(
            text=f"{len(apps)} applications installed",
            text_color=TEXT_SECONDARY)

    def _filter(self):
        q = self._search.get().lower().strip()
        matched = (
            [a for a in self._apps
             if q in a["name"].lower() or q in a["publisher"].lower()]
            if q else self._apps
        )
        matched = sorted(matched, key=lambda x: x.get(self._sort_col, "").lower(),
                          reverse=self._sort_rev)
        self._tree.delete(*self._tree.get_children())
        for a in matched:
            self._tree.insert(
                "", "end", iid=a["name"],
                values=(a["name"], a["version"], a["publisher"]))

    def _sort(self, col: str):
        self._sort_rev = (col == self._sort_col) and not self._sort_rev
        self._sort_col = col
        self._filter()

    def _on_select(self, _=None):
        sel = self._tree.selection()
        if not sel:
            return
        name = sel[0]
        for a in self._apps:
            if a["name"] == name:
                self._selected = a
                self._sel_lbl.configure(
                    text=f"Selected: {name[:60]}",
                    text_color=TEXT_PRIMARY)
                break

    # ── Uninstall ───────────────────────────────────────────────────
    def _uninstall_selected(self):
        if not self._selected:
            return
        app    = self._selected
        parent = self.winfo_toplevel()
        if not ask_confirm(
            parent, "Uninstall Application",
            f"Uninstall '{app['name']}'?\n\n"
            "A restore point will be created first.\n"
            "This action cannot be undone."
        ):
            return

        self._status.configure(
            text="Creating restore point…", text_color=TEXT_ORANGE)

        def do():
            create_restore_point(f"Before uninstalling {app['name']}")
            self.after(0, lambda: self._status.configure(
                text=f"Uninstalling {app['name']}…",
                text_color=TEXT_ORANGE))
            rc, out = _run_uninstall(app)
            if rc == 0:
                log.success(f"Uninstalled: {app['name']}")
                self.after(0, self._load)
            else:
                log.error(f"Uninstall failed ({app['name']}): {out}")
                self.after(0, lambda: self._status.configure(
                    text=f"Uninstall failed: {out[:80]}",
                    text_color=TEXT_RED))

        threading.Thread(target=do, daemon=True).start()
