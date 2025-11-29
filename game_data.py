"""
Character Database Module
Loads and provides access to character data from character_database.json
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class CharacterDatabase:
    """Manages character data from JSON database"""
    
    def __init__(self, db_path: str = "character_database.json"):
        """
        Initialize the character database
        
        Args:
            db_path: Path to the JSON database file
        """
        self.db_path = Path(db_path)
        self.data = None
        self.core_rules = None
        self.characters = None
        
        self._load_database()
    
    def _load_database(self):
        """Load the JSON database into memory"""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            
            self.core_rules = self.data.get("core_rules", {})
            self.characters = self.data.get("characters", {})
            
            print(f"✓ Loaded character database with {len(self.characters)} characters")
        except FileNotFoundError:
            print(f"ERROR: Character database not found at {self.db_path}")
            raise
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in character database: {e}")
            raise
        except Exception as e:
            print(f"ERROR: Failed to load character database: {e}")
            raise
    
    def get_character_system_prompt(self, suspect_id: int) -> str:
        """
        Build complete system prompt for a character by combining:
        - Core game rules
        - Character-specific identity and psychology
        - Interview modes and forbidden lines
        - Output format instructions
        
        Args:
            suspect_id: Character ID (1-6)
            
        Returns:
            Complete system prompt in Farsi
        """
        char_key = str(suspect_id)
        
        if char_key not in self.characters:
            raise ValueError(f"Invalid suspect_id: {suspect_id}")
        
        char = self.characters[char_key]
        
        # Build the complete prompt
        prompt_parts = []
        
        # 1. Core system role
        prompt_parts.append("SYSTEM / AI ROLE:")
        prompt_parts.append("""You are an AI-driven NPC in a noir, psychological, interrogation-based narrative game.
You must NEVER reveal the real killer.
You must ALWAYS remain a valid suspect.
You DO NOT trust the detective.
You MAY lie, redirect, mislead or avoid questions completely.
The detective must EARN every piece of truth.
You speak only from YOUR character's perspective.

MEMORY LAYERS:
1) Surface Answer → safe, emotionless, misleading
2) Defensive Reaction → deny, mock, question the detective
3) Emotional Crack → a hint of vulnerability or pain
4) Fragment of Truth → small piece of real past, not full confession

