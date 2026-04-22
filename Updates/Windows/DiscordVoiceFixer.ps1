# ===============================================================================
# DISCORD VOICE FIXER - Stereo Audio Module Installer
# ===============================================================================
# Usage: .\DiscordVoiceFixer.ps1 [-Silent] [-CheckOnly] [-FixClient <n>] [-Help]
# ===============================================================================

param([switch]$Silent, [switch]$CheckOnly, [string]$FixClient, [switch]$Help)

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = 'SilentlyContinue'

if ($Help) { Write-Host "Discord Voice Fixer`nUsage: .\DiscordVoiceFixer.ps1 [-Silent] [-CheckOnly] [-FixClient <n>] [-Help]"; exit 0 }

Add-Type -AssemblyName System.Windows.Forms, System.Drawing

if ([System.Environment]::OSVersion.Version.Major -ge 6) {
    try {
        [System.Windows.Forms.Application]::EnableVisualStyles()
        [System.Windows.Forms.Application]::SetCompatibleTextRenderingDefault($false)
    } catch {}
}

#region CONFIGURATION

$Theme = @{
    Background=[System.Drawing.Color]::FromArgb(32,34,37); ControlBg=[System.Drawing.Color]::FromArgb(47,49,54)
    Primary=[System.Drawing.Color]::FromArgb(88,101,242); Secondary=[System.Drawing.Color]::FromArgb(70,73,80)
    Warning=[System.Drawing.Color]::FromArgb(250,168,26); Success=[System.Drawing.Color]::FromArgb(87,158,87)
    TextPrimary=[System.Drawing.Color]::White; TextSecondary=[System.Drawing.Color]::FromArgb(150,150,150)
    TextDim=[System.Drawing.Color]::FromArgb(180,180,180)
}

$Fonts = @{
    Title=New-Object System.Drawing.Font("Segoe UI",16,[System.Drawing.FontStyle]::Bold)
    Normal=New-Object System.Drawing.Font("Segoe UI",9)
    Button=New-Object System.Drawing.Font("Segoe UI",11,[System.Drawing.FontStyle]::Bold)
    ButtonSmall=New-Object System.Drawing.Font("Segoe UI",9,[System.Drawing.FontStyle]::Bold)
    Console=New-Object System.Drawing.Font("Consolas",9)
    Small=New-Object System.Drawing.Font("Segoe UI",8.5)
}

$DiscordClients = [ordered]@{
    0 = @{Name="Discord - Stable         [Official]"; Path="$env:LOCALAPPDATA\Discord";            RoamingPath="$env:APPDATA\discord";            Processes=@("Discord","Update");            Exe="Discord.exe";            Shortcut="Discord"}
    1 = @{Name="Discord - Canary         [Official]"; Path="$env:LOCALAPPDATA\DiscordCanary";      RoamingPath="$env:APPDATA\discordcanary";      Processes=@("DiscordCanary","Update");      Exe="DiscordCanary.exe";      Shortcut="Discord Canary"}
    2 = @{Name="Discord - PTB            [Official]"; Path="$env:LOCALAPPDATA\DiscordPTB";         RoamingPath="$env:APPDATA\discordptb";         Processes=@("DiscordPTB","Update");         Exe="DiscordPTB.exe";         Shortcut="Discord PTB"}
    3 = @{Name="Discord - Development    [Official]"; Path="$env:LOCALAPPDATA\DiscordDevelopment"; RoamingPath="$env:APPDATA\discorddevelopment"; Processes=@("DiscordDevelopment","Update"); Exe="DiscordDevelopment.exe"; Shortcut="Discord Development"}
    4 = @{Name="Lightcord                [Mod]";      Path="$env:LOCALAPPDATA\Lightcord";          RoamingPath="$env:APPDATA\Lightcord";          Processes=@("Lightcord","Update");          Exe="Lightcord.exe";          Shortcut="Lightcord"}
    5 = @{Name="BetterDiscord            [Mod]";      Path="$env:LOCALAPPDATA\Discord";            RoamingPath="$env:APPDATA\discord";            Processes=@("Discord","Update");            Exe="Discord.exe";            Shortcut="Discord"}
    6 = @{Name="Vencord                  [Mod]";      Path="$env:LOCALAPPDATA\Vencord";            RoamingPath="$env:APPDATA\discord";            FallbackPath="$env:LOCALAPPDATA\Discord"; Processes=@("Vencord","Discord","Update");       Exe="Discord.exe"; Shortcut="Vencord"}
    7 = @{Name="Equicord                 [Mod]";      Path="$env:LOCALAPPDATA\Equicord";           RoamingPath="$env:APPDATA\discord";            FallbackPath="$env:LOCALAPPDATA\Discord"; Processes=@("Equicord","Discord","Update");      Exe="Discord.exe"; Shortcut="Equicord"}
    8 = @{Name="BetterVencord            [Mod]";      Path="$env:LOCALAPPDATA\BetterVencord";      RoamingPath="$env:APPDATA\discord";            FallbackPath="$env:LOCALAPPDATA\Discord"; Processes=@("BetterVencord","Discord","Update"); Exe="Discord.exe"; Shortcut="BetterVencord"}
}

$UPDATE_URL = "https://raw.githubusercontent.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/main/Updates/Windows/DiscordVoiceFixer.ps1"
# Patched Windows voice bundle (installer): https://github.com/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/tree/main/Updates/Nodes/Patched%20Nodes%20(for%20Installer)/Windows
$VOICE_BACKUP_API = "https://api.github.com/repos/ProdHallow/Discord-Stereo-Windows-MacOS-Linux/contents/Updates%2FNodes%2FPatched%20Nodes%20%28for%20Installer%29%2FWindows"
$SETTINGS_JSON_URL = "https://raw.githubusercontent.com/ProdHallow/voice-backup/main/settings.json"
$DISCORD_SETUP_URL = "https://discord.com/api/downloads/distributions/app/installers/latest?channel=stable&platform=win&arch=x64"

$APP_DATA_ROOT = "$env:APPDATA\StereoInstaller"
$BACKUP_ROOT = "$APP_DATA_ROOT\backups"
$ORIGINAL_BACKUP_ROOT = "$APP_DATA_ROOT\original_discord_modules"
$STATE_FILE = "$APP_DATA_ROOT\state.json"
$SETTINGS_FILE = "$APP_DATA_ROOT\settings.json"
$SAVED_SCRIPT_PATH = "$APP_DATA_ROOT\DiscordVoiceFixer.ps1"
$SETTINGS_BACKUP_ROOT = "$APP_DATA_ROOT\settings_backups"
$LOG_FILE = "$APP_DATA_ROOT\debug.log"
$MAX_SETTINGS_BACKUPS = 5

#endregion

#region UTILITY FUNCTIONS

function EnsureDir($p) { if (-not (Test-Path $p)) { try { [void](New-Item $p -ItemType Directory -Force) } catch { } } }

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    try {
        EnsureDir (Split-Path $LOG_FILE -Parent)
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "$timestamp [$Level] $Message" | Out-File $LOG_FILE -Append -Force
    } catch { }
}

function Get-AvailableDiskSpace {
    param([string]$Path)
    try {
        $drive = (Get-Item $Path -ErrorAction SilentlyContinue).PSDrive
        if ($drive) { return [math]::Round(($drive.Free / 1MB), 2) }
        return -1
    } catch { return -1 }
}

function Get-DefaultSettings { return [PSCustomObject]@{CheckForUpdates=$true; AutoApplyUpdates=$true; CreateShortcut=$false; AutoStartDiscord=$true; SelectedClientIndex=0; SilentStartup=$false; FixEqApo=$false; AutoFixOnDiscordUpdate=$true} }

function Load-Settings {
    $d = Get-DefaultSettings
    if (Test-Path $SETTINGS_FILE) {
        try { 
            $s = Get-Content $SETTINGS_FILE -Raw | ConvertFrom-Json
            foreach ($k in $d.PSObject.Properties.Name) { 
                if ($k -notin $s.PSObject.Properties.Name) { $s | Add-Member -NotePropertyName $k -NotePropertyValue $d.$k -Force } 
            }
            return $s
        } catch { Write-Log "Failed to load settings: $($_.Exception.Message)" "WARN" }
    }
    return $d
}

function Save-Settings { param([PSCustomObject]$Settings)
    try { EnsureDir (Split-Path $SETTINGS_FILE -Parent); $Settings | ConvertTo-Json -Depth 5 | Out-File $SETTINGS_FILE -Force } catch { Write-Log "Failed to save settings: $($_.Exception.Message)" "ERROR" }
}

function Parse-BackupDate {
    param([string]$DateString)
    if ([string]::IsNullOrWhiteSpace($DateString)) { return [DateTime]::MinValue }
    try { return [DateTime]::Parse($DateString, [System.Globalization.CultureInfo]::InvariantCulture) } catch { }
    try { return [DateTime]::Parse($DateString) } catch { }
    try { return [DateTime]::ParseExact($DateString, "o", [System.Globalization.CultureInfo]::InvariantCulture) } catch { }
    $formats = @("yyyy-MM-ddTHH:mm:ss.fffffffzzz","yyyy-MM-ddTHH:mm:ss.fffzzz","yyyy-MM-ddTHH:mm:sszzz","yyyy-MM-ddTHH:mm:ss","yyyy-MM-dd HH:mm:ss")
    foreach ($fmt in $formats) { try { return [DateTime]::ParseExact($DateString, $fmt, [System.Globalization.CultureInfo]::InvariantCulture) } catch { } }
    return [DateTime]::MinValue
}

function Safe-ParseDateTime {
    param([string]$DateString)
    if ([string]::IsNullOrWhiteSpace($DateString)) { return $null }
    $result = Parse-BackupDate $DateString
    if ($result -eq [DateTime]::MinValue) { return $null }
    return $result
}

function Get-HttpStatusCode {
    param($ErrorRecord)
    try {
        if ($null -eq $ErrorRecord -or $null -eq $ErrorRecord.Exception) { return $null }
        $response = $ErrorRecord.Exception.Response
        if ($null -eq $response) { return $null }
        return [int]$response.StatusCode
    } catch {
        return $null
    }
}

#endregion

#region BACKUP VALIDATION & FIX VERIFICATION

# Validates backup has required .node/.dll files
function Test-BackupHasContent {
    param([string]$BackupPath)
    $voiceModulePath = Join-Path $BackupPath "voice_module"
    if (-not (Test-Path $voiceModulePath)) { return @{ Valid = $false; Reason = "voice_module folder missing" } }
    $files = Get-ChildItem $voiceModulePath -File -Recurse -ErrorAction SilentlyContinue
    if (-not $files -or $files.Count -eq 0) { return @{ Valid = $false; Reason = "voice_module folder is empty" } }
    $criticalFiles = $files | Where-Object { $_.Extension -in @(".node", ".dll") }
    if (-not $criticalFiles -or $criticalFiles.Count -eq 0) { return @{ Valid = $false; Reason = "voice_module missing critical files (.node/.dll)" } }
    $emptyFiles = $criticalFiles | Where-Object { $_.Length -eq 0 }
    if ($emptyFiles -and $emptyFiles.Count -gt 0) { return @{ Valid = $false; Reason = "voice_module has empty critical files" } }
    return @{ Valid = $true; FileCount = $files.Count; TotalSize = ($files | Measure-Object -Property Length -Sum).Sum }
}

# Compares MD5 hashes to verify if stereo fix is currently applied
function Verify-StereoFix {
    param([string]$VoiceFolderPath, [string]$ClientName, [System.Windows.Forms.RichTextBox]$StatusBox, [System.Windows.Forms.Form]$Form)
    try {
        if (-not (Test-Path $VoiceFolderPath)) {
            return @{ Status = "Error"; Message = "Voice folder not found"; IsFixed = $false }
        }
        $currentFiles = Get-ChildItem $VoiceFolderPath -File -ErrorAction SilentlyContinue
        if (-not $currentFiles -or $currentFiles.Count -eq 0) {
            return @{ Status = "Error"; Message = "Voice folder is empty"; IsFixed = $false }
        }
        $nodeFile = $currentFiles | Where-Object { $_.Extension -eq ".node" } | Select-Object -First 1
        if (-not $nodeFile) {
            return @{ Status = "Error"; Message = "No .node file found in voice module"; IsFixed = $false }
        }
        $currentHash = (Get-FileHash $nodeFile.FullName -Algorithm MD5).Hash
        $currentSize = $nodeFile.Length
        $scn = Get-SanitizedClientKey $ClientName
        $originalBackupPath = Join-Path $ORIGINAL_BACKUP_ROOT $scn
        if (Test-Path $originalBackupPath) {
            $origVoicePath = Join-Path $originalBackupPath "voice_module"
            $origNodeFile = Get-ChildItem $origVoicePath -Filter "*.node" -File -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($origNodeFile) {
                $origHash = (Get-FileHash $origNodeFile.FullName -Algorithm MD5).Hash
                if ($currentHash -eq $origHash) {
                    return @{ Status = "NotFixed"; Message = "Original mono modules detected"; IsFixed = $false; CurrentHash = $currentHash; OriginalHash = $origHash }
                }
            }
        }
        $clientBackupPrefix = "${scn}_"
        $latestBackups = Get-ChildItem $BACKUP_ROOT -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -like "$clientBackupPrefix*" } |
            Sort-Object Name -Descending
        $hasClientBackupHashes = $false
        foreach ($backup in $latestBackups) {
            $backupVoicePath = Join-Path $backup.FullName "voice_module"
            $backupNodeFile = Get-ChildItem $backupVoicePath -Filter "*.node" -File -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($backupNodeFile) {
                $hasClientBackupHashes = $true
                $backupHash = (Get-FileHash $backupNodeFile.FullName -Algorithm MD5).Hash
                if ($currentHash -eq $backupHash) {
                    return @{ Status = "NotFixed"; Message = "Current voice module matches a saved mono backup"; IsFixed = $false; CurrentHash = $currentHash; BackupHash = $backupHash }
                }
            }
        }
        if ($hasClientBackupHashes -and (Test-Path $originalBackupPath)) {
            return @{ Status = "Fixed"; Message = "Stereo fix is applied"; IsFixed = $true; CurrentHash = $currentHash; FileSize = $currentSize }
        }
        if (Test-Path $originalBackupPath) {
            return @{ Status = "Fixed"; Message = "Stereo fix appears to be applied (differs from original)"; IsFixed = $true; CurrentHash = $currentHash; FileSize = $currentSize }
        }
        return @{ Status = "Unknown"; Message = "No original backup to compare - run fix first to create baseline"; IsFixed = $null; CurrentHash = $currentHash; FileSize = $currentSize }
    } catch {
        return @{ Status = "Error"; Message = $_.Exception.Message; IsFixed = $false }
    }
}

# Checks all clients for Discord updates since last fix
function Get-UpdatedDiscordClients {
    $updatedClients = [System.Collections.ArrayList]@()
    $ic = Get-InstalledClients
    foreach ($ci in $ic) {
        $uc = Check-DiscordUpdated $ci.Path $ci.Name
        if ($uc -and $uc.Updated) {
            [void]$updatedClients.Add(@{
                Name = $ci.Name
                Path = $ci.Path
                AppPath = $ci.AppPath
                Client = $ci.Client
                OldVersion = $uc.OldVersion
                NewVersion = $uc.NewVersion
            })
        }
    }
    return $updatedClients
}

#endregion

#region UI HELPERS

function New-StyledLabel {
    param([int]$X, [int]$Y, [int]$Width, [int]$Height, [string]$Text, [System.Drawing.Font]$Font=$Fonts.Normal,
          [System.Drawing.Color]$ForeColor=$Theme.TextPrimary, [string]$TextAlign="MiddleLeft")
    $l = New-Object System.Windows.Forms.Label
    $l.Location = New-Object System.Drawing.Point($X,$Y); $l.Size = New-Object System.Drawing.Size($Width,$Height)
    $l.Text = $Text; $l.Font = $Font; $l.TextAlign = $TextAlign; $l.ForeColor = $ForeColor
    $l.BackColor = [System.Drawing.Color]::Transparent; $l
}

function New-StyledCheckBox {
    param([int]$X, [int]$Y, [int]$Width, [int]$Height, [string]$Text, [bool]$Checked=$false, [System.Drawing.Color]$ForeColor=$Theme.TextPrimary)
    $c = New-Object System.Windows.Forms.CheckBox
    $c.Location = New-Object System.Drawing.Point($X,$Y); $c.Size = New-Object System.Drawing.Size($Width,$Height)
    $c.Text = $Text; $c.Checked = $Checked; $c.ForeColor = $ForeColor; $c.Font = $Fonts.Normal; $c
}

