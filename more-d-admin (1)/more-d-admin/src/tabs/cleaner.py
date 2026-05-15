"""
Temporary File Cleaner tab.
"""
import os
import shutil
import threading
import glob
import customtkinter as ctk
from ..theme import *
from ..utils import logger as log
from ..utils.confirm import ask_confirm

_TEMP_DIRS = [
    os.environ.get("TEMP", ""),
    os.environ.get("TMP", ""),
    os.path.join(os.environ.get("SYSTEMROOT", r"C:\Windows"), "Temp"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Microsoft\Windows\INetCache"),
]

_PREFETCH = os.path.join(os.environ.get("SYSTEMROOT", r"C:\Windows"), "Prefetch")
_RECYCLE  = r"C:\$Recycle.Bin"

_BROWSER_CACHES = [
    os.path.join(os.environ.get("LOCALAPPDATA", ""),
                 r"Google\Chrome\User Data\Default\Cache"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""),
                 r"Microsoft\Edge\User Data\Default\Cache"),
    os.path.join(os.environ.get("APPDATA", ""),
                 r"Mozilla\Firefox\Profiles"),
]

PROTECTED_DIRS = {
    r"C:\Windows",
    r"C:\Windows\System32",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\Users\Default",
}


def _is_protected(path: str) -> bool:
    p = os.path.normcase(os.path.abspath(path))
    for d in PROTECTED_DIRS:
        if p.startswith(os.path.normcase(d)) and len(p) <= len(os.path.normcase(d)) + 2:
            return True
    return False


def _sizeof(path: str) -> int:
    total = 0
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except Exception:
            return 0
    try:
        for root, dirs, files in os.walk(path, onerror=None):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except Exception:
                    pass
    except Exception:
        pass
    return total


