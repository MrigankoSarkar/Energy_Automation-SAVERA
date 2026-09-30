@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo   EnergyAutomation — Microservices Supervisor
echo ===================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)

echo Starting all decoupled microservices...
%PYTHON_CMD% -m services.service_manager

if errorlevel 1 (
    echo.
    echo ===================================================
    echo Services supervisor stopped.
    echo ===================================================
    echo.
    pause
)

endlocal
