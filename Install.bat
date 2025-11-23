@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Telegram Channel Reposter - Installation
echo ========================================
echo.

set "INSTALL_DIR=%APPDATA%\TelegramBotData\env"
set "PYTHON_DIR=%INSTALL_DIR%\python"
set "GIT_DIR=%INSTALL_DIR%\git"
set "PYTHON=%PYTHON_DIR%\python.exe"
set "PIP=%PYTHON_DIR%\Scripts\pip.exe"

set "LOGFILE=%INSTALL_DIR%\install.log"

echo [%date% %time%] Starting installation... >> "%LOGFILE%"

if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
)

echo.
echo [1/4] Checking Python installation...
if not exist "%PYTHON%" (
    echo Python not found. Downloading Python 3.11...
    set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    set "PYTHON_INSTALLER=%TEMP%\python-installer.exe"
    
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'}"
    
    if not exist "%PYTHON_INSTALLER%" (
        echo Error: Failed to download Python installer.
        pause
        exit /b 1
    )
    
    echo Installing Python...
    "%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 TargetDir="%PYTHON_DIR%"
    
    if errorlevel 1 (
        echo Error: Python installation failed.
        pause
        exit /b 1
    )
    
    del "%PYTHON_INSTALLER%"
    echo Python installed successfully.
) else (
    echo Python found at %PYTHON%
)

echo.
echo [2/4] Checking Git installation...
if not exist "%GIT_DIR%\cmd\git.exe" (
    echo Git not found. Downloading Git...
    set "GIT_URL=https://github.com/git-for-windows/git/releases/download/v2.47.1.windows.1/Git-2.47.1-64-bit.exe"
    set "GIT_INSTALLER=%TEMP%\git-installer.exe"
    
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%GIT_URL%' -OutFile '%GIT_INSTALLER%'}"
    
    if not exist "%GIT_INSTALLER%" (
        echo Error: Failed to download Git installer.
        pause
        exit /b 1
    )
    
    echo Installing Git...
    "%GIT_INSTALLER%" /VERYSILENT /DIR="%GIT_DIR%"
    
    if errorlevel 1 (
        echo Error: Git installation failed.
        pause
        exit /b 1
    )
    
    del "%GIT_INSTALLER%"
    echo Git installed successfully.
) else (
    echo Git found at %GIT_DIR%\cmd\git.exe
)

echo.
echo [3/4] Installing Python packages...
if not exist "%PIP%" (
    echo Error: pip not found. Python installation may be incomplete.
    pause
    exit /b 1
)

"%PYTHON%" -m pip install --upgrade pip >> "%LOGFILE%" 2>&1

set "REQUIREMENTS=%~dp0system\src\requirements.txt"
if exist "%REQUIREMENTS%" (
    echo Installing dependencies from requirements.txt...
    "%PYTHON%" -m pip install -r "%REQUIREMENTS%" >> "%LOGFILE%" 2>&1
    if errorlevel 1 (
        echo Warning: Some packages failed to install. Check %LOGFILE% for details.
    ) else (
        echo Dependencies installed successfully.
    )
) else (
    echo Warning: requirements.txt not found.
)

echo.
echo [4/4] Installing additional packages...
"%PYTHON%" -m pip install customtkinter >> "%LOGFILE%" 2>&1
"%PYTHON%" -m pip install "tkinter-embed>=3.10.0" >> "%LOGFILE%" 2>&1

if exist "%PYTHON_DIR%\python.exe" (
    "%PYTHON_DIR%\python.exe" -c "import tkinter_embed; print('OK: tkinter_embed installed')" >> "%LOGFILE%" 2>&1
)

echo.
echo ========================================
echo Installation completed!
echo ========================================
echo.
echo You can now run Launch.bat to start the launcher.
echo.
pause

