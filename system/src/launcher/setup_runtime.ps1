# Setup Runtime Script
# Creates a portable Python 3.11 environment with Tkinter support

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$RootDir = "$ScriptDir\..\..\.."
$RuntimeDir = "$RootDir\system\runtime"
$AppDataDir = "$env:APPDATA\TelegramBotData"
$TempDir = "$AppDataDir\data\temp"
$PythonDir = "$RuntimeDir\python"

# URLs
$PyEmbedUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
$PyInstallUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"

Write-Host "[SETUP] Starting Portable Python Setup..." -ForegroundColor Cyan

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
        # Try to continue anyway, maybe it's empty enough
    }
}

if (Test-Path $TempDir) { 
    try {
        Remove-Item -Path $TempDir -Recurse -Force -ErrorAction Stop
    } catch {
        Write-Host "[WARNING] Could not clean Temp dir: $_" -ForegroundColor Red
        Write-Host "Please manually close any setup programs and try again."
        exit 1
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

# 2. Download & Extract Embeddable Python
Write-Host "[SETUP] Downloading Python Embeddable..." -ForegroundColor Yellow
$ZipFile = "$TempDir\python.zip"
Download-File -Url $PyEmbedUrl -Dest $ZipFile

Write-Host "[SETUP] Extracting Embeddable Python..." -ForegroundColor Yellow
Expand-Archive -Path $ZipFile -DestinationPath $PythonDir -Force

# 3. Enable site-packages
Write-Host "[SETUP] Enabling site-packages..." -ForegroundColor Yellow
$PthFile = "$PythonDir\python311._pth"
(Get-Content $PthFile) -replace '#import site', 'import site' | Set-Content $PthFile

# 4. Harvest Tkinter from Full Installer
Write-Host "[SETUP] Downloading Python Installer (for Tkinter)..." -ForegroundColor Yellow
$Installer = "$TempDir\python_installer.exe"
Download-File -Url $PyInstallUrl -Dest $Installer

Write-Host "[SETUP] Extracting Tkinter components..." -ForegroundColor Yellow
$TempPython = "$TempDir\python_full"
New-Item -ItemType Directory -Path $TempPython -Force | Out-Null

# Use /layout to extract files without installing (avoids error 1603)
$InstallArgs = "/layout", "$TempPython", "/quiet"
Write-Host "[SETUP] Starting extraction (monitoring for tcltk.msi)..." -ForegroundColor Yellow
$Process = Start-Process -FilePath $Installer -ArgumentList $InstallArgs -PassThru

# Monitor loop to grab tcltk.msi early
$Timeout = 180 # 3 minutes max
$Timer = [System.Diagnostics.Stopwatch]::StartNew()
$MsiFound = $false

while ($Timer.Elapsed.TotalSeconds -lt $Timeout) {
    if ($Process.HasExited) {
        break
    }

    $Msi = Get-ChildItem "$TempPython" -Filter "*tcltk*.msi" | Select-Object -First 1
    if ($Msi) {
        # Check if file is stable (not being written to)
        $Size1 = $Msi.Length
        Start-Sleep -Milliseconds 500
        $Msi.Refresh()
        $Size2 = $Msi.Length

        if ($Size1 -eq $Size2 -and $Size1 -gt 0) {
            Write-Host "[SETUP] Found tcltk.msi ($($Msi.Length) bytes). Grabbing it..." -ForegroundColor Green
            $MsiFound = $true
            
            # Copy to safe location immediately
            $SafeMsi = "$TempDir\tcltk.msi"
            Copy-Item $Msi.FullName -Destination $SafeMsi -Force
            
            # Kill the installer to save time
            Write-Host "[SETUP] Terminating installer to skip other components..." -ForegroundColor Yellow
            Stop-Process -Id $Process.Id -Force -ErrorAction SilentlyContinue
            break
        }
    }
    Start-Sleep -Milliseconds 500
}

if (-not $MsiFound) {
    # If we exited loop without finding MSI, maybe it finished?
    $Msi = Get-ChildItem "$TempPython" -Filter "*tcltk*.msi" | Select-Object -First 1
    if ($Msi) {
        $SafeMsi = "$TempDir\tcltk.msi"
        Copy-Item $Msi.FullName -Destination $SafeMsi -Force
    } else {
        Write-Host "[ERROR] Tcl/Tk MSI not found after waiting!" -ForegroundColor Red
        exit 1
    }
}

# Extract MSI using msiexec /a
Write-Host "[SETUP] Extracting files from MSI..." -ForegroundColor Yellow
$ExtractDir = "$TempPython\extracted"
New-Item -ItemType Directory -Path $ExtractDir -Force | Out-Null
$LogFile = "$TempPython\msi_log.txt"
Start-Process "msiexec.exe" -ArgumentList "/a `"$SafeMsi`" /qn TARGETDIR=`"$ExtractDir`" /l*v `"$LogFile`"" -Wait

# Locate the actual files inside the extracted structure
# Usually in extracted/Lib/tkinter and extracted/tcl or similar
# We need to find where they are
$SourceLib = Get-ChildItem "$ExtractDir" -Recurse -Filter "tkinter" -Directory | Select-Object -First 1 -ExpandProperty FullName
$SourceTcl = Get-ChildItem "$ExtractDir" -Recurse -Filter "tcl" -Directory | Select-Object -First 1 -ExpandProperty FullName
$SourceDlls = Get-ChildItem "$ExtractDir" -Recurse -Filter "DLLs" -Directory | Select-Object -First 1 -ExpandProperty FullName

if (-not $SourceLib -or -not $SourceTcl) {
    Write-Host "[ERROR] Could not locate extracted Tkinter files!" -ForegroundColor Red
    exit 1
}

# 5. Transplant Tkinter Files
Write-Host "[SETUP] Transplanting Tkinter files..." -ForegroundColor Yellow

# Copy tcl folder
Copy-Item -Path "$SourceTcl" -Destination "$PythonDir\tcl" -Recurse -Force

# Copy tkinter module
if (-not (Test-Path "$PythonDir\Lib")) {
    New-Item -ItemType Directory -Path "$PythonDir\Lib" -Force | Out-Null
}
Copy-Item -Path "$SourceLib" -Destination "$PythonDir\Lib\tkinter" -Recurse -Force

# Copy DLLs (need to find them in the extracted DLLs folder)
if ($SourceDlls) {
    Copy-Item -Path "$SourceDlls\_tkinter.pyd" -Destination "$PythonDir\_tkinter.pyd" -Force
    Copy-Item -Path "$SourceDlls\tcl86t.dll" -Destination "$PythonDir\tcl86t.dll" -Force
    Copy-Item -Path "$SourceDlls\tk86t.dll" -Destination "$PythonDir\tk86t.dll" -Force
} else {
    # Fallback search if DLLs folder structure is different
    Get-ChildItem "$ExtractDir" -Recurse -Include "_tkinter.pyd","tcl86t.dll","tk86t.dll" | Copy-Item -Destination "$PythonDir" -Force
}

# Verify destination
if (-not (Test-Path "$PythonDir\tcl")) {
    Write-Host "[ERROR] Failed to copy 'tcl' directory!" -ForegroundColor Red
    exit 1
}

# 6. Install Pip
Write-Host "[SETUP] Installing Pip..." -ForegroundColor Yellow
$GetPip = "$TempDir\get-pip.py"
Download-File -Url $GetPipUrl -Dest $GetPip
& "$PythonDir\python.exe" $GetPip --no-warn-script-location

# 7. Cleanup
Write-Host "[SETUP] Cleaning up temp files..." -ForegroundColor Yellow
Remove-Item -Path $TempDir -Recurse -Force

Write-Host "[SETUP] Runtime Setup Complete!" -ForegroundColor Green
