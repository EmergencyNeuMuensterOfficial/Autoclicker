@echo off
echo ========================================
echo   Autoclicker Ultimate - Setup
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed!
    echo Please install Python 3.6 or later from:
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -r requirements.txt

if errorlevel 1 (
    echo Failed to install dependencies!
    pause
    exit /b 1
)

echo Starting bootstrapper...
python bootstrapper.py

pause