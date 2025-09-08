@echo off
REM Wallbox eM4 EVSE Controller - Dependency Installation Script (Windows)
REM
REM This script installs all required Python dependencies for the eM4 controller

echo ================================================
echo   Wallbox eM4 EVSE Controller Setup
echo ================================================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://python.org
    echo.
    pause
    exit /b 1
)

python --version
echo.

echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to install dependencies
    echo Please check your internet connection and try again
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Installation Complete!
echo ================================================
echo.
echo You can now run the eM4 controller:
echo   python em4_interface.py    (Interactive interface)
echo   python em4_modbus.py --help (Command line)
echo.
echo Before first use, edit config.py to set your eM4 IP address.
echo.
pause