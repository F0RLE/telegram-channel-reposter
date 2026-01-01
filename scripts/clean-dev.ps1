<#
.SYNOPSIS
    Sanitizes the environment and launches the development server.

.DESCRIPTION
    This script:
    1. Removes conflicting tools (MinGW, GNU Rust, MSYS) from the PATH.
    2. Prioritizes the MSVC Rust toolchain.
    3. Launches the Tauri development server.

.EXAMPLE
    .\clean-dev.ps1
#>

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "👉 $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

Write-Host "🚀 Starting Clean Dev Environment..." -ForegroundColor Cyan

# 1. Sanitize Environment
Write-Step "Sanitizing environment variables..."
$CurrentPath = $env:PATH
$CleanPath = ($CurrentPath -split ';').Where({
        $_ -notlike "*GnuWin32*" -and
        $_ -notlike "*mingw*" -and
        $_ -notlike "*MSYS*" -and
        $_ -notlike "*Rust stable GNU*"
    }) -join ';'

# 2. Configure Toolchain
Write-Step "Configuring MSVC Toolchain..."
$UserCargo = "$env:USERPROFILE\.cargo\bin"
$env:PATH = $UserCargo + ";" + $CleanPath

# 3. Ensure Target
Write-Step "Checking Rust target..."
rustup target add x86_64-pc-windows-msvc | Out-Null

# 4. Launch
Write-Success "Environment ready. Launching Tauri..."
Set-Location "$PSScriptRoot/../src"
npm run tauri:dev
