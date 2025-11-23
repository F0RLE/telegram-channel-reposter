@echo off
setlocal
title AI Bot Launcher
chcp 65001 >nul

:: === PATHS (APPDATA) ===
set "ROOT_DIR=%APPDATA%\TelegramBotData"
set "PYTHON=%ROOT_DIR%\env\python\pythonw.exe"
set "GIT_PATH=%ROOT_DIR%\env\git\cmd"

:: === NEW PATH TO LAUNCHER ===
:: Указываем путь внутрь папки system\src\launcher
set "WORK_DIR=%~dp0system\src"
set "LAUNCHER=%WORK_DIR%\launcher\launcher.pyw"

:: === CHECKS ===
if not exist "%PYTHON%" (
    color 4F
    echo.
    echo [ERROR] Python not found in AppData.
    echo Please run "Установка.bat" first.
    echo.
    pause & exit
)

if not exist "%LAUNCHER%" (
    color 4F
    echo.
    echo [ERROR] launcher.pyw not found in:
    echo %LAUNCHER%
    echo.
    pause & exit
)

:: === LAUNCH ===
set "PATH=%GIT_PATH%;%PATH%"

:: Переходим в папку с исходным кодом перед запуском
cd /d "%WORK_DIR%"

echo [INFO] Starting Manager...
start "" "%PYTHON%" "%LAUNCHER%"
if errorlevel 1 (
    color 4F
    echo.
    echo [ERROR] Failed to start launcher
    pause
    exit /b 1
)
exit /b 0