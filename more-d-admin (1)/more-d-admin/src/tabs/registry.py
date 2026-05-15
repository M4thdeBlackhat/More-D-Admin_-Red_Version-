"""
Registry Tools tab.
"""
import threading
import winreg
import customtkinter as ctk
from ..theme import *
from ..utils import logger as log
from ..utils.confirm import ask_confirm
from ..utils.restore import create_restore_point

_HIVE_MAP = {
    "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
    "HKEY_CURRENT_USER":  winreg.HKEY_CURRENT_USER,
    "HKEY_USERS":         winreg.HKEY_USERS,
    "HKEY_CLASSES_ROOT":  winreg.HKEY_CLASSES_ROOT,
}

_TYPE_MAP = {
    winreg.REG_SZ:        "REG_SZ",
    winreg.REG_EXPAND_SZ: "REG_EXPAND_SZ",
    winreg.REG_DWORD:     "REG_DWORD",
    winreg.REG_QWORD:     "REG_QWORD",
    winreg.REG_BINARY:    "REG_BINARY",
    winreg.REG_MULTI_SZ:  "REG_MULTI_SZ",
    winreg.REG_NONE:      "REG_NONE",
}


def _read_key(hive_name: str, key_path: str) -> list[dict]:
    hive = _HIVE_MAP.get(hive_name)
    if not hive:
        return []
    try:
        key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ)
        results = []
        i = 0
        while True:
            try:
                name, data, rtype = winreg.EnumValue(key, i)
                results.append({
                    "name": name or "(Default)",
                    "data": str(data)[:120],
                    "type": _TYPE_MAP.get(rtype, f"REG_{rtype}"),
                })
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
        return results
    except Exception as e:
        return [{"name": "Error", "data": str(e), "type": ""}]


def _delete_value(hive_name: str, key_path: str, value_name: str) -> tuple[int, str]:
    hive = _HIVE_MAP.get(hive_name)
    if not hive:
        return 1, "Unknown hive"
    try:
        key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_SET_VALUE)
        real_name = "" if value_name == "(Default)" else value_name
        winreg.DeleteValue(key, real_name)
        winreg.CloseKey(key)
        return 0, "ok"
    except Exception as e:
        return 1, str(e)


def _set_value(hive_name: str, key_path: str,
               value_name: str, data: str, reg_type: str) -> tuple[int, str]:
    hive = _HIVE_MAP.get(hive_name)
    if not hive:
        return 1, "Unknown hive"
    type_rev = {v: k for k, v in _TYPE_MAP.items()}
    rtype = type_rev.get(reg_type, winreg.REG_SZ)
    try:
        key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_SET_VALUE)
        real_name = "" if value_name == "(Default)" else value_name
        if rtype == winreg.REG_DWORD:
            data_val = int(data, 0) if data.startswith("0x") else int(data)
        else:
            data_val = data
        winreg.SetValueEx(key, real_name, 0, rtype, data_val)
        winreg.CloseKey(key)
        return 0, "ok"
    except Exception as e:
        return 1, str(e)


class RegistryTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.columnconfigure(0, weight=1)
        self._results = []
        self._selected_value = None
        self._rows = []
        self._build_ui()

    def _build_ui(self):
        ctk.CTkLabel(self, text="Registry Tools",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY, anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 12))

        # ── Key navigator ─────────────────────────────────────────────
        nav = ctk.CTkFrame(self, fg_color=BG_CARD,
                            corner_radius=CORNER_RADIUS,
                            border_width=1, border_color=BORDER)
        nav.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        nav.columnconfigure(1, weight=1)

        ctk.CTkLabel(nav, text="Hive:", font=FONT_BODY,
                     text_color=TEXT_SECONDARY).grid(row=0, column=0, padx=(14, 6), pady=12)

        self._hive_combo = ctk.CTkOptionMenu(
            nav, values=list(_HIVE_MAP.keys()),
            fg_color=BG_HOVER, button_color=ACCENT_DIM,
            button_hover_color=ACCENT, text_color=TEXT_PRIMARY,
            font=FONT_BODY, corner_radius=CORNER_RADIUS, width=240)
        self._hive_combo.grid(row=0, column=1, padx=6, pady=12, sticky="w")

        ctk.CTkLabel(nav, text="Key Path:", font=FONT_BODY,
                     text_color=TEXT_SECONDARY).grid(row=0, column=2, padx=6)

        self._path_entry = ctk.CTkEntry(
            nav, height=34, fg_color=BG_HOVER, border_color=BORDER,
            text_color=TEXT_PRIMARY, font=FONT_MONO,
            corner_radius=CORNER_RADIUS,
            placeholder_text=r"SOFTWARE\Microsoft\Windows\CurrentVersion")
        self._path_entry.grid(row=0, column=3, padx=6, pady=12, sticky="ew")
        nav.columnconfigure(3, weight=1)

        ctk.CTkButton(
            nav, text="Read Key", width=100, height=34,
            fg_color=ACCENT_DIM, hover_color=ACCENT,
            text_color=TEXT_PRIMARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS, command=self._read).grid(
            row=0, column=4, padx=(6, 14))

        # ── Values table ──────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color=BG_PANEL, corner_radius=CORNER_RADIUS,
            border_width=1, border_color=BORDER, height=220)
        self._scroll.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        self._scroll.columnconfigure(0, weight=1)

        # ── Edit section ──────────────────────────────────────────────
        edit = ctk.CTkFrame(self, fg_color=BG_CARD,
                             corner_radius=CORNER_RADIUS,
                             border_width=1, border_color=BORDER)
        edit.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        edit.columnconfigure(1, weight=1)
        edit.columnconfigure(3, weight=1)

        ctk.CTkLabel(edit, text="Edit / Create Value",
                     font=FONT_HEADING, text_color=TEXT_PRIMARY).grid(
            row=0, column=0, columnspan=6, padx=14, pady=(12, 8), sticky="w")

        ctk.CTkLabel(edit, text="Name:", font=FONT_BODY,
                     text_color=TEXT_SECONDARY).grid(row=1, column=0, padx=(14, 6), pady=(0, 12))
        self._val_name = ctk.CTkEntry(
            edit, height=32, fg_color=BG_HOVER, border_color=BORDER,
            text_color=TEXT_PRIMARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS, placeholder_text="Value name")
        self._val_name.grid(row=1, column=1, padx=6, pady=(0, 12), sticky="ew")

        ctk.CTkLabel(edit, text="Type:", font=FONT_BODY,
                     text_color=TEXT_SECONDARY).grid(row=1, column=2, padx=6)
        self._val_type = ctk.CTkOptionMenu(
            edit, values=list(_TYPE_MAP.values()),
            fg_color=BG_HOVER, button_color=ACCENT_DIM,
            button_hover_color=ACCENT, text_color=TEXT_PRIMARY,
            font=FONT_BODY, corner_radius=CORNER_RADIUS, width=160)
        self._val_type.grid(row=1, column=3, padx=6, sticky="ew")

        ctk.CTkLabel(edit, text="Data:", font=FONT_BODY,
                     text_color=TEXT_SECONDARY).grid(row=1, column=4, padx=6)
        self._val_data = ctk.CTkEntry(
            edit, height=32, fg_color=BG_HOVER, border_color=BORDER,
            text_color=TEXT_PRIMARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS, placeholder_text="Value data")
        self._val_data.grid(row=1, column=5, padx=(6, 14), sticky="ew")
        edit.columnconfigure(5, weight=1)

        btn_row = ctk.CTkFrame(edit, fg_color="transparent")
        btn_row.grid(row=2, column=0, columnspan=6, padx=14, pady=(0, 12), sticky="w")

        ctk.CTkButton(
            btn_row, text="💾 Set Value", width=130, height=32,
            fg_color=ACCENT_DIM, hover_color=ACCENT,
            text_color=TEXT_PRIMARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS, command=self._set_value).grid(row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="🗑 Delete Selected", width=140, height=32,
            fg_color=BG_HOVER, hover_color="#3a1a1a",
            text_color=TEXT_SECONDARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS, command=self._delete_value).grid(row=0, column=1)

        self._status = ctk.CTkLabel(self, text="Enter a registry path and click Read Key.",
                                     font=FONT_SMALL, text_color=TEXT_SECONDARY, anchor="w")
        self._status.grid(row=4, column=0, sticky="w")

    def _read(self):
        hive = self._hive_combo.get()
        path = self._path_entry.get().strip()
        if not path:
            return
        self._status.configure(text="Reading…", text_color=TEXT_SECONDARY)
        threading.Thread(target=self._fetch, args=(hive, path), daemon=True).start()

    def _fetch(self, hive, path):
        results = _read_key(hive, path)
        self.after(0, self._show, results)

    def _show(self, results):
        self._results = results
        self._clear_rows()
        for r in results:
            self._add_row(r)
        self._status.configure(
            text=f"{len(results)} values", text_color=TEXT_SECONDARY)

    def _add_row(self, r: dict):
        row = ctk.CTkFrame(self._scroll, fg_color=BG_CARD,
                            corner_radius=5, border_width=1, border_color=BORDER)
        row.grid(sticky="ew", padx=2, pady=1)
        self._scroll.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)

        ctk.CTkLabel(row, text=r["name"], font=FONT_MONO,
                     text_color=TEXT_ORANGE, width=200, anchor="w").grid(
            row=0, column=0, padx=(10, 6), pady=5)
        ctk.CTkLabel(row, text=r["type"], font=FONT_SMALL,
                     text_color=TEXT_BLUE, width=120, anchor="w").grid(
            row=0, column=1, padx=4)
        ctk.CTkLabel(row, text=r["data"], font=FONT_MONO,
                     text_color=TEXT_PRIMARY, anchor="w").grid(
            row=0, column=2, padx=(4, 10), sticky="ew")
        row.columnconfigure(2, weight=1)

        row.bind("<Button-1>", lambda e, _r=r, _rw=row: self._select(_r, _rw))
        for child in row.winfo_children():
            child.bind("<Button-1>", lambda e, _r=r, _rw=row: self._select(_r, _rw))
        self._rows.append((row, r))

    def _select(self, r, row_widget):
        self._selected_value = r
        for rw, _ in self._rows:
            rw.configure(fg_color=BG_CARD, border_color=BORDER)
        row_widget.configure(fg_color=BG_SELECTED, border_color=ACCENT_DIM)
        self._val_name.delete(0, "end")
        self._val_name.insert(0, r["name"])
        self._val_data.delete(0, "end")
        self._val_data.insert(0, r["data"])

    def _clear_rows(self):
        for w in self._scroll.winfo_children():
            w.destroy()
        self._rows = []
        self._selected_value = None

    def _set_value(self):
        hive = self._hive_combo.get()
        path = self._path_entry.get().strip()
        name = self._val_name.get().strip()
        data = self._val_data.get().strip()
        vtype = self._val_type.get()
        if not all([path, name, data]):
            return
        parent = self.winfo_toplevel()
        if not ask_confirm(parent, "Set Registry Value",
                           f"Set '{name}' = '{data}' ({vtype})\nin {hive}\\{path}?",
                           danger=False):
            return
        create_restore_point(f"Before registry edit: {path}\\{name}")
        def do():
            rc, out = _set_value(hive, path, name, data, vtype)
            (log.success if rc == 0 else log.error)(
                f"Registry set {name}: {'ok' if rc==0 else out}")
            self.after(0, self._read)
        threading.Thread(target=do, daemon=True).start()

    def _delete_value(self):
        if not self._selected_value:
            return
        hive = self._hive_combo.get()
        path = self._path_entry.get().strip()
        name = self._selected_value["name"]
        parent = self.winfo_toplevel()
        if not ask_confirm(parent, "Delete Registry Value",
                           f"Delete value '{name}' from:\n{hive}\\{path}?"):
            return
        create_restore_point(f"Before deleting registry value: {name}")
        def do():
            rc, out = _delete_value(hive, path, name)
            (log.success if rc == 0 else log.error)(
                f"Registry delete {name}: {'ok' if rc==0 else out}")
            self.after(0, self._read)
        threading.Thread(target=do, daemon=True).start()