function New-StyledButton {
    param([int]$X, [int]$Y, [int]$Width, [int]$Height, [string]$Text, [System.Drawing.Font]$Font=$Fonts.Button, [System.Drawing.Color]$BackColor=$Theme.Primary)
    $b = New-Object System.Windows.Forms.Button
    $b.Location = New-Object System.Drawing.Point($X,$Y); $b.Size = New-Object System.Drawing.Size($Width,$Height)
    $b.Text = $Text; $b.Font = $Font; $b.BackColor = $BackColor; $b.ForeColor = $Theme.TextPrimary
    $b.FlatStyle = "Flat"; $b.FlatAppearance.BorderSize = 0; $b.Cursor = [System.Windows.Forms.Cursors]::Hand; $b
}

function Add-Status {
    param([System.Windows.Forms.RichTextBox]$StatusBox, [System.Windows.Forms.Form]$Form, [string]$Message, [string]$ColorName="White")
    Write-Log $Message
    if ($null -eq $StatusBox) { if ($Silent) { Write-Host $Message }; return }
    $c = [System.Drawing.Color]::FromName($ColorName)
    if (-not $c.IsKnownColor -and $c.A -eq 0) { $c = [System.Drawing.Color]::White }
    $ts = Get-Date -Format "HH:mm:ss"
    $StatusBox.SelectionStart = $StatusBox.TextLength; $StatusBox.SelectionLength = 0
    $StatusBox.SelectionColor = $c
    $StatusBox.AppendText("[$ts] $Message`r`n"); $StatusBox.ScrollToCaret()
    if ($null -ne $Form) { $Form.Refresh(); [System.Windows.Forms.Application]::DoEvents() }
}

function Play-CompletionSound { param([bool]$Success=$true)
    try { if ($Success) { [System.Media.SystemSounds]::Exclamation.Play() } else { [System.Media.SystemSounds]::Hand.Play() } } catch {}
}

function Update-Progress { param([System.Windows.Forms.ProgressBar]$ProgressBar, [System.Windows.Forms.Form]$Form, [int]$Value)
    if ($null -ne $ProgressBar) { $ProgressBar.Value = [Math]::Min([Math]::Max($Value, 0), 100) }
    if ($null -ne $Form) { $Form.Refresh(); [System.Windows.Forms.Application]::DoEvents() }
}

#endregion

#region DISCORD PROCESS & PATH MANAGEMENT

function Stop-DiscordProcesses { param([string[]]$ProcessNames)
    $mainNames = @("Discord","DiscordCanary","DiscordPTB","DiscordDevelopment","Lightcord","Vencord","Equicord","BetterVencord")
    $toKill = $ProcessNames | Where-Object { $_ -in $mainNames }
    $discordPathRegex = "\\Discord|\\Lightcord|\\Vencord|\\Equicord|\\BetterVencord"

    $getDiscordUpdatePids = {
        try {
            $up = Get-Process -Name "Update" -ErrorAction SilentlyContinue
            if (-not $up) { return @() }
            $pids = @()
            foreach ($p in $up) {
                try {
                    $cim = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.Id)" -ErrorAction SilentlyContinue
                    if ($cim -and $cim.ExecutablePath -and $cim.ExecutablePath -match $discordPathRegex) { $pids += $p.Id }
                } catch { }
            }
            return $pids
        } catch { return @() }
    }

    foreach ($n in $toKill) {
        try { & taskkill /F /IM "$n.exe" 2>$null | Out-Null } catch { }
    }
    $updatePids = & $getDiscordUpdatePids
    foreach ($upId in $updatePids) {
        try { & taskkill /F /PID $upId 2>$null | Out-Null } catch { }
    }
    Start-Sleep -Milliseconds 400
    foreach ($n in $toKill) {
        try { & taskkill /F /IM "$n.exe" 2>$null | Out-Null } catch { }
    }

    $deadline = [DateTime]::UtcNow.AddSeconds(5)
    $checkNames = @($toKill) + @("Update")
    while ([DateTime]::UtcNow -lt $deadline) {
        $remaining = Get-Process -Name $checkNames -ErrorAction SilentlyContinue
        $killed = $false
        if ($remaining) {
            foreach ($r in $remaining) {
                $pathOk = $true
                if ($r.Name -eq "Update") {
                    try {
                        $cim = Get-CimInstance Win32_Process -Filter "ProcessId=$($r.Id)" -ErrorAction SilentlyContinue
                        $pathOk = $cim -and $cim.ExecutablePath -match $discordPathRegex
                    } catch { $pathOk = $false }
                }
                if ($pathOk) {
                    try { & taskkill /F /PID $r.Id 2>$null | Out-Null; $killed = $true } catch { }
                }
            }
        }
        if (-not $remaining -or -not $killed) {
            $updatePids = & $getDiscordUpdatePids
            if ($updatePids.Count -eq 0) { return $true }
            foreach ($upId in $updatePids) {
                try { & taskkill /F /PID $upId 2>$null | Out-Null; $killed = $true } catch { }
            }
            if (-not $killed) { return $true }
        }
        Start-Sleep -Milliseconds 200
    }
    foreach ($n in $toKill) {
        try { & taskkill /F /IM "$n.exe" 2>$null | Out-Null } catch { }
    }
    $updatePids = & $getDiscordUpdatePids
    foreach ($upId in $updatePids) {
        try { & taskkill /F /PID $upId 2>$null | Out-Null } catch { }
    }
    return $true
}

# Finds latest app-* folder with valid modules/voice structure
function Find-DiscordAppPath { 
    param([string]$BasePath, [switch]$ReturnDiagnostics)
    $af = Get-ChildItem $BasePath -Filter "app-*" -Directory -ErrorAction SilentlyContinue | 
        Sort-Object { 
            $folder = $_
            if ($folder.Name -match "app-([\d\.]+)") { 
                $versionStr = $matches[1]
                $parts = @()
                foreach ($partText in $versionStr.Split('.')) {
                    [int]$partValue = 0
                    if (-not [int]::TryParse($partText, [ref]$partValue)) {
                        return [Version]::new(0, 0, 0, 0)
                    }
                    $parts += $partValue
                }
                while ($parts.Count -lt 4) { $parts += 0 }
                $parts = $parts[0..3]
                return [Version]::new($parts[0], $parts[1], $parts[2], $parts[3])
            }
            return [Version]::new(0, 0, 0, 0)
        } -Descending
    $diag = @{ BasePath = $BasePath; AppFoldersFound = @(); ModulesFolderExists = $false; VoiceModuleExists = $false
               LatestAppFolder = $null; LatestAppVersion = $null; ModulesPath = $null; VoiceModulePath = $null; Error = $null }
    if (-not $af -or $af.Count -eq 0) { $diag.Error = "NoAppFolders"; if ($ReturnDiagnostics) { return $diag }; return $null }
    $diag.AppFoldersFound = @($af | ForEach-Object { $_.Name })
    $diag.LatestAppFolder = $af[0].FullName
    $versionMatch = [regex]::Match($af[0].Name, "app-([\d\.]+)")
    if ($versionMatch.Success) { $diag.LatestAppVersion = $versionMatch.Groups[1].Value } else { $diag.LatestAppVersion = $af[0].Name }
    foreach ($f in $af) {
        $mp = Join-Path $f.FullName "modules"
        if (Test-Path $mp) { 
            $diag.ModulesFolderExists = $true; $diag.ModulesPath = $mp
            $vm = Get-ChildItem $mp -Filter "discord_voice*" -Directory -ErrorAction SilentlyContinue
            if ($vm) { 
                $diag.VoiceModuleExists = $true; $diag.VoiceModulePath = $vm[0].FullName
                if ($ReturnDiagnostics) { return $diag }; return $f.FullName 
            }
        }
    }
    if (-not $diag.ModulesFolderExists) { $diag.Error = "NoModulesFolder" } 
    elseif (-not $diag.VoiceModuleExists) { $diag.Error = "NoVoiceModule" }
    if ($ReturnDiagnostics) { return $diag }; return $null
}

function Get-DiscordAppVersion { param([string]$AppPath)
    $versionMatch = [regex]::Match($AppPath, "app-([\d\.]+)")
    if ($versionMatch.Success) { return $versionMatch.Groups[1].Value }
    try { $exe = Get-ChildItem $AppPath -Filter "*.exe" | Select-Object -First 1; if ($exe) { return (Get-Item $exe.FullName).VersionInfo.ProductVersion } } catch {}
    return "Unknown"
}

function Start-DiscordClient { param([string]$ExePath)
    if (-not (Test-Path $ExePath)) { return $false }
    $updateExe = Join-Path (Split-Path (Split-Path $ExePath -Parent) -Parent) "Update.exe"
    $exeName = Split-Path $ExePath -Leaf
    # Prefer detached launch paths to avoid inheriting the current terminal handles.
    if (Test-Path $updateExe) { try { Start-Process $updateExe -ArgumentList "--processStart",$exeName -WindowStyle Hidden; return $true } catch { } }
    try { Start-Process "cmd.exe" -ArgumentList "/d","/c","start",'""',"`"$ExePath`"" -WindowStyle Hidden; return $true } catch { }
    try { Start-Process $ExePath -WindowStyle Hidden; return $true } catch { }
    return $false
}

function Get-PathFromProcess { param([string]$ProcessName)
    try { $p = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue | Select-Object -First 1; if ($p) { return (Split-Path (Split-Path $p.MainModule.FileName -Parent) -Parent) } } catch {}
    return $null
}

function Get-PathFromShortcuts { param([string]$ShortcutName)
    if (-not $ShortcutName) { return $null }
    $sm = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs"
    if (!(Test-Path $sm)) { return $null }
    $scs = Get-ChildItem $sm -Filter "$ShortcutName.lnk" -Recurse -ErrorAction SilentlyContinue
    if (-not $scs) { return $null }
    $ws = New-Object -ComObject WScript.Shell
    $result = $null
    foreach ($lf in $scs) { try { $sc = $ws.CreateShortcut($lf.FullName); if (Test-Path $sc.TargetPath) { $result = (Split-Path $sc.TargetPath -Parent); break } } catch { } }
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($ws)
    return $result
}

# Resolves actual client path from config, running process, or shortcuts
function Get-RealClientPath { param($ClientObj)
    $p = $ClientObj.Path
    if (Test-Path $p) { return $p }
    if ($ClientObj.FallbackPath -and (Test-Path $ClientObj.FallbackPath)) { return $ClientObj.FallbackPath }
    foreach ($pr in $ClientObj.Processes) { if ($pr -eq "Update") { continue }; $pp = Get-PathFromProcess $pr; if ($pp -and (Test-Path $pp)) { return $pp } }
    if ($ClientObj.Shortcut) { $sp = Get-PathFromShortcuts $ClientObj.Shortcut; if ($sp -and (Test-Path $sp)) { return $sp } }
    return $null
}

# Scans system for all installed Discord clients with valid voice modules
function Get-InstalledClients {
    $inst = [System.Collections.ArrayList]@()
    $foundPaths = New-Object 'System.Collections.Generic.HashSet[string]'
    foreach ($k in $DiscordClients.Keys) {
        $c = $DiscordClients[$k]; $fp = $null
        if (Test-Path $c.Path) { $fp = $c.Path }
        elseif ($c.FallbackPath -and (Test-Path $c.FallbackPath)) { $fp = $c.FallbackPath }
        else { foreach ($pn in $c.Processes) { if ($pn -eq "Update") { continue }; $dp = Get-PathFromProcess $pn; if ($dp -and (Test-Path $dp)) { $fp = $dp; break } } }
        if (-not $fp -and $c.Shortcut) { $sp = Get-PathFromShortcuts $c.Shortcut; if ($sp -and (Test-Path $sp)) { $fp = $sp } }
        if ($fp) { 
            try { $fp = (Get-Item $fp).FullName } catch {}
            if ($foundPaths.Contains($fp)) { continue }
            $ap = Find-DiscordAppPath $fp
            if ($ap) { [void]$inst.Add(@{Index=$k; Name=$c.Name; Path=$fp; AppPath=$ap; Client=$c}); [void]$foundPaths.Add($fp) } 
        }
    }
    return $inst
}

#endregion

#region DISCORD REINSTALL

$script:DiscordWasReinstalled = $false

# Reinstalls corrupted Discord installations (official clients only)
function Reinstall-DiscordClient {
    param(
        [string]$ClientPath,
        [hashtable]$ClientInfo,
        [System.Windows.Forms.RichTextBox]$StatusBox,
        [System.Windows.Forms.Form]$Form,
        [switch]$SkipConfirmation
    )
    try {
        $clientName = $ClientInfo.Name
        if ($clientName -notmatch "\[Official\]") {
            Add-Status $StatusBox $Form "[X] Automatic reinstall only supported for official Discord clients" "Red"
            Add-Status $StatusBox $Form "    Please manually reinstall $clientName" "Yellow"
            return $false
        }
        $discordVariant = "stable"
        $setupUrl = $DISCORD_SETUP_URL
        if ($clientName -match "Canary") {
            $discordVariant = "canary"
            $setupUrl = "https://discord.com/api/downloads/distributions/app/installers/latest?channel=canary&platform=win&arch=x64"
        } elseif ($clientName -match "PTB") {
            $discordVariant = "ptb"
            $setupUrl = "https://discord.com/api/downloads/distributions/app/installers/latest?channel=ptb&platform=win&arch=x64"
        } elseif ($clientName -match "Development") {
            $discordVariant = "development"
            $setupUrl = "https://discord.com/api/downloads/distributions/app/installers/latest?channel=development&platform=win&arch=x64"
        }
        Add-Status $StatusBox $Form "" "White"
        Add-Status $StatusBox $Form "=== DISCORD REINSTALL ($discordVariant) ===" "Magenta"
        Add-Status $StatusBox $Form "Your Discord installation is missing the modules folder." "Yellow"
        Add-Status $StatusBox $Form "This usually means Discord is corrupted or very outdated." "Yellow"
        if (-not $SkipConfirmation) {
            $confirmResult = [System.Windows.Forms.MessageBox]::Show(
                $Form,
                "Discord appears to be corrupted because its internal 'modules' folder is missing.`n`n" +
                "This folder is required for Discord's voice system to function correctly.`n`n" +
                "To fix this, the installer will perform a safe automatic repair by:`n" +
                "- Fully closing Discord`n" +
                "- Removing the broken Discord app files`n" +
                "- Downloading and installing the latest official Discord version`n" +
                "- Allowing Discord to rebuild its missing voice modules`n" +
                "- Applying the stereo / filterless audio fix afterward`n`n" +
                "Your Discord account, settings, and login will NOT be removed.`n" +
                "This only repairs program files and resolves voice module errors.`n`n" +
                "Would you like to continue?",
                "Repair Corrupted Discord Installation",
                "YesNo",
                "Question"
            )
            if ($confirmResult -ne "Yes") {
                Add-Status $StatusBox $Form "Reinstall cancelled by user" "Yellow"
                return $false
            }
        }
        $script:DiscordWasReinstalled = $true
        Add-Status $StatusBox $Form "Step 1/4: Closing all Discord processes..." "Blue"
        $allProcs = @("Discord","DiscordCanary","DiscordPTB","DiscordDevelopment","Lightcord","BetterVencord","Equicord","Vencord","Update")
        Stop-DiscordProcesses $allProcs | Out-Null
        Start-Sleep -Seconds 2
        Add-Status $StatusBox $Form "[OK] Discord processes terminated" "LimeGreen"
        Add-Status $StatusBox $Form "Step 2/4: Removing corrupted Discord files..." "Blue"
        Get-ChildItem $ClientPath -Filter "app-*" -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }
        $updateExe = Join-Path $ClientPath "Update.exe"
        if (Test-Path $updateExe) { Remove-Item $updateExe -Force -ErrorAction SilentlyContinue }
        Add-Status $StatusBox $Form "[OK] Corrupted files removed" "LimeGreen"
        Add-Status $StatusBox $Form "Step 3/4: Downloading Discord installer..." "Blue"
        $installerPath = Join-Path $env:TEMP "DiscordSetup_$([guid]::NewGuid()).exe"
        Invoke-WebRequest -Uri $setupUrl -OutFile $installerPath -UseBasicParsing -TimeoutSec 120
        if (-not (Test-Path $installerPath)) { throw "Installer download failed - file not created" }
        $installerSize = (Get-Item $installerPath).Length / 1MB
        if ($installerSize -lt 1) { Remove-Item $installerPath -Force -ErrorAction SilentlyContinue; throw "Installer file is too small ($([math]::Round($installerSize, 2)) MB) - download may have failed" }
        Add-Status $StatusBox $Form "[OK] Downloaded installer ($([math]::Round($installerSize, 1)) MB)" "LimeGreen"
        Add-Status $StatusBox $Form "Step 4/4: Running Discord installer..." "Blue"
        Start-Process $installerPath
        Add-Status $StatusBox $Form "Waiting for voice modules to download..." "Blue"
        $maxWait = 90
        $waited = 0
        $voiceModuleFound = $false
        while ($waited -lt $maxWait) {
            Start-Sleep -Seconds 5
            $waited += 5
            $newDiag = Find-DiscordAppPath $ClientPath -ReturnDiagnostics
            if ($newDiag.VoiceModuleExists) {
                Add-Status $StatusBox $Form "[OK] Voice module detected!" "LimeGreen"
                $voiceModuleFound = $true
                break
            }
        }
        if (-not $voiceModuleFound) {
            Add-Status $StatusBox $Form "[!] Voice module not detected after reinstall" "Orange"
            return $false
        }
        if ($script:DiscordWasReinstalled) {
            Add-Status $StatusBox $Form "Reinstall detected - releasing voice module lock..." "Cyan"
            Get-Process -Name "Discord","DiscordCanary","DiscordPTB","DiscordDevelopment" -ErrorAction SilentlyContinue | Stop-Process -Force
            $voiceNodePath = Join-Path $newDiag.VoiceModulePath "discord_voice.node"
            for ($i = 0; $i -lt 10; $i++) {
                try {
                    $fs = [System.IO.File]::Open($voiceNodePath, 'Open', 'ReadWrite', 'None')
                    $fs.Close()
                    break
                } catch {
                    Start-Sleep -Seconds 1
                }
            }
            Add-Status $StatusBox $Form "[OK] Voice module released" "LimeGreen"
        }
        Add-Status $StatusBox $Form "[OK] Discord reinstallation completed successfully!" "LimeGreen"
        return $true
    } catch {
        Add-Status $StatusBox $Form "[X] Reinstall failed: $($_.Exception.Message)" "Red"
        return $false
    }
}

