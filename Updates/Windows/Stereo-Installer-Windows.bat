@echo off
REM Launcher: fetch + run DiscordVoiceFixer.ps1 (raw + cache-bust each run).
REM Browser: https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/blob/main/Updates/Windows/DiscordVoiceFixer.ps1
REM Linux payloads folder: https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Linux/Updates

title Stereo Installer
echo Fetching latest Stereo Installer from repo, then starting...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$b='https://raw.githubusercontent.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/main/Updates/Windows/DiscordVoiceFixer.ps1'; $u=$b+'?t='+[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(); $c=(Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 120 -Headers @{'Cache-Control'='no-cache'; 'Pragma'='no-cache'}).Content; iex $c"

pause
