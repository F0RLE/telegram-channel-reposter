 @echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "RUNTIME_DIR=%SCRIPT_DIR%system\runtime"
set "PYTHON_DIR=%RUNTIME_DIR%\python"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "BOOTSTRAPPER=%SCRIPT_DIR%system\src\launcher\bootstrapper.py"

:: 1. Check/Install Runtime
if not exist "%PYTHON_EXE%" (
    echo [BOOT] Runtime not found. Installing local Python environment...
    
    if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%"
    
    :: Download Python Installer
    echo [BOOT] Downloading Python 3.11...
    set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    set "INSTALLER=%RUNTIME_DIR%\python_installer.exe"
    
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '!PYTHON_URL!' -OutFile '!INSTALLER!'}"
    
    if not exist "!INSTALLER!" (
        echo [ERROR] Failed to download Python. Check internet connection.
        pause
        exit /b 1
    )
    
    :: Install Python locally
    echo [BOOT] Extracting Runtime...
    "!INSTALLER!" /quiet InstallAllUsers=0 PrependPath=0 TargetDir="%PYTHON_DIR%" Include_test=0
    
    del "!INSTALLER!"
    
    if not exist "%PYTHON_EXE%" (
        echo [ERROR] Runtime installation failed.
        pause
        exit /b 1
    )
    echo [BOOT] Runtime ready.
)

:: 2. Launch Bootstrapper (Installs modules & starts Launcher)
start "" "%PYTHON_EXE%" "%BOOTSTRAPPER%"

exit /b 0

