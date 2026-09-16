@echo off
echo =====================================================================
echo  Savera MS - EnergyAutomation Streamlit BI Dashboard Launcher
echo =====================================================================
echo.

cd /d "%~dp0"

IF EXIST ".venv\Scripts\streamlit.exe" (
    echo [OK] Using virtual environment Streamlit (.venv)
    ".venv\Scripts\streamlit.exe" run streamlit_app/app.py --server.port 8501
    goto END
)

IF EXIST ".venv\Scripts\python.exe" (
    echo [OK] Using virtual environment Python (.venv)
    ".venv\Scripts\python.exe" -m streamlit run streamlit_app/app.py --server.port 8501
    goto END
)

echo [INFO] Virtual environment not found. Using system Python...
python -m streamlit run streamlit_app/app.py --server.port 8501

:END
pause