#endregion

#region DOWNLOAD & EQ APO FIX

# Downloads voice backup files from GitHub
function Download-VoiceBackupFiles { param([string]$DestinationPath, [System.Windows.Forms.RichTextBox]$StatusBox, [System.Windows.Forms.Form]$Form)
    $maxRetries = 3; $retryDelay = 2
    for ($attempt = 1; $attempt -le $maxRetries; $attempt++) {
        try {
            EnsureDir $DestinationPath
            if ($attempt -gt 1) { Add-Status $StatusBox $Form "  Retry attempt $attempt of $maxRetries..." "Yellow"; Start-Sleep -Seconds $retryDelay }
            Add-Status $StatusBox $Form "  Fetching file list from GitHub..." "Cyan"
            try { $r = Invoke-RestMethod -Uri $VOICE_BACKUP_API -UseBasicParsing -TimeoutSec 30 }
            catch {
                $statusCode = Get-HttpStatusCode $_
                if ($statusCode -eq 403) { throw "GitHub API Rate Limit exceeded. Please try again later." }
                throw $_
            }
            $r = @($r)
            if ($r.Count -eq 0) { throw "GitHub repository response is empty." }
            $fc = 0; $failedFiles = @()
            foreach ($f in $r) {
                if ($f.type -eq "file") {
                    $fp = Join-Path $DestinationPath $f.name
                    Add-Status $StatusBox $Form "  Downloading: $($f.name)" "Cyan"
                    try {
                        Invoke-WebRequest -Uri $f.download_url -OutFile $fp -UseBasicParsing -TimeoutSec 30 | Out-Null
                        if (-not (Test-Path $fp)) { throw "File was not created" }
                        $fileInfo = Get-Item $fp
                        if ($fileInfo.Length -eq 0) { throw "Downloaded file is empty" }
                        $ext = [System.IO.Path]::GetExtension($f.name).ToLower()
                        if ($ext -eq ".node" -or $ext -eq ".dll") { if ($fileInfo.Length -lt 1024) { Add-Status $StatusBox $Form "  [!] Warning: $($f.name) seems too small ($($fileInfo.Length) bytes)" "Orange" } }
                        $fc++
                    } catch { Add-Status $StatusBox $Form "  [!] Failed to download $($f.name): $($_.Exception.Message)" "Orange"; $failedFiles += $f.name }
                }
            }
            if ($fc -eq 0) { throw "No valid files were downloaded." }
            if ($failedFiles.Count -gt 0) { Add-Status $StatusBox $Form "  [!] Warning: $($failedFiles.Count) file(s) failed to download" "Orange" }
            Add-Status $StatusBox $Form "  Downloaded $fc voice backup files" "Cyan"
            return $true
        } catch {
            $errMsg = $_.Exception.Message
            if ($attempt -lt $maxRetries) { Add-Status $StatusBox $Form "  [!] Attempt $attempt failed: $errMsg - retrying..." "Orange"; Write-Log "Download attempt $attempt failed: $errMsg" "WARN" }
            else { Add-Status $StatusBox $Form "  [X] Failed to download files after $maxRetries attempts: $errMsg" "Red"; Write-Log "Download failed after $maxRetries attempts: $errMsg" "ERROR"; return $false }
        }
    }
    return $false
}

# Replaces Discord settings.json with EQ APO compatible version
function Apply-EqApoFix {
    param([string]$RoamingPath, [string]$ClientName, [System.Windows.Forms.RichTextBox]$StatusBox, [System.Windows.Forms.Form]$Form, [bool]$SkipConfirmation = $false)
    try {
        Add-Status $StatusBox $Form "" "White"
        Add-Status $StatusBox $Form "=== EQ APO FIX: $ClientName ===" "Blue"
        if (-not (Test-Path $RoamingPath)) {
            Add-Status $StatusBox $Form "[X] Discord roaming folder not found: $RoamingPath" "Red"
            Add-Status $StatusBox $Form "    Please ensure Discord has been run at least once." "Yellow"
            return $false
        }
        $targetSettingsPath = Join-Path $RoamingPath "settings.json"
        if (-not $SkipConfirmation) {
            $confirmResult = [System.Windows.Forms.MessageBox]::Show($Form, "Replace Discord settings.json to fix EQ APO for $($ClientName)?", "Confirm EQ APO Fix", "YesNo", "Question")
            if ($confirmResult -ne "Yes") { Add-Status $StatusBox $Form "EQ APO fix cancelled by user" "Yellow"; return $false }
        }
        Add-Status $StatusBox $Form "Applying EQ APO fix to $ClientName..." "Blue"
        if (Test-Path $targetSettingsPath) {
            EnsureDir $SETTINGS_BACKUP_ROOT
            $sanitizedName = $ClientName -replace '\s+','_' -replace '\[|\]','' -replace '-','_'
            $backupTimestamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
            $backupPath = Join-Path $SETTINGS_BACKUP_ROOT "settings_${sanitizedName}_$backupTimestamp.json"
            Add-Status $StatusBox $Form "  Backing up existing settings.json..." "Cyan"
            try { Copy-Item $targetSettingsPath $backupPath -Force; Add-Status $StatusBox $Form "  [OK] Backup created: settings_${sanitizedName}_$backupTimestamp.json" "LimeGreen" }
            catch { Add-Status $StatusBox $Form "  [!] Warning: Could not create backup: $($_.Exception.Message)" "Orange" }
            Remove-OldSettingsBackups $sanitizedName
        } else { Add-Status $StatusBox $Form "  No existing settings.json found (will create new)" "Yellow" }
        Add-Status $StatusBox $Form "  Downloading settings.json from GitHub..." "Cyan"
        $tempSettingsPath = Join-Path $env:TEMP "discord_settings_$(Get-Random).json"
        try { Invoke-WebRequest -Uri $SETTINGS_JSON_URL -OutFile $tempSettingsPath -UseBasicParsing -TimeoutSec 30 | Out-Null }
        catch {
            $statusCode = Get-HttpStatusCode $_
            if ($statusCode -eq 404) { Add-Status $StatusBox $Form "  [X] settings.json not found in repository" "Red"; return $false }
            throw $_
        }
        Add-Status $StatusBox $Form "  Verifying downloaded file..." "Cyan"
        try { $jsonContent = Get-Content $tempSettingsPath -Raw | ConvertFrom-Json; if ($null -eq $jsonContent -or ($jsonContent -is [array] -and $jsonContent.Count -eq 0) -or ($jsonContent -is [PSCustomObject] -and $jsonContent.PSObject.Properties.Count -eq 0)) { throw "Downloaded file is empty or invalid" }; Add-Status $StatusBox $Form "  [OK] File verified as valid JSON" "LimeGreen" }
        catch { Add-Status $StatusBox $Form "  [X] Downloaded file is not valid JSON: $($_.Exception.Message)" "Red"; Remove-Item $tempSettingsPath -Force -ErrorAction SilentlyContinue; return $false }
        if (Test-Path $targetSettingsPath) {
            Add-Status $StatusBox $Form "  Removing old settings.json..." "Cyan"
            try { Remove-Item $targetSettingsPath -Force }
            catch { Add-Status $StatusBox $Form "  [X] Could not remove old settings.json: $($_.Exception.Message)" "Red"; Add-Status $StatusBox $Form "    Make sure Discord is completely closed." "Yellow"; Remove-Item $tempSettingsPath -Force -ErrorAction SilentlyContinue; return $false }
        }
        Add-Status $StatusBox $Form "  Installing new settings.json..." "Cyan"
        try { Copy-Item $tempSettingsPath $targetSettingsPath -Force; Add-Status $StatusBox $Form "[OK] EQ APO fix applied successfully for $ClientName!" "LimeGreen" }
        catch { Add-Status $StatusBox $Form "  [X] Could not install new settings.json: $($_.Exception.Message)" "Red"; Remove-Item $tempSettingsPath -Force -ErrorAction SilentlyContinue; return $false }
        Remove-Item $tempSettingsPath -Force -ErrorAction SilentlyContinue
        Add-Status $StatusBox $Form "  Settings replaced at: $targetSettingsPath" "Cyan"
        return $true
    } catch { Add-Status $StatusBox $Form "[X] EQ APO fix failed: $($_.Exception.Message)" "Red"; Write-Log "EQ APO fix failed: $($_.Exception.Message)" "ERROR"; return $false }
}

function Remove-OldSettingsBackups {
    param([string]$SanitizedClientName)
    try {
        $backups = Get-ChildItem $SETTINGS_BACKUP_ROOT -Filter "settings_${SanitizedClientName}_*.json" -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
        if ($backups -and $backups.Count -gt $MAX_SETTINGS_BACKUPS) {
            $backups | Select-Object -Skip $MAX_SETTINGS_BACKUPS | ForEach-Object { Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue }
        }
    } catch { Write-Log "Failed to clean up old settings backups: $($_.Exception.Message)" "WARN" }
}

function Apply-EqApoFixAll {
    param([System.Windows.Forms.RichTextBox]$StatusBox, [System.Windows.Forms.Form]$Form, [bool]$SkipConfirmation = $false)
    $processedPaths = New-Object 'System.Collections.Generic.HashSet[string]'
    $successCount = 0; $failCount = 0
    foreach ($k in $DiscordClients.Keys) {
        $client = $DiscordClients[$k]
        $roamingPath = $client.RoamingPath
        if ($processedPaths.Contains($roamingPath)) { continue }
        if (-not (Test-Path $roamingPath)) { continue }
        [void]$processedPaths.Add($roamingPath)
        $result = Apply-EqApoFix -RoamingPath $roamingPath -ClientName $client.Name.Trim() -StatusBox $StatusBox -Form $Form -SkipConfirmation $SkipConfirmation
        if ($result) { $successCount++ } else { $failCount++ }
    }
    return @{ Success = $successCount; Failed = $failCount; Total = $processedPaths.Count }
}

#endregion

#region BACKUP MANAGEMENT

function Initialize-BackupDirectory { EnsureDir $BACKUP_ROOT; EnsureDir $ORIGINAL_BACKUP_ROOT; EnsureDir (Split-Path $STATE_FILE -Parent) }
function Get-StateData { if (Test-Path $STATE_FILE) { try { return Get-Content $STATE_FILE -Raw | ConvertFrom-Json } catch { return $null } }; return $null }
function Save-StateData { param([hashtable]$State); $State | ConvertTo-Json -Depth 5 | Out-File $STATE_FILE -Force }
function Get-SanitizedClientKey { param([string]$ClientName); return $ClientName -replace '\s+','_' -replace '\[|\]','' -replace '-','_' }

function Test-OriginalBackupExists { param([string]$ClientName)
    Initialize-BackupDirectory
    $scn = Get-SanitizedClientKey $ClientName
    return (Test-Path (Join-Path $ORIGINAL_BACKUP_ROOT $scn))
}

function Get-OriginalBackup { param([string]$ClientName)
    Initialize-BackupDirectory
    $scn = Get-SanitizedClientKey $ClientName
    $originalPath = Join-Path $ORIGINAL_BACKUP_ROOT $scn
    if (Test-Path $originalPath) {
        $mp = Join-Path $originalPath "metadata.json"
        if (Test-Path $mp) {
            try {
                $m = Get-Content $mp -Raw | ConvertFrom-Json
                $backupDate = Parse-BackupDate $m.BackupDate
                if ($backupDate -eq [DateTime]::MinValue) { $backupDate = (Get-Item $originalPath).CreationTime }
                return @{ Path=$originalPath; Name="Original Discord Modules"; ClientName=$m.ClientName; AppVersion=$m.AppVersion; BackupDate=$backupDate; IsOriginal=$true
                          DisplayName="[ORIGINAL] $($m.ClientName) v$($m.AppVersion) - $($backupDate.ToString('MMM dd, yyyy HH:mm', [System.Globalization.CultureInfo]::InvariantCulture))" }
            } catch { return $null }
        }
    }
    return $null
}

# Creates permanent backup of original voice modules (never auto-deleted)
function Create-OriginalBackup {
    param([string]$VoiceFolderPath, [string]$ClientName, [string]$AppVersion, [System.Windows.Forms.RichTextBox]$StatusBox, [System.Windows.Forms.Form]$Form)
    try {
        Initialize-BackupDirectory
        $scn = Get-SanitizedClientKey $ClientName
        $bp = Join-Path $ORIGINAL_BACKUP_ROOT $scn
        if (Test-Path $bp) { Add-Status $StatusBox $Form "  Original backup already exists, skipping..." "Yellow"; return $bp }
        if (-not (Test-Path $VoiceFolderPath)) { Add-Status $StatusBox $Form "  [!] Source voice folder does not exist: $VoiceFolderPath" "Orange"; return $null }
        $sourceFiles = Get-ChildItem $VoiceFolderPath -File -Recurse -ErrorAction SilentlyContinue
        if (-not $sourceFiles -or $sourceFiles.Count -eq 0) { Add-Status $StatusBox $Form "  [!] Source voice folder is empty, cannot create backup" "Orange"; return $null }
        $requiredSpace = ($sourceFiles | Measure-Object -Property Length -Sum).Sum / 1MB + 10
        $availableSpace = Get-AvailableDiskSpace $ORIGINAL_BACKUP_ROOT
        if ($availableSpace -gt 0 -and $availableSpace -lt $requiredSpace) {
            Add-Status $StatusBox $Form "  [!] Insufficient disk space for backup (need $([math]::Round($requiredSpace, 1)) MB, have $availableSpace MB)" "Orange"
            return $null
        }
        try { [void](New-Item $bp -ItemType Directory -Force) } catch { }
        $vbp = Join-Path $bp "voice_module"
        Add-Status $StatusBox $Form "  Creating ORIGINAL backup (will never be deleted)..." "Magenta"
        EnsureDir $vbp
        Copy-Item "$VoiceFolderPath\*" $vbp -Recurse -Force
        $validation = Test-BackupHasContent $bp
        if (-not $validation.Valid) { Add-Status $StatusBox $Form "  [!] Backup validation failed: $($validation.Reason)" "Orange"; Remove-Item $bp -Recurse -Force -ErrorAction SilentlyContinue; return $null }
        @{ ClientName=$ClientName; AppVersion=$AppVersion; BackupDate=(Get-Date).ToString("o", [System.Globalization.CultureInfo]::InvariantCulture); VoiceModulePath=$VoiceFolderPath; IsOriginal=$true; Description="Original Discord modules - preserved for reverting to mono audio"; FileCount=$validation.FileCount; TotalSize=$validation.TotalSize } | ConvertTo-Json | Out-File (Join-Path $bp "metadata.json") -Force
        Add-Status $StatusBox $Form "[OK] Original backup created: $scn ($($validation.FileCount) files, $([math]::Round($validation.TotalSize / 1KB, 1)) KB)" "Magenta"
        Add-Status $StatusBox $Form "     This backup will NEVER be deleted automatically" "Cyan"
        return $bp
    } catch { Add-Status $StatusBox $Form "[!] Original backup failed: $($_.Exception.Message)" "Orange"; Write-Log "Original backup failed: $($_.Exception.Message)" "ERROR"; return $null }
}

