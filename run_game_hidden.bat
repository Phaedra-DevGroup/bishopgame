@echo off
REM Hidden launcher - no console window

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    REM Fall back to regular launcher if venv doesn't exist
    call run_game.bat
    exit /b
)

REM Activate venv and run with pythonw (no console)
call venv\Scripts\activate.bat
pythonw main.py
