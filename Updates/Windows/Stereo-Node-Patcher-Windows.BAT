@echo off
REM Launcher only: downloads the latest Discord_voice_node_patcher.ps1 from main, then runs it.
REM Each run uses a cache-busted URL so you get the current script, not a stale CDN copy.

title Discord Voice Node Patcher
echo Fetching latest Voice Node Patcher from repo, then starting...
echo.

set "PS1=%TEMP%\discord_voice_node_patcher.ps1"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$u='https://raw.githubusercontent.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/main/Updates/Windows/Discord_voice_node_patcher.ps1?t='+[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(); Invoke-WebRequest -Uri $u -OutFile '%PS1%' -UseBasicParsing -TimeoutSec 120 -Headers @{'Cache-Control'='no-cache'; 'Pragma'='no-cache'}"

if errorlevel 1 (
  echo Download failed.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
pause
