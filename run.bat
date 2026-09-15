@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo       EnergyAutomation
echo ==========================================
echo.

if exist ".venv\Scripts\python.exe" (
    echo Using project virtual environment...
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)

echo Starting application...
%PYTHON_CMD% main.py

if errorlevel 1 (
    echo.
    echo ==========================================
    echo EnergyAutomation stopped with an error.
    echo ==========================================
    echo.
    pause
)

endlocal