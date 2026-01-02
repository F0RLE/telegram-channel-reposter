<#
.SYNOPSIS
    Cleans build artifacts and caches.

.DESCRIPTION
    Removes:
    - src-tauri/target/
    - src/dist/
    - src/node_modules/ (Optional, usually we keeps deps but user asked to clean cache)
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

$ScriptDir = $PSScriptRoot
$ProjectRoot = Resolve-Path "$ScriptDir\.."

# 1. Clean Rust Target
if (Test-Path "$ProjectRoot\src-tauri\target") {
    Write-Step "Removing Rust target directory..."
    Remove-Item -Path "$ProjectRoot\src-tauri\target" -Recurse -Force -ErrorAction SilentlyContinue
}

# 2. Clean Frontend Dist
if (Test-Path "$ProjectRoot\src\dist") {
    Write-Step "Removing Frontend dist directory..."
    Remove-Item -Path "$ProjectRoot\src\dist" -Recurse -Force -ErrorAction SilentlyContinue
}

# 3. Clean Frontend Cache (node_modules/.vite)
if (Test-Path "$ProjectRoot\src\node_modules\.vite") {
    Write-Step "Cleaning Vite cache..."
    Remove-Item -Path "$ProjectRoot\src\node_modules\.vite" -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Success "Cleanup complete!"
