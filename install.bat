@echo off
setlocal enabledelayedexpansion
title Traficom KAP Converter - Setup

echo ============================================
echo  Traficom KAP Converter - Setup
echo ============================================
echo.

REM --- Check Python is installed and reachable ---
py --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python was not found on this computer.
    echo.
    echo Please install Python 3.9 or newer from:
    echo     https://www.python.org/downloads/
    echo.
    echo IMPORTANT: during installation, tick the box that says
    echo "Add python.exe to PATH" before clicking Install.
    echo.
    echo After installing Python, run this setup script again.
    echo.
    pause
    exit /b 1
)

echo [OK] Python found:
py --version
echo.

REM --- Install required packages ---
echo Installing required packages (requests, pillow, pyproj) ...
echo This may take a minute the first time.
echo.
py -m pip install --upgrade pip >nul
py -m pip install requests pillow pyproj
if errorlevel 1 (
    echo.
    echo [ERROR] Package installation failed. Check your internet connection
    echo and try running this script again.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Setup complete!
echo ============================================
echo.

REM --- Check for imgkap.exe ---
if not exist "imgkap.exe" (
    echo [WARNING] imgkap.exe was not found in this folder.
    echo make_sheets.py needs it to build the final chart files.
    echo Please download imgkap.exe separately and place it in this
    echo same folder before running the chart scripts.
    echo.
) else (
    echo [OK] imgkap.exe found.
    echo.
)

echo You can now run:
echo     run_50k.bat   - build the 1:50,000 chart set
echo     run_20k.bat   - build the 1:20,000 chart set
echo.
pause
