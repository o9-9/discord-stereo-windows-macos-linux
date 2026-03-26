@echo off
REM Launcher only: downloads the latest DiscordVoiceFixer.ps1 from main and runs it via Invoke-Expression.
REM Each run uses a cache-busted URL so you always get the current installer script.

title Stereo Installer
echo Fetching latest Stereo Installer from repo, then starting...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$b='https://raw.githubusercontent.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/main/Updates/Windows/DiscordVoiceFixer.ps1'; $u=$b+'?t='+[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(); $c=(Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 120 -Headers @{'Cache-Control'='no-cache'; 'Pragma'='no-cache'}).Content; iex $c"

pause
