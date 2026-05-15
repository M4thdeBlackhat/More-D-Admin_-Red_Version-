@echo off
setlocal EnableDelayedExpansion
title More-D-Admin Launcher
color 0C

echo.
echo  ============================================================
echo   MORE-D-ADMIN  ^|  Professional Admin Toolkit
echo   Launcher v1.0
echo  ============================================================
echo.

REM ── Step 1: Check for Python ─────────────────────────────────
set PYTHON_EXE=
for %%P in (
    "python"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
) do (
    if exist %%~P (
        set PYTHON_EXE=%%~P
        goto :found_python
    )
)

REM Try PATH
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set PYTHON_EXE=python
    goto :found_python
)

REM Python not found — install via winget
echo  [!] Python not found. Installing Python 3.12 via winget...
echo      (This only happens once)
echo.
winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
if !errorlevel! neq 0 (
    echo.
    echo  [ERROR] Automatic install failed.
    echo  Please download Python 3.12+ from https://python.org
    echo  Tick "Add Python to PATH" during installation, then run this again.
    echo.
    pause
    exit /b 1
)

REM Refresh PATH after install
set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;%PATH%"
set PYTHON_EXE=python

:found_python
echo  [OK] Python found: %PYTHON_EXE%

REM ── Step 2: Ensure pip is up to date ─────────────────────────
%PYTHON_EXE% -m pip install --upgrade pip --quiet 2>nul

REM ── Step 3: Install dependencies (silently) ──────────────────
echo  [..] Checking dependencies...

%PYTHON_EXE% -c "import customtkinter" 2>nul
if !errorlevel! neq 0 (
    echo  [..] Installing customtkinter...
    %PYTHON_EXE% -m pip install customtkinter --quiet
)

%PYTHON_EXE% -c "import psutil" 2>nul
if !errorlevel! neq 0 (
    echo  [..] Installing psutil...
    %PYTHON_EXE% -m pip install psutil --quiet
)

%PYTHON_EXE% -c "import PIL" 2>nul
if !errorlevel! neq 0 (
    echo  [..] Installing Pillow...
    %PYTHON_EXE% -m pip install pillow --quiet
)

echo  [OK] All dependencies ready.
echo.
echo  [>>] Starting More-D-Admin...
echo.

REM ── Step 4: Launch (windowless via pythonw) ──────────────────
REM Find pythonw.exe next to python.exe for a console-free launch
set PYTHONW_EXE=%PYTHON_EXE:python.exe=pythonw.exe%
if exist "%PYTHONW_EXE%" (
    start "" "%PYTHONW_EXE%" "%~dp0main.py"
) else (
    REM Fallback: use pythonw from PATH
    where pythonw >nul 2>&1
    if !errorlevel! equ 0 (
        start "" pythonw "%~dp0main.py"
    ) else (
        REM Last resort: use python (console will flash briefly then close)
        start "" %PYTHON_EXE% "%~dp0main.py"
    )
)

REM Close this launcher window
exit
