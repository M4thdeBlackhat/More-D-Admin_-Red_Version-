"""
System restore-point helpers.
"""
from .admin import run_powershell
from . import logger as log


def create_restore_point(description: str = "More-D-Admin action") -> bool:
    """
    Create a Windows System Restore point.
    Returns True on success.
    """
    script = (
        f"Checkpoint-Computer -Description '{description}' "
        f"-RestorePointType 'MODIFY_SETTINGS'"
    )
    rc, out = run_powershell(script)
    if rc == 0:
        log.success(f"Restore point created: {description}")
        return True
    else:
        log.error(f"Restore point failed: {out}")
        return False
