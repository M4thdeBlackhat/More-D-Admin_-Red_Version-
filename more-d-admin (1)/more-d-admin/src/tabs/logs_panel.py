"""
Action Logs / History panel tab.
"""
import customtkinter as ctk
from ..theme import *
from ..utils import logger as log

_LEVEL_COLORS = {
    "INFO":    TEXT_SECONDARY,
    "SUCCESS": TEXT_GREEN,
    "WARNING": TEXT_ORANGE,
    "ERROR":   TEXT_RED,
    "ACTION":  TEXT_BLUE,
}


class LogsTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._build_ui()
        self._load_history()
        log.subscribe(self._on_log)

    def _build_ui(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        hdr.columnconfigure(1, weight=1)

        ctk.CTkLabel(hdr, text="Action Logs",
                     font=FONT_TITLE, text_color=TEXT_PRIMARY).grid(
            row=0, column=0, sticky="w")

        btn_row = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_row.grid(row=0, column=1, sticky="e")

        ctk.CTkButton(
            btn_row, text="↻ Reload from File", width=150, height=32,
            fg_color=BG_CARD, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, font=FONT_SMALL,
            corner_radius=CORNER_RADIUS, command=self._load_history).grid(
            row=0, column=0, padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="🗑 Clear Log", width=110, height=32,
            fg_color=ACCENT_DIM, hover_color=ACCENT,
            text_color=TEXT_PRIMARY, font=FONT_SMALL,
            corner_radius=CORNER_RADIUS, command=self._clear).grid(
            row=0, column=1)

        self._filter_var = ctk.StringVar(value="ALL")
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.grid(row=1, column=0, sticky="w", pady=(0, 8))

        ctk.CTkLabel(filter_frame, text="Filter:",
                     font=FONT_SMALL, text_color=TEXT_SECONDARY).grid(
            row=0, column=0, padx=(0, 8))

        for i, level in enumerate(["ALL", "SUCCESS", "ERROR", "WARNING", "INFO", "ACTION"]):
            color = _LEVEL_COLORS.get(level, TEXT_SECONDARY)
            btn = ctk.CTkButton(
                filter_frame, text=level, width=80, height=26,
                fg_color=BG_CARD, hover_color=BG_HOVER,
                text_color=color, font=FONT_SMALL,
                corner_radius=CORNER_RADIUS,
                command=lambda l=level: self._set_filter(l))
            btn.grid(row=0, column=i + 1, padx=3)

        self._textbox = ctk.CTkTextbox(
            self, font=FONT_MONO, fg_color=BG_CARD,
            text_color=TEXT_PRIMARY, corner_radius=CORNER_RADIUS,
            border_width=1, border_color=BORDER, wrap="word")
        self._textbox.grid(row=2, column=0, sticky="nsew")
        self._textbox.configure(state="disabled")

        self._textbox.tag_config("INFO",    foreground=TEXT_SECONDARY)
        self._textbox.tag_config("SUCCESS", foreground=TEXT_GREEN)
        self._textbox.tag_config("WARNING", foreground=TEXT_ORANGE)
        self._textbox.tag_config("ERROR",   foreground=TEXT_RED)
        self._textbox.tag_config("ACTION",  foreground=TEXT_BLUE)

        self._current_filter = "ALL"

    def _load_history(self):
        lines = log.read_log()
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        for line in lines:
            self._insert_line(line.rstrip())
        self._textbox.see("end")
        self._textbox.configure(state="disabled")

    def _on_log(self, level: str, entry: str):
        """Called by logger on each new log entry (real-time)."""
        self.after(0, self._append_live, level, entry)

    def _append_live(self, level: str, entry: str):
        if self._current_filter not in ("ALL", level):
            return
        self._textbox.configure(state="normal")
        self._textbox.insert("end", entry + "\n", level)
        self._textbox.see("end")
        self._textbox.configure(state="disabled")

    def _insert_line(self, line: str):
        tag = "INFO"
        for lvl in ("SUCCESS", "ERROR", "WARNING", "ACTION", "INFO"):
            if f"[{lvl}]" in line:
                tag = lvl
                break
        if self._current_filter in ("ALL", tag):
            self._textbox.insert("end", line + "\n", tag)

    def _set_filter(self, level: str):
        self._current_filter = level
        self._load_history()

    def _clear(self):
        log.clear_log()
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.configure(state="disabled")
