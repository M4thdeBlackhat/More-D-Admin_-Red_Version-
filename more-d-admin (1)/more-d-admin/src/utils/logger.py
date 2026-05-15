"""
Action logger — writes to file and broadcasts to the in-app log panel.
"""
import os
import logging
import datetime
from pathlib import Path

LOG_DIR  = Path(os.environ.get("APPDATA", ".")) / "MoreDAdmin" / "logs"
LOG_FILE = LOG_DIR / "actions.log"

_subscribers: list = []

def _ensure_dir():
    LOG_DIR.mkdir(parents=True, exist_ok=True)

def subscribe(callback):
    """Register a callable that receives (level, message) on each log entry."""
    _subscribers.append(callback)

def _broadcast(level: str, message: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] [{level}] {message}"
    for cb in _subscribers:
        try:
            cb(level, entry)
        except Exception:
            pass

def _write(level: str, message: str):
    _ensure_dir()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {message}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    _broadcast(level, message)

def info(msg: str):    _write("INFO",    msg)
def success(msg: str): _write("SUCCESS", msg)
def warning(msg: str): _write("WARNING", msg)
def error(msg: str):   _write("ERROR",   msg)
def action(msg: str):  _write("ACTION",  msg)

def read_log() -> list[str]:
    _ensure_dir()
    if not LOG_FILE.exists():
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return f.readlines()
    except Exception:
        return []

def clear_log():
    _ensure_dir()
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("")
        info("Log cleared")
    except Exception:
        pass
