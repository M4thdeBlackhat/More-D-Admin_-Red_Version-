@echo off
setlocal EnableDelayedExpansion
title More-D-Admin — Build .exe
color 0C

echo.
echo  ============================================================
echo   MORE-D-ADMIN  ^|  PyInstaller Build Script
echo  ============================================================
echo.

REM ── Find Python ───────────────────────────────────────────────
set PYTHON_EXE=
python --version >nul 2>&1
if !errorlevel! equ 0 set PYTHON_EXE=python

if "!PYTHON_EXE!"=="" (
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "C:\Python312\python.exe"
        "C:\Python311\python.exe"
    ) do (
        if exist %%~P (
            set PYTHON_EXE=%%~P
            goto :got_py
        )
    )
    echo  [ERROR] Python not found. Run launch.bat first to auto-install it.
    pause & exit /b 1
)
:got_py
echo  [OK] Python: %PYTHON_EXE%

REM ── Install deps ─────────────────────────────────────────────
echo  [1/4] Installing/updating build dependencies...
%PYTHON_EXE% -m pip install customtkinter psutil pillow pyinstaller --quiet --upgrade
if !errorlevel! neq 0 (
    echo  [ERROR] pip install failed.
    pause & exit /b 1
)

REM ── Generate icon if missing ──────────────────────────────────
if not exist "assets\icon.ico" (
    echo  [1b ] Generating icon...
    %PYTHON_EXE% create_icon.py
)

REM ── Get customtkinter path ───────────────────────────────────
echo  [2/4] Locating customtkinter data...
for /f "delims=" %%i in ('%PYTHON_EXE% -c "import customtkinter,os;print(os.path.dirname(customtkinter.__file__))"') do set CTK_PATH=%%i
echo       Path: !CTK_PATH!

REM ── Run PyInstaller ───────────────────────────────────────────
echo  [3/4] Building standalone .exe (this may take 1-3 minutes)...

set ICON_FLAG=
if exist "assets\icon.ico" set ICON_FLAG=--icon "assets\icon.ico"

%PYTHON_EXE% -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "MoreDAdmin" ^
    %ICON_FLAG% ^
    --add-data "!CTK_PATH!;customtkinter" ^
    --add-data "assets;assets" ^
    --hidden-import "customtkinter" ^
    --hidden-import "PIL" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "psutil" ^
    --hidden-import "winreg" ^
    --uac-admin ^
    --version-file "version_info.txt" ^
    --clean ^
    --noconfirm ^
    main.py

if !errorlevel! neq 0 (
    echo.
    echo  [ERROR] Build failed. See output above for details.
    pause & exit /b 1
)

echo.
echo  ============================================================
echo   [4/4] BUILD COMPLETE!
echo.
echo   Output:  dist\MoreDAdmin.exe
echo.
echo   - Double-click MoreDAdmin.exe to launch
echo   - It will auto-request admin (UAC) on startup
echo   - No Python required on the target PC
echo  ============================================================
echo.

REM Open the dist folder
explorer dist

pause
