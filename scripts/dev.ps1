<#
.SYNOPSIS
    Launches the Flux Platform in development mode.

.DESCRIPTION
    Standard development launch script.
    Running this script starts both the Vite frontend server and the Tauri backend.
#>

$ErrorActionPreference = "Stop"

function Write-Header {
    param([string]$Message)
    Write-Host "`n🚀 $Message" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Message)
    Write-Host "👉 $Message" -ForegroundColor Yellow
}

Write-Header "Starting Flux Platform (Dev Mode)"

# 1. Setup Environment
$ScriptDir = $PSScriptRoot
$SrcDir = "$ScriptDir\..\src"
$TauriDir = "$ScriptDir\..\src-tauri"

# Ensure Cargo is found
$env:PATH = "$env:USERPROFILE\.cargo\bin;" + $env:PATH

# 2. Check Dependencies
if (-not (Test-Path "$SrcDir\node_modules")) {
    Write-Step "Installing frontend dependencies..."
    Set-Location $SrcDir
    npm install
}

# 3. Start Frontend
Write-Step "Starting Vite server..."
# Use cmd /c to ensure npm works reliably across shells
$ViteProcess = Start-Process -FilePath "cmd" -ArgumentList "/c npm run dev" -WorkingDirectory $SrcDir -PassThru -NoNewWindow
Start-Sleep -Seconds 3

# 4. Start Backend
Write-Step "Launching Tauri..."
Set-Location $TauriDir
try {
    # Specify stable-msvc explicitly to avoid ambiguity
    rustup run stable-msvc cargo tauri dev
}
finally {
    # 5. Cleanup
    if ($ViteProcess -and -not $ViteProcess.HasExited) {
        Stop-Process -Id $ViteProcess.Id -ErrorAction SilentlyContinue
        Write-Host "🛑 Stopped Vite server." -ForegroundColor DarkGray
    }
}
