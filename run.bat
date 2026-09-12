@echo off

setlocal

cd /d "%~dp0"

echo ==========================================
echo       EnergyAutomation
echo ==========================================
echo.

echo Starting application...

python main.py

if errorlevel 1 (
    echo.
    echo ==========================================
    echo EnergyAutomation stopped with an error.
    echo ==========================================
    echo.
    pause
)

endlocal