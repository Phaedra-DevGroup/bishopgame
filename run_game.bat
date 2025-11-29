@echo off
echo ============================================================
echo    AI DETECTIVE GAME - VIRTUAL ENVIRONMENT LAUNCHER
echo ============================================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created!
    echo.
    echo Installing dependencies...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies!
        pause
        exit /b 1
    )
) else (
    call venv\Scripts\activate.bat
)

echo.
echo [OK] Virtual environment activated!
echo Starting game...
echo.
python main.py

pause