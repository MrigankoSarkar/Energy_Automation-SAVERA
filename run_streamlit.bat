@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo   EnergyAutomation - Streamlit Management BI
echo ===================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
    set "PYTHON_CMD=python"
)

echo Starting Streamlit BI on http://localhost:8501...
%PYTHON_CMD% -m streamlit run streamlit_app.py

if errorlevel 1 (
    echo.
    echo ===================================================
    echo Streamlit app stopped with an error.
    echo ===================================================
    pause
)

endlocal