# Creates timestamped backup before applying fix (rotated, keeps 1 per client)
function Create-VoiceBackup { 
    param([string]$VoiceFolderPath, [string]$ClientName, [string]$AppVersion, [System.Windows.Forms.RichTextBox]$StatusBox, [System.Windows.Forms.Form]$Form)
    try {
        Initialize-BackupDirectory
        if (-not (Test-OriginalBackupExists $ClientName)) { Create-OriginalBackup $VoiceFolderPath $ClientName $AppVersion $StatusBox $Form | Out-Null }
        if (-not (Test-Path $VoiceFolderPath)) { Add-Status $StatusBox $Form "  [!] Source voice folder does not exist: $VoiceFolderPath" "Orange"; return $null }
        $sourceFiles = Get-ChildItem $VoiceFolderPath -File -Recurse -ErrorAction SilentlyContinue
        if (-not $sourceFiles -or $sourceFiles.Count -eq 0) { Add-Status $StatusBox $Form "  [!] Source voice folder is empty, cannot create backup" "Orange"; return $null }
        $ts = Get-Date -Format "yyyy-MM-dd_HHmmss"
        $scn = Get-SanitizedClientKey $ClientName
        $bn = "${scn}_${AppVersion}_${ts}"
        $bp = Join-Path $BACKUP_ROOT $bn
        try { [void](New-Item $bp -ItemType Directory -Force) } catch { }
        $vbp = Join-Path $bp "voice_module"
        Add-Status $StatusBox $Form "  Backing up voice module..." "Cyan"
        EnsureDir $vbp
        Copy-Item "$VoiceFolderPath\*" $vbp -Recurse -Force
        $validation = Test-BackupHasContent $bp
        if (-not $validation.Valid) { Add-Status $StatusBox $Form "  [!] Backup validation failed: $($validation.Reason)" "Orange"; Remove-Item $bp -Recurse -Force -ErrorAction SilentlyContinue; return $null }
        @{ ClientName=$ClientName; AppVersion=$AppVersion; BackupDate=(Get-Date).ToString("o", [System.Globalization.CultureInfo]::InvariantCulture); VoiceModulePath=$VoiceFolderPath; IsOriginal=$false; FileCount=$validation.FileCount; TotalSize=$validation.TotalSize } | ConvertTo-Json | Out-File (Join-Path $bp "metadata.json") -Force
        Add-Status $StatusBox $Form "[OK] Backup created: $bn ($($validation.FileCount) files)" "LimeGreen"
        return $bp
    } catch { Add-Status $StatusBox $Form "[!] Backup failed: $($_.Exception.Message)" "Orange"; Write-Log "Backup failed: $($_.Exception.Message)" "ERROR"; return $null }
}

# Gets all valid backups (original + rotated) with metadata
function Get-AvailableBackups {
    param([System.Windows.Forms.RichTextBox]$StatusBox = $null, [System.Windows.Forms.Form]$Form = $null)
    Initialize-BackupDirectory
    $bks = [System.Collections.ArrayList]@()
    $skippedBackups = [System.Collections.ArrayList]@()
    $originals = Get-ChildItem $ORIGINAL_BACKUP_ROOT -Directory -ErrorAction SilentlyContinue
    foreach ($f in $originals) {
        $mp = Join-Path $f.FullName "metadata.json"
        if (Test-Path $mp) {
            try {
                $m = Get-Content $mp -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
                if (-not $m.ClientName -or -not $m.AppVersion) { [void]$skippedBackups.Add(@{ Path = $f.FullName; Reason = "Missing required metadata fields" }); continue }
                $validation = Test-BackupHasContent $f.FullName
                if (-not $validation.Valid) { [void]$skippedBackups.Add(@{ Path = $f.FullName; Reason = $validation.Reason }); continue }
                $backupDate = Parse-BackupDate $m.BackupDate
                if ($backupDate -eq [DateTime]::MinValue) { $backupDate = (Get-Item $f.FullName).CreationTime }
                [void]$bks.Add(@{ Path=$f.FullName; Name=$f.Name; ClientName=$m.ClientName; AppVersion=$m.AppVersion; BackupDate=$backupDate; IsOriginal=$true; DisplayName="[ORIGINAL] $($m.ClientName) v$($m.AppVersion) - $($backupDate.ToString('MMM dd, yyyy HH:mm', [System.Globalization.CultureInfo]::InvariantCulture))"; FileCount = $validation.FileCount; TotalSize = $validation.TotalSize })
            } catch { [void]$skippedBackups.Add(@{ Path = $f.FullName; Reason = "Corrupted metadata.json" }); continue }
        } else { [void]$skippedBackups.Add(@{ Path = $f.FullName; Reason = "Missing metadata.json" }) }
    }
    $bfs = Get-ChildItem $BACKUP_ROOT -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending
    foreach ($f in $bfs) {
        $mp = Join-Path $f.FullName "metadata.json"
        if (Test-Path $mp) {
            try {
                $m = Get-Content $mp -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
                if (-not $m.ClientName -or -not $m.AppVersion) { [void]$skippedBackups.Add(@{ Path = $f.FullName; Reason = "Missing required metadata fields" }); continue }
                $validation = Test-BackupHasContent $f.FullName
                if (-not $validation.Valid) { [void]$skippedBackups.Add(@{ Path = $f.FullName; Reason = $validation.Reason }); continue }
                $backupDate = Parse-BackupDate $m.BackupDate
                if ($backupDate -eq [DateTime]::MinValue) { $backupDate = (Get-Item $f.FullName).CreationTime }
                [void]$bks.Add(@{ Path=$f.FullName; Name=$f.Name; ClientName=$m.ClientName; AppVersion=$m.AppVersion; BackupDate=$backupDate; IsOriginal=$false; DisplayName="$($m.ClientName) v$($m.AppVersion) - $($backupDate.ToString('MMM dd, yyyy HH:mm', [System.Globalization.CultureInfo]::InvariantCulture))"; FileCount = $validation.FileCount; TotalSize = $validation.TotalSize })
            } catch { [void]$skippedBackups.Add(@{ Path = $f.FullName; Reason = "Corrupted metadata.json" }); continue }
        } else { [void]$skippedBackups.Add(@{ Path = $f.FullName; Reason = "Missing metadata.json" }) }
    }
    if ($StatusBox -and $skippedBackups.Count -gt 0) {
        Add-Status $StatusBox $Form "  [!] Skipped $($skippedBackups.Count) invalid backup(s):" "Orange"
        foreach ($skip in $skippedBackups) { Add-Status $StatusBox $Form "      - $(Split-Path $skip.Path -Leaf) : $($skip.Reason)" "Orange" }
    }
    if ($bks.Count -eq 0) { return ,@() }
    return ,$bks.ToArray()
}

# Restores voice module from backup to target Discord installation
function Restore-FromBackup {
    param([hashtable]$Backup, [string]$TargetVoicePath, [System.Windows.Forms.RichTextBox]$StatusBox, [System.Windows.Forms.Form]$Form)
    try {
        if (-not $Backup -or -not $Backup.Path) { Add-Status $StatusBox $Form "[X] Invalid backup: backup data is null or missing path" "Red"; return $false }
        if (-not (Test-Path $Backup.Path)) { Add-Status $StatusBox $Form "[X] Backup folder no longer exists: $($Backup.Path)" "Red"; return $false }
        $vbp = Join-Path $Backup.Path "voice_module"
        if (-not (Test-Path $vbp)) { Add-Status $StatusBox $Form "[X] Backup is corrupted: voice_module folder not found" "Red"; return $false }
        $validation = Test-BackupHasContent $Backup.Path
        if (-not $validation.Valid) { Add-Status $StatusBox $Form "[X] Backup is invalid: $($validation.Reason)" "Red"; return $false }
        if ($Backup.IsOriginal) { Add-Status $StatusBox $Form "  Restoring ORIGINAL voice module (reverting to mono)..." "Magenta" }
        else { Add-Status $StatusBox $Form "  Restoring voice module ($($validation.FileCount) files, $([math]::Round($validation.TotalSize / 1KB, 1)) KB)..." "Cyan" }
        if (Test-Path $TargetVoicePath) { Remove-Item "$TargetVoicePath\*" -Recurse -Force -ErrorAction SilentlyContinue } else { EnsureDir $TargetVoicePath }
        Copy-Item "$vbp\*" $TargetVoicePath -Recurse -Force
        $restoredFiles = Get-ChildItem $TargetVoicePath -File -Recurse -ErrorAction SilentlyContinue
        if (-not $restoredFiles -or $restoredFiles.Count -eq 0) { Add-Status $StatusBox $Form "[X] Restore failed: no files were copied to target" "Red"; return $false }
        Add-Status $StatusBox $Form "  [OK] Restored $($restoredFiles.Count) files to target" "Cyan"
        return $true
    } catch { Add-Status $StatusBox $Form "[X] Restore failed: $($_.Exception.Message)" "Red"; Write-Log "Restore failed: $($_.Exception.Message)" "ERROR"; return $false }
}

# Removes old backups keeping only most recent per client
function Remove-OldBackups {
    $bfs = Get-ChildItem $BACKUP_ROOT -Directory -ErrorAction SilentlyContinue
    $byClient = @{}
    foreach ($f in $bfs) {
        $mp = Join-Path $f.FullName "metadata.json"
        if (Test-Path $mp) {
            try {
                $m = Get-Content $mp -Raw | ConvertFrom-Json
                $clientKey = $m.ClientName
                if (-not $byClient.ContainsKey($clientKey)) { $byClient[$clientKey] = [System.Collections.ArrayList]@() }
                $backupDate = Parse-BackupDate $m.BackupDate
                if ($backupDate -eq [DateTime]::MinValue) { $backupDate = (Get-Item $f.FullName).CreationTime }
                [void]$byClient[$clientKey].Add(@{ Path = $f.FullName; BackupDate = $backupDate })
            } catch { continue }
        }
    }
    foreach ($clientKey in $byClient.Keys) {
        $backups = $byClient[$clientKey] | Sort-Object { $_.BackupDate } -Descending
        $backups | Select-Object -Skip 1 | ForEach-Object { Remove-Item $_.Path -Recurse -Force -ErrorAction SilentlyContinue }
    }
}

#endregion

#region VERSION CHECK & UPDATE

# Checks if Discord was updated since last fix by comparing versions
function Check-DiscordUpdated { param([string]$ClientPath, [string]$ClientName)
    $st = Get-StateData; if (-not $st) { return $null }
    $ck = $ClientName -replace '\s+','_' -replace '\[|\]','' -replace '-','_'
    $ap = Find-DiscordAppPath $ClientPath; if (-not $ap) { return $null }
    $cv = Get-DiscordAppVersion $ap
    if ($st.$ck) {
        $lv = $st.$ck.LastFixedVersion; $lfd = $st.$ck.LastFixDate
        if ($lv -and $cv -ne $lv) { return @{Updated=$true; OldVersion=$lv; NewVersion=$cv; LastFixDate=$lfd; CurrentVersion=$cv} }
        return @{Updated=$false; CurrentVersion=$cv; LastFixDate=$lfd}
    }
    return @{Updated=$false; CurrentVersion=$cv; LastFixDate=$null}
}

# Saves fix state (version and timestamp) for tracking updates
function Save-FixState { param([string]$ClientName, [string]$Version)
    Initialize-BackupDirectory
    $st = Get-StateData; if (-not $st) { $st = @{} }
    if ($st -is [PSCustomObject]) { $ns = @{}; $st.PSObject.Properties | ForEach-Object { $ns[$_.Name] = $_.Value }; $st = $ns }
    $ck = $ClientName -replace '\s+','_' -replace '\[|\]','' -replace '-','_'
    $st[$ck] = @{LastFixedVersion=$Version; LastFixDate=(Get-Date).ToString("o", [System.Globalization.CultureInfo]::InvariantCulture)}
    Save-StateData $st
}

function Save-ScriptToAppData { param([System.Windows.Forms.RichTextBox]$StatusBox, [System.Windows.Forms.Form]$Form)
    try {
        EnsureDir (Split-Path $SAVED_SCRIPT_PATH -Parent)
        if (-not [string]::IsNullOrEmpty($PSCommandPath) -and (Test-Path $PSCommandPath)) { Copy-Item $PSCommandPath $SAVED_SCRIPT_PATH -Force; Add-Status $StatusBox $Form "[OK] Script saved to: $SAVED_SCRIPT_PATH" "LimeGreen"; return $SAVED_SCRIPT_PATH }
        Add-Status $StatusBox $Form "Downloading script from GitHub..." "Cyan"
        Invoke-WebRequest -Uri $UPDATE_URL -OutFile $SAVED_SCRIPT_PATH -UseBasicParsing -TimeoutSec 30 | Out-Null
        Add-Status $StatusBox $Form "[OK] Script downloaded and saved" "LimeGreen"; return $SAVED_SCRIPT_PATH
    } catch { Add-Status $StatusBox $Form "[X] Failed to save script: $($_.Exception.Message)" "Red"; Write-Log "Failed to save script: $($_.Exception.Message)" "ERROR"; return $null }
}

