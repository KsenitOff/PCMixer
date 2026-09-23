@echo off
net session >nul 2>&1
if %errorlevel% neq 0 (
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
powershell -NoProfile -Command "Get-NetFirewallRule -DisplayName 'PC Mixer (Private LAN)' -ErrorAction SilentlyContinue | Remove-NetFirewallRule; New-NetFirewallRule -DisplayName 'PC Mixer (Private LAN)' -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8765 -Profile Private"
echo.
echo PC Mixer firewall rule added for Private networks only.
pause
