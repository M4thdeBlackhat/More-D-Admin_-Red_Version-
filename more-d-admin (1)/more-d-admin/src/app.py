"""
More-D-Admin — Main Application Window
"""
import sys
import os
import threading
import customtkinter as ctk

from .theme import *
from .tabs.dashboard   import DashboardTab
from .tabs.services    import ServicesTab
from .tabs.processes   import ProcessesTab
from .tabs.startup     import StartupTab
from .tabs.apps        import AppsTab
from .tabs.cleaner     import CleanerTab
from .tabs.files       import FilesTab
from .tabs.registry    import RegistryTab
from .tabs.defender    import DefenderTab
from .tabs.logs_panel  import LogsTab
from .utils            import logger as log

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

_TABS = [
    ("🖥  Dashboard",      DashboardTab),
    ("⚙  Services",        ServicesTab),
    ("⚡  Processes",       ProcessesTab),
    ("🚀  Startup",         StartupTab),
    ("📦  Applications",    AppsTab),
    ("🧹  Cleaner",         CleanerTab),
    ("📁  File Tools",      FilesTab),
    ("🗂  Registry",        RegistryTab),
    ("🛡  Advanced",        DefenderTab),
    ("📋  Logs",            LogsTab),
]


class SidebarButton(ctk.CTkFrame):
    def __init__(self, parent, text: str, is_active: bool, command):
        super().__init__(parent, fg_color=BG_SELECTED if is_active else "transparent",
                         corner_radius=CORNER_RADIUS, cursor="hand2")
        self._cmd = command
        self._text = text
        self._is_active = is_active

        lbl = ctk.CTkLabel(self, text=text, font=FONT_BODY,
                            text_color=ACCENT if is_active else TEXT_SECONDARY,
                            anchor="w", cursor="hand2")
        lbl.pack(fill="x", padx=14, pady=9)

        self.bind("<Button-1>", self._click)
        lbl.bind("<Button-1>", self._click)
        self.bind("<Enter>", self._hover_on)
        self.bind("<Leave>", self._hover_off)

    def _click(self, _):
        self._cmd()

    def _hover_on(self, _):
        if not self._is_active:
            self.configure(fg_color=BG_HOVER)

    def _hover_off(self, _):
        if not self._is_active:
            self.configure(fg_color="transparent")

    def set_active(self, active: bool):
        self._is_active = active
        self.configure(fg_color=BG_SELECTED if active else "transparent")
        for child in self.winfo_children():
            child.configure(
                text_color=ACCENT if active else TEXT_SECONDARY)


class LoadingScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(fg_color=BG_DARK)
        w, h = 400, 280
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        self.lift()
        self.attributes("-topmost", True)

        ctk.CTkLabel(self, text="MORE-D-ADMIN",
                     font=("Segoe UI", 28, "bold"),
                     text_color=ACCENT).pack(pady=(50, 4))

        ctk.CTkLabel(self, text="Professional Admin Toolkit",
                     font=FONT_SMALL, text_color=TEXT_SECONDARY).pack()

        self._bar = ctk.CTkProgressBar(self, width=300, height=6,
                                        fg_color=BG_CARD,
                                        progress_color=ACCENT,
                                        corner_radius=3)
        self._bar.pack(pady=40)
        self._bar.set(0)

        self._lbl = ctk.CTkLabel(self, text="Initializing…",
                                  font=FONT_SMALL, text_color=TEXT_DIM)
        self._lbl.pack()

        ctk.CTkLabel(self, text="Running with Administrator Privileges",
                     font=FONT_SMALL, text_color=TEXT_DIM).pack(pady=(16, 0))

        self._animate(0)

    def _animate(self, step: int):
        msgs = [
            "Requesting admin privileges…",
            "Loading system components…",
            "Initializing service manager…",
            "Loading registry tools…",
            "Preparing UI…",
        ]
        pct = min(step / (len(msgs) - 1), 1.0)
        self._bar.set(pct)
        self._lbl.configure(text=msgs[min(step, len(msgs) - 1)])
        if step < len(msgs) - 1:
            self.after(280, self._animate, step + 1)
        else:
            self.after(400, self.destroy)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("More-D-Admin — Professional Admin Toolkit")
        self.geometry("1280x820")
        self.minsize(1000, 650)
        self.configure(fg_color=BG_DARK)

        try:
            self.iconbitmap(self._find_icon())
        except Exception:
            pass

        self._tab_instances: dict[str, ctk.CTkFrame] = {}
        self._sidebar_btns: list[SidebarButton] = []
        self._current_tab = None

        self._build_ui()
        self._show_loading()
        log.info("More-D-Admin started")

    def _find_icon(self) -> str:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ico = os.path.join(base, "assets", "icon.ico")
        return ico if os.path.exists(ico) else ""

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        # ── Top bar ───────────────────────────────────────────────────
        topbar = ctk.CTkFrame(self, fg_color=BG_PANEL, height=52,
                               corner_radius=0)
        topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        topbar.grid_propagate(False)
        topbar.columnconfigure(1, weight=1)

        logo = ctk.CTkLabel(topbar, text="  MORE-D-ADMIN",
                             font=("Segoe UI", 17, "bold"),
                             text_color=ACCENT)
        logo.grid(row=0, column=0, padx=(16, 0), pady=12, sticky="w")

        admin_badge = ctk.CTkLabel(
            topbar, text="● ADMINISTRATOR",
            font=FONT_SMALL, text_color=TEXT_GREEN)
        admin_badge.grid(row=0, column=1, padx=16, sticky="e")

        # ── Sidebar ───────────────────────────────────────────────────
        sidebar = ctk.CTkFrame(self, fg_color=BG_PANEL, width=SIDEBAR_W,
                                corner_radius=0)
        sidebar.grid(row=1, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.columnconfigure(0, weight=1)

        sep = ctk.CTkFrame(sidebar, fg_color=BORDER, height=1)
        sep.grid(row=0, column=0, sticky="ew", padx=0, pady=(4, 8))

        for i, (label, _cls) in enumerate(_TABS):
            btn = SidebarButton(sidebar, label, i == 0,
                                 command=lambda idx=i: self._switch(idx))
            btn.grid(row=i + 1, column=0, sticky="ew", padx=6, pady=2)
            self._sidebar_btns.append(btn)

        # version footer
        ver = ctk.CTkLabel(sidebar, text="v1.0.0  |  More-D-Admin",
                            font=("Segoe UI", 9), text_color=TEXT_DIM)
        ver.grid(row=len(_TABS) + 2, column=0, pady=(12, 8), sticky="s")
        sidebar.rowconfigure(len(_TABS) + 2, weight=1)

        sep2 = ctk.CTkFrame(self, fg_color=BORDER, width=1)
        sep2.grid(row=1, column=0, sticky="ns")

        # ── Content area ──────────────────────────────────────────────
        self._content = ctk.CTkFrame(self, fg_color=BG_DARK, corner_radius=0)
        self._content.grid(row=1, column=1, sticky="nsew", padx=0)
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(0, weight=1)

        self._switch(0)

    def _show_loading(self):
        loading = LoadingScreen(self)
        self.wait_window(loading)

    def _switch(self, idx: int):
        label, cls = _TABS[idx]

        for i, btn in enumerate(self._sidebar_btns):
            btn.set_active(i == idx)

        for w in self._content.winfo_children():
            w.grid_forget()

        if label not in self._tab_instances:
            self._tab_instances[label] = cls(self._content)

        tab = self._tab_instances[label]
        tab.grid(row=0, column=0, sticky="nsew", padx=24, pady=20)
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(0, weight=1)
        self._current_tab = label
        log.info(f"Switched to tab: {label.strip()}")


def run():
    app = App()
    app.mainloop()
