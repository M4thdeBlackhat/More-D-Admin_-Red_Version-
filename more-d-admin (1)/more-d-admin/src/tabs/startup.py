"""
Startup App Manager tab — fixed winreg import, uses Treeview.
"""
import threading
import customtkinter as ctk
from tkinter import ttk

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

from ..theme import *
from ..utils import logger as log
from ..utils.confirm import ask_confirm

_STARTUP_KEYS = []
if HAS_WINREG:
    _STARTUP_KEYS = [
        (winreg.HKEY_CURRENT_USER,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM32"),
    ]


def _get_startup_entries() -> list[dict]:
    if not HAS_WINREG:
        return []
    entries = []
    for hive, path, label in _STARTUP_KEYS:
        try:
            key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
        except Exception:
            continue
        i = 0
        while True:
            try:
                name, val, _ = winreg.EnumValue(key, i)
                entries.append({
                    "name":      name,
                    "command":   val,
                    "hive":      hive,
                    "path":      path,
                    "hive_name": label,
                })
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
    return entries


def _remove_startup(entry: dict) -> bool:
    if not HAS_WINREG:
        return False
    try:
        key = winreg.OpenKey(entry["hive"], entry["path"],
                              0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, entry["name"])
        winreg.CloseKey(key)
        return True
    except Exception as e:
        log.error(f"Remove startup failed: {e}")
        return False


def _style_startup_tree():
    s = ttk.Style()
    s.theme_use("default")
    for style in ("Startup.Treeview", "Startup.Treeview.Heading"):
        pass
    s.configure(
        "Startup.Treeview",
        background=BG_CARD, foreground=TEXT_PRIMARY,
        rowheight=34, fieldbackground=BG_CARD,
        borderwidth=0, relief="flat",
        font=("Segoe UI", 11),
    )
    s.configure(
        "Startup.Treeview.Heading",
        background=BG_PANEL, foreground=TEXT_SECONDARY,
        font=("Segoe UI", 10, "bold"),
        borderwidth=0, relief="flat",
    )
    s.map("Startup.Treeview",
          background=[("selected", BG_SELECTED)],
          foreground=[("selected", ACCENT)])
    s.map("Startup.Treeview.Heading",
          background=[("active", BG_HOVER)])


class StartupTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._entries:  list[dict] = []
        self._selected: dict | None = None
        self._build_ui()
        self._load()

    def _build_ui(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        hdr.columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="Startup App Manager",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).grid(
            row=0, column=0, sticky="w")

        self._search = ctk.CTkEntry(
            hdr, placeholder_text="🔍  Search startup apps…",
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
            self, text="Scanning registry…",
            font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w")
        self._status.grid(row=1, column=0, sticky="w", pady=(0, 6))

        # ── Treeview ───────────────────────────────────────────────
        _style_startup_tree()

        tree_frame = ctk.CTkFrame(
            self, fg_color=BG_CARD,
            corner_radius=CORNER_RADIUS,
            border_width=1, border_color=BORDER)
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        cols = ("hive", "name", "command")
        self._tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings",
            style="Startup.Treeview", selectmode="browse")

        for col, heading, w, stretch in [
            ("hive",    "Hive",    70,  False),
            ("name",    "Name",    200, False),
            ("command", "Command", 500, True),
        ]:
            self._tree.heading(col, text=heading, anchor="w")
            self._tree.column(col, width=w, minwidth=40,
                               stretch=stretch, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew", padx=(2, 0), pady=2)
        vsb.grid(row=0, column=1, sticky="ns", pady=2, padx=(0, 2))

        self._tree.tag_configure("hklm", foreground=TEXT_ORANGE)
        self._tree.tag_configure("hkcu", foreground=TEXT_BLUE)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        # ── Buttons ────────────────────────────────────────────────
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=3, column=0, sticky="ew", pady=(10, 0))

        ctk.CTkButton(
            btn_bar, text="🗑 Remove Selected Entry",
            width=190, height=BTN_HEIGHT,
            fg_color=ACCENT_DIM, hover_color=ACCENT,
            text_color=TEXT_PRIMARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS,
            command=self._remove_selected
        ).grid(row=0, column=0, padx=(0, 12))

        ctk.CTkLabel(
            btn_bar,
            text="Removes the registry key only — the app itself is NOT uninstalled.",
            font=FONT_SMALL, text_color=TEXT_DIM
        ).grid(row=0, column=1, sticky="w")

    def _load(self):
        self._status.configure(text="Scanning registry…", text_color=TEXT_SECONDARY)
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        entries = _get_startup_entries()
        self.after(0, self._show, entries)

    def _show(self, entries: list[dict]):
        self._entries = entries
        self._filter()
        self._status.configure(
            text=f"{len(entries)} startup entries found",
            text_color=TEXT_SECONDARY)

    def _filter(self):
        q = self._search.get().lower().strip()
        matched = (
            [e for e in self._entries
             if q in e["name"].lower() or q in e["command"].lower()]
            if q else self._entries
        )
        self._tree.delete(*self._tree.get_children())
        for e in matched:
            tag = "hklm" if "HKLM" in e["hive_name"] else "hkcu"
            self._tree.insert(
                "", "end", iid=f"{e['hive_name']}::{e['name']}",
                values=(e["hive_name"], e["name"], e["command"]),
                tags=(tag,))

    def _on_select(self, _=None):
        sel = self._tree.selection()
        if not sel:
            return
        iid = sel[0]
        for e in self._entries:
            if f"{e['hive_name']}::{e['name']}" == iid:
                self._selected = e
                break

    def _remove_selected(self):
        if not self._selected:
            return
        parent = self.winfo_toplevel()
        if ask_confirm(
            parent, "Remove Startup Entry",
            f"Remove startup entry:\n\n'{self._selected['name']}'\n\n"
            "The application will no longer launch at startup."
        ):
            ok = _remove_startup(self._selected)
            if ok:
                log.success(f"Startup entry removed: {self._selected['name']}")
            else:
                log.error(f"Failed to remove startup: {self._selected['name']}")
            self._load()
