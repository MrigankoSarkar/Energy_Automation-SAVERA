@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo   EnergyAutomation — Plotly Dash Management BI
echo ===================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)

echo Starting Plotly Dash microservice on http://localhost:8050...
%PYTHON_CMD% -m services.dash_service.app

if errorlevel 1 (
    echo.
    echo ===================================================
    echo Dash microservice stopped with an error.
    echo ===================================================
    echo.
    pause
)

endlocal
