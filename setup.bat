@echo off
REM AI Detective Game - Windows Quick Setup Script
REM Run this to set up everything automatically

echo ============================================================
echo    AI DETECTIVE GAME - AUTOMATIC SETUP
echo ============================================================
echo.

REM Check Python
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.8+ from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation!
    pause
    exit /b 1
)
python --version
echo [OK] Python found!
echo.

REM Check CUDA (optional but recommended for GPU acceleration)
echo [2/5] Checking CUDA installation...
nvcc --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] CUDA toolkit not detected!
    echo GPU acceleration may not be available.
    echo For full GPU support, install CUDA 11.8+ from:
    echo https://developer.nvidia.com/cuda-downloads
    echo.
    echo Continuing with CPU/fallback mode...
) else (
    nvcc --version | findstr "release"
    echo [OK] CUDA found!
)
echo.

REM Install Python packages
echo [3/5] Installing Python packages...
echo This may take a few minutes...
echo.
echo Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python packages!
    pause
    exit /b 1
)
echo [OK] Packages installed!
echo.

REM Verify Ollama
echo [4/5] Verifying Ollama...
where ollama >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Ollama not found in PATH!
    echo Please ensure Ollama is installed and running.
    echo Download from: https://ollama.com/
    echo.
) else (
    echo [OK] Ollama found!
    echo Please ensure you have pulled the model: ollama pull gemma3n
)
echo.

REM Generate assets (optional)
echo [5/5] Generating game assets...
python generate_assets.py
echo [OK] Assets created!
echo.

REM Final verification
echo ============================================================
echo Running setup verification...
echo ============================================================
python check_setup.py
echo.

echo ============================================================
echo    SETUP COMPLETE!
echo ============================================================
echo.
echo To play the game, run:
echo    python play.py
echo.
echo Or simply double-click "play.py" in Windows Explorer!
echo.
echo ============================================================
pause
