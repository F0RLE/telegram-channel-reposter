<#
.SYNOPSIS
    Compiles the Flux Platform into a single portable EXE using the MSVC toolchain.
#>

$ErrorActionPreference = 'Stop'

Write-Host "🚀 Starting Flux Platform Portable Build..." -ForegroundColor Cyan

# 1. Paths
$UserCargo = "$env:USERPROFILE\.cargo\bin"
$WinSdk = 'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64'
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."

# 2. Environment (Safe Concat)
Write-Host "🔧 Configuring isolated environment..." -ForegroundColor Yellow
$env:PATH = $UserCargo + ';' + $WinSdk + ';' + $env:PATH

# 3. Validation
$Cargo = Get-Command cargo -ErrorAction SilentlyContinue
if ($Cargo) {
    Write-Host "   Using Cargo at: $($Cargo.Source)" -ForegroundColor Gray
}
else {
    Write-Error "❌ Cargo not found."
    exit 1
}

# 4. Build
Write-Host "🔨 Building (MSVC)..." -ForegroundColor Yellow
Set-Location "$ProjectRoot\src-tauri"

try {
    # Using rustup run to enforce toolchain
    rustup run stable-x86_64-pc-windows-msvc cargo build --release --target x86_64-pc-windows-msvc
}
catch {
    Write-Error "❌ Build failed."
    exit 1
}

# 5. Result
$Target = "$ProjectRoot\src-tauri\target\x86_64-pc-windows-msvc\release\flux-platform.exe"

if (Test-Path $Target) {
    $Size = "{0:N2} MB" -f ((Get-Item $Target).Length / 1MB)
    Write-Host "`n✅ Build Success!" -ForegroundColor Green
    Write-Host "   File: $Target" -ForegroundColor White
    Write-Host "   Size: $Size" -ForegroundColor White
}
else {
    Write-Error "❌ Executable not found."
    exit 1
}
