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
    echo.
    python bootstrapper.py --cli
    pause
    exit /b 0
)

echo Python detected successfully
echo Installing in: %CD%
echo.

:: Launch installer
echo Launching installer...
timeout /t 2 /nobreak >nul
python bootstrapper.py

if errorlevel 1 (
    echo.
    echo Installer failed with error code: %errorlevel%
    echo Check installer.log for details.
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