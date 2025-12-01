# Setup Runtime Script
# Installs Python 3.11 using WinPython (Portable, Fast)
# Solves "slow disk" and "error 1603" issues by avoiding MSI installation entirely.

$ErrorActionPreference = "Stop"
[System.Diagnostics.Process]::GetCurrentProcess().PriorityClass = [System.Diagnostics.ProcessPriorityClass]::High

$ScriptDir = $PSScriptRoot
$RootDir = "$ScriptDir\..\..\.."
$RuntimeDir = "$RootDir\system\runtime"
$AppDataDir = "$env:APPDATA\TelegramBotData"
$RandomId = Get-Random
$TempDir = "$AppDataDir\data\temp_$RandomId"
$PythonDir = "$RuntimeDir\python"

# WinPython 3.11.8.0dot (Stable version with Tkinter)
# SourceForge Direct Link
$WinPyUrl = "https://downloads.sourceforge.net/project/winpython/WinPython_3.11/3.11.8.0/Winpython64-3.11.8.0dot.exe"

Write-Host "[SETUP] Starting Fast Python Setup (WinPython)..." -ForegroundColor Cyan
Write-Host "[DEBUG] Temp Dir: $TempDir" -ForegroundColor DarkGray

# 1. Prepare Directories
Write-Host "[SETUP] Cleaning up previous run..." -ForegroundColor Yellow

Get-Process "python_installer" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process "python" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

if (Test-Path $PythonDir) { 
    try {
        Remove-Item -Path $PythonDir -Recurse -Force -ErrorAction Stop
    } catch {
        Write-Host "[WARNING] Could not clean Python dir: $_" -ForegroundColor Red
    }
}

New-Item -ItemType Directory -Path $PythonDir -Force | Out-Null
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

# Helper function for fast download
function Download-File {
    param([string]$Url, [string]$Dest)
    Write-Host "Downloading: $Url" -ForegroundColor Gray
    
    # Method 1: curl (Fastest, handles redirects well)
    try {
        # -L follows redirects, -f fails on HTTP errors
        $CurlArgs = "-L", "-f", "-o", "`"$Dest`"", "$Url"
        $Process = Start-Process -FilePath "curl.exe" -ArgumentList $CurlArgs -Wait -PassThru -NoNewWindow
        if ($Process.ExitCode -eq 0 -and (Test-Path $Dest)) {
            return
        }
    } catch {
        Write-Host "curl failed, falling back to WebClient..." -ForegroundColor Gray
    }

    # Method 2: WebClient
    try {
        $WebClient = New-Object System.Net.WebClient
        $WebClient.DownloadFile($Url, $Dest)
        return
    } catch {
        Write-Host "[ERROR] All download methods failed for $Url" -ForegroundColor Red
        throw $_
    }
}

try {
    # 2. Download WinPython
    Write-Host "[SETUP] Downloading WinPython (Portable)..." -ForegroundColor Yellow
    $Installer = "$TempDir\winpython.exe"
    Download-File -Url $WinPyUrl -Dest $Installer

    if (-not (Test-Path $Installer)) {
        throw "Installer file not found after download."
    }

    # CHECK FILE SIZE
    $Size = (Get-Item $Installer).Length
    Write-Host "[DEBUG] Downloaded size: $($Size / 1MB) MB" -ForegroundColor DarkGray
    if ($Size -lt 10000000) { # Less than 10MB is definitely wrong (WinPython dot is ~25MB)
        throw "Downloaded file is too small ($Size bytes). Download likely failed or was blocked."
    }

    # 3. Extract WinPython
    Write-Host "[SETUP] Extracting files (Fast)..." -ForegroundColor Yellow
    
    # WinPython .exe is a 7-Zip SFX. 
    # -y: assume yes on all queries
    # -o: output directory (no space after -o)
    $ExtractDir = "$TempDir\extracted"
    $ExtractArgs = "-y", "-o`"$ExtractDir`""
    
    Write-Host "[DEBUG] Extracting to $ExtractDir..." -ForegroundColor DarkGray
    $Process = Start-Process -FilePath $Installer -ArgumentList $ExtractArgs -Wait -PassThru

    if ($Process.ExitCode -ne 0) {
        Write-Host "[ERROR] Extraction failed with exit code $($Process.ExitCode)" -ForegroundColor Red
        exit 1
    }

    # 4. Locate and Move Python
    Write-Host "[SETUP] Configuring runtime..." -ForegroundColor Yellow
    
    # Structure is usually: extracted\WPy64-xxxx\python-3.11.x.amd64
    # Let's find the python folder recursively
    $ExtractedPython = Get-ChildItem -Path $ExtractDir -Filter "python.exe" -Recurse | Select-Object -First 1
    
    if ($ExtractedPython) {
        $SourceDir = $ExtractedPython.DirectoryName
        Write-Host "[DEBUG] Found Python at: $SourceDir" -ForegroundColor DarkGray
        
        # Move contents to $PythonDir
        Get-ChildItem -Path $SourceDir | Move-Item -Destination $PythonDir -Force
    } else {
        throw "Could not find python.exe in extracted files."
    }

    # 5. Ensure Portability (._pth file)
    $PthFile = "$PythonDir\python311._pth"
    Write-Host "[INFO] Creating python311._pth..." -ForegroundColor Gray
    $PthContent = @(
        ".",
        "Lib",
        "DLLs",
        ".",
        "import site"
    )
    Set-Content -Path $PthFile -Value $PthContent

    # 6. Initialize Pip (WinPython usually has it, but let's ensure)
    Write-Host "[SETUP] Verifying pip..." -ForegroundColor Yellow
    try {
        $Proc = Start-Process -FilePath "$PythonDir\python.exe" -ArgumentList "-m", "ensurepip" -Wait -PassThru -NoNewWindow
    } catch {
        Write-Host "[WARNING] ensurepip check failed: $_" -ForegroundColor Yellow
    }

    Write-Host "[SETUP] Runtime Setup Complete!" -ForegroundColor Green

} catch {
    Write-Host "[ERROR] Setup Exception: $_" -ForegroundColor Red
    exit 1
} finally {
    # 7. Cleanup
    if (Test-Path $TempDir) {
        Write-Host "[SETUP] Cleaning up temp files..." -ForegroundColor Yellow
        try {
            Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
        } catch {
            Write-Host "[WARNING] Failed to clean temp dir (non-critical)" -ForegroundColor DarkGray
        }
    }
}
