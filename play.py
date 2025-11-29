"""
Safe Launcher for AI Detective Game
Checks prerequisites before starting the game
"""

import sys
import subprocess
from pathlib import Path

def check_model_file():
    """Check if Ollama model is available"""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return False, "Ollama not running"
            
        if "gemma3n" in result.stdout:
            return True, "gemma3n"
        else:
            return False, "Model 'gemma3n' not pulled"
    except FileNotFoundError:
        return False, "Ollama not installed"
    except Exception as e:
        return False, str(e)

def check_required_files():
    """Check if data files exist"""
    data_files = [
        "data/case_summary.txt",
        "data/suspect_1_blacksmith.txt",
        "data/suspect_2_nun.txt",
        "data/suspect_3_merchant.txt",
        "data/suspect_4_soldier.txt",
        "data/suspect_5_boy.txt",
        "data/suspect_6_cook.txt",
    ]
    
    for file_path in data_files:
        if not Path(file_path).exists():
            return False, file_path
    return True, None

def main():
    """Launch the game with safety checks"""
    print("=" * 60)
    print("🕵️  AI DETECTIVE GAME LAUNCHER")
    print("=" * 60)
    
    # Check model file
    print("\n🔍 Checking AI model...")
    model_exists, status = check_model_file()
    if not model_exists:
        print(f"❌ ERROR: {status}")
        print("\n📋 To fix:")
        print("   1. Install Ollama from https://ollama.com/")
        print("   2. Run: ollama serve")
        print("   3. Run: ollama pull gemma3n")
        print("\nRun 'check_setup.py' for detailed diagnostics.")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    print(f"✅ Ollama model found: {status}")
    
    # Check data files
    print("\n📄 Checking data files...")
    files_ok, missing_file = check_required_files()
    if not files_ok:
        print(f"❌ ERROR: Missing data file: {missing_file}")
        print("\n📋 To fix:")
        print("   Make sure all files in data/ directory exist")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    print("✅ All data files present")
    
    # Try to import required modules
    print("\n📦 Checking Python packages...")
    try:
        import pygame
        from llama_index.core import VectorStoreIndex
        from llama_index.llms.ollama import Ollama
        from sentence_transformers import SentenceTransformer
        print("✅ All packages installed")
    except ImportError as e:
        if 'llama_index.core' in str(e):
            print("❌ ERROR: Your `llama-index` package is outdated.")
            print("\n📋 To fix:")
            print("   Run: pip install --upgrade llama-index")
            print("   This game requires version 0.10.0 or newer.")
        elif 'ollama' in str(e):
            print("❌ ERROR: llama-index-llms-ollama not installed.")
            print("\n📋 To fix:")
            print("   pip install llama-index-llms-ollama")
        else:
            print(f"❌ ERROR: Missing package: {e}")
            print("\n📋 To fix:")
            print("   pip install -r requirements.txt")
        input("\nPress Enter to exit...")
        sys.exit(1)
    
    # All checks passed - launch game
    print("\n✅ All checks passed!")
    print("=" * 60)
    print("\n🎮 Starting game...\n")
    
    # Import and run main game
    try:
        from main import main as game_main
        game_main()
    except KeyboardInterrupt:
        print("\n\nGame closed by user.")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nFor detailed diagnostics, run: python check_setup.py")
        input("\nPress Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