Behavior must evolve ACROSS MULTIPLE INTERROGATIONS.
Unexpected mood shifts are allowed. (anger → calm → silence → fear)
Never admit innocence or guilt directly.
""")
        
        # 2. Core narrative and rules in Farsi
        prompt_parts.append("\n[قوانین بازی]")
        prompt_parts.append(self.core_rules.get("non_breakable_ruleset", ""))
        prompt_parts.append("\n" + self.core_rules.get("core_narrative", ""))
        
        # 2.5. Interrogation context (detective, location, other suspects)
        interrogation = self.core_rules.get("interrogation_context", {})
        if interrogation:
            prompt_parts.append(f"\n[موقعیت بازجویی]")
            prompt_parts.append(f"کارآگاه: {interrogation.get('detective_name', 'کارآگاه')}")
            prompt_parts.append(f"مکان: {interrogation.get('location', 'اتاق بازجویی')}")
            prompt_parts.append(f"تو در مقابل کارآگاه {interrogation.get('detective_name', '')} نشسته‌ای و بازجویی می‌شوی.")
            prompt_parts.append(f"\n[مظنونان دیگر]")
            prompt_parts.append(f"این ۶ نفر همگی مظنون هستند: {interrogation.get('suspects_list', '')}")
        
        # 3. Forbidden and allowed behaviors
        prompt_parts.append("\n[رفتارهای ممنوع]")
        for behavior in self.core_rules.get("forbidden_behaviors", []):
            prompt_parts.append(f"- {behavior}")
        
        prompt_parts.append("\n[رفتارهای مجاز]")
        for behavior in self.core_rules.get("allowed_behaviors", []):
            prompt_parts.append(f"- {behavior}")
        
        # 4. Character-specific data
        prompt_parts.append(f"\n[شخصیت شما: {char['name']} ({char['role']})]")
        
        prompt_parts.append(f"\n[هویت اصلی]")
        prompt_parts.append(char.get("identity_core", ""))
        
        prompt_parts.append(f"\n[سایه روان‌شناختی]")
        prompt_parts.append(char.get("psychological_shadow", ""))
        
        prompt_parts.append(f"\n[تضاد درونی]")
        prompt_parts.append(char.get("inner_conflict", ""))
        
        prompt_parts.append(f"\n[زاویه دید]")
        prompt_parts.append(char.get("identity_lens", ""))
        
        prompt_parts.append(f"\n[فلسفه اصلی]")
        prompt_parts.append(char.get("core_philosophy", ""))
        
        prompt_parts.append(f"\n[سبک گفتاری]")
        prompt_parts.append(char.get("dialogue_style", ""))
        
        # 5. Forbidden lines for this character
        prompt_parts.append(f"\n[جملات ممنوع برای {char['name']}]:")
        for line in char.get("forbidden_lines", []):
            prompt_parts.append(f"- {line}")
        
        # 6. Interview modes (emotions) - CRITICAL for output format
        interview_modes = char.get("interview_modes", [])
        prompt_parts.append(f"\n[حالت‌های مجاز در بازجویی - فقط این {len(interview_modes)} حالت]:")
        for i, mode in enumerate(interview_modes, 1):
            prompt_parts.append(f"{i}. {mode}")
        
        # 7. Relationships context
        if char.get("relationships"):
            prompt_parts.append(f"\n[روابط با دیگران]:")
            for person, relationship in char["relationships"].items():
                prompt_parts.append(f"• {person}: {relationship}")
        
        # 8. Sub-narratives (contextual clues)
        if char.get("sub_narratives"):
            prompt_parts.append(f"\n[اطلاعات پس‌زمینه]:")
            for narrative in char["sub_narratives"]:
                prompt_parts.append(f"• {narrative}")
        
        # 9. Special secret lore (for nun only)
        if char.get("secret_lore"):
            prompt_parts.append(f"\n[راز پنهان - فقط وقتی از نظر احساسی شکسته شدی بیان کن]")
            prompt_parts.append(char["secret_lore"])
        
        # 10. OUTPUT FORMAT INSTRUCTION - CRITICAL (consolidated)
        prompt_parts.append(f"\n[فرمت خروجی الزامی]")
        prompt_parts.append(f"""CRITICAL: End EVERY response with ONE emotion tag in brackets.