def _fmt_size(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1_048_576:
        return f"{b/1024:.1f} KB"
    if b < 1_073_741_824:
        return f"{b/1_048_576:.1f} MB"
    return f"{b/1_073_741_824:.2f} GB"


def _clean_dir(path: str) -> tuple[int, int]:
    """Returns (files_deleted, bytes_freed)."""
    deleted, freed = 0, 0
    if not path or not os.path.exists(path) or _is_protected(path):
        return 0, 0
    for entry in os.scandir(path):
        try:
            sz = _sizeof(entry.path)
            if entry.is_file(follow_symlinks=False):
                os.unlink(entry.path)
            elif entry.is_dir(follow_symlinks=False):
                shutil.rmtree(entry.path, ignore_errors=True)
            deleted += 1
            freed += sz
        except Exception:
            pass
    return deleted, freed


class CleanerTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.columnconfigure(0, weight=1)
        self._checks: dict[str, ctk.BooleanVar] = {}
        self._build_ui()
        self._scan()

    def _build_ui(self):
        ctk.CTkLabel(self, text="Temporary File Cleaner",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 4))

        ctk.CTkLabel(self,
                     text="Select categories to clean. Files cannot be recovered after deletion.",
                     font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w").grid(
            row=1, column=0, sticky="w", pady=(0, 14))

        # ── Category cards ────────────────────────────────────────────
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)

        self._categories = {
            "windows_temp": {
                "label": "Windows Temp Files",
                "icon": "🗂",
                "dirs": [d for d in _TEMP_DIRS if d],
                "size_var": ctk.StringVar(value="Scanning…"),
            },
            "prefetch": {
                "label": "Prefetch Cache",
                "icon": "⚡",
                "dirs": [_PREFETCH],
                "size_var": ctk.StringVar(value="Scanning…"),
            },
            "recycle": {
                "label": "Recycle Bin",
                "icon": "🗑",
                "dirs": [_RECYCLE],
                "size_var": ctk.StringVar(value="Scanning…"),
            },
            "browser": {
                "label": "Browser Caches",
                "icon": "🌐",
                "dirs": _BROWSER_CACHES,
                "size_var": ctk.StringVar(value="Scanning…"),
            },
        }

        for idx, (key, cat) in enumerate(self._categories.items()):
            var = ctk.BooleanVar(value=True)
            self._checks[key] = var
            row, col = divmod(idx, 2)
            card = ctk.CTkFrame(cards, fg_color=BG_CARD,
                                corner_radius=CORNER_RADIUS,
                                border_width=1, border_color=BORDER)
            card.grid(row=row, column=col, padx=(0 if col == 0 else 6, 0),
                      pady=(0, 6), sticky="ew")
            card.columnconfigure(1, weight=1)

            ctk.CTkLabel(card, text=cat["icon"], font=("Segoe UI", 22)).grid(
                row=0, column=0, rowspan=2, padx=(12, 8), pady=12)

            ctk.CTkLabel(card, text=cat["label"], font=FONT_BODY,
                         text_color=TEXT_PRIMARY, anchor="w").grid(
                row=0, column=1, sticky="w", pady=(10, 0))

            sz_lbl = ctk.CTkLabel(card, textvariable=cat["size_var"],
                                   font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w")
            sz_lbl.grid(row=1, column=1, sticky="w", pady=(0, 10))

            ctk.CTkCheckBox(card, text="", variable=var,
                             fg_color=ACCENT, hover_color=ACCENT_HOVER,
                             checkmark_color=TEXT_PRIMARY, width=26).grid(
                row=0, column=2, rowspan=2, padx=12)

        # ── Action buttons ────────────────────────────────────────────
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        ctk.CTkButton(
            btn_bar, text="🔍 Scan Sizes", width=140, height=BTN_HEIGHT,
            fg_color=BG_CARD, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS, command=self._scan).grid(
            row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            btn_bar, text="🗑 Clean Selected", width=160, height=BTN_HEIGHT,
            fg_color=ACCENT_DIM, hover_color=ACCENT,
            text_color=TEXT_PRIMARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS, command=self._clean).grid(
            row=0, column=1, padx=(0, 8))

        ctk.CTkButton(
            btn_bar, text="Select All", width=100, height=BTN_HEIGHT,
            fg_color=BG_CARD, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, font=FONT_SMALL,
            corner_radius=CORNER_RADIUS,
            command=lambda: [v.set(True) for v in self._checks.values()]).grid(
            row=0, column=2, padx=(0, 4))

        ctk.CTkButton(
            btn_bar, text="Deselect All", width=100, height=BTN_HEIGHT,
            fg_color=BG_CARD, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, font=FONT_SMALL,
            corner_radius=CORNER_RADIUS,
            command=lambda: [v.set(False) for v in self._checks.values()]).grid(
            row=0, column=3)

        # ── Log ───────────────────────────────────────────────────────
        self._log_box = ctk.CTkTextbox(
            self, height=180, font=FONT_MONO,
            fg_color=BG_CARD, text_color=TEXT_PRIMARY,
            corner_radius=CORNER_RADIUS, border_width=1, border_color=BORDER)
        self._log_box.grid(row=4, column=0, sticky="ew")
        self._log_box.configure(state="disabled")

    def _append_log(self, text: str):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", text + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _scan(self):
        def do():
            for key, cat in self._categories.items():
                total = sum(_sizeof(d) for d in cat["dirs"] if os.path.exists(d))
                cat["size_var"].set(_fmt_size(total))
        threading.Thread(target=do, daemon=True).start()

    def _clean(self):
        selected = [k for k, v in self._checks.items() if v.get()]
        if not selected:
            return
        parent = self.winfo_toplevel()
        if not ask_confirm(parent, "Clean Temporary Files",
                           f"Clean {len(selected)} selected category(ies)?\n\n"
                           "This action cannot be undone."):
            return

        def do():
            total_files, total_bytes = 0, 0
            for key in selected:
                cat = self._categories[key]
                self.after(0, self._append_log, f"Cleaning {cat['label']}…")
                f, b = 0, 0
                for d in cat["dirs"]:
                    df, db = _clean_dir(d)
                    f += df
                    b += db
                total_files += f
                total_bytes += b
                self.after(0, self._append_log,
                           f"  → Deleted {f} items, freed {_fmt_size(b)}")
                cat["size_var"].set("0 B")

            summary = f"Done — {total_files} items deleted, {_fmt_size(total_bytes)} freed"
            log.success(summary)
            self.after(0, self._append_log, f"\n{summary}\n")

        threading.Thread(target=do, daemon=True).start()
