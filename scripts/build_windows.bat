@echo off
setlocal
cd /d "%~dp0\.."

echo ============================================================
echo   EnergyAutomation — Windows Production Build
echo ============================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1" %*

if errorlevel 1 (
    echo.
    echo Build failed with error code %errorlevel%.
    exit /b %errorlevel%
)

echo Build finished successfully.
endlocal
