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
    echo [BOOT] Downloading Python 3.11 Installer...
    set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    set "INSTALLER=%RUNTIME_DIR%\python_installer.exe"
    set "LOG_FILE=%RUNTIME_DIR%\install.log"
    
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '!PYTHON_URL!' -OutFile '!INSTALLER!'}"
    
    if not exist "!INSTALLER!" (
        echo [ERROR] Failed to download Python. Check internet connection.
        pause
        exit /b 1
    )
    
    echo [BOOT] Installing Runtime (this may take a minute)...
    :: Use /passive to show progress bar but automate installation
    "!INSTALLER!" /passive InstallAllUsers=0 PrependPath=0 TargetDir="%PYTHON_DIR%" Include_test=0 Include_tcltk=1 Include_pip=1
    
    del "!INSTALLER!"
    
    if not exist "%PYTHON_EXE%" (
        echo [ERROR] Runtime installation failed.
        if exist "!LOG_FILE!" type "!LOG_FILE!"
        pause
        exit /b 1
    )
    echo [BOOT] Runtime ready.
)

:: 2. Launch Bootstrapper (Installs modules & starts Launcher)
start "" "%PYTHON_EXE%" "%BOOTSTRAPPER%"

exit /b 0

