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
    
    :: Download Python Embeddable Zip
    echo [BOOT] Downloading Python 3.11 (Embeddable)...
    set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
    set "ZIP_FILE=%RUNTIME_DIR%\python.zip"
    
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '!PYTHON_URL!' -OutFile '!ZIP_FILE!'}"
    
    if not exist "!ZIP_FILE!" (
        echo [ERROR] Failed to download Python. Check internet connection.
        pause
        exit /b 1
    )
    
    :: Extract Python
    echo [BOOT] Extracting Runtime...
    powershell -Command "Expand-Archive -Path '!ZIP_FILE!' -DestinationPath '%PYTHON_DIR%' -Force"
    del "!ZIP_FILE!"
    
    if not exist "%PYTHON_EXE%" (
        echo [ERROR] Runtime extraction failed.
        pause
        exit /b 1
    )
    
    :: Enable site-packages (required for pip)
    echo [BOOT] Configuring Runtime...
    set "PTH_FILE=%PYTHON_DIR%\python311._pth"
    powershell -Command "(Get-Content '%PTH_FILE%') -replace '#import site', 'import site' | Set-Content '%PTH_FILE%'"
    
    :: Install pip
    echo [BOOT] Installing pip...
    set "GET_PIP=%RUNTIME_DIR%\get-pip.py"
    powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '!GET_PIP!'}"
    
    "%PYTHON_EXE%" "!GET_PIP!" --no-warn-script-location
    del "!GET_PIP!"
    
    :: Install Tkinter support (Embeddable python doesn't have it by default, we need to handle this)
    :: Actually, for embeddable python, tkinter is tricky. 
    :: We will use 'pip install tk' or similar if possible, but standard tkinter is part of stdlib.
    :: Embeddable python DOES NOT include tkinter.
    :: We might need to download the full installer and extract it, OR use the nuget package.
    :: Let's revert to the installer but fix the arguments.
    :: The user said "Runtime installation failed".
    :: Let's try the installer again but with different arguments and logging.
    
    :: WAIT! Embeddable python is bad for GUI apps because of missing Tkinter.
    :: We MUST use the installer or a portable build that includes Tkinter.
    :: Let's go back to the installer but make it robust.
    
    :: REVERTING TO INSTALLER STRATEGY WITH BETTER LOGGING AND ARGUMENTS
    
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
    :: Use simple path for TargetDir to avoid issues
    "!INSTALLER!" /quiet InstallAllUsers=0 PrependPath=0 TargetDir="%PYTHON_DIR%" Include_test=0 Include_tcltk=1 Include_pip=1 > "!LOG_FILE!" 2>&1
    
    :: Check if it worked
    if not exist "%PYTHON_EXE%" (
        echo [ERROR] Runtime installation failed. Checking logs...
        type "!LOG_FILE!"
        echo.
        echo [RETRY] Trying alternative installation method...
        "!INSTALLER!" /passive InstallAllUsers=0 PrependPath=0 TargetDir="%PYTHON_DIR%" Include_test=0 Include_tcltk=1 Include_pip=1
    )
    
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

