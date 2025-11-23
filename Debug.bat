@echo off
setlocal
title AI Bot: DEBUG MODE
chcp 65001 >nul
cls

:: === PATHS (APPDATA) ===
set "ROOT_DIR=%APPDATA%\TelegramBotData"
set "PYTHON=%ROOT_DIR%\env\python\python.exe"
set "GIT_PATH=%ROOT_DIR%\env\git\cmd"

:: === NEW PATH TO LAUNCHER ===
set "WORK_DIR=%~dp0system\src"
set "LAUNCHER=%WORK_DIR%\launcher\launcher.pyw"

echo [INFO] Debug Mode Started.
echo [INFO] Environment: %ROOT_DIR%
echo [INFO] Source Dir:  %WORK_DIR%

:: === CHECKS ===
if not exist "%PYTHON%" (
    color 4F
    echo.
    echo [ERROR] Python environment not found.
    echo Run "Установка.bat".
    echo.
    pause & exit
)

if not exist "%LAUNCHER%" (
    color 4F
    echo.
    echo [ERROR] launcher.pyw not found!
    echo.
    pause & exit
)

:: === LAUNCH ===
set "PATH=%GIT_PATH%;%PATH%"

echo [INFO] Python Version:
"%PYTHON%" --version
echo.
echo [INFO] Launching Bot Manager (Console Mode)...
echo ---------------------------------------------------

:: Переходим в папку с кодом
cd /d "%WORK_DIR%"

"%PYTHON%" "%LAUNCHER%"

echo.
echo ---------------------------------------------------
echo [END] Process finished with code: %errorlevel%
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Process exited with error code: %errorlevel%
    echo.
)
pause
exit /b %errorlevel%