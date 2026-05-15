"""
UAC / administrator elevation helpers.
"""
import sys
import os
import ctypes
import subprocess
import winreg


def is_admin() -> bool:
    """Return True if the current process has administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def elevate():
    """Re-launch the current script with administrator rights via ShellExecute."""
    if is_admin():
        return
    script = os.path.abspath(sys.argv[0])
    params = " ".join(f'"{a}"' for a in sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{script}" {params}', None, 1
    )
    sys.exit(0)


def run_as_admin(cmd: str | list, capture: bool = True) -> tuple[int, str]:
    """
    Run a shell command (already elevated since this process is admin).
    Returns (returncode, combined stdout+stderr).
    """
    if isinstance(cmd, str):
        cmd = ["cmd", "/c", cmd]
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if capture else 0,
        )
        out = (result.stdout or "") + (result.stderr or "")
        return result.returncode, out.strip()
    except Exception as exc:
        return 1, str(exc)


def run_powershell(script: str, capture: bool = True) -> tuple[int, str]:
    """Run a PowerShell script string and return (returncode, output)."""
    cmd = [
        "powershell", "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass", "-Command", script,
    ]
    return run_as_admin(cmd, capture=capture)
