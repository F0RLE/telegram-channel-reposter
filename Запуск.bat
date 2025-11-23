@echo off
setlocal
:: Запуск без консоли - используем минимальный вывод
chcp 65001 >nul 2>&1

:: === PATHS (APPDATA) ===
set "ROOT_DIR=%APPDATA%\TelegramBotData"
set "PYTHON=%ROOT_DIR%\env\python\pythonw.exe"
set "GIT_PATH=%ROOT_DIR%\env\git\cmd"

:: === NEW PATH TO LAUNCHER ===
set "WORK_DIR=%~dp0system\src"
set "LAUNCHER=%WORK_DIR%\launcher\launcher.pyw"

:: === QUICK CHECKS (без вывода) ===
if not exist "%PYTHON%" (
    :: Если Python не найден, показываем ошибку только если запущено напрямую
    if "%~1"=="" (
        start "" cmd /c "echo [ERROR] Python not found. Please run Установка.bat first. & pause"
    )
    exit /b 1
)

if not exist "%LAUNCHER%" (
    if "%~1"=="" (
        start "" cmd /c "echo [ERROR] Launcher not found: %LAUNCHER% & pause"
    )
    exit /b 1
)

:: === LAUNCH (без консоли) ===
set "PATH=%GIT_PATH%;%PATH%"
cd /d "%WORK_DIR%" >nul 2>&1

:: Запускаем лаунчер через pythonw.exe (без консоли) в фоне
start "" "%PYTHON%" "%LAUNCHER%"

:: Выходим сразу, не ждем
exit /b 0