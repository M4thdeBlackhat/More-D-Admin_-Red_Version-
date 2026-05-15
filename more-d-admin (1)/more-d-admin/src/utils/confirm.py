"""
Reusable confirmation dialog for destructive actions.
"""
import customtkinter as ctk
from ..theme import *


class ConfirmDialog(ctk.CTkToplevel):
    """
    Modal dialog that requires the user to confirm a destructive action.
    Returns True if confirmed, False otherwise.
    """

    def __init__(self, parent, title: str, message: str,
                 confirm_text: str = "Confirm", danger: bool = True):
        super().__init__(parent)
        self.result = False
        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=BG_PANEL)
        self.grab_set()

        w, h = 420, 200
        self.geometry(f"{w}x{h}")
        self._center(parent, w, h)

        # Icon row
        icon = "⚠" if danger else "ℹ"
        color = TEXT_RED if danger else TEXT_BLUE
        ctk.CTkLabel(self, text=icon, font=("Segoe UI", 32),
                     text_color=color).pack(pady=(18, 4))

        ctk.CTkLabel(self, text=message, font=FONT_BODY,
                     text_color=TEXT_PRIMARY, wraplength=380,
                     justify="center").pack(padx=20)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=18)

        cancel = ctk.CTkButton(
            btn_frame, text="Cancel", width=120, height=BTN_HEIGHT,
            fg_color=BG_CARD, hover_color=BG_HOVER,
            text_color=TEXT_SECONDARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS,
            command=self._cancel,
        )
        cancel.grid(row=0, column=0, padx=8)

        ok_color = ACCENT if danger else "#1a5fa8"
        ok_hover = ACCENT_HOVER if danger else "#2a7fd8"
        confirm_btn = ctk.CTkButton(
            btn_frame, text=confirm_text, width=120, height=BTN_HEIGHT,
            fg_color=ok_color, hover_color=ok_hover,
            text_color=TEXT_PRIMARY, font=FONT_BODY,
            corner_radius=CORNER_RADIUS,
            command=self._confirm,
        )
        confirm_btn.grid(row=0, column=1, padx=8)

        self.wait_window()

    def _center(self, parent, w, h):
        px = parent.winfo_rootx() + parent.winfo_width() // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"+{px - w//2}+{py - h//2}")

    def _confirm(self):
        self.result = True
        self.destroy()

    def _cancel(self):
        self.result = False
        self.destroy()


def ask_confirm(parent, title: str, message: str,
                confirm_text: str = "Confirm", danger: bool = True) -> bool:
    dlg = ConfirmDialog(parent, title, message, confirm_text, danger)
    return dlg.result