function Create-StartupShortcut { param([string]$ScriptPath, [bool]$RunSilent=$false)
    $sf = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
    $sp = Join-Path $sf "DiscordVoiceFixer.lnk"
    $ws = $null
    try {
        EnsureDir $sf
        $ws = New-Object -ComObject WScript.Shell
        $sc = $ws.CreateShortcut($sp)
        $sc.TargetPath = "powershell.exe"
        $ar = "-NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`""
        if ($RunSilent) { $ar += " -Silent" }
        $sc.Arguments = $ar; $sc.WorkingDirectory = (Split-Path $ScriptPath -Parent); $sc.WindowStyle = 7; $sc.Save()
        return $true
    } catch {
        Write-Log "Failed to create startup shortcut: $($_.Exception.Message)" "WARN"
        return $false
    } finally {
        if ($null -ne $ws) {
            try { [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($ws) } catch { }
        }
    }
}

function Remove-StartupShortcut {
    $sp = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\DiscordVoiceFixer.lnk"
    try {
        if (Test-Path $sp) { Remove-Item $sp -Force -ErrorAction SilentlyContinue }
    } catch {
        Write-Log "Failed to remove startup shortcut: $($_.Exception.Message)" "WARN"
    }
}

function Apply-ScriptUpdate { param([string]$UpdatedScriptPath, [string]$CurrentScriptPath)
    $bf = Join-Path $env:TEMP "StereoInstaller_Update.bat"
    $bc = "@echo off`ntimeout /t 2 /nobreak >nul`ncopy /Y `"$UpdatedScriptPath`" `"$CurrentScriptPath`" >nul`ntimeout /t 1 /nobreak >nul`nstart `"`" powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$CurrentScriptPath`"`ndel `"$UpdatedScriptPath`" >nul 2>&1`n(goto) 2>nul & del `"%~f0`""
    $bc | Out-File $bf -Encoding OEM -Force
    Start-Process "cmd.exe" -ArgumentList "/c","`"$bf`"" -WindowStyle Hidden
}

# Normalize script text so line-ending/BOM differences don't trigger false "updates".
function Normalize-ScriptTextForCompare {
    param([string]$Text)
    if ($null -eq $Text) { return "" }
    $t = [string]$Text
    # Strip UTF-8 BOM if present
    if ($t.Length -gt 0 -and [int][char]$t[0] -eq 0xFEFF) { $t = $t.Substring(1) }
    # Normalize newlines
    $t = $t -replace "`r`n", "`n"
    $t = $t -replace "`r", "`n"
    # Trim trailing whitespace on each line (git/raw can differ)
    $t = ($t -split "`n" | ForEach-Object { $_.TrimEnd() }) -join "`n"
    return $t.Trim()
}

#endregion

#region SILENT MODE

if ($Silent -or $CheckOnly) {
    Write-Log "Starting in $(if($Silent){'Silent'}else{'CheckOnly'}) mode"
    $ic = Get-InstalledClients
    $corruptedClients = @()
    foreach ($k in $DiscordClients.Keys) {
        $c = $DiscordClients[$k]
        if (Test-Path $c.Path) {
            $diag = Find-DiscordAppPath $c.Path -ReturnDiagnostics
            if ($diag.Error -eq "NoModulesFolder" -and $c.Name -match "\[Official\]") {
                $corruptedClients += @{ Key = $k; Client = $c; Path = $c.Path; Diag = $diag }
            }
        }
    }
    if ($corruptedClients.Count -gt 0 -and $ic.Count -eq 0) {
        if ($CheckOnly) {
            Write-Host "[!] Detected $($corruptedClients.Count) corrupted Discord installation(s):"
            foreach ($corrupt in $corruptedClients) {
                Write-Host "    - $($corrupt.Client.Name.Trim()) at $($corrupt.Path)"
            }
            Write-Host ""
            Write-Host "    Run without -CheckOnly flag to attempt automatic repair."
            Write-Host "    Or run in GUI mode for guided repair."
            exit 1
        }
        Write-Host "Detected $($corruptedClients.Count) corrupted Discord installation(s)"
        Write-Log "Detected $($corruptedClients.Count) corrupted Discord installation(s)"
        foreach ($corrupt in $corruptedClients) {
            Write-Host "Attempting to repair: $($corrupt.Client.Name.Trim())"
            $reinstallSuccess = $false
            try {
                $allProcs = @("Discord","DiscordCanary","DiscordPTB","DiscordDevelopment","Lightcord","BetterVencord","Equicord","Vencord","Update")
                Stop-DiscordProcesses $allProcs | Out-Null
                Start-Process "taskkill" -ArgumentList "/F","/IM","Discord*.exe" -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue
                Start-Sleep -Seconds 2
                $appFolders = Get-ChildItem $corrupt.Path -Filter "app-*" -Directory -ErrorAction SilentlyContinue
                foreach ($folder in $appFolders) { Remove-Item $folder.FullName -Recurse -Force -ErrorAction SilentlyContinue }
                $updateExe = Join-Path $corrupt.Path "Update.exe"
                if (Test-Path $updateExe) { Remove-Item $updateExe -Force -ErrorAction SilentlyContinue }
                $setupUrl = $DISCORD_SETUP_URL
                if ($corrupt.Client.Name -match "Canary") { $setupUrl = "https://discord.com/api/downloads/distributions/app/installers/latest?channel=canary&platform=win&arch=x64" }
                elseif ($corrupt.Client.Name -match "PTB") { $setupUrl = "https://discord.com/api/downloads/distributions/app/installers/latest?channel=ptb&platform=win&arch=x64" }
                elseif ($corrupt.Client.Name -match "Development") { $setupUrl = "https://discord.com/api/downloads/distributions/app/installers/latest?channel=development&platform=win&arch=x64" }
                $installerPath = Join-Path $env:TEMP "DiscordSetup_$(Get-Random).exe"
                Write-Host "  Downloading Discord installer..."
                try {
                    Invoke-WebRequest -Uri $setupUrl -OutFile $installerPath -UseBasicParsing -TimeoutSec 120
                    if (-not (Test-Path $installerPath)) { throw "Installer download failed - file not created" }
                    $installerSize = (Get-Item $installerPath).Length / 1MB
                    if ($installerSize -lt 1) { throw "Installer file is too small ($([math]::Round($installerSize, 2)) MB) - download may have failed" }
                    Write-Host "  [OK] Downloaded installer ($([math]::Round($installerSize, 1)) MB)"
                } catch {
                    Write-Host "  [FAIL] Failed to download Discord installer: $($_.Exception.Message)"
                    Write-Log "Silent mode installer download failed: $($_.Exception.Message)" "ERROR"
                    Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
                    continue
                }
                Write-Host "  Running installer..."
                Start-Process $installerPath
                $waited = 0
                while ($waited -lt 60) {
                    Start-Sleep -Seconds 2; $waited += 2
                    if (Get-Process -Name "Discord","DiscordCanary","DiscordPTB","DiscordDevelopment" -ErrorAction SilentlyContinue) { break }
                }
                Remove-Item $installerPath -Force -ErrorAction SilentlyContinue
                Write-Host "  Waiting for Discord to initialize..."
                $waitedSeconds = 0
                while ($waitedSeconds -lt 90) {
                    Start-Sleep -Seconds 5; $waitedSeconds += 5
                    $newDiag = Find-DiscordAppPath $corrupt.Path -ReturnDiagnostics
                    if ($newDiag.VoiceModuleExists) { Write-Host "  [OK] Discord repaired successfully"; $reinstallSuccess = $true; break }
                }
                if (-not $reinstallSuccess) { Write-Host "  [!] Voice module not detected after reinstall" }
            } catch { Write-Host "  [FAIL] Repair failed: $($_.Exception.Message)"; Write-Log "Silent repair failed: $($_.Exception.Message)" "ERROR" }
        }
        $ic = Get-InstalledClients
    }
    if ($ic.Count -eq 0) { 
        $noVoiceClients = @(); $noModulesClients = @()
        foreach ($k in $DiscordClients.Keys) {
            $c = $DiscordClients[$k]
            if (Test-Path $c.Path) {
                $diag = Find-DiscordAppPath $c.Path -ReturnDiagnostics
                if ($diag.Error -eq "NoVoiceModule") { $noVoiceClients += $c.Name.Trim() }
                elseif ($diag.Error -eq "NoModulesFolder") { $noModulesClients += $c.Name.Trim() }
            }
        }
        if ($noVoiceClients.Count -gt 0) {
            Write-Host "[!] Discord found but voice module not downloaded yet."
            Write-Host "    The voice module downloads when you first join a voice channel."
            Write-Host ""; Write-Host "    To fix this:"; Write-Host "    1) Open Discord"; Write-Host "    2) Join any voice channel"
            Write-Host "    3) Wait 30 seconds for modules to download"; Write-Host "    4) Run this script again"
            Write-Host ""; Write-Host "    Affected clients: $($noVoiceClients -join ', ')"; exit 1
        }
        if ($noModulesClients.Count -gt 0) {
            Write-Host "[!] Discord installation is corrupted (missing modules folder)."
            Write-Host "    Affected clients: $($noModulesClients -join ', ')"; Write-Host ""
            Write-Host "    Please run the script in GUI mode to auto-repair, or reinstall Discord manually."; exit 1
        }
        Write-Host "No Discord clients found."; exit 1 
    }
    if ($CheckOnly) {
        Write-Host "Checking Discord versions..."; $nf = $false
        foreach ($ci in $ic) {
            $uc = Check-DiscordUpdated $ci.Path $ci.Name
            if ($uc -and $uc.Updated) { Write-Host "[UPDATE] $($ci.Name.Trim()): v$($uc.OldVersion) -> v$($uc.NewVersion)"; $nf = $true }
            elseif ($uc -and $uc.LastFixDate) { 
                $lf = Safe-ParseDateTime $uc.LastFixDate
                if ($lf) { Write-Host "[OK] $($ci.Name.Trim()): v$($uc.CurrentVersion) (fixed: $($lf.ToString('MMM dd', [System.Globalization.CultureInfo]::InvariantCulture)))" }
                else { Write-Host "[OK] $($ci.Name.Trim()): v$($uc.CurrentVersion) (fixed: unknown date)" }
            }
            else { Write-Host "[NEW] $($ci.Name.Trim()): Never fixed"; $nf = $true }
        }
        if ($nf) { exit 1 }; exit 0
    }
    if ($FixClient) { $ic = @($ic | Where-Object { $_.Name -like "*$FixClient*" }); if ($ic.Count -eq 0) { Write-Host "Client '$FixClient' not found."; exit 1 } }
    $up = @{}; $uc = [System.Collections.ArrayList]@()
    foreach ($c in $ic) { if (-not $up.ContainsKey($c.AppPath)) { $up[$c.AppPath] = $true; [void]$uc.Add($c) } }
    
    $set = Load-Settings
    $updatedClients = Get-UpdatedDiscordClients
    if ($set.AutoFixOnDiscordUpdate -and $updatedClients.Count -gt 0) {
        Write-Host "=== DISCORD UPDATE DETECTED ==="
        foreach ($upd in $updatedClients) {
            Write-Host "  $($upd.Name.Trim()): v$($upd.OldVersion) -> v$($upd.NewVersion)"
        }
        $updatedPaths = $updatedClients | ForEach-Object { $_.AppPath }
        $uc = [System.Collections.ArrayList]@($uc | Where-Object { $_.AppPath -in $updatedPaths })
        Write-Host "Auto-fixing $($uc.Count) updated client(s)..."
    } elseif ($set.AutoFixOnDiscordUpdate -and $updatedClients.Count -eq 0) {
        $needsFix = $false
        foreach ($ci in $uc) {
            $checkResult = Check-DiscordUpdated $ci.Path $ci.Name
            if (-not $checkResult -or -not $checkResult.LastFixDate) { $needsFix = $true; break }
        }
        if (-not $needsFix) {
            $shouldAutoStart = $set.AutoStartDiscord -and $uc.Count -gt 0
            if (-not $shouldAutoStart) {
                Write-Host "No Discord updates detected. All clients are up to date."
            }
            Write-Log "Silent mode: No updates detected, skipping fix"
            if ($shouldAutoStart) {
                $pc = $uc[0]; $de = Join-Path $pc.AppPath $pc.Client.Exe
                if (-not (Start-DiscordClient $de)) { Write-Log "Auto-start Discord failed in silent mode (no updates path)" "WARN" }
            }
            exit 0
        }
        Write-Host "Found $($uc.Count) client(s) that need initial fix..."
    } else {
        Write-Host "Found $($uc.Count) client(s)"
    }
    
    if ($uc.Count -eq 0) {
        Write-Host "No clients to fix."
        exit 0
    }

    $td = Join-Path $env:TEMP "StereoInstaller_$(Get-Random)"
    EnsureDir $td
    try {
        $vbp = Join-Path $td "VoiceBackup"
        if (-not (Download-VoiceBackupFiles $vbp $null $null)) {
            throw "Download Failed"
        }
        $allProcs = @("Discord","DiscordCanary","DiscordPTB","DiscordDevelopment","Lightcord","BetterVencord","Equicord","Vencord","Update")
        $stopResult = Stop-DiscordProcesses $allProcs
        if (-not $stopResult) {
            Write-Host "[!] Warning: Some Discord processes may still be running"
            Start-Sleep -Seconds 2
        }
        Start-Sleep -Seconds 1
        $fxc = 0
        foreach ($ci in $uc) {
            $cl = $ci.Client
            $ap = $ci.AppPath
            $av = Get-DiscordAppVersion $ap
            Write-Host "Fixing $($cl.Name.Trim()) v$av..."
            try {
                $vm = Get-ChildItem "$ap\modules" -Filter "discord_voice*" -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
                if (-not $vm) { throw "No voice module found" }
                $tvf = if (Test-Path "$($vm.FullName)\discord_voice") { "$($vm.FullName)\discord_voice" } else { $vm.FullName }
                Create-VoiceBackup $tvf $cl.Name $av $null $null | Out-Null
                if (Test-Path $tvf) { Remove-Item "$tvf\*" -Recurse -Force -ErrorAction SilentlyContinue } else { EnsureDir $tvf }
                Copy-Item "$vbp\*" $tvf -Recurse -Force
                Save-FixState $cl.Name $av
                Write-Host "  [OK] Fixed successfully"
                $fxc++
            } catch {
                Write-Host "  [FAIL] $($_.Exception.Message)"
                Write-Log "Silent fix failed for $($cl.Name): $($_.Exception.Message)" "ERROR"
            }
        }
        Remove-OldBackups
        if ($set.FixEqApo) {
            Write-Host "Applying EQ APO fix to all clients..."
            $processedPaths = New-Object 'System.Collections.Generic.HashSet[string]'
            foreach ($ci in $uc) {
                $roamingPath = $ci.Client.RoamingPath
                if ($processedPaths.Contains($roamingPath)) { continue }
                if (-not (Test-Path $roamingPath)) { continue }
                [void]$processedPaths.Add($roamingPath)
                $result = Apply-EqApoFix -RoamingPath $roamingPath -ClientName $ci.Client.Name.Trim() -StatusBox $null -Form $null -SkipConfirmation $true
                if ($result) {
                    Write-Host "  [OK] EQ APO fix applied to $($ci.Client.Name.Trim())"
                } else {
                    Write-Host "  [FAIL] EQ APO fix failed for $($ci.Client.Name.Trim())"
                }
            }
        }
        if ($set.CreateShortcut) {
            $spt = $SAVED_SCRIPT_PATH
            if (!(Test-Path $spt)) { $spt = Save-ScriptToAppData $null $null }
            if ($spt) {
                if (Create-StartupShortcut $spt $set.SilentStartup) { Write-Host "  [OK] Startup shortcut created/updated" }
                else { Write-Host "  [!] Failed to create startup shortcut" }
            }
        }
        if ($set.AutoStartDiscord -and $fxc -gt 0 -and $uc.Count -gt 0) {
            $pc = $uc[0]
            $de = Join-Path $pc.AppPath $pc.Client.Exe
            if (-not (Start-DiscordClient $de)) { Write-Log "Auto-start Discord failed in silent mode (post-fix path)" "WARN" }
        }
        Write-Host "Fixed $fxc of $($uc.Count) client(s)"
        exit 0
    } finally {
        if (Test-Path $td) {
            Remove-Item $td -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

#endregion

#region GUI MODE

Write-Log "Starting in GUI mode"
$settings = Load-Settings

$form = New-Object System.Windows.Forms.Form
$form.Text = "Stereo Installer"; $form.Size = New-Object System.Drawing.Size(520,730)
$form.StartPosition = "CenterScreen"; $form.FormBorderStyle = "FixedDialog"; $form.MaximizeBox = $false
$form.BackColor = $Theme.Background; $form.TopMost = $true

$titleLabel = New-StyledLabel 20 15 460 35 "Stereo Installer" $Fonts.Title $Theme.TextPrimary "MiddleCenter"
$form.Controls.Add($titleLabel)
$creditsLabel = New-StyledLabel 20 52 460 28 "Made by`r`nOracle | Shaun | Hallow | Ascend | Sentry | Sikimzo | Cypher" $Fonts.Small $Theme.TextSecondary "MiddleCenter"
$form.Controls.Add($creditsLabel)

$updateStatusLabel = New-StyledLabel 20 82 460 18 "" $Fonts.Small $Theme.Warning "MiddleCenter"; $form.Controls.Add($updateStatusLabel)
$discordRunningLabel = New-StyledLabel 20 100 460 18 "" $Fonts.Small $Theme.Warning "MiddleCenter"; $form.Controls.Add($discordRunningLabel)

$clientGroup = New-Object System.Windows.Forms.GroupBox
$clientGroup.Location = New-Object System.Drawing.Point(20,120); $clientGroup.Size = New-Object System.Drawing.Size(460,60)
$clientGroup.Text = "Discord Client"; $clientGroup.ForeColor = $Theme.TextPrimary
$clientGroup.BackColor = [System.Drawing.Color]::Transparent; $clientGroup.Font = $Fonts.Normal
$form.Controls.Add($clientGroup)

$clientCombo = New-Object System.Windows.Forms.ComboBox
$clientCombo.Location = New-Object System.Drawing.Point(20,25); $clientCombo.Size = New-Object System.Drawing.Size(420,28)
$clientCombo.DropDownStyle = "DropDownList"; $clientCombo.BackColor = $Theme.ControlBg; $clientCombo.ForeColor = $Theme.TextPrimary
$clientCombo.FlatStyle = "Flat"; $clientCombo.Font = New-Object System.Drawing.Font("Consolas",9)
foreach ($c in $DiscordClients.Values) { [void]$clientCombo.Items.Add($c.Name) }
$selectedIndex = [Math]::Min([Math]::Max($settings.SelectedClientIndex, 0), $clientCombo.Items.Count - 1)
$clientCombo.SelectedIndex = $selectedIndex
$clientGroup.Controls.Add($clientCombo)

$optionsGroup = New-Object System.Windows.Forms.GroupBox
$optionsGroup.Location = New-Object System.Drawing.Point(20,190); $optionsGroup.Size = New-Object System.Drawing.Size(460,205)
$optionsGroup.Text = "Options"; $optionsGroup.ForeColor = $Theme.TextPrimary
$optionsGroup.BackColor = [System.Drawing.Color]::Transparent; $optionsGroup.Font = $Fonts.Normal
$form.Controls.Add($optionsGroup)

$chkUpdate = New-StyledCheckBox 20 25 420 22 "Check for script updates before fixing" $settings.CheckForUpdates; $optionsGroup.Controls.Add($chkUpdate)
$chkAutoUpdate = New-StyledCheckBox 40 47 400 22 "Automatically download and apply updates" $settings.AutoApplyUpdates $Theme.TextPrimary
$chkAutoUpdate.Enabled = $chkUpdate.Checked; $chkAutoUpdate.Visible = $chkUpdate.Checked; $optionsGroup.Controls.Add($chkAutoUpdate)
$chkShortcut = New-StyledCheckBox 20 69 280 22 "Create startup shortcut" $settings.CreateShortcut; $optionsGroup.Controls.Add($chkShortcut)
$btnSaveScript = New-StyledButton 305 69 135 22 "Save Script" $Fonts.ButtonSmall $Theme.Secondary; $optionsGroup.Controls.Add($btnSaveScript)
$chkSilentStartup = New-StyledCheckBox 40 91 400 22 "Run silently on startup (no GUI, auto-fix all)" $settings.SilentStartup $Theme.TextPrimary
$chkSilentStartup.Enabled = $chkShortcut.Checked; $chkSilentStartup.Visible = $chkShortcut.Checked; $optionsGroup.Controls.Add($chkSilentStartup)
$chkAutoFixOnUpdate = New-StyledCheckBox 20 113 420 22 "Auto-fix when Discord updates (on startup)" $settings.AutoFixOnDiscordUpdate $Theme.Success; $optionsGroup.Controls.Add($chkAutoFixOnUpdate)
$chkAutoStart = New-StyledCheckBox 20 135 420 22 "Automatically start Discord after fixing" $settings.AutoStartDiscord; $optionsGroup.Controls.Add($chkAutoStart)
$chkFixEqApo = New-StyledCheckBox 20 157 420 22 "Fix EQ APO not working (replaces settings.json)" $settings.FixEqApo $Theme.Warning; $optionsGroup.Controls.Add($chkFixEqApo)
$lblScriptStatus = New-StyledLabel 20 181 420 18 "" $Fonts.Small $Theme.TextSecondary "MiddleLeft"; $optionsGroup.Controls.Add($lblScriptStatus)

$statusBox = New-Object System.Windows.Forms.RichTextBox
$statusBox.Location = New-Object System.Drawing.Point(20,405); $statusBox.Size = New-Object System.Drawing.Size(460,145)
$statusBox.ReadOnly = $true; $statusBox.BackColor = $Theme.ControlBg; $statusBox.ForeColor = $Theme.TextPrimary
$statusBox.Font = $Fonts.Console; $statusBox.DetectUrls = $false; $statusBox.BorderStyle = "FixedSingle"
$form.Controls.Add($statusBox)

$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Location = New-Object System.Drawing.Point(20,560); $progressBar.Size = New-Object System.Drawing.Size(460,22)
$progressBar.Style = "Continuous"; $form.Controls.Add($progressBar)

$btnStart = New-StyledButton 20 595 100 38 "Start Fix"; $form.Controls.Add($btnStart)
$btnFixAll = New-StyledButton 125 595 100 38 "Fix All" $Fonts.Button $Theme.Success; $form.Controls.Add($btnFixAll)
$btnRollback = New-StyledButton 230 595 70 38 "Rollback" $Fonts.ButtonSmall $Theme.Secondary; $form.Controls.Add($btnRollback)
$btnOpenBackups = New-StyledButton 305 595 70 38 "Backups" $Fonts.ButtonSmall $Theme.Secondary; $form.Controls.Add($btnOpenBackups)
$btnCheckUpdate = New-StyledButton 380 595 100 38 "Check" $Fonts.ButtonSmall $Theme.Warning; $form.Controls.Add($btnCheckUpdate)
$btnVerify = New-StyledButton 20 640 100 32 "Verify Fix" $Fonts.ButtonSmall $Theme.Primary; $form.Controls.Add($btnVerify)
$btnFixEqApo = New-StyledButton 190 640 220 32 "Apply EQ APO Fix Only" $Fonts.ButtonSmall $Theme.Warning; $form.Controls.Add($btnFixEqApo)

function Update-ScriptStatusLabel {
    if (Test-Path $SAVED_SCRIPT_PATH) { $lm = (Get-Item $SAVED_SCRIPT_PATH).LastWriteTime.ToString("MMM dd, HH:mm"); $lblScriptStatus.Text = "Script saved: $lm"; $lblScriptStatus.ForeColor = $Theme.TextSecondary }
    else { $lblScriptStatus.Text = "Script not saved locally (required for startup shortcut)"; $lblScriptStatus.ForeColor = $Theme.Warning }
}

function Update-DiscordRunningWarning {
    $dp = @("Discord","DiscordCanary","DiscordPTB","DiscordDevelopment","Lightcord","Vencord","Equicord","BetterVencord")
    $r = Get-Process -Name $dp -ErrorAction SilentlyContinue
    if ($r) { $discordRunningLabel.Text = "[!] Discord is running - it will be closed when you apply the fix"; $discordRunningLabel.Visible = $true }
    else { $discordRunningLabel.Text = ""; $discordRunningLabel.Visible = $false }
}

function Save-CurrentSettings {
    $cs = [PSCustomObject]@{CheckForUpdates=$chkUpdate.Checked; AutoApplyUpdates=$chkAutoUpdate.Checked; CreateShortcut=$chkShortcut.Checked
        AutoStartDiscord=$chkAutoStart.Checked; SilentStartup=$chkSilentStartup.Checked; SelectedClientIndex=$clientCombo.SelectedIndex; FixEqApo=$chkFixEqApo.Checked; AutoFixOnDiscordUpdate=$chkAutoFixOnUpdate.Checked}
    Save-Settings $cs
}

$chkUpdate.Add_CheckedChanged({ $chkAutoUpdate.Enabled = $chkUpdate.Checked; $chkAutoUpdate.Visible = $chkUpdate.Checked; if (-not $chkUpdate.Checked) { $chkAutoUpdate.Checked = $false } })
$chkShortcut.Add_CheckedChanged({ $chkSilentStartup.Enabled = $chkShortcut.Checked; $chkSilentStartup.Visible = $chkShortcut.Checked; if (-not $chkShortcut.Checked) { $chkSilentStartup.Checked = $false } })
$btnSaveScript.Add_Click({ $statusBox.Clear(); $sp = Save-ScriptToAppData $statusBox $form; if ($sp) { Update-ScriptStatusLabel; [System.Windows.Forms.MessageBox]::Show($form,"Script saved to:`n$sp`n`nYou can now create a startup shortcut.","Script Saved","OK","Information") } })
$btnOpenBackups.Add_Click({ Initialize-BackupDirectory; Start-Process "explorer.exe" $APP_DATA_ROOT })

#endregion

#region BUTTON HANDLERS

$btnVerify.Add_Click({
    $btnVerify.Enabled = $false; $statusBox.Clear(); $progressBar.Value = 0
    try {
        $idx = $clientCombo.SelectedIndex
        if ($idx -lt 0 -or $idx -ge $DiscordClients.Count) { Add-Status $statusBox $form "[X] Invalid client selection" "Red"; return }
        $sc = $DiscordClients[$idx]
        Add-Status $statusBox $form "=== VERIFYING STEREO FIX ===" "Blue"
        Add-Status $statusBox $form "Client: $($sc.Name.Trim())" "Cyan"
        Update-Progress $progressBar $form 20
        $bp = Get-RealClientPath $sc
        if (-not $bp) { Add-Status $statusBox $form "[X] Discord client not found" "Red"; return }
        Add-Status $statusBox $form "Path: $bp" "Cyan"
        $ap = Find-DiscordAppPath $bp
        if (-not $ap) { Add-Status $statusBox $form "[X] Could not find Discord app folder" "Red"; return }
        $vm = Get-ChildItem "$ap\modules" -Filter "discord_voice*" -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $vm) { Add-Status $statusBox $form "[X] No voice module found" "Red"; return }
        $tvf = if (Test-Path "$($vm.FullName)\discord_voice") { "$($vm.FullName)\discord_voice" } else { $vm.FullName }
        Add-Status $statusBox $form "Voice module: $($vm.Name)" "Cyan"
        Update-Progress $progressBar $form 50
        Add-Status $statusBox $form "" "White"
        Add-Status $statusBox $form "Analyzing voice module files..." "Blue"
        $result = Verify-StereoFix $tvf $sc.Name $statusBox $form
        Update-Progress $progressBar $form 80
        Add-Status $statusBox $form "" "White"
        switch ($result.Status) {
            "Fixed" { 
                Add-Status $statusBox $form "[OK] STEREO FIX IS ACTIVE" "LimeGreen"
                Add-Status $statusBox $form "  $($result.Message)" "Cyan"
                if ($result.CurrentHash) { Add-Status $statusBox $form "  File hash: $($result.CurrentHash.Substring(0,8))..." "Cyan" }
            }
            "NotFixed" {
                Add-Status $statusBox $form "[!] STEREO FIX NOT APPLIED" "Orange"
                Add-Status $statusBox $form "  $($result.Message)" "Yellow"
                Add-Status $statusBox $form "  Discord is using original mono audio modules" "Yellow"
                Add-Status $statusBox $form "  Click 'Start Fix' or 'Fix All' to apply stereo fix" "Cyan"
            }
            "Unknown" {
                Add-Status $statusBox $form "[?] CANNOT DETERMINE FIX STATUS" "Yellow"
                Add-Status $statusBox $form "  $($result.Message)" "Yellow"
                Add-Status $statusBox $form "  Run 'Start Fix' once to create baseline for comparison" "Cyan"
            }
            "Error" {
                Add-Status $statusBox $form "[X] VERIFICATION FAILED" "Red"
                Add-Status $statusBox $form "  $($result.Message)" "Red"
            }
        }
        $uc = Check-DiscordUpdated $bp $sc.Name
        if ($uc -and $uc.Updated) {
            Add-Status $statusBox $form "" "White"
            Add-Status $statusBox $form "[!] Discord has been updated since last fix!" "Orange"
            Add-Status $statusBox $form "  Previous: v$($uc.OldVersion) -> Current: v$($uc.NewVersion)" "Orange"
            Add-Status $statusBox $form "  Re-applying the fix is recommended" "Yellow"
        }
        Update-Progress $progressBar $form 100
    } catch {
        Add-Status $statusBox $form "[X] Verification error: $($_.Exception.Message)" "Red"
        Write-Log "Verify error: $($_.Exception.Message)" "ERROR"
    } finally {
        $btnVerify.Enabled = $true
    }
})

$btnFixEqApo.Add_Click({
    $btnFixEqApo.Enabled = $false; $statusBox.Clear(); $progressBar.Value = 0
    try {
        Update-Progress $progressBar $form 10
        $dp = @("Discord","DiscordCanary","DiscordPTB","DiscordDevelopment","Lightcord","Vencord","Equicord","BetterVencord")
        $r = Get-Process -Name $dp -ErrorAction SilentlyContinue
        if ($r) {
            $closeResult = [System.Windows.Forms.MessageBox]::Show($form, "Discord is currently running. It needs to be closed to apply the EQ APO fix.`n`nClose Discord now?", "Discord Running", "YesNo", "Question")
            if ($closeResult -eq "Yes") {
                Add-Status $statusBox $form "Closing Discord processes..." "Blue"
                $allProcs = @("Discord","DiscordCanary","DiscordPTB","DiscordDevelopment","Lightcord","BetterVencord","Equicord","Vencord","Update")
                $stopResult = Stop-DiscordProcesses $allProcs
                if ($stopResult) { Add-Status $statusBox $form "[OK] Discord processes closed" "LimeGreen" }
                else { Add-Status $statusBox $form "[!] Warning: Some processes may still be running, waiting..." "Orange"; Start-Sleep -Seconds 2 }
                Start-Sleep -Seconds 1
            } else { Add-Status $statusBox $form "EQ APO fix cancelled - Discord must be closed" "Yellow"; return }
        }
        Update-Progress $progressBar $form 30
        $result = Apply-EqApoFixAll $statusBox $form $true
        Update-Progress $progressBar $form 90
        if ($result.Success -gt 0) {
            if ($chkAutoStart.Checked) {
                $idx = $clientCombo.SelectedIndex
                if ($idx -ge 0 -and $idx -lt $DiscordClients.Count) {
                    $sc = $DiscordClients[$idx]; $bp = Get-RealClientPath $sc
                    if ($bp) { $ap = Find-DiscordAppPath $bp; if ($ap) { Add-Status $statusBox $form "Starting Discord..." "Blue"; try { $de = Join-Path $ap $sc.Exe; if (Start-DiscordClient $de) { Add-Status $statusBox $form "[OK] Discord started" "LimeGreen" } else { Add-Status $statusBox $form "[!] Could not start Discord automatically" "Orange" } } catch { Add-Status $statusBox $form "[!] Could not start Discord automatically" "Orange" } } }
                }
            }
            Update-Progress $progressBar $form 100; Play-CompletionSound $true
            [System.Windows.Forms.MessageBox]::Show($form, "EQ APO fix applied to $($result.Success) client(s)!", "Success", "OK", "Information")
        } else { Update-Progress $progressBar $form 100; Play-CompletionSound $false }
    } catch { Add-Status $statusBox $form "[X] ERROR: $($_.Exception.Message)" "Red"; Write-Log "EQ APO button error: $($_.Exception.Message)" "ERROR"; Play-CompletionSound $false }
    finally { $btnFixEqApo.Enabled = $true }
})

$clientCombo.Add_SelectedIndexChanged({
    $idx = $clientCombo.SelectedIndex
    if ($idx -lt 0 -or $idx -ge $DiscordClients.Count) { $updateStatusLabel.Text = "Invalid selection"; $updateStatusLabel.ForeColor = $Theme.TextDim; return }
    $sc = $DiscordClients[$idx]; $bp = Get-RealClientPath $sc
    if (-not $bp) { $updateStatusLabel.Text = "Client not found"; $updateStatusLabel.ForeColor = $Theme.TextDim; return }
    $uc = Check-DiscordUpdated $bp $sc.Name
    if ($uc -and $uc.Updated) { $updateStatusLabel.Text = "Discord updated! v$($uc.OldVersion) -> v$($uc.NewVersion) - Fix recommended"; $updateStatusLabel.ForeColor = $Theme.Warning }
    elseif ($uc -and $uc.LastFixDate) { 
        $lf = Safe-ParseDateTime $uc.LastFixDate
        if ($lf) { $updateStatusLabel.Text = "Last fixed: $($lf.ToString('MMM dd, yyyy HH:mm', [System.Globalization.CultureInfo]::InvariantCulture)) (v$($uc.CurrentVersion))"; $updateStatusLabel.ForeColor = $Theme.TextSecondary }
        else { $updateStatusLabel.Text = "Last fixed: unknown date (v$($uc.CurrentVersion))"; $updateStatusLabel.ForeColor = $Theme.TextSecondary }
    }
    else { $updateStatusLabel.Text = "" }
})

$btnCheckUpdate.Add_Click({
    $btnCheckUpdate.Enabled = $false; $statusBox.Clear(); $progressBar.Value = 0
    try {
        $idx = $clientCombo.SelectedIndex
        if ($idx -lt 0 -or $idx -ge $DiscordClients.Count) { Add-Status $statusBox $form "[X] Invalid client selection" "Red"; return }
        $sc = $DiscordClients[$idx]
        Add-Status $statusBox $form "Checking Discord version..." "Blue"
        Update-Progress $progressBar $form 10
        $bp = Get-RealClientPath $sc
        if (-not $bp) { Add-Status $statusBox $form "[X] Discord client not found" "Red"; Add-Status $statusBox $form "    Try opening Discord first so we can detect the path." "Yellow"; return }
        Add-Status $statusBox $form "Found installation at: $bp" "Cyan"
        Update-Progress $progressBar $form 30
        $diag = Find-DiscordAppPath $bp -ReturnDiagnostics
        if ($diag.Error) {
            switch ($diag.Error) {
                "NoAppFolders" { Add-Status $statusBox $form "[X] No Discord app folders found (app-*)" "Red"; Add-Status $statusBox $form "    Discord may not be fully installed." "Yellow" }
                "NoModulesFolder" {
                    Add-Status $statusBox $form "[X] No 'modules' folder found in Discord" "Red"
                    Add-Status $statusBox $form "    Found app folder: $($diag.LatestAppVersion)" "Cyan"
                    Add-Status $statusBox $form "    Your Discord version is corrupted or severely outdated." "Yellow"
                    if ($sc.Name -match "\[Official\]") {
                        Add-Status $statusBox $form "[?] Would you like to automatically reinstall Discord?" "Magenta"
                        $reinstallResult = Reinstall-DiscordClient -ClientPath $bp -ClientInfo $sc -StatusBox $statusBox -Form $form
                        if ($reinstallResult) { Add-Status $statusBox $form "" "White"; Add-Status $statusBox $form "Waiting for Discord to stabilize..." "Cyan"; Start-Sleep -Seconds 5; Add-Status $statusBox $form "Discord reinstalled! Now applying the stereo fix..." "Blue"; $form.Refresh(); $btnFixAll.PerformClick() }
                    } else { Add-Status $statusBox $form "    Please manually reinstall $($sc.Name.Trim())" "Yellow" }
                }
                "NoVoiceModule" {
                    Add-Status $statusBox $form "[X] No 'discord_voice' module found" "Red"
                    Add-Status $statusBox $form "    Found app folder: $($diag.LatestAppVersion)" "Cyan"
                    Add-Status $statusBox $form "    The voice module may not have been downloaded yet." "Yellow"
                    Add-Status $statusBox $form "    Try: 1) Join a voice channel in Discord  2) Wait 30 seconds  3) Check again" "Yellow"
                }
                default { Add-Status $statusBox $form "[X] Unknown error finding Discord installation" "Red" }
            }
            return
        }
        Update-Progress $progressBar $form 50
        $ap = $diag.LatestAppFolder; $cv = Get-DiscordAppVersion $ap
        Add-Status $statusBox $form "Current version: $cv" "Cyan"
        Add-Status $statusBox $form "Voice module: $($diag.VoiceModulePath | Split-Path -Leaf)" "Cyan"
        Update-Progress $progressBar $form 70
        $uc = Check-DiscordUpdated $bp $sc.Name
        if ($uc -and $uc.Updated) {
            Add-Status $statusBox $form "[!] Discord has been updated!" "Yellow"
            Add-Status $statusBox $form "    Previous fixed: v$($uc.OldVersion)" "Cyan"
            Add-Status $statusBox $form "    Current: v$($uc.NewVersion)" "Cyan"
            Add-Status $statusBox $form "    Re-running the fix is recommended." "Cyan"
            $updateStatusLabel.Text = "Discord updated! v$($uc.OldVersion) -> v$($uc.NewVersion) - Fix recommended"
            $updateStatusLabel.ForeColor = $Theme.Warning
        } elseif ($uc -and $uc.LastFixDate) {
            $lf = Safe-ParseDateTime $uc.LastFixDate
            if ($lf) {
                Add-Status $statusBox $form "[OK] No update detected" "LimeGreen"
                Add-Status $statusBox $form "    Version: v$($uc.CurrentVersion)" "Cyan"
                Add-Status $statusBox $form "    Last fixed: $($lf.ToString('MMM dd, yyyy HH:mm', [System.Globalization.CultureInfo]::InvariantCulture))" "Cyan"
                $updateStatusLabel.Text = "Last fixed: $($lf.ToString('MMM dd, yyyy HH:mm', [System.Globalization.CultureInfo]::InvariantCulture)) (v$($uc.CurrentVersion))"
                $updateStatusLabel.ForeColor = $Theme.TextSecondary
            } else {
                Add-Status $statusBox $form "[OK] No update detected" "LimeGreen"
                Add-Status $statusBox $form "    Version: v$($uc.CurrentVersion)" "Cyan"
            }
        } else {
            Add-Status $statusBox $form "[?] Client has never been fixed" "Yellow"
            Add-Status $statusBox $form "    Version: v$cv" "Cyan"
            Add-Status $statusBox $form "    Run 'Start Fix' or 'Fix All' to apply the stereo fix." "Cyan"
        }
        Update-Progress $progressBar $form 100
    } catch {
        Add-Status $statusBox $form "[X] Check failed: $($_.Exception.Message)" "Red"
        Write-Log "Check error: $($_.Exception.Message)" "ERROR"
    } finally {
        $btnCheckUpdate.Enabled = $true
    }
})

$btnRollback.Add_Click({
    $btnRollback.Enabled = $false; $statusBox.Clear(); $progressBar.Value = 0
    try {
        $idx = $clientCombo.SelectedIndex
        if ($idx -lt 0 -or $idx -ge $DiscordClients.Count) { Add-Status $statusBox $form "[X] Invalid client selection" "Red"; return }
        $sc = $DiscordClients[$idx]
        Add-Status $statusBox $form "=== ROLLBACK ===" "Blue"
        Add-Status $statusBox $form "Client: $($sc.Name.Trim())" "Cyan"
        Update-Progress $progressBar $form 10
        $bp = Get-RealClientPath $sc
        if (-not $bp) { Add-Status $statusBox $form "[X] Discord client not found" "Red"; return }
        $ap = Find-DiscordAppPath $bp
        if (-not $ap) { Add-Status $statusBox $form "[X] Could not find Discord app folder" "Red"; return }
        $vm = Get-ChildItem "$ap\modules" -Filter "discord_voice*" -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $vm) { Add-Status $statusBox $form "[X] No voice module found" "Red"; return }
        $tvf = if (Test-Path "$($vm.FullName)\discord_voice") { "$($vm.FullName)\discord_voice" } else { $vm.FullName }
        Update-Progress $progressBar $form 20
        Add-Status $statusBox $form "Scanning available backups..." "Blue"
        $backups = Get-AvailableBackups $statusBox $form
        if (-not $backups -or $backups.Count -eq 0) { Add-Status $statusBox $form "[X] No backups found" "Red"; Add-Status $statusBox $form "    You need to run the fix at least once to create a backup." "Yellow"; return }
        $origBackup = Get-OriginalBackup $sc.Name
        Update-Progress $progressBar $form 30
        $backupForm = New-Object System.Windows.Forms.Form
        $backupForm.Text = "Select Backup to Restore"; $backupForm.Size = New-Object System.Drawing.Size(500,400)
        $backupForm.StartPosition = "CenterParent"; $backupForm.BackColor = $Theme.Background
        $backupForm.FormBorderStyle = "FixedDialog"; $backupForm.MaximizeBox = $false
        $lblSelect = New-StyledLabel 20 15 440 25 "Select a backup to restore:" $Fonts.Normal $Theme.TextPrimary
        $backupForm.Controls.Add($lblSelect)
        $listBackups = New-Object System.Windows.Forms.ListBox
        $listBackups.Location = New-Object System.Drawing.Point(20,45); $listBackups.Size = New-Object System.Drawing.Size(440,250)
        $listBackups.BackColor = $Theme.ControlBg; $listBackups.ForeColor = $Theme.TextPrimary
        $listBackups.Font = $Fonts.Console
        foreach ($b in $backups) { [void]$listBackups.Items.Add($b.DisplayName) }
        $backupForm.Controls.Add($listBackups)
        $btnRestore = New-StyledButton 20 310 200 35 "Restore Selected" $Fonts.Button $Theme.Primary
        $btnCancel = New-StyledButton 240 310 200 35 "Cancel" $Fonts.Button $Theme.Secondary
        $backupForm.Controls.Add($btnRestore); $backupForm.Controls.Add($btnCancel)
        $script:selectedBackup = $null
        $btnRestore.Add_Click({
            if ($listBackups.SelectedIndex -ge 0) { $script:selectedBackup = $backups[$listBackups.SelectedIndex]; $backupForm.DialogResult = "OK"; $backupForm.Close() }
            else { [System.Windows.Forms.MessageBox]::Show($backupForm, "Please select a backup first.", "No Selection", "OK", "Warning") }
        })
        $btnCancel.Add_Click({ $backupForm.DialogResult = "Cancel"; $backupForm.Close() })
        $result = $backupForm.ShowDialog($form)
        if ($result -ne "OK" -or -not $script:selectedBackup) { Add-Status $statusBox $form "Rollback cancelled" "Yellow"; return }
        Update-Progress $progressBar $form 40
        $sb = $script:selectedBackup
        if ($sb.IsOriginal) {
            $confirmResult = [System.Windows.Forms.MessageBox]::Show($form, "You are about to restore the ORIGINAL Discord voice modules.`n`nThis will REVERT to mono audio.`n`nAre you sure you want to continue?", "Confirm Restore Original", "YesNo", "Warning")
            if ($confirmResult -ne "Yes") { Add-Status $statusBox $form "Rollback cancelled" "Yellow"; return }
        }
        Add-Status $statusBox $form "Selected backup: $($sb.DisplayName)" "Cyan"
        Update-Progress $progressBar $form 50
        Add-Status $statusBox $form "Closing Discord processes..." "Blue"
        $allProcs = @("Discord","DiscordCanary","DiscordPTB","DiscordDevelopment","Lightcord","BetterVencord","Equicord","Vencord","Update")
        $stopResult = Stop-DiscordProcesses $allProcs
        if (-not $stopResult) { Add-Status $statusBox $form "[!] Warning: Some processes may still be running, waiting..." "Orange"; Start-Sleep -Seconds 2 }
        Start-Sleep -Seconds 1
        Update-Progress $progressBar $form 70
        Add-Status $statusBox $form "Restoring backup..." "Blue"
        $restoreResult = Restore-FromBackup $sb $tvf $statusBox $form
        if (-not $restoreResult) { Add-Status $statusBox $form "[X] Restore failed" "Red"; return }
        Update-Progress $progressBar $form 90
        if ($chkAutoStart.Checked) {
            Add-Status $statusBox $form "Starting Discord..." "Blue"
            try {
                $de = Join-Path $ap $sc.Exe
                if (Start-DiscordClient $de) { Add-Status $statusBox $form "[OK] Discord started" "LimeGreen" }
                else { Add-Status $statusBox $form "[!] Could not start Discord automatically - please start it manually" "Orange" }
            } catch { Add-Status $statusBox $form "[!] Could not start Discord automatically - please start it manually" "Orange"; Write-Log "Auto-start Discord failed: $($_.Exception.Message)" "WARN" }
        }
        Update-Progress $progressBar $form 100
        Add-Status $statusBox $form "" "White"
        if ($sb.IsOriginal) { Add-Status $statusBox $form "[OK] Rollback complete - ORIGINAL modules restored (mono audio)" "Magenta" }
        else { Add-Status $statusBox $form "[OK] Rollback complete!" "LimeGreen" }
        Play-CompletionSound $true
    } catch {
        Add-Status $statusBox $form "[X] Rollback failed: $($_.Exception.Message)" "Red"
        Write-Log "Rollback error: $($_.Exception.Message)" "ERROR"
        Play-CompletionSound $false
    } finally {
        $btnRollback.Enabled = $true
    }
})

$btnStart.Add_Click({
    $btnStart.Enabled = $false; $btnFixAll.Enabled = $false; $btnRollback.Enabled = $false; $btnCheckUpdate.Enabled = $false; $btnFixEqApo.Enabled = $false
    $statusBox.Clear(); $progressBar.Value = 0
    $td = Join-Path $env:TEMP "StereoInstaller_$(Get-Random)"
    try {
        $idx = $clientCombo.SelectedIndex
        if ($idx -lt 0 -or $idx -ge $DiscordClients.Count) { Add-Status $statusBox $form "[X] Invalid client selection" "Red"; return }
        $sc = $DiscordClients[$idx]
        Add-Status $statusBox $form "=== STARTING FIX ===" "Blue"
        Add-Status $statusBox $form "Client: $($sc.Name.Trim())" "Cyan"
        Update-Progress $progressBar $form 5
        $bp = Get-RealClientPath $sc
        if (-not $bp) { Add-Status $statusBox $form "[X] Discord client not found" "Red"; Add-Status $statusBox $form "    Try opening Discord first so we can detect the path." "Yellow"; return }
        Add-Status $statusBox $form "Found: $bp" "Cyan"
        Update-Progress $progressBar $form 10
        $diag = Find-DiscordAppPath $bp -ReturnDiagnostics
        if ($diag.Error) {
            switch ($diag.Error) {
                "NoAppFolders" { Add-Status $statusBox $form "[X] No Discord app folders found" "Red" }
                "NoModulesFolder" {
                    Add-Status $statusBox $form "[X] No 'modules' folder found - Discord may be corrupted" "Red"
                    if ($sc.Name -match "\[Official\]") {
                        $reinstallResult = Reinstall-DiscordClient -ClientPath $bp -ClientInfo $sc -StatusBox $statusBox -Form $form
                        if ($reinstallResult) { $diag = Find-DiscordAppPath $bp -ReturnDiagnostics }
                        else { return }
                    } else { Add-Status $statusBox $form "    Please manually reinstall $($sc.Name.Trim())" "Yellow"; return }
                }
                "NoVoiceModule" {
                    Add-Status $statusBox $form "[X] No voice module found" "Red"
                    Add-Status $statusBox $form "    Please join a voice channel in Discord first to download modules." "Yellow"
                    return
                }
            }
            if ($diag.Error) { return }
        }
        $ap = $diag.LatestAppFolder; $av = Get-DiscordAppVersion $ap
        Add-Status $statusBox $form "Version: v$av" "Cyan"
        $vm = Get-ChildItem "$ap\modules" -Filter "discord_voice*" -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
        if (-not $vm) { Add-Status $statusBox $form "[X] No voice module found after operation" "Red"; return }
        $tvf = if (Test-Path "$($vm.FullName)\discord_voice") { "$($vm.FullName)\discord_voice" } else { $vm.FullName }
        Add-Status $statusBox $form "Voice module: $($vm.Name)" "Cyan"
        Update-Progress $progressBar $form 15
        if ($chkUpdate.Checked) {
            Add-Status $statusBox $form "" "White"
            Add-Status $statusBox $form "Checking for script updates..." "Blue"
            try {
                $tmpScript = Join-Path $env:TEMP "DiscordVoiceFixer_check_$(Get-Random).ps1"
                Invoke-WebRequest -Uri $UPDATE_URL -OutFile $tmpScript -UseBasicParsing -TimeoutSec 15 | Out-Null
                $remoteContent = Get-Content $tmpScript -Raw
                $currentContent = if (Test-Path $SAVED_SCRIPT_PATH) { Get-Content $SAVED_SCRIPT_PATH -Raw } 
                                  elseif (-not [string]::IsNullOrEmpty($PSCommandPath) -and (Test-Path $PSCommandPath)) { Get-Content $PSCommandPath -Raw }
                                  else { $null }
                $remoteNorm = Normalize-ScriptTextForCompare $remoteContent
                $currentNorm = Normalize-ScriptTextForCompare $currentContent
                if ($currentContent -and $remoteNorm -and $currentNorm -and $remoteNorm -ne $currentNorm) {
                    Add-Status $statusBox $form "[!] Script update available!" "Yellow"
                    if ($chkAutoUpdate.Checked) {
                        Add-Status $statusBox $form "Auto-applying update..." "Blue"
                        $targetPath = if (Test-Path $SAVED_SCRIPT_PATH) { $SAVED_SCRIPT_PATH }
                                      elseif (-not [string]::IsNullOrEmpty($PSCommandPath) -and (Test-Path $PSCommandPath)) { $PSCommandPath }
                                      else { $SAVED_SCRIPT_PATH }
                        Apply-ScriptUpdate $tmpScript $targetPath
                        Add-Status $statusBox $form "[OK] Update applied - restarting..." "LimeGreen"
                        return
                    } else {
                        $updateResult = [System.Windows.Forms.MessageBox]::Show($form, "A script update is available. Would you like to update now?", "Update Available", "YesNo", "Question")
                        if ($updateResult -eq "Yes") {
                            $targetPath = if (Test-Path $SAVED_SCRIPT_PATH) { $SAVED_SCRIPT_PATH }
                                          elseif (-not [string]::IsNullOrEmpty($PSCommandPath) -and (Test-Path $PSCommandPath)) { $PSCommandPath }
                                          else { $SAVED_SCRIPT_PATH }
                            Apply-ScriptUpdate $tmpScript $targetPath
                            Add-Status $statusBox $form "[OK] Update applied - restarting..." "LimeGreen"
                            return
                        }
                    }
                } else { Add-Status $statusBox $form "[OK] Script is up to date" "LimeGreen" }
                Remove-Item $tmpScript -Force -ErrorAction SilentlyContinue
            } catch { Add-Status $statusBox $form "[!] Could not check for updates: $($_.Exception.Message)" "Orange" }
        }
        Update-Progress $progressBar $form 20
        Add-Status $statusBox $form "" "White"
        Add-Status $statusBox $form "Downloading voice backup files..." "Blue"
        EnsureDir $td
        $vbp = Join-Path $td "VoiceBackup"
        if (-not (Download-VoiceBackupFiles $vbp $statusBox $form)) { throw "Failed to download voice backup files" }
        Update-Progress $progressBar $form 40
        Add-Status $statusBox $form "" "White"
        Add-Status $statusBox $form "Closing Discord processes..." "Blue"
        $allProcs = @("Discord","DiscordCanary","DiscordPTB","DiscordDevelopment","Lightcord","BetterVencord","Equicord","Vencord","Update")
        $stopResult = Stop-DiscordProcesses $allProcs
        if (-not $stopResult) {
            Add-Status $statusBox $form "[!] Warning: Some processes may still be running, retrying..." "Orange"
            Start-Sleep -Seconds 2
            $stopResult = Stop-DiscordProcesses $allProcs
            if (-not $stopResult) {
                throw "Could not close all Discord processes. Please close Discord manually (check system tray) and try again."
            }
        }
        Add-Status $statusBox $form "[OK] Discord processes closed" "LimeGreen"
        Start-Sleep -Milliseconds 500
        Update-Progress $progressBar $form 50
        Add-Status $statusBox $form "" "White"
        Add-Status $statusBox $form "Creating backup..." "Blue"
        Create-VoiceBackup $tvf $sc.Name $av $statusBox $form | Out-Null
        Update-Progress $progressBar $form 60
        Add-Status $statusBox $form "" "White"
        Add-Status $statusBox $form "Applying stereo fix..." "Blue"
        if (Test-Path $tvf) { Remove-Item "$tvf\*" -Recurse -Force -ErrorAction SilentlyContinue } else { EnsureDir $tvf }
        Copy-Item "$vbp\*" $tvf -Recurse -Force
        Save-FixState $sc.Name $av
        Add-Status $statusBox $form "[OK] Stereo fix applied!" "LimeGreen"
        Update-Progress $progressBar $form 70
        Remove-OldBackups
        if ($chkFixEqApo.Checked) {
            Add-Status $statusBox $form "" "White"
            $eqResult = Apply-EqApoFix -RoamingPath $sc.RoamingPath -ClientName $sc.Name.Trim() -StatusBox $statusBox -Form $form -SkipConfirmation $true
        }
        Update-Progress $progressBar $form 80
        if ($chkShortcut.Checked) {
            Add-Status $statusBox $form "" "White"
            Add-Status $statusBox $form "Creating startup shortcut..." "Blue"
            $spt = $SAVED_SCRIPT_PATH
            if (!(Test-Path $spt)) { $spt = Save-ScriptToAppData $statusBox $form }
            if ($spt) {
                if (Create-StartupShortcut $spt $chkSilentStartup.Checked) { Add-Status $statusBox $form "[OK] Startup shortcut created" "LimeGreen" }
                else { Add-Status $statusBox $form "[!] Failed to create startup shortcut" "Orange" }
            } else { Add-Status $statusBox $form "[!] Could not save script - shortcut not created" "Orange" }
        } else { Remove-StartupShortcut }
        Update-Progress $progressBar $form 90
        if ($chkAutoStart.Checked) {
            Add-Status $statusBox $form "" "White"
            Add-Status $statusBox $form "Starting Discord..." "Blue"
            try {
                $de = Join-Path $ap $sc.Exe
                if (Start-DiscordClient $de) { Add-Status $statusBox $form "[OK] Discord started" "LimeGreen" }
                else { Add-Status $statusBox $form "[!] Could not start Discord automatically - please start it manually" "Orange" }
            } catch { Add-Status $statusBox $form "[!] Could not start Discord automatically - please start it manually" "Orange"; Write-Log "Auto-start Discord failed: $($_.Exception.Message)" "WARN" }
        }
        Update-Progress $progressBar $form 100
        Add-Status $statusBox $form "" "White"
        Add-Status $statusBox $form "=== FIX COMPLETED SUCCESSFULLY ===" "LimeGreen"
        Save-CurrentSettings
        Play-CompletionSound $true
        [System.Windows.Forms.MessageBox]::Show($form, "Stereo fix applied successfully!`n`nOriginal modules preserved for rollback.", "Success", "OK", "Information")
    } catch {
        Add-Status $statusBox $form "" "White"
        Add-Status $statusBox $form "[X] ERROR: $($_.Exception.Message)" "Red"
        Write-Log "Fix error: $($_.Exception.Message)" "ERROR"
        Play-CompletionSound $false
        [System.Windows.Forms.MessageBox]::Show($form, "An error occurred: $($_.Exception.Message)", "Error", "OK", "Error")
    } finally {
        if (Test-Path $td) { Remove-Item $td -Recurse -Force -ErrorAction SilentlyContinue }
        $btnStart.Enabled = $true; $btnFixAll.Enabled = $true; $btnRollback.Enabled = $true; $btnCheckUpdate.Enabled = $true; $btnFixEqApo.Enabled = $true
    }
})

$btnFixAll.Add_Click({
    if (-not $btnFixAll.Enabled) { return }
    $btnStart.Enabled = $false; $btnFixAll.Enabled = $false; $btnRollback.Enabled = $false; $btnCheckUpdate.Enabled = $false; $btnFixEqApo.Enabled = $false
    $statusBox.Clear(); $progressBar.Value = 0
    $td = Join-Path $env:TEMP "StereoInstaller_$(Get-Random)"
    try {
        Add-Status $statusBox $form "=== FIX ALL DISCORD CLIENTS ===" "Blue"
        Add-Status $statusBox $form "Scanning for installed clients..." "Cyan"
        $ic = Get-InstalledClients
        $corruptedClients = @()
        foreach ($k in $DiscordClients.Keys) {
            $c = $DiscordClients[$k]
            if (Test-Path $c.Path) {
                $diag = Find-DiscordAppPath $c.Path -ReturnDiagnostics
                if ($diag.Error -eq "NoModulesFolder" -and $c.Name -match "\[Official\]") {
                    $corruptedClients += @{ Key = $k; Client = $c; Path = $c.Path; Diag = $diag }
                }
            }
        }
        if ($corruptedClients.Count -gt 0) {
            Add-Status $statusBox $form "[!] Found $($corruptedClients.Count) corrupted Discord installation(s)" "Orange"
            foreach ($corrupt in $corruptedClients) {
                Add-Status $statusBox $form "    - $($corrupt.Client.Name.Trim())" "Yellow"
                $reinstallResult = Reinstall-DiscordClient -ClientPath $corrupt.Path -ClientInfo $corrupt.Client -StatusBox $statusBox -Form $form
                if ($reinstallResult) { $ic = Get-InstalledClients }
            }
        }
        if ($ic.Count -eq 0) {
            $noVoiceClients = @(); $noModulesClients = @()
            foreach ($k in $DiscordClients.Keys) {
                $c = $DiscordClients[$k]
                if (Test-Path $c.Path) {
                    $diag = Find-DiscordAppPath $c.Path -ReturnDiagnostics
                    if ($diag.Error -eq "NoVoiceModule") { $noVoiceClients += $c.Name.Trim() }
                    elseif ($diag.Error -eq "NoModulesFolder") { $noModulesClients += $c.Name.Trim() }
                }
            }
            if ($noVoiceClients.Count -gt 0) {
                Add-Status $statusBox $form "[!] Discord found but voice module not downloaded yet" "Orange"
                Add-Status $statusBox $form "    The voice module downloads when you first join a voice channel." "Yellow"
                Add-Status $statusBox $form "" "White"
                Add-Status $statusBox $form "    To fix: 1) Open Discord  2) Join any voice channel  3) Wait 30 seconds  4) Try again" "Yellow"
                Add-Status $statusBox $form "" "White"
                Add-Status $statusBox $form "    Affected: $($noVoiceClients -join ', ')" "Yellow"
                return
            }
            if ($noModulesClients.Count -gt 0) {
                Add-Status $statusBox $form "[!] Discord installation is corrupted (missing modules folder)" "Orange"
                Add-Status $statusBox $form "    Affected: $($noModulesClients -join ', ')" "Yellow"
                Add-Status $statusBox $form "" "White"
                Add-Status $statusBox $form "    Please reinstall Discord manually or use the Check button for guided repair." "Yellow"
                return
            }
            Add-Status $statusBox $form "[X] No Discord clients found" "Red"
            return
        }
        $up = @{}; $uc = [System.Collections.ArrayList]@()
        foreach ($c in $ic) { if (-not $up.ContainsKey($c.AppPath)) { $up[$c.AppPath] = $true; [void]$uc.Add($c) } }
        Add-Status $statusBox $form "[OK] Found $($uc.Count) client(s):" "LimeGreen"
        foreach ($c in $uc) { $v = Get-DiscordAppVersion $c.AppPath; Add-Status $statusBox $form "    - $($c.Name.Trim()) (v$v)" "Cyan" }
        Update-Progress $progressBar $form 5
        $cr = [System.Windows.Forms.MessageBox]::Show($form,"Found $($uc.Count) Discord client(s). Apply fix to all?","Confirm Fix All","YesNo","Question")
        if ($cr -ne "Yes") { Add-Status $statusBox $form "Operation cancelled by user" "Yellow"; return }
        Add-Status $statusBox $form "" "White"; Add-Status $statusBox $form "Downloading required files from GitHub..." "Blue"; EnsureDir $td
        $vbp = Join-Path $td "VoiceBackup"; 
        if (-not (Download-VoiceBackupFiles $vbp $statusBox $form)) { throw "Failed to download voice backup files" }
        Update-Progress $progressBar $form 20
        Add-Status $statusBox $form "" "White"; Add-Status $statusBox $form "Closing all Discord processes..." "Blue"
        $allProcs = @("Discord","DiscordCanary","DiscordPTB","DiscordDevelopment","Lightcord","BetterVencord","Equicord","Vencord","Update")
        $stopResult = Stop-DiscordProcesses $allProcs
        if (-not $stopResult) {
            Add-Status $statusBox $form "[!] Warning: Some processes may still be running, retrying..." "Orange"
            Start-Sleep -Seconds 2
            $stopResult = Stop-DiscordProcesses $allProcs
            if (-not $stopResult) {
                throw "Could not close all Discord processes. Please close Discord manually (check system tray) and try again."
            }
        }
        Add-Status $statusBox $form "[OK] Discord processes closed" "LimeGreen"
        Start-Sleep -Milliseconds 500
        Update-Progress $progressBar $form 30
        $ppc = 50 / [Math]::Max($uc.Count, 1); $cp = 30; $fxc = 0; $fc = @()
        foreach ($ci in $uc) {
            Add-Status $statusBox $form "" "White"; Add-Status $statusBox $form "=== Fixing: $($ci.Name.Trim()) ===" "Blue"
            try {
                $ap = $ci.AppPath; $av = Get-DiscordAppVersion $ap
                $vm = Get-ChildItem "$ap\modules" -Filter "discord_voice*" -Directory | Select-Object -First 1
                if (-not $vm) { throw "No discord_voice module found" }
                $tvf = if (Test-Path "$($vm.FullName)\discord_voice") { "$($vm.FullName)\discord_voice" } else { $vm.FullName }
                Add-Status $statusBox $form "  Creating backup..." "Cyan"
                Create-VoiceBackup $tvf $ci.Name $av $statusBox $form | Out-Null
                if (Test-Path $tvf) { Remove-Item "$tvf\*" -Recurse -Force -ErrorAction SilentlyContinue } else { EnsureDir $tvf }
                Add-Status $statusBox $form "  Copying module files..." "Cyan"; Copy-Item "$vbp\*" $tvf -Recurse -Force
                Save-FixState $ci.Name $av; Add-Status $statusBox $form "[OK] $($ci.Name.Trim()) fixed successfully" "LimeGreen"; $fxc++
            } catch { Add-Status $statusBox $form "[X] Failed to fix $($ci.Name.Trim()): $($_.Exception.Message)" "Red"; $fc += $ci.Name; Write-Log "Fix All failed for $($ci.Name): $($_.Exception.Message)" "ERROR" }
            $cp += $ppc; Update-Progress $progressBar $form ([int]$cp)
        }
        Remove-OldBackups; Update-Progress $progressBar $form 85
        if ($chkFixEqApo.Checked) {
            $eqResult = Apply-EqApoFixAll $statusBox $form $true
            if ($eqResult.Success -eq 0) { Add-Status $statusBox $form "[!] EQ APO fix was not applied to any clients" "Orange" }
            else { Add-Status $statusBox $form "[OK] EQ APO fix applied to $($eqResult.Success) client(s)" "LimeGreen" }
        }
        Update-Progress $progressBar $form 90
        if ($chkShortcut.Checked) {
            Add-Status $statusBox $form "Creating startup shortcut..." "Blue"
            $spt = $SAVED_SCRIPT_PATH; if (!(Test-Path $spt)) { $spt = Save-ScriptToAppData $statusBox $form }
            if ($spt) {
                if (Create-StartupShortcut $spt $chkSilentStartup.Checked) { Add-Status $statusBox $form "[OK] Startup shortcut created" "LimeGreen" }
                else { Add-Status $statusBox $form "[!] Failed to create startup shortcut" "Orange" }
            } else { Add-Status $statusBox $form "[!] Could not save script - shortcut not created" "Orange" }
        } else { Remove-StartupShortcut }
        if ($chkAutoStart.Checked -and $fxc -gt 0 -and $uc.Count -gt 0) {
            Add-Status $statusBox $form "" "White"; Add-Status $statusBox $form "Starting Discord..." "Blue"
            try {
                $pc = $uc[0]; $de = Join-Path $pc.AppPath $pc.Client.Exe
                if (Start-DiscordClient $de) { Add-Status $statusBox $form "[OK] Discord started" "LimeGreen" }
                else { Add-Status $statusBox $form "[!] Could not start Discord automatically - please start it manually" "Orange" }
            } catch { Add-Status $statusBox $form "[!] Could not start Discord automatically - please start it manually" "Orange"; Write-Log "Auto-start Discord failed: $($_.Exception.Message)" "WARN" }
        }
        Update-Progress $progressBar $form 100
        Add-Status $statusBox $form "" "White"; Add-Status $statusBox $form "=== FIX ALL COMPLETED ===" "LimeGreen"
        Add-Status $statusBox $form "Fixed: $fxc / $($uc.Count) clients" "Cyan"; Save-CurrentSettings
        if ($fc.Count -gt 0) { Play-CompletionSound $false; [System.Windows.Forms.MessageBox]::Show($form,"Fixed $fxc of $($uc.Count) clients.`n`nFailed: $($fc -join ', ')","Completed with Errors","OK","Warning") }
        else { Play-CompletionSound $true; [System.Windows.Forms.MessageBox]::Show($form,"Successfully fixed all $fxc Discord client(s)!`n`nOriginal modules preserved for each client.","Success","OK","Information") }
    } catch {
        Add-Status $statusBox $form "" "White"; Add-Status $statusBox $form "[X] ERROR: $($_.Exception.Message)" "Red"
        Write-Log "Fix All error: $($_.Exception.Message)" "ERROR"
        Play-CompletionSound $false; [System.Windows.Forms.MessageBox]::Show($form,"An error occurred: $($_.Exception.Message)","Error","OK","Error")
    } finally {
        if (Test-Path $td) { Remove-Item $td -Recurse -Force -ErrorAction SilentlyContinue }
        $btnStart.Enabled = $true; $btnFixAll.Enabled = $true; $btnRollback.Enabled = $true; $btnCheckUpdate.Enabled = $true; $btnFixEqApo.Enabled = $true
    }
})

#endregion

#region FORM EVENTS & STARTUP

$timer = New-Object System.Windows.Forms.Timer; $timer.Interval = 5000
$timer.Add_Tick({ Update-DiscordRunningWarning }); $timer.Start()

$form.Add_Shown({
    $form.Activate(); Update-DiscordRunningWarning; Update-ScriptStatusLabel
    $idx = $clientCombo.SelectedIndex
    if ($idx -ge 0 -and $idx -lt $DiscordClients.Count) {
        $sc = $DiscordClients[$idx]; $bp = Get-RealClientPath $sc
        if ($bp) {
            $uc = Check-DiscordUpdated $bp $sc.Name
            if ($uc -and $uc.Updated) { $updateStatusLabel.Text = "Discord updated! v$($uc.OldVersion) -> v$($uc.NewVersion) - Fix recommended"; $updateStatusLabel.ForeColor = $Theme.Warning }
            elseif ($uc -and $uc.LastFixDate) { 
                $lf = Safe-ParseDateTime $uc.LastFixDate
                if ($lf) { $updateStatusLabel.Text = "Last fixed: $($lf.ToString('MMM dd, yyyy HH:mm', [System.Globalization.CultureInfo]::InvariantCulture)) (v$($uc.CurrentVersion))"; $updateStatusLabel.ForeColor = $Theme.TextSecondary }
            }
        }
    }
    if ($chkAutoFixOnUpdate.Checked) {
        try {
            $updatedClients = Get-UpdatedDiscordClients
            if ($updatedClients.Count -gt 0) {
                $clientNames = ($updatedClients | ForEach-Object { "$($_.Name.Trim()): v$($_.OldVersion) -> v$($_.NewVersion)" }) -join "`n"
                Add-Status $statusBox $form "=== DISCORD UPDATE DETECTED ===" "Magenta"
                Add-Status $statusBox $form "The following Discord client(s) have been updated:" "Yellow"
                foreach ($client in $updatedClients) { Add-Status $statusBox $form "  - $($client.Name.Trim()): v$($client.OldVersion) -> v$($client.NewVersion)" "Orange" }
                $autoFixResult = [System.Windows.Forms.MessageBox]::Show($form, "Discord has been updated!`n`n$clientNames`n`nWould you like to automatically re-apply the stereo fix?", "Discord Updated - Auto-Fix", "YesNo", "Question")
                if ($autoFixResult -eq "Yes") {
                    Add-Status $statusBox $form "" "White"
                    Add-Status $statusBox $form "Auto-fixing updated clients..." "Blue"
                    $btnFixAll.PerformClick()
                } else {
                    Add-Status $statusBox $form "" "White"
                    Add-Status $statusBox $form "Auto-fix skipped. Click 'Fix All' when ready." "Yellow"
                }
            }
        } catch {
            Write-Log "Auto-fix check failed: $($_.Exception.Message)" "ERROR"
        }
    }
})

$form.Add_FormClosing({ Save-CurrentSettings })
$form.Add_FormClosed({ 
    $timer.Stop(); $timer.Dispose()
    foreach ($font in $Fonts.Values) { try { $font.Dispose() } catch { } }
})

[void]$form.ShowDialog()

#endregion
