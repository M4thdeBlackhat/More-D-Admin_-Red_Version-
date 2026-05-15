# More-D-Admin — Build Instructions

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Windows | 10 / 11 | Required (uses Windows-only APIs) |
| Python | 3.11 or 3.12 | Add to PATH during install |
| pip | latest | Bundled with Python |

---

## Quick Build (Recommended)

Double-click **`build.bat`** — it handles everything automatically:

1. Installs all Python dependencies
2. Locates the `customtkinter` data directory
3. Runs PyInstaller with the correct flags
4. Opens the `dist/` folder when done

The output is **`dist/MoreDAdmin.exe`** — a single self-contained executable.

---

## Manual Build

```bat
REM Install dependencies
pip install -r requirements.txt

REM Get customtkinter path
python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"
REM Copy the output path — you need it below

REM Build (replace <CTK_PATH> with the path printed above)
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "MoreDAdmin" ^
    --icon "assets\icon.ico" ^
    --add-data "<CTK_PATH>;customtkinter" ^
    --add-data "assets;assets" ^
    --hidden-import "customtkinter" ^
    --hidden-import "PIL" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "psutil" ^
    --hidden-import "winreg" ^
    --uac-admin ^
    --version-file "version_info.txt" ^
    main.py
```

---

## Run Without Building (Development)

```bat
pip install -r requirements.txt
python main.py
```

> The app auto-requests UAC elevation on startup. Run from an
> account that can approve the UAC prompt, or right-click and
> choose "Run as Administrator".

---

## Project Structure

```
more-d-admin/
├── main.py                  Entry point — UAC elevation + crash handler
├── requirements.txt         Python dependencies
├── build.bat                One-click PyInstaller build script
├── version_info.txt         Windows version metadata for the .exe
├── assets/
│   └── icon.ico             Application icon (place your .ico here)
└── src/
    ├── app.py               Main CTk window, sidebar, tab router
    ├── theme.py             Color palette, fonts, sizing constants
    ├── utils/
    │   ├── admin.py         UAC / run_as_admin / run_powershell helpers
    │   ├── confirm.py       Reusable confirmation dialog
    │   ├── logger.py        Action logger (file + live broadcast)
    │   └── restore.py       System restore-point creation
    └── tabs/
        ├── dashboard.py     System info dashboard + live metrics
        ├── services.py      Windows service manager
        ├── processes.py     Process manager with force-kill
        ├── startup.py       Startup app manager (registry)
        ├── apps.py          Installed apps / uninstaller
        ├── cleaner.py       Temp file cleaner
        ├── files.py         File tools — ownership, unlock, delete, permissions
        ├── registry.py      Registry viewer / editor
        ├── defender.py      Defender, WU, hidden files, optimization
        └── logs_panel.py    Action log history panel
```

---

## Features at a Glance

| Tab | What it does |
|---|---|
| Dashboard | Live CPU / RAM / Disk metrics, top processes |
| Services | Start / stop / disable Windows services |
| Processes | Process list with force-kill and graceful terminate |
| Startup | View and remove registry startup entries |
| Applications | Browse and uninstall installed apps |
| Cleaner | Delete temp files, prefetch, recycle bin, browser caches |
| File Tools | Take ownership, unlock locked files, force delete, icacls |
| Registry | Read / edit / delete registry values |
| Advanced | Toggle Defender, Windows Update, hidden files, optimization |
| Logs | Full timestamped action history with level filtering |

---

## Security Notes

- Every destructive action shows a confirmation dialog
- Critical system paths (`System32`, `SysWOW64`) are blocked from deletion
- A System Restore point is created automatically before high-risk operations
- All actions are logged to `%APPDATA%\MoreDAdmin\logs\actions.log`
- Crashes are logged to `%APPDATA%\MoreDAdmin\logs\crash.log`

---

## Troubleshooting

**"Access denied" errors** — ensure the UAC prompt was accepted on startup.

**PyInstaller `hidden-import` errors** — run `pip install --upgrade pyinstaller` then rebuild.

**`customtkinter` not found in the exe** — confirm `--add-data` in `build.bat` points to the correct path printed by `python -c "import customtkinter, os; print(os.path.dirname(customtkinter.__file__))"`.

**App won't start on another PC** — ensure the target PC has the Visual C++ Redistributable installed (usually pre-installed on Windows 10/11).