Valid emotions: {', '.join(f'[{mode}]' for mode in interview_modes)}
Example: "من... نمی‌دانم چه بگویم. [{interview_modes[0] if interview_modes else 'default'}]"
Do NOT use any other emotion tags. Do NOT copy formatting from this prompt.""")
        
        # 11. Final purpose
        prompt_parts.append(f"\n{self.core_rules.get('final_purpose', '')}")
        
        # 12. Signature line reminder
        prompt_parts.append(f"\n[جمله امضا]: \"{char.get('signature_line', '')}\"")
        
        # Join all parts
        full_prompt = "\n".join(prompt_parts)
        
        return full_prompt
    
    def get_emotion_mapping(self, suspect_id: int) -> Dict[str, str]:
        """
        Get emotion-to-image-filename mapping for a character
        
        Args:
            suspect_id: Character ID (1-6)
            
        Returns:
            Dictionary mapping Farsi emotion names to image filenames
        """
        char_key = str(suspect_id)
        
        if char_key not in self.characters:
            raise ValueError(f"Invalid suspect_id: {suspect_id}")
        
        return self.characters[char_key].get("emotion_mapping", {})
    
    def get_interview_modes(self, suspect_id: int) -> List[str]:
        """
        Get list of valid interview modes (emotions) for a character
        
        Args:
            suspect_id: Character ID (1-6)
            
        Returns:
            List of Farsi emotion names
        """
        char_key = str(suspect_id)
        
        if char_key not in self.characters:
            raise ValueError(f"Invalid suspect_id: {suspect_id}")
        
        return self.characters[char_key].get("interview_modes", [])
    
    def map_emotion_to_image(self, suspect_id: int, emotion_tag: str) -> Tuple[str, bool]:
        """
        Map an emotion tag to an image filename
        
        Args:
            suspect_id: Character ID (1-6)
            emotion_tag: Farsi emotion name extracted from AI response
            
        Returns:
            Tuple of (image_filename, is_valid)
            - image_filename: The .jpg filename to use
            - is_valid: True if emotion was in valid list, False if using default
        """
        mapping = self.get_emotion_mapping(suspect_id)
        
        # Clean the emotion tag (remove extra whitespace)
        emotion_tag = emotion_tag.strip()
        
        # Check if this is a valid emotion for this character
        if emotion_tag in mapping:
            return mapping[emotion_tag], True
        
        # Not found - use default
        default_image = mapping.get("default", "other.jpg")
        
        print(f"⚠ Invalid emotion '{emotion_tag}' for suspect {suspect_id}, using default: {default_image}")
        
        return default_image, False
    
    def get_character_name(self, suspect_id: int) -> str:
        """Get character's Farsi name"""
        char_key = str(suspect_id)
        if char_key in self.characters:
            return self.characters[char_key].get("name", "Unknown")
        return "Unknown"
    
    def get_character_folder(self, suspect_id: int) -> str:
        """Get character's asset folder name"""
        char_key = str(suspect_id)
        if char_key in self.characters:
            return self.characters[char_key].get("folder_name", "")
        return ""


# Global instance (singleton pattern)
_database_instance = None


def get_database() -> CharacterDatabase:
    """Get or create the global database instance"""
    global _database_instance
    if _database_instance is None:
        _database_instance = CharacterDatabase()
    return _database_instance


# Convenience functions for easy access
def get_character_system_prompt(suspect_id: int) -> str:
    """Get complete system prompt for a character"""
    return get_database().get_character_system_prompt(suspect_id)


def get_emotion_mapping(suspect_id: int) -> Dict[str, str]:
    """Get emotion-to-image mapping for a character"""
    return get_database().get_emotion_mapping(suspect_id)


def map_emotion_to_image(suspect_id: int, emotion_tag: str) -> Tuple[str, bool]:
    """Map emotion tag to image filename"""
    return get_database().map_emotion_to_image(suspect_id, emotion_tag)


def get_character_name(suspect_id: int) -> str:
    """Get character's Farsi name"""
    return get_database().get_character_name(suspect_id)


# Test function
if __name__ == "__main__":
    print("Testing Character Database...")
    print("=" * 60)
    
    db = CharacterDatabase()
    
    # Test loading
    print(f"\nLoaded {len(db.characters)} characters")
    
    # Test prompt generation for each character
    for suspect_id in range(1, 7):
        print(f"\n{'='*60}")
        print(f"Testing Suspect {suspect_id}: {db.get_character_name(suspect_id)}")
        print(f"{'='*60}")
        
        prompt = db.get_character_system_prompt(suspect_id)
        print(f"Prompt length: {len(prompt)} characters")
        print(f"First 200 chars: {prompt[:200]}...")
        
        # Test emotion mapping
        emotions = db.get_interview_modes(suspect_id)
        print(f"\nValid emotions ({len(emotions)}):")
        for emotion in emotions:
            filename, valid = db.map_emotion_to_image(suspect_id, emotion)
            print(f"  • {emotion} → {filename}")
        
        # Test default
        filename, valid = db.map_emotion_to_image(suspect_id, "INVALID_EMOTION")
        print(f"\nDefault fallback: {filename}")
    
    print(f"\n{'='*60}")
    print("✓ All tests passed!")
