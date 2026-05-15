"""
File Tools tab — Take Ownership, Unlock, Delete, Permission Editor.
"""
import os
import threading
import customtkinter as ctk
from tkinter import filedialog
from ..theme import *
from ..utils import logger as log
from ..utils.confirm import ask_confirm
from ..utils.admin import run_as_admin, run_powershell
from ..utils.restore import create_restore_point

PROTECTED_PATHS = {
    r"C:\Windows\System32",
    r"C:\Windows\SysWOW64",
    r"C:\Windows\boot",
}


def _is_critical(path: str) -> bool:
    norm = os.path.normcase(os.path.abspath(path))
    for p in PROTECTED_PATHS:
        if norm.startswith(os.path.normcase(p)):
            return True
    return False


def _take_ownership(path: str) -> tuple[int, str]:
    rc1, _ = run_as_admin(f'takeown /f "{path}" /r /d y')
    rc2, out = run_as_admin(
        f'icacls "{path}" /grant *S-1-5-32-544:F /t /c /l /q')
    return max(rc1, rc2), out


def _unlock_file(path: str) -> tuple[int, str]:
    """Use handle.exe (Sysinternals) if available, else PowerShell fallback."""
    script = (
        f"$locked = '{path}'; "
        "$processes = Get-Process | Where-Object { "
        "  $_.Modules | Where-Object { $_.FileName -eq $locked } "
        "}; "
        "foreach ($p in $processes) { Stop-Process -Id $p.Id -Force }; "
        "Write-Output 'Done'"
    )
    return run_powershell(script)


def _delete_path(path: str) -> tuple[int, str]:
    if os.path.isfile(path):
        rc, out = run_as_admin(f'del /f /q "{path}"')
    else:
        rc, out = run_as_admin(f'rd /s /q "{path}"')
    return rc, out


def _get_permissions(path: str) -> str:
    rc, out = run_as_admin(f'icacls "{path}"')
    return out if rc == 0 else f"Error: {out}"


def _set_permissions(path: str, user: str, perms: str) -> tuple[int, str]:
    return run_as_admin(f'icacls "{path}" /grant "{user}:{perms}" /t /c')


class FilesTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.columnconfigure(0, weight=1)
        self._path_var = ctk.StringVar()
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self, text="File & Folder Tools",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 12))

        # ── Path selector ─────────────────────────────────────────────
        path_frame = ctk.CTkFrame(self, fg_color=BG_CARD,
                                   corner_radius=CORNER_RADIUS,
                                   border_width=1, border_color=BORDER)
        path_frame.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        path_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(path_frame, text="Target Path",
                     font=FONT_BODY, text_color=TEXT_SECONDARY).grid(
            row=0, column=0, padx=14, pady=12)

        self._path_entry = ctk.CTkEntry(
            path_frame, textvariable=self._path_var,
            height=34, fg_color=BG_HOVER, border_color=BORDER,
            text_color=TEXT_PRIMARY, font=FONT_MONO,
            corner_radius=CORNER_RADIUS, placeholder_text="Select a file or folder…")
        self._path_entry.grid(row=0, column=1, padx=8, pady=12, sticky="ew")

        ctk.CTkButton(
            path_frame, text="📁 Browse File", width=120, height=34,
            fg_color=BG_HOVER, hover_color=BG_SELECTED,
            text_color=TEXT_SECONDARY, font=FONT_SMALL,
            corner_radius=CORNER_RADIUS, command=self._browse_file).grid(
            row=0, column=2, padx=4)

        ctk.CTkButton(
            path_frame, text="📂 Browse Folder", width=130, height=34,
            fg_color=BG_HOVER, hover_color=BG_SELECTED,
            text_color=TEXT_SECONDARY, font=FONT_SMALL,
            corner_radius=CORNER_RADIUS, command=self._browse_folder).grid(
            row=0, column=3, padx=(4, 12))

        # ── Action buttons ────────────────────────────────────────────
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 14))

        buttons = [
            ("👑 Take Ownership",  self._take_ownership,  ACCENT_DIM,   ACCENT),
            ("🔓 Unlock File",     self._unlock,           "#1a3a5c",    "#2460a0"),
            ("🗑 Force Delete",    self._force_delete,     "#4a1a00",    "#aa3300"),
            ("🔒 View Perms",      self._view_perms,       BG_CARD,      BG_HOVER),
        ]
        for col, (txt, cmd, bg, hv) in enumerate(buttons):
            ctk.CTkButton(
                actions, text=txt, height=BTN_HEIGHT, width=155,
                fg_color=bg, hover_color=hv,
                text_color=TEXT_PRIMARY, font=FONT_BODY,
                corner_radius=CORNER_RADIUS, command=cmd).grid(
                row=0, column=col, padx=(0 if col == 0 else 6, 0))

        # ── Permission editor ─────────────────────────────────────────
        perm_frame = ctk.CTkFrame(self, fg_color=BG_CARD,
                                   corner_radius=CORNER_RADIUS,
                                   border_width=1, border_color=BORDER)
        perm_frame.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        perm_frame.columnconfigure(1, weight=1)

        ctk.CTkLabel(perm_frame, text="Grant Permission",
                     font=FONT_HEADING, text_color=TEXT_PRIMARY).grid(
            row=0, column=0, columnspan=4, padx=14, pady=(12, 8), sticky="w")

        ctk.CTkLabel(perm_frame, text="User/Group:",
                     font=FONT_BODY, text_color=TEXT_SECONDARY).grid(
            row=1, column=0, padx=14, pady=(0, 12))

        self._user_entry = ctk.CTkEntry(
            perm_frame, height=32, width=180, fg_color=BG_HOVER,
            border_color=BORDER, text_color=TEXT_PRIMARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS, placeholder_text="DOMAIN\\User or Everyone")
        self._user_entry.grid(row=1, column=1, padx=8, pady=(0, 12), sticky="w")

        ctk.CTkLabel(perm_frame, text="Permission:",
                     font=FONT_BODY, text_color=TEXT_SECONDARY).grid(
            row=1, column=2, padx=8)

        self._perm_combo = ctk.CTkOptionMenu(
            perm_frame, values=["F (Full Control)", "M (Modify)",
                                "RX (Read & Execute)", "R (Read)", "W (Write)"],
            fg_color=BG_HOVER, button_color=ACCENT_DIM,
            button_hover_color=ACCENT, text_color=TEXT_PRIMARY,
            font=FONT_BODY, corner_radius=CORNER_RADIUS, width=200)
        self._perm_combo.grid(row=1, column=3, padx=(4, 14))

        ctk.CTkButton(
            perm_frame, text="Apply Permission", height=32, width=150,
            fg_color=ACCENT_DIM, hover_color=ACCENT,
            text_color=TEXT_PRIMARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS, command=self._apply_perms).grid(
            row=2, column=0, columnspan=4, padx=14, pady=(0, 12), sticky="w")

        # ── Output ────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="Output", font=FONT_HEADING,
                     text_color=TEXT_PRIMARY, anchor="w").grid(
            row=4, column=0, sticky="w", pady=(0, 6))

        self._output = ctk.CTkTextbox(
            self, height=200, font=FONT_MONO,
            fg_color=BG_CARD, text_color=TEXT_PRIMARY,
            corner_radius=CORNER_RADIUS, border_width=1, border_color=BORDER)
        self._output.grid(row=5, column=0, sticky="ew")
        self._output.configure(state="disabled")

    def _browse_file(self):
        p = filedialog.askopenfilename()
        if p:
            self._path_var.set(p)

    def _browse_folder(self):
        p = filedialog.askdirectory()
        if p:
            self._path_var.set(p)

    def _path(self) -> str:
        return self._path_var.get().strip()

    def _log(self, text: str):
        self._output.configure(state="normal")
        self._output.insert("end", text + "\n")
        self._output.see("end")
        self._output.configure(state="disabled")

    def _guard(self) -> bool:
        p = self._path()
        if not p:
            self._log("ERROR: No path selected.")
            return False
        if _is_critical(p):
            self._log(f"BLOCKED: '{p}' is a critical system path.")
            return False
        if not os.path.exists(p):
            self._log(f"ERROR: Path does not exist: {p}")
            return False
        return True

    def _take_ownership(self):
        if not self._guard():
            return
        p = self._path()
        parent = self.winfo_toplevel()
        if not ask_confirm(parent, "Take Ownership",
                           f"Take ownership of:\n{p}\n\nThis modifies file permissions."):
            return
        def do():
            rc, out = _take_ownership(p)
            msg = f"Ownership taken: {p}" if rc == 0 else f"Failed: {out}"
            (log.success if rc == 0 else log.error)(msg)
            self.after(0, self._log, out or msg)
        threading.Thread(target=do, daemon=True).start()

    def _unlock(self):
        if not self._guard():
            return
        def do():
            rc, out = _unlock_file(self._path())
            msg = f"Unlock attempted: {out}"
            (log.success if rc == 0 else log.warning)(msg)
            self.after(0, self._log, msg)
        threading.Thread(target=do, daemon=True).start()

    def _force_delete(self):
        if not self._guard():
            return
        p = self._path()
        parent = self.winfo_toplevel()
        if not ask_confirm(parent, "Force Delete",
                           f"Permanently delete:\n{p}\n\n"
                           "This CANNOT be undone. A restore point will be created first."):
            return
        create_restore_point(f"Before force-delete {os.path.basename(p)}")
        def do():
            rc, out = _delete_path(p)
            msg = f"Deleted: {p}" if rc == 0 else f"Delete failed: {out}"
            (log.success if rc == 0 else log.error)(msg)
            self.after(0, self._log, msg)
        threading.Thread(target=do, daemon=True).start()

    def _view_perms(self):
        if not self._guard():
            return
        def do():
            out = _get_permissions(self._path())
            self.after(0, self._log, out)
        threading.Thread(target=do, daemon=True).start()

    def _apply_perms(self):
        if not self._guard():
            return
        user  = self._user_entry.get().strip()
        perm  = self._perm_combo.get().split()[0]
        if not user:
            self._log("ERROR: No user/group specified.")
            return
        parent = self.winfo_toplevel()
        if not ask_confirm(parent, "Apply Permission",
                           f"Grant '{user}' permission '{perm}' on:\n{self._path()}"):
            return
        def do():
            rc, out = _set_permissions(self._path(), user, perm)
            (log.success if rc == 0 else log.error)(
                f"Permission {perm} on {self._path()} for {user}: {'ok' if rc==0 else out}")
            self.after(0, self._log, out)
        threading.Thread(target=do, daemon=True).start()
