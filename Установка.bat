@echo off
chcp 65001 >nul
title AI Bot — Установка (Debug Mode)
color 0A
setlocal EnableDelayedExpansion

:: === 1. НАСТРОЙКА ПУТЕЙ ===
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "ROOT=%APPDATA%\TelegramBotData"
set "LOGS=%ROOT%\data\logs"
set "ENV=%ROOT%\env"
set "PYTHON=%ENV%\python"
set "GIT=%ENV%\git"
set "ENGINE=%ROOT%\data\Engine"
set "SD_DIR=%ENGINE%\stable-diffusion-webui-reforge"
set "REQ=%SCRIPT_DIR%\system\src\requirements.txt"

if not exist "%LOGS%" mkdir "%LOGS%" 2>nul
if not exist "%ENGINE%" mkdir "%ENGINE%" 2>nul
if not exist "%PYTHON%" mkdir "%PYTHON%" 2>nul
if not exist "%GIT%" mkdir "%GIT%" 2>nul

:: Проверка наличия curl
where curl >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] CURL не найден. Установите CURL.
    goto :ERROR
)

set "LOGFILE=%LOGS%\install_log.txt"
echo [START] %DATE% %TIME% > "%LOGFILE%"

echo.
echo ============================================================
echo         УСТАНОВКА BOT (PYTHON 3.11)
echo ============================================================
echo [INFO] Путь установки: %ROOT%
echo [INFO] Конфиг: %REQ%
echo [INFO] Используется Python 3.11 - лучшая совместимость
echo [INFO] Для Python 3.10 и 3.11 есть предкомпилированные пакеты (wheels)
echo.

:: === 2. PYTHON ===
echo [1/6] Проверка Python 3.11.9...
echo [INFO] Python 3.11.9 - последняя версия с бинарными установщиками
echo [INFO] Python 3.11.14+ доступны только в исходниках (без установщиков)
if not exist "%PYTHON%\python.exe" (
    echo   Скачивание Python 3.11.9...
    curl -k -L -f -o "%TEMP%\py_full.zip" "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.zip" --progress-bar || goto :ERROR
    echo   Распаковка...
    powershell -Command "Expand-Archive -Force '%TEMP%\py_full.zip' '%PYTHON%'" >> "%LOGFILE%" 2>&1 || goto :ERROR
)

:: === 3. PIP ===
echo [2/6] Проверка PIP...
if not exist "%PYTHON%\Scripts\pip.exe" (
    curl -k -L -o "%TEMP%\get-pip.py" "https://bootstrap.pypa.io/get-pip.py" --progress-bar || goto :ERROR
    "%PYTHON%\python.exe" "%TEMP%\get-pip.py" --no-warn-script-location >> "%LOGFILE%" 2>&1 || goto :ERROR
)

:: === 4. GIT ===
echo [3/6] Проверка Git...
if not exist "%GIT%\cmd\git.exe" (
    curl -k -L -o "%TEMP%\git.zip" "https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/MinGit-2.47.1-64-bit.zip" --progress-bar
    powershell -Command "Expand-Archive -Force '%TEMP%\git.zip' '%GIT%'" >> "%LOGFILE%" 2>&1
)

set "PATH=%PYTHON%;%PYTHON%\Scripts;%GIT%\cmd;%PATH%"

:: === 5. ОБНОВЛЕНИЕ КОМПОНЕНТОВ ===
echo [4/6] Обновление pip, setuptools, wheel...
"%PYTHON%\python.exe" -m pip install --upgrade pip setuptools wheel --no-warn-script-location >> "%LOGFILE%" 2>&1

:: === 6. REQUIREMENTS ===
echo [5/6] Установка зависимостей...
if exist "%REQ%" (
    "%PYTHON%\python.exe" -m pip install -r "%REQ%" --no-warn-script-location >> "%LOGFILE%" 2>&1
    if errorlevel 1 goto :ERROR
) else (
    "%PYTHON%\python.exe" -m pip install customtkinter aiogram aiohttp requests psutil pillow beautifulsoup4 python-dotenv tkinter-embed --no-warn-script-location >> "%LOGFILE%" 2>&1
    if errorlevel 1 goto :ERROR
)

:: Проверка установки критических модулей
echo [5.1/6] Проверка установленных модулей...
"%PYTHON%\python.exe" -c "import requests, psutil, customtkinter, aiogram; print('OK: Все модули установлены')" >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [WARNING] Некоторые модули не установились корректно
    echo Проверьте лог: %LOGFILE%
)

:: === 7. TKINTER FIX ===
echo [6/6] Проверка tkinter-embed...
"%PYTHON%\python.exe" -m pip install --upgrade tkinter-embed --no-warn-script-location >> "%LOGFILE%" 2>&1
:: tkinter-embed is a package, not a runnable module - no need to execute it
:: Just verify it's installed correctly
"%PYTHON%\python.exe" -c "import tkinter_embed; print('OK: tkinter-embed installed')" >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    echo [WARNING] tkinter-embed may not be installed correctly
    echo Check log: %LOGFILE%
)

:: === 8. ИНФОРМАЦИЯ ===
echo.
echo [INFO] Stable Diffusion будет установлен автоматически при первом запуске из лаунчера
echo [INFO] Модель также будет скачана автоматически при первом запуске SD

echo.
echo ============================================================
echo [OK] Установка завершена!
echo ============================================================
echo.
pause
exit /b 0

:ERROR
color 4C
echo.
echo ============================================================
echo [ERROR] Произошла ошибка. Проверьте лог: %LOGFILE%
echo ============================================================
echo.
if exist "%LOGFILE%" (
    echo Последние 20 строк лога:
    echo.
    powershell -Command "Get-Content '%LOGFILE%' -Tail 20 -ErrorAction SilentlyContinue"
    echo.
)
pause
exit /b 1
