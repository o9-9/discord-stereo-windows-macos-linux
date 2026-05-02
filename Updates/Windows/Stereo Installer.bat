@echo off
title Stereo Installer (Voice Fixer)
REM Fetches DiscordVoiceFixer.ps1 from bundle repo. Hub: STEREO_HUB\Launch Stereo Hub.bat
echo Fetching Voice Fixer...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$b='https://raw.githubusercontent.com/o9-9/discord-stereo-windows-macos-linux/main/Updates/Windows/DiscordVoiceFixer.ps1'; $u=$b+'?t='+[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(); iex (Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 120 -Headers @{'Cache-Control'='no-cache'; 'Pragma'='no-cache'}).Content"
