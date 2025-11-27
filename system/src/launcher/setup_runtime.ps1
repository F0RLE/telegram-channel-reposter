# Setup Runtime Script
# Creates a portable Python 3.11 environment with Tkinter support

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$RootDir = "$ScriptDir\..\..\.."
$RuntimeDir = "$RootDir\system\runtime"
$TempDir = "$RootDir\system\temp"
$PythonDir = "$RuntimeDir\python"

# URLs
$PyEmbedUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
$PyInstallUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"

Write-Host "[SETUP] Starting Portable Python Setup..." -ForegroundColor Cyan

# 1. Prepare Directories
if (Test-Path $PythonDir) { Remove-Item -Path $PythonDir -Recurse -Force }
if (Test-Path $TempDir) { Remove-Item -Path $TempDir -Recurse -Force }
New-Item -ItemType Directory -Path $PythonDir -Force | Out-Null
New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

# 2. Download & Extract Embeddable Python
Write-Host "[SETUP] Downloading Python Embeddable..." -ForegroundColor Yellow
$ZipFile = "$TempDir\python.zip"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $PyEmbedUrl -OutFile $ZipFile

Write-Host "[SETUP] Extracting Embeddable Python..." -ForegroundColor Yellow
Expand-Archive -Path $ZipFile -DestinationPath $PythonDir -Force

# 3. Enable site-packages
Write-Host "[SETUP] Enabling site-packages..." -ForegroundColor Yellow
$PthFile = "$PythonDir\python311._pth"
(Get-Content $PthFile) -replace '#import site', 'import site' | Set-Content $PthFile

# 4. Harvest Tkinter from Full Installer
Write-Host "[SETUP] Downloading Python Installer (for Tkinter)..." -ForegroundColor Yellow
$Installer = "$TempDir\python_installer.exe"
Invoke-WebRequest -Uri $PyInstallUrl -OutFile $Installer

Write-Host "[SETUP] Extracting Tkinter components..." -ForegroundColor Yellow
$TempPython = "$TempDir\python_full"
New-Item -ItemType Directory -Path $TempPython -Force | Out-Null

# Install to temp dir to get files
# Note: /layout is for creating an offline layout, but /quiet install is better for getting binaries
$InstallArgs = "/quiet", "InstallAllUsers=0", "TargetDir=$TempPython", "Include_tcltk=1", "Include_pip=0", "Include_test=0", "PrependPath=0", "Include_launcher=0"
$Process = Start-Process -FilePath $Installer -ArgumentList $InstallArgs -Wait -PassThru

if ($Process.ExitCode -ne 0) {
    Write-Host "[ERROR] Installer failed with exit code $($Process.ExitCode)" -ForegroundColor Red
    # Try to list temp dir to see what happened
    Get-ChildItem $TempPython -Recurse | Select-Object Name
    exit 1
}

# Verify source files exist
if (-not (Test-Path "$TempPython\tcl")) {
    Write-Host "[ERROR] 'tcl' directory not found in extracted files!" -ForegroundColor Red
    Write-Host "Contents of $TempPython :"
    Get-ChildItem $TempPython
    exit 1
}

# 5. Transplant Tkinter Files
Write-Host "[SETUP] Transplanting Tkinter files..." -ForegroundColor Yellow

# Copy tcl folder
Copy-Item -Path "$TempPython\tcl" -Destination "$PythonDir\tcl" -Recurse -Force

# Copy tkinter module
if (-not (Test-Path "$PythonDir\Lib")) {
    New-Item -ItemType Directory -Path "$PythonDir\Lib" -Force | Out-Null
}
Copy-Item -Path "$TempPython\Lib\tkinter" -Destination "$PythonDir\Lib\tkinter" -Recurse -Force

# Copy DLLs
Copy-Item -Path "$TempPython\DLLs\_tkinter.pyd" -Destination "$PythonDir\_tkinter.pyd" -Force
Copy-Item -Path "$TempPython\DLLs\tcl86t.dll" -Destination "$PythonDir\tcl86t.dll" -Force
Copy-Item -Path "$TempPython\DLLs\tk86t.dll" -Destination "$PythonDir\tk86t.dll" -Force

# Verify destination
if (-not (Test-Path "$PythonDir\tcl")) {
    Write-Host "[ERROR] Failed to copy 'tcl' directory!" -ForegroundColor Red
    exit 1
}

# 6. Install Pip
Write-Host "[SETUP] Installing Pip..." -ForegroundColor Yellow
$GetPip = "$TempDir\get-pip.py"
Invoke-WebRequest -Uri $GetPipUrl -OutFile $GetPip
& "$PythonDir\python.exe" $GetPip --no-warn-script-location

# 7. Cleanup
Write-Host "[SETUP] Cleaning up temp files..." -ForegroundColor Yellow
Remove-Item -Path $TempDir -Recurse -Force

Write-Host "[SETUP] Runtime Setup Complete!" -ForegroundColor Green
