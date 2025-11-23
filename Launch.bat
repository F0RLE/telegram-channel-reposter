@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "LAUNCHER=%SCRIPT_DIR%system\src\launcher\launcher.pyw"

if not exist "%LAUNCHER%" (
    echo Error: Launcher not found at %LAUNCHER%
    pause
    exit /b 1
)

set "PYTHON=%APPDATA%\TelegramBotData\env\python\pythonw.exe"

if not exist "%PYTHON%" (
    set "PYTHON=%APPDATA%\TelegramBotData\env\python\python.exe"
)

if not exist "%PYTHON%" (
    echo Error: Python not found. Please run Install.bat first.
    pause
    exit /b 1
)

start "" "%PYTHON%" "%LAUNCHER%"

exit /b 0

