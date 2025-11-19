@echo off
echo ==========================================
echo ZeCo Setup Script (Windows)
echo ==========================================

REM Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python 3.10+ and try again.
    pause
    exit /b 1
)

echo Installing dependencies...
python -m pip install cryptography

echo.
echo Running setup script...
python setup_env.py

echo.
echo Setup finished.
pause
