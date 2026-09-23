@echo off
setlocal
cd /d "%~dp0"
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
title PC Mixer Setup

echo.
echo ==========================================
echo            PC Mixer - Setup
echo ==========================================
echo.

set "PY="
if exist ".venv\Scripts\python.exe" goto :pythonfound
where py >nul 2>nul
if not errorlevel 1 (
  py -3.12 -c "import sys" >nul 2>nul && set "PY=py -3.12" && goto :pythonfound
  py -3.11 -c "import sys" >nul 2>nul && set "PY=py -3.11" && goto :pythonfound
  py -3.10 -c "import sys" >nul 2>nul && set "PY=py -3.10" && goto :pythonfound
)
where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] <= (3,12) else 1)" >nul 2>nul
  if not errorlevel 1 set "PY=python" & goto :pythonfound
)
goto :nopython

:pythonfound
if not exist ".venv\Scripts\python.exe" (
  echo [1/3] Creating virtual environment with %PY%...
  %PY% -m venv .venv
  if errorlevel 1 goto :fail
) else (
  echo [1/3] Virtual environment already exists.
)

echo [2/3] Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [3/3] Creating Desktop and app-folder shortcuts...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\create_shortcuts.ps1" -Root "%ROOT%"
if errorlevel 1 goto :fail

echo.
echo Setup complete.
echo Shortcuts named "PC Mixer" were created on the Desktop and in this folder.
echo First launch: if Windows Firewall asks, allow access on PRIVATE networks.
echo.
echo Starting PC Mixer now...
start "" ".venv\Scripts\pythonw.exe" "%~dp0launcher.pyw"
exit /b 0

:nopython
echo.
echo Supported Python was not found.
echo Install Python 3.12 (recommended), 3.11, or 3.10 from python.org,
echo enable "Add Python to PATH", and run this file again.
pause
exit /b 1

:fail
echo.
echo Setup failed. See the error above.
pause
exit /b 1
