#requires -Version 5.1
<#
.SYNOPSIS
  AST-parse Discord_voice_node_patcher.ps1 (local path or raw URL). Exit 1 on errors.
.EXAMPLE
  .\validate_discord_voice_node_patcher.ps1
.EXAMPLE
  .\validate_discord_voice_node_patcher.ps1 -Url 'https://raw.githubusercontent.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/main/Updates/Windows/Discord_voice_node_patcher.ps1'
#>
param(
    [string]$Path = "",
    [string]$Url = ""
)

$ErrorActionPreference = "Stop"
$tmp = $null
try {
    if ($Url) {
        $tmp = Join-Path $env:TEMP ("dvp_validate_{0}.ps1" -f [Guid]::NewGuid().ToString("N"))
        $sep = if ($Url -match "\?") { "&" } else { "?" }
        $fetch = "$Url$sep" + "t=$([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())"
        Invoke-WebRequest -Uri $fetch -OutFile $tmp -UseBasicParsing -TimeoutSec 120 -Headers @{
            "Cache-Control" = "no-cache"
            "Pragma"        = "no-cache"
        }
        $Path = $tmp
    }
    if (-not $Path) {
        $Path = Join-Path $PSScriptRoot "Discord_voice_node_patcher.ps1"
    }
    if (-not (Test-Path -LiteralPath $Path)) {
        Write-Error "File not found: $Path"
    }
    $full = (Resolve-Path -LiteralPath $Path).Path
    $tok = $null
    $err = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile($full, [ref]$tok, [ref]$err)
    if ($err -and $err.Count -gt 0) {
        foreach ($e in $err) { Write-Host $e.ToString() -ForegroundColor Red }
        exit 1
    }
    Write-Host "OK: parse $full" -ForegroundColor Green
    exit 0
}
finally {
    if ($tmp -and (Test-Path -LiteralPath $tmp)) {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }
}
