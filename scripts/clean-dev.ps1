# Clean Environment Launch Script
$ErrorActionPreference = "Stop"

Write-Host "Cleaning environment variables..." -ForegroundColor Cyan

# Remove GnuWin32, MinGW, and Rogue Rust GNU from PATH
$cleanPath = ($env:PATH -split ';').Where({
    $_ -notlike "*GnuWin32*" -and
    $_ -notlike "*mingw*" -and
    $_ -notlike "*MSYS*" -and
    $_ -notlike "*Rust stable GNU*"
}) -join ';'

# The original script had an intermediate assignment to $env:PATH here.
# We are removing that intermediate assignment and directly applying the final desired PATH.
# This ensures .cargo/bin is prepended to the *cleaned* path.

# Force Cargo/Rustup to the FRONT of PATH to override any rogue installs
$env:PATH = "C:\Users\FORLE\.cargo\bin;" + $cleanPath

Write-Host "PATH sanitized. Checking Toolchain..." -ForegroundColor Cyan

# Ensure target is present for the ACTIVE toolchain
rustup target add x86_64-pc-windows-msvc

Write-Host "Launching Tauri..." -ForegroundColor Green

# Navigate to root and run the dev command
Set-Location "$PSScriptRoot/.."
npm run tauri:dev
