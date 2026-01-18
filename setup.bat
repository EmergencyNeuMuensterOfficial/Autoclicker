@echo off
chcp 65001 >nul
cls

echo ============================================
echo     AUTOCLICKER ULTIMATE INSTALLER
echo ============================================
echo.
echo This will install Autoclicker Ultimate in the current folder.
echo Everything will be kept together - no system installation!
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo.
    echo Please install Python 3.6 or later from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)

:: Check tkinter
python -c "import tkinter" 2>nul
if errorlevel 1 (
    echo WARNING: tkinter is not available!
    echo.
    echo The graphical installer requires tkinter.
    echo Press any key to use command-line installer...
    pause >nul
    goto :CLI_DOWNLOAD
)

echo Python detected successfully
echo Installing in: %CD%
echo.

:: Download bootstrapper from GitHub
echo Downloading bootstrapper from GitHub...
echo.

:: Method 1: Try PowerShell first (Windows 8+)
where powershell >nul 2>nul
if %errorlevel% equ 0 (
    powershell -Command "& {Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/EmergencyNeuMuensterOfficial/Autoclicker/main/bootstrapper.py' -OutFile 'bootstrapper.py' -UseBasicParsing}"
    if %errorlevel% equ 0 goto :RUN_INSTALLER
)

:: Method 2: Try bitsadmin (Windows built-in)
bitsadmin /transfer "DownloadBootstrapper" /download /priority foreground "https://raw.githubusercontent.com/EmergencyNeuMuensterOfficial/Autoclicker/main/bootstrapper.py" "bootstrapper.py" >nul 2>&1
if %errorlevel% equ 0 goto :RUN_INSTALLER

:: Method 3: Try curl (if available)
where curl >nul 2>nul
if %errorlevel% equ 0 (
    curl -L -o bootstrapper.py "https://raw.githubusercontent.com/EmergencyNeuMuensterOfficial/Autoclicker/main/bootstrapper.py" >nul 2>&1
    if %errorlevel% equ 0 goto :RUN_INSTALLER
)

:: Method 4: Try Python itself
python -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/EmergencyNeuMuensterOfficial/Autoclicker/main/bootstrapper.py', 'bootstrapper.py')" >nul 2>&1
if %errorlevel% equ 0 goto :RUN_INSTALLER

:: If all download methods fail
echo ERROR: Could not download bootstrapper from GitHub!
echo.
echo Please download bootstrapper.py manually from:
echo https://raw.githubusercontent.com/EmergencyNeuMuensterOfficial/Autoclicker/main/bootstrapper.py
echo.
echo Save it in the same folder as this setup.bat file and run setup.bat again.
echo.
pause
exit /b 1

:RUN_INSTALLER
:: Check if bootstrapper was downloaded
if not exist "bootstrapper.py" (
    echo ERROR: bootstrapper.py was not downloaded!
    echo.
    goto :MANUAL_DOWNLOAD
)

echo Launching installer...
timeout /t 1 /nobreak >nul
python bootstrapper.py

if errorlevel 1 (
    echo.
    echo Installer failed with error code: %errorlevel%
    if exist "installer.log" (
        echo Check installer.log for details.
    )
    pause
    exit /b 1
)

echo.
echo Installation completed successfully!
echo.
echo To launch the application:
echo   1. Double-click "run.bat"
echo   2. Or run "python run.py"
echo.
pause
exit /b 0

:CLI_DOWNLOAD
echo.
echo Downloading bootstrapper (CLI mode)...

:: Download bootstrapper using Python
python -c "import urllib.request; urllib.request.urlretrieve('https://raw.githubusercontent.com/EmergencyNeuMuensterOfficial/Autoclicker/main/bootstrapper.py', 'bootstrapper.py')" >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Could not download bootstrapper!
    goto :MANUAL_DOWNLOAD
)

echo Running installer in command-line mode...
python bootstrapper.py --cli
if errorlevel 1 (
    echo.
    echo Installer failed with error code: %errorlevel%
    if exist "installer.log" (
        echo Check installer.log for details.
    )
    pause
    exit /b 1
)

echo.
echo Installation completed!
echo.
pause
exit /b 0

:MANUAL_DOWNLOAD
echo.
echo ============================================
echo MANUAL DOWNLOAD REQUIRED
echo ============================================
echo.
echo 1. Open this URL in your browser:
echo    https://raw.githubusercontent.com/EmergencyNeuMuensterOfficial/Autoclicker/main/bootstrapper.py
echo.
echo 2. Save the page as 'bootstrapper.py' in this folder:
echo    %CD%
echo.
echo 3. Then run this setup.bat file again.
echo.
pause
exit /b 1