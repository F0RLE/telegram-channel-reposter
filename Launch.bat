 @echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "RUNTIME_DIR=%SCRIPT_DIR%system\runtime"
set "PYTHON_DIR=%RUNTIME_DIR%\python"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "BOOTSTRAPPER=%SCRIPT_DIR%system\src\launcher\bootstrapper.py"
set "SETUP_SCRIPT=%SCRIPT_DIR%system\src\launcher\setup_runtime.ps1"

:: 1. Check/Install Runtime
if not exist "%PYTHON_EXE%" (
    echo [BOOT] Runtime not found. Starting setup...
    
    powershell -ExecutionPolicy Bypass -File "%SETUP_SCRIPT%"
    
    if not exist "%PYTHON_EXE%" (
        echo [ERROR] Runtime setup failed.
        pause
        exit /b 1
    )
    echo [BOOT] Runtime ready.
)

:: 2. Configure Environment for Portable Tkinter
set "TCL_LIBRARY=%PYTHON_DIR%\tcl\tcl8.6"
set "TK_LIBRARY=%PYTHON_DIR%\tcl\tk8.6"

:: 3. Launch Bootstrapper (Installs modules & starts Launcher)
"%PYTHON_EXE%" "%BOOTSTRAPPER%"
if errorlevel 1 (
    echo [ERROR] Bootstrapper failed.
    pause
)

exit /b 0

