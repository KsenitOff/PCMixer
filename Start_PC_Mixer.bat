@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo PC Mixer is not installed yet. Run Install_PC_Mixer.bat first.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "%~dp0launcher.pyw"
