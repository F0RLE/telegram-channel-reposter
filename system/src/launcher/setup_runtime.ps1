# Setup Runtime Script
# Installs standard Python 3.11 locally

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$RootDir = "$ScriptDir\..\..\.."
$RuntimeDir = "$RootDir\system\runtime"
$AppDataDir = "$env:APPDATA\TelegramBotData"
$TempDir = "$AppDataDir\data\temp"
$PythonDir = "$RuntimeDir\python"

# URLs
$PyInstallUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"

Write-Host "[SETUP] Starting Standard Python Setup..." -ForegroundColor Cyan

# 1. Prepare Directories
Write-Host "[SETUP] Cleaning up previous run..." -ForegroundColor Yellow

# Kill potential lingering processes
Get-Process "python_installer" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process "msiexec" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

if (Test-Path $PythonDir) { 
    try {
        Remove-Item -Path $PythonDir -Recurse -Force -ErrorAction Stop
    } catch {
        Write-Host "[WARNING] Could not clean Python dir: $_" -ForegroundColor Red
    }
}

if (Test-Path $TempDir) { 
    try {
        Remove-Item -Path $TempDir -Recurse -Force -ErrorAction Stop
    } catch {
        Write-Host "[WARNING] Could not clean Temp dir: $_" -ForegroundColor Red
    }
}
New-Item -ItemType Directory -Path $PythonDir -Force | Out-Null
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

# Helper function for fast download
function Download-File {
    param([string]$Url, [string]$Dest)
    Write-Host "Downloading: $Url" -ForegroundColor Gray
    
    # Method 1: BITS (Foreground Priority)
    try {
        Start-BitsTransfer -Source $Url -Destination $Dest -Priority Foreground -ErrorAction Stop
        return
    } catch {
        Write-Host "BITS failed, trying curl..." -ForegroundColor Gray
    }

    # Method 2: curl (Windows native)
    try {
        $CurlArgs = "-L", "-o", "`"$Dest`"", "$Url"
        $Process = Start-Process -FilePath "curl.exe" -ArgumentList $CurlArgs -Wait -PassThru -NoNewWindow
        if ($Process.ExitCode -eq 0 -and (Test-Path $Dest)) {
            return
        }
    } catch {
        Write-Host "curl failed, falling back to WebClient..." -ForegroundColor Gray
    }

    # Method 3: WebClient (Last resort)
    try {
        $WebClient = New-Object System.Net.WebClient
        $WebClient.DownloadFile($Url, $Dest)
    } catch {
        Write-Host "[ERROR] All download methods failed for $Url" -ForegroundColor Red
        throw $_
    }
}

# 2. Download Installer
Write-Host "[SETUP] Downloading Python Installer..." -ForegroundColor Yellow
$Installer = "$TempDir\python_installer.exe"
Download-File -Url $PyInstallUrl -Dest $Installer

# 3. Install
Write-Host "[SETUP] Installing Python (this may take a minute)..." -ForegroundColor Yellow
# /passive shows progress bar but requires no interaction
# InstallAllUsers=0 installs to current user (no admin needed usually, but we target specific dir)
# TargetDir sets the installation location
$InstallArgs = "/passive", "InstallAllUsers=0", "TargetDir=$PythonDir", "Include_test=0", "Include_doc=0", "Include_tcltk=1", "Include_pip=1", "PrependPath=0", "Include_launcher=0"

$Process = Start-Process -FilePath $Installer -ArgumentList $InstallArgs -Wait -PassThru

if ($Process.ExitCode -ne 0) {
    Write-Host "[ERROR] Installer failed with exit code $($Process.ExitCode)" -ForegroundColor Red
    exit 1
}

# 4. Cleanup
Write-Host "[SETUP] Cleaning up temp files..." -ForegroundColor Yellow
Remove-Item -Path $TempDir -Recurse -Force

Write-Host "[SETUP] Runtime Setup Complete!" -ForegroundColor Green
