@echo off
title Traficom KAP Converter - Building 1:20,000 charts

if not exist "imgkap.exe" (
    echo [ERROR] imgkap.exe not found in this folder.
    echo Please download it and place it next to this script, then try again.
    pause
    exit /b 1
)

if not exist "sheets_subs.txt" (
    echo [ERROR] sheets_subs.txt not found in this folder.
    pause
    exit /b 1
)

py make_sheets.py sheets_subs.txt --zoom 13 --scale 20000 --prefix FIN -y
if errorlevel 1 (
    echo.
    echo [ERROR] Something went wrong. Scroll up to see the error message.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Done! Charts written to: sheets_out\
echo ============================================
echo.
pause
