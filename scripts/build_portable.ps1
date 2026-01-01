$ErrorActionPreference = 'Stop'

Write-Host 'Starting Flux Platform Portable Build...' -ForegroundColor Cyan

# 1. Setup Paths
$UserCargo = "$env:USERPROFILE\.cargo\bin"
$WinSdk = 'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64'

# 2. Update Environment
# Put MSVC cargo first
$env:PATH = $UserCargo + ';' + $WinSdk + ';' + $env:PATH

# 3. Verify
Write-Host 'Active Cargo:'
Get-Command cargo | Select-Object Source

# 4. Build
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location "$ProjectRoot\src-tauri"

Write-Host 'Building...'
cargo build --release --target x86_64-pc-windows-msvc
