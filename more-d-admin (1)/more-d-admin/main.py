"""
More-D-Admin — Entry Point
Requests UAC elevation if not already running as Administrator.
"""
import sys
import os
import traceback


def _setup_crash_handler():
    import datetime, pathlib
    log_dir = pathlib.Path(os.environ.get("APPDATA", ".")) / "MoreDAdmin" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    crash_log = log_dir / "crash.log"

    def handle(exc_type, exc_val, exc_tb):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{ts}] CRASH:\n{''.join(traceback.format_exception(exc_type, exc_val, exc_tb))}\n"
        try:
            with open(crash_log, "a") as f:
                f.write(msg)
        except Exception:
            pass
        # Show error dialog
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "More-D-Admin Crashed",
                f"An unexpected error occurred:\n\n{exc_val}\n\n"
                f"Crash log saved to:\n{crash_log}"
            )
            root.destroy()
        except Exception:
            pass
        sys.__excepthook__(exc_type, exc_val, exc_tb)

    sys.excepthook = handle


if __name__ == "__main__":
    _setup_crash_handler()

    # ── Ensure running on Windows ─────────────────────────────────────
    if sys.platform != "win32":
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Platform Error",
            "More-D-Admin is designed for Windows only.\n"
            "Please run this on a Windows system."
        )
        sys.exit(1)

    # ── Request admin elevation ────────────────────────────────────────
    try:
        from src.utils.admin import is_admin, elevate
        if not is_admin():
            elevate()
            sys.exit(0)
    except Exception as e:
        pass  # If elevation check fails, continue anyway

    # ── Launch app ────────────────────────────────────────────────────
    try:
        from src.app import run
        run()
    except Exception as e:
        traceback.print_exc()
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Startup Error", str(e))
            root.destroy()
        except Exception:
            pass
        sys.exit(1)
