#!/bin/bash
# AI Detective Game - Linux/Mac Quick Setup Script
# Run this to set up everything automatically

echo "============================================================"
echo "   AI DETECTIVE GAME - AUTOMATIC SETUP"
echo "============================================================"
echo ""

# Check Python
echo "[1/5] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed!"
    echo "Please install Python 3.8+ from your package manager"
    exit 1
fi
python3 --version
echo "[OK] Python found!"
echo ""

# Check CUDA (optional but recommended for GPU acceleration)
echo "[2/5] Checking CUDA installation..."
if ! command -v nvcc &> /dev/null; then
    echo "[WARNING] CUDA toolkit not detected!"
    echo "GPU acceleration may not be available."
    echo "For full GPU support, install CUDA 11.8+ from:"
    echo "https://developer.nvidia.com/cuda-downloads"
    echo ""
    echo "Continuing with CPU/fallback mode..."
else
    nvcc --version | grep "release"
    echo "[OK] CUDA found!"
fi
echo ""

# Install Python packages
echo "[3/5] Installing Python packages..."
echo "This may take a few minutes..."
echo ""
echo "Installing requirements..."
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install Python packages!"
    exit 1
fi
echo "[OK] Packages installed!"
echo ""

# Verify Ollama
echo "[4/5] Verifying Ollama..."
if ! command -v ollama &> /dev/null; then
    echo "[WARNING] Ollama not found in PATH!"
    echo "Please ensure Ollama is installed and running."
    echo "Download from: https://ollama.com/"
    echo ""
else
    echo "[OK] Ollama found!"
    echo "Please ensure you have pulled the model: ollama pull gemma3n"
fi
echo ""

# Generate assets (optional)
echo "[5/5] Generating game assets..."
python3 generate_assets.py
echo "[OK] Assets created!"
echo ""

# Final verification
echo "============================================================"
echo "Running setup verification..."
echo "============================================================"
python3 check_setup.py
echo ""

echo "============================================================"
echo "   SETUP COMPLETE!"
echo "============================================================"
echo ""
echo "To play the game, run:"
echo "   python3 play.py"
echo ""
echo "============================================================"
