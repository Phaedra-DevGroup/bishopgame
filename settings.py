"""
Settings Module for AI Detective Game
Manages API settings for AI backend (Ollama vs OpenAI-compatible API)
"""

import json
import os
from pathlib import Path

SETTINGS_FILE = "ai_settings.json"

# Default settings
DEFAULT_SETTINGS = {
    "model": "gemma3n",
    "isApiAvailable": False,
    "openai_base_url": "",
    "openai_api_key": "",
    "openai_model": ""
}


def load_settings() -> dict:
    """
    Load settings from file or return defaults
    
    Returns:
        Dictionary with AI settings
    """
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # Merge with defaults for any missing keys
                return {**DEFAULT_SETTINGS, **settings}
    except Exception as e:
        print(f"Error loading settings: {e}")
    
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict) -> bool:
    """
    Save settings to file
    
    Args:
        settings: Dictionary with AI settings
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False


def get_setting(key: str, default=None):
    """
    Get a specific setting value
    
    Args:
        key: Setting key to retrieve
        default: Default value if key not found
        
    Returns:
        Setting value or default
    """
    settings = load_settings()
    return settings.get(key, default)


def update_setting(key: str, value) -> bool:
    """
    Update a specific setting
    
    Args:
        key: Setting key to update
        value: New value
        
    Returns:
        True if successful, False otherwise
    """
    settings = load_settings()
    settings[key] = value
    return save_settings(settings)


def is_api_mode() -> bool:
    """Check if API mode is enabled"""
    return get_setting("isApiAvailable", False)


def get_api_config() -> dict:
    """
    Get OpenAI API configuration
    
    Returns:
        Dictionary with base_url, api_key, and model
    """
    settings = load_settings()
    return {
        "base_url": settings.get("openai_base_url", ""),
        "api_key": settings.get("openai_api_key", ""),
        "model": settings.get("openai_model", "")
    }


def get_ollama_model() -> str:
    """Get the Ollama model name"""
    return get_setting("model", "gemma3n")


# Initialize settings file with defaults if it doesn't exist
if not os.path.exists(SETTINGS_FILE):
    save_settings(DEFAULT_SETTINGS)
