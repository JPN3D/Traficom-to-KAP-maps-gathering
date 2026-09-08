@echo off
title Traficom KAP Converter - Building 1:50,000 charts

if not exist "imgkap.exe" (
    echo [ERROR] imgkap.exe not found in this folder.
    echo Please download it and place it next to this script, then try again.
    pause
    exit /b 1
)

if not exist "sheets_scaindex.txt" (
    echo [ERROR] sheets_scaindex.txt not found in this folder.
    pause
    exit /b 1
)

py make_sheets.py sheets_scaindex.txt --zoom 12 --scale 50000 --prefix FIN -y
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
