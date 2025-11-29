"""
Game state management for AI Detective game.
Handles day progression, notebook pages, and save/load functionality.
"""

import json
import os
from typing import List, Dict, Any


def get_default_emotion(suspect_id: int) -> str:
    """Get the default emotion for a suspect based on their persona"""
    default_emotions = {
        1: "scared",   # Blacksmith - "ترس از حقیقت"
        2: "other",    # Nun - "سکون مقدس" (calm/neutral)
        3: "happy",    # Merchant - "غرور خودشیفته" (confident)
        4: "other",    # Soldier - "اطاعت کورکورانه" (neutral/duty)
        5: "angry",    # Boy - "خشم خام، بیشکل" (raw anger)
        6: "scared"    # Cook - "ترس از دروغ ناخواسته"
    }
    return default_emotions.get(suspect_id, "other")


class GameState:
    """Manages game state including day counter and notebook pages."""
    
    def __init__(self):
        """Initialize game state with default values."""
        self.current_day: int = 1
        self.notebook_pages: List[Dict[str, Any]] = [
            {"day": 1, "content": ""}
        ]
        self.game_ended: bool = False  # Track if game has ended (win/lose)
        self.win_state: str = ""  # "win" or "lose" if game ended
        self.intro_shown: bool = False  # Track if intro has been shown
        self.case_files_text: str = ""  # AI-generated intro text for case files document
        self.save_file: str = "savegame.json"
    
    def advance_day(self) -> int:
        """
        Advance to the next day.
        
        Returns:
            int: The new current day number
        """
        self.current_day += 1
        # Create a new blank page for the new day
        self.notebook_pages.append({
            "day": self.current_day,
            "content": ""
        })
        return self.current_day
    
    def get_current_page(self) -> Dict[str, Any]:
        """
        Get the current day's notebook page.
        
        Returns:
            Dict with 'day' and 'content' keys
        """
        # Find the page for the current day
        for page in self.notebook_pages:
            if page["day"] == self.current_day or page["day"] == "Final":
                return page
        
        # If not found (shouldn't happen), return the last page
        return self.notebook_pages[-1] if self.notebook_pages else {"day": 1, "content": ""}
    
    def update_current_page(self, content: str):
        """
        Update the content of the current day's page.
        
        Args:
            content: The new content for the page
        """
        current_page = self.get_current_page()
        current_page["content"] = content
    
    def create_final_page(self):
        """Create a final notes page after accusation."""
        # Check if final page already exists
        for page in self.notebook_pages:
            if page["day"] == "Final":
                return
        
        self.notebook_pages.append({
            "day": "Final",
            "content": ""
        })
        self.current_day = "Final"
    
    def get_page_by_index(self, index: int) -> Dict[str, Any]:
        """
        Get a notebook page by index.
        
        Args:
            index: Page index (0-based)
            
        Returns:
            Dict with 'day' and 'content' keys
        """
        if 0 <= index < len(self.notebook_pages):
            return self.notebook_pages[index]
        return {"day": 1, "content": ""}
    
    def get_total_pages(self) -> int:
        """Get the total number of notebook pages."""
        return len(self.notebook_pages)
    
    def save(self):
        """Save game state to JSON file."""
        data = {
            "current_day": self.current_day,
            "notebook_pages": self.notebook_pages,
            "game_ended": self.game_ended,
            "win_state": self.win_state,
            "intro_shown": self.intro_shown,
            "case_files_text": self.case_files_text
        }
        
        try:
            with open(self.save_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving game state: {e}")
    
    def load(self) -> bool:
        """
        Load game state from JSON file.
        
        Returns:
            bool: True if load was successful, False otherwise
        """
        if not os.path.exists(self.save_file):
            return False
        
        try:
            with open(self.save_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.current_day = data.get("current_day", 1)
            self.notebook_pages = data.get("notebook_pages", [{"day": 1, "content": ""}])
            self.game_ended = data.get("game_ended", False)
            self.win_state = data.get("win_state", "")
            self.intro_shown = data.get("intro_shown", False)
            self.case_files_text = data.get("case_files_text", "")
            
            return True
        except Exception as e:
            print(f"Error loading game state: {e}")
            return False
    
    def reset(self):
        """Reset game state to initial values."""
        self.current_day = 1
        self.notebook_pages = [{"day": 1, "content": ""}]
        self.game_ended = False
        self.win_state = ""
        self.intro_shown = False
        self.case_files_text = ""
