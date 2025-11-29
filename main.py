"""
AI Detective Game - Main Application
A whodunnit detective mystery game using Pygame and AI-powered dialogue
"""

import pygame
import sys
import threading
import math
from pathlib import Path
from typing import List, Tuple, Optional
from ai_handler import AIDetectiveEngine
from game_state import GameState
import game_data
import settings as ai_settings

# Import for Persian/Arabic text rendering
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    PERSIAN_SUPPORT = True
except ImportError:
    PERSIAN_SUPPORT = False
    print("Warning: arabic-reshaper or python-bidi not installed. Persian text may not display correctly.")
    print("Install with: pip install arabic-reshaper python-bidi")

# Helper function for Persian text
def reshape_persian_text(text: str) -> str:
    """Reshape Persian/Arabic text for proper display in Pygame"""
    if not PERSIAN_SUPPORT:
        return text
    try:
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text
    except:
        return text

def to_persian_number(num) -> str:
    """Convert English digits to Persian digits"""
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    return ''.join(persian_digits[int(d)] if d.isdigit() else d for d in str(num))

# Initialize Pygame
pygame.init()

# Helper function to blur a surface (using scale down/up method)
def blur_surface(surface, amount=4):
    """Apply blur effect to a pygame surface by scaling down and back up"""
    if amount < 1:
        return surface
    
    # Get original size
    orig_size = surface.get_size()
    
    # Scale down
    scale = max(1, amount)
    small_size = (max(1, orig_size[0] // scale), max(1, orig_size[1] // scale))
    small_surface = pygame.transform.smoothscale(surface, small_size)
    
    # Scale back up - this creates blur effect
    blurred = pygame.transform.smoothscale(small_surface, orig_size)
    
    return blurred

# Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors - Gothic Noir Palette
COLOR_BG = (22, 20, 25)              # Warm dark background
COLOR_PANEL = (45, 40, 38)           # Aged paper/wood panels
COLOR_BUTTON = (60, 50, 45)          # Muted brown buttons
COLOR_BUTTON_HOVER = (80, 70, 60)    # Lighter brown hover
COLOR_BUTTON_ACTIVE = (90, 120, 85)  # Muted green active
COLOR_TEXT = (240, 230, 210)         # Warm parchment text
COLOR_INPUT_BG = (35, 32, 30)        # Dark input background
COLOR_PLAYER_TEXT = (180, 210, 240)  # Soft blue player text
COLOR_SUSPECT_TEXT = (255, 220, 180) # Warm orange suspect text
COLOR_ACCENT = (120, 40, 50)         # Deep burgundy accent

# Additional Gothic Noir Colors
COLOR_GOLD = (180, 150, 90)          # Gold highlights
COLOR_SHADOW = (0, 0, 0)             # Pure black shadows
COLOR_GLOW = (255, 200, 100)         # Warm glow effect
COLOR_BORDER_DARK = (30, 25, 22)     # Dark border color
COLOR_BORDER_LIGHT = (100, 85, 70)   # Light border color

# ============== RENDERING HELPER FUNCTIONS ==============

def lerp_color(c1: Tuple[int, int, int], c2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    """Linearly interpolate between two colors"""
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t)
    )

def draw_text_with_shadow(surface: pygame.Surface, text: str, font: pygame.font.Font, 
                          color: Tuple[int, int, int], pos: Tuple[int, int], 
                          shadow_offset: int = 2, shadow_color: Tuple[int, int, int] = None,
                          center: bool = False):
    """Draw text with a shadow effect for better readability"""
    if shadow_color is None:
        shadow_color = COLOR_SHADOW
    
    # Reshape Persian text
    display_text = reshape_persian_text(text)
    
    # Render shadow
    shadow_surface = font.render(display_text, True, shadow_color)
    # Render main text
    text_surface = font.render(display_text, True, color)
    
    if center:
        shadow_rect = shadow_surface.get_rect(center=(pos[0] + shadow_offset, pos[1] + shadow_offset))
        text_rect = text_surface.get_rect(center=pos)
        surface.blit(shadow_surface, shadow_rect)
        surface.blit(text_surface, text_rect)
    else:
        surface.blit(shadow_surface, (pos[0] + shadow_offset, pos[1] + shadow_offset))
        surface.blit(text_surface, pos)
    
    return text_surface

def draw_vignette(surface: pygame.Surface, intensity: int = 100):
    """Draw a vignette effect (darkened edges) on the surface"""
    width, height = surface.get_size()
    vignette = pygame.Surface((width, height), pygame.SRCALPHA)
    
    # Create radial gradient from center (transparent) to edges (dark)
    center_x, center_y = width // 2, height // 2
    max_dist = (center_x ** 2 + center_y ** 2) ** 0.5
    
    # Draw concentric rectangles for efficiency (approximate radial gradient)
    for i in range(0, intensity, 5):
        alpha = int((i / intensity) * 40)  # Max alpha of 40 for very subtle effect
        shrink = int((1 - i / intensity) * min(width, height) * 0.15)  # Only affect outer 15%
        rect = pygame.Rect(shrink, shrink, width - 2 * shrink, height - 2 * shrink)
        if rect.width > 0 and rect.height > 0:
            pygame.draw.rect(vignette, (0, 0, 0, alpha), rect, border_radius=shrink // 2)
    
    # Draw solid dark borders at edges (subtle, only at very edge)
    border_size = 25
    # Top
    for i in range(border_size):
        alpha = int((1 - i / border_size) * 70)
        pygame.draw.line(vignette, (0, 0, 0, alpha), (0, i), (width, i))
    # Bottom
    for i in range(border_size):
        alpha = int((1 - i / border_size) * 70)
        pygame.draw.line(vignette, (0, 0, 0, alpha), (0, height - 1 - i), (width, height - 1 - i))
    # Left
    for i in range(border_size):
        alpha = int((1 - i / border_size) * 50)
        pygame.draw.line(vignette, (0, 0, 0, alpha), (i, 0), (i, height))
    # Right
    for i in range(border_size):
        alpha = int((1 - i / border_size) * 50)
        pygame.draw.line(vignette, (0, 0, 0, alpha), (width - 1 - i, 0), (width - 1 - i, height))
    
    surface.blit(vignette, (0, 0))

def draw_inner_shadow(surface: pygame.Surface, rect: pygame.Rect, shadow_size: int = 8, alpha: int = 60):
    """Draw inner shadow effect on a rectangular area"""
    shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    
    # Top shadow (strongest)
    for i in range(shadow_size):
        a = int((1 - i / shadow_size) * alpha)
        pygame.draw.line(shadow, (0, 0, 0, a), (0, i), (rect.width, i))
    
    # Left shadow
    for i in range(shadow_size):
        a = int((1 - i / shadow_size) * (alpha // 2))
        pygame.draw.line(shadow, (0, 0, 0, a), (i, 0), (i, rect.height))
    
    surface.blit(shadow, (rect.x, rect.y))

def draw_warm_tint(surface: pygame.Surface, alpha: int = 15):
    """Apply a subtle warm color tint for candlelit ambiance"""
    tint = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    tint.fill((40, 30, 20, alpha))
    surface.blit(tint, (0, 0))

def draw_glow(surface: pygame.Surface, pos: Tuple[int, int], radius: int, color: Tuple[int, int, int], alpha: int = 60):
    """Draw a soft glow effect at a position"""
    glow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for i in range(radius, 0, -2):
        a = int((i / radius) * alpha)
        pygame.draw.circle(glow_surf, (*color, a), (radius, radius), i)
    surface.blit(glow_surf, (pos[0] - radius, pos[1] - radius))

# Fonts
FONT_LARGE = None
FONT_MEDIUM = None
FONT_SMALL = None
FONT_FARSI = None
FONT_FARSI_SMALL = None


class Button:
    """A clickable button UI element with gothic noir styling"""
    
    def __init__(self, x: int, y: int, width: int, height: int, text: str, 
                 font: pygame.font.Font, color: Tuple[int, int, int] = COLOR_BUTTON):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = COLOR_BUTTON_HOVER
        self.is_hovered = False
        self.is_active = False
        self.is_disabled = False
        self.hover_progress = 0.0  # 0.0 to 1.0 for smooth transitions
        self.hover_speed = 8.0  # Speed of hover transition
        self.hide_background = False  # If True, don't draw button background
        
    def update(self, dt: float):
        """Update hover animation"""
        # dt is in milliseconds, convert to seconds
        dt_sec = dt / 1000.0
        
        if self.is_hovered and not self.is_disabled:
            self.hover_progress = min(1.0, self.hover_progress + self.hover_speed * dt_sec)
        else:
            self.hover_progress = max(0.0, self.hover_progress - self.hover_speed * dt_sec)
        
    def draw(self, surface: pygame.Surface):
        """Draw the button with gothic noir styling"""
        # Skip background drawing if hide_background is True
        if getattr(self, 'hide_background', False):
            # Just draw text if any
            if self.text:
                display_text = reshape_persian_text(self.text)
                shadow_surface = self.font.render(display_text, True, COLOR_SHADOW)
                text_surface = self.font.render(display_text, True, COLOR_TEXT)
                text_rect = text_surface.get_rect(center=self.rect.center)
                surface.blit(shadow_surface, (text_rect.x + 2, text_rect.y + 2))
                surface.blit(text_surface, text_rect)
            return
            
        if self.is_disabled:
            # Grayed out appearance when disabled
            bg_color = (40, 38, 35)
            text_color = (90, 85, 80)
            border_color = (60, 55, 50)
        elif self.is_active:
            bg_color = COLOR_BUTTON_ACTIVE
            text_color = COLOR_TEXT
            border_color = COLOR_GOLD
        else:
            # Interpolate colors based on hover progress
            bg_color = lerp_color(self.color, self.hover_color, self.hover_progress)
            text_color = COLOR_TEXT
            border_color = lerp_color(COLOR_BORDER_DARK, COLOR_GOLD, self.hover_progress)
        
        # Draw outer dark border (gothic frame effect)
        outer_rect = self.rect.inflate(4, 4)
        pygame.draw.rect(surface, COLOR_BORDER_DARK, outer_rect, border_radius=10)
        
        # Draw main button background
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=8)
        
        # Draw inner glow on hover
        if self.hover_progress > 0 and not self.is_disabled:
            glow_alpha = int(30 * self.hover_progress)
            glow_rect = self.rect.inflate(-6, -6)
            glow_surface = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(glow_surface, (*COLOR_GLOW, glow_alpha), 
                           glow_surface.get_rect(), border_radius=6)
            surface.blit(glow_surface, glow_rect)
        
        # Draw border with gold tint on hover
        pygame.draw.rect(surface, border_color, self.rect, 2, border_radius=8)
        
        # Draw inner highlight line at top for depth
        if not self.is_disabled:
            highlight_rect = pygame.Rect(self.rect.x + 4, self.rect.y + 2, self.rect.width - 8, 1)
            highlight_color = lerp_color((80, 70, 60), (120, 100, 80), self.hover_progress)
            pygame.draw.rect(surface, highlight_color, highlight_rect)
        
        # Draw text with shadow
        if self.text:
            display_text = reshape_persian_text(self.text)
            
            # Shadow
            shadow_surface = self.font.render(display_text, True, COLOR_SHADOW)
            shadow_rect = shadow_surface.get_rect(center=(self.rect.centerx + 1, self.rect.centery + 1))
            surface.blit(shadow_surface, shadow_rect)
            
            # Main text
            text_surface = self.font.render(display_text, True, text_color)
            text_rect = text_surface.get_rect(center=self.rect.center)
            surface.blit(text_surface, text_rect)
        
    def handle_event(self, event: pygame.event.Event) -> bool:
        """
        Handle mouse events
        Returns True if button was clicked
        """
        if self.is_disabled:
            return False
            
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False


class TextBox:
    """A text input box with gothic noir styling"""
    
    def __init__(self, x: int, y: int, width: int, height: int, font: pygame.font.Font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.text = ""
        self.is_active = False
        self.is_disabled = False
        self.cursor_visible = True
        self.cursor_timer = 0
        self.glow_timer = 0  # For pulsing glow effect
        self.placeholder = "سوال خود را بنویسید..."
        
    def draw(self, surface: pygame.Surface):
        """Draw the text box with gothic noir styling"""
        if self.is_disabled:
            bg_color = (35, 32, 30)
            text_color = (90, 85, 80)
            border_color = (50, 45, 40)
        elif self.is_active:
            bg_color = (45, 40, 38)
            text_color = COLOR_TEXT
            # Pulsing gold border when active
            pulse = (math.sin(self.glow_timer * 4) + 1) / 2  # 0 to 1
            border_color = lerp_color(COLOR_BORDER_LIGHT, COLOR_GOLD, pulse * 0.7)
        else:
            bg_color = COLOR_INPUT_BG
            text_color = COLOR_TEXT
            border_color = COLOR_BORDER_LIGHT
        
        # Draw outer dark border
        outer_rect = self.rect.inflate(4, 4)
        pygame.draw.rect(surface, COLOR_BORDER_DARK, outer_rect, border_radius=10)
        
        # Draw main background
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=8)
        
        # Draw pulsing glow when active
        if self.is_active and not self.is_disabled:
            pulse = (math.sin(self.glow_timer * 4) + 1) / 2
            glow_alpha = int(25 * pulse)
            glow_rect = self.rect.inflate(8, 8)
            glow_surface = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
            pygame.draw.rect(glow_surface, (*COLOR_GOLD, glow_alpha), 
                           glow_surface.get_rect(), border_radius=12)
            surface.blit(glow_surface, glow_rect)
        
        # Draw inner shadow at top
        draw_inner_shadow(surface, self.rect, shadow_size=6, alpha=40)
        
        # Draw border
        pygame.draw.rect(surface, border_color, self.rect, 2, border_radius=8)
        
        # Set clipping to prevent text overflow
        old_clip = surface.get_clip()
        content_rect = pygame.Rect(self.rect.x + 5, self.rect.y + 2, self.rect.width - 10, self.rect.height - 4)
        surface.set_clip(content_rect)
        
        max_text_width = self.rect.width - 20
        
        # Draw text with RTL support (reshape for Persian)
        if self.text:
            display_text = reshape_persian_text(self.text)
            
            # Draw shadow
            shadow_surface = self.font.render(display_text, True, COLOR_SHADOW)
            text_surface = self.font.render(display_text, True, text_color)
            
            # If text is too wide, show only the rightmost portion (for RTL)
            if text_surface.get_width() > max_text_width:
                text_surface = text_surface.subsurface((0, 0, max_text_width, text_surface.get_height()))
                shadow_surface = shadow_surface.subsurface((0, 0, max_text_width, shadow_surface.get_height()))
            
            # Right-align for RTL text
            text_x = self.rect.x + self.rect.width - text_surface.get_width() - 10
            surface.blit(shadow_surface, (text_x + 1, self.rect.y + 11))
            surface.blit(text_surface, (text_x, self.rect.y + 10))
            
            # Draw cursor at the right side for RTL
            if self.is_active and self.cursor_visible and not self.is_disabled:
                cursor_x = text_x - 5
                cursor_y = self.rect.y + 8
                pygame.draw.line(surface, COLOR_GOLD, 
                               (cursor_x, cursor_y), 
                               (cursor_x, cursor_y + self.rect.height - 16), 2)
        else:
            # Draw placeholder text when empty (centered)
            if not self.is_active:
                placeholder_text = reshape_persian_text(self.placeholder)
                placeholder_surface = self.font.render(placeholder_text, True, (100, 90, 80))
                placeholder_x = self.rect.x + (self.rect.width - placeholder_surface.get_width()) // 2
                placeholder_y = self.rect.y + (self.rect.height - placeholder_surface.get_height()) // 2
                surface.blit(placeholder_surface, (placeholder_x, placeholder_y))
            
            # Draw cursor at right side when empty and active
            if self.is_active and self.cursor_visible and not self.is_disabled:
                cursor_x = self.rect.x + self.rect.width - 15
                cursor_y = self.rect.y + 8
                pygame.draw.line(surface, COLOR_GOLD, 
                               (cursor_x, cursor_y), 
                               (cursor_x, cursor_y + self.rect.height - 16), 2)
        
        # Restore original clipping
        surface.set_clip(old_clip)
    
    def update(self, dt: float):
        """Update cursor blink and glow animation"""
        self.cursor_timer += dt
        if self.cursor_timer >= 500:  # Blink every 500ms
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0
        
        # Update glow timer
        self.glow_timer += dt / 1000.0
            
    def handle_event(self, event: pygame.event.Event):
        """Handle keyboard and mouse events"""
        if self.is_disabled:
            return None
            
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.is_active = self.rect.collidepoint(event.pos)
            
        if event.type == pygame.KEYDOWN and self.is_active:
            if event.key == pygame.K_RETURN:
                return "submit"
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                # Handle Unicode input properly for Farsi/Arabic
                if event.unicode and event.unicode.isprintable():
                    # Limit text length
                    if len(self.text) < 80:
                        self.text += event.unicode
        return None


class SettingsTextBox:
    """A text input box for settings (LTR text like URLs and API keys)"""
    
    def __init__(self, x: int, y: int, width: int, height: int, font: pygame.font.Font, placeholder: str = ""):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.text = ""
        self.is_active = False
        self.cursor_visible = True
        self.cursor_timer = 0
        self.glow_timer = 0
        self.placeholder = placeholder
        self.is_password = False  # For API key masking
        self.max_length = 500
        
    def draw(self, surface: pygame.Surface):
        """Draw the text box"""
        if self.is_active:
            bg_color = (45, 40, 38)
            text_color = COLOR_TEXT
            pulse = (math.sin(self.glow_timer * 4) + 1) / 2
            border_color = lerp_color(COLOR_BORDER_LIGHT, COLOR_GOLD, pulse * 0.7)
        else:
            bg_color = COLOR_INPUT_BG
            text_color = COLOR_TEXT
            border_color = COLOR_BORDER_LIGHT
        
        # Draw outer dark border
        outer_rect = self.rect.inflate(4, 4)
        pygame.draw.rect(surface, COLOR_BORDER_DARK, outer_rect, border_radius=6)
        
        # Draw main background
        pygame.draw.rect(surface, bg_color, self.rect, border_radius=4)
        
        # Draw border
        pygame.draw.rect(surface, border_color, self.rect, 2, border_radius=4)
        
        # Set clipping
        old_clip = surface.get_clip()
        content_rect = pygame.Rect(self.rect.x + 5, self.rect.y + 2, self.rect.width - 10, self.rect.height - 4)
        surface.set_clip(content_rect)
        
        max_text_width = self.rect.width - 20
        
        # Draw text (LTR - left aligned)
        if self.text:
            display_text = "•" * len(self.text) if self.is_password else self.text
            text_surface = self.font.render(display_text, True, text_color)
            
            # Show rightmost portion if too long
            if text_surface.get_width() > max_text_width:
                offset = text_surface.get_width() - max_text_width
                text_surface = text_surface.subsurface((offset, 0, max_text_width, text_surface.get_height()))
            
            text_x = self.rect.x + 10
            text_y = self.rect.y + (self.rect.height - text_surface.get_height()) // 2
            surface.blit(text_surface, (text_x, text_y))
            
            # Draw cursor at the end
            if self.is_active and self.cursor_visible:
                cursor_x = text_x + min(text_surface.get_width(), max_text_width) + 2
                cursor_y = self.rect.y + 5
                pygame.draw.line(surface, COLOR_GOLD, 
                               (cursor_x, cursor_y), 
                               (cursor_x, cursor_y + self.rect.height - 10), 2)
        else:
            # Draw placeholder
            if not self.is_active and self.placeholder:
                placeholder_surface = self.font.render(self.placeholder, True, (100, 90, 80))
                text_x = self.rect.x + 10
                text_y = self.rect.y + (self.rect.height - placeholder_surface.get_height()) // 2
                surface.blit(placeholder_surface, (text_x, text_y))
            
            # Draw cursor when empty and active
            if self.is_active and self.cursor_visible:
                cursor_x = self.rect.x + 12
                cursor_y = self.rect.y + 5
                pygame.draw.line(surface, COLOR_GOLD, 
                               (cursor_x, cursor_y), 
                               (cursor_x, cursor_y + self.rect.height - 10), 2)
        
        surface.set_clip(old_clip)
    
    def update(self, dt: float):
        """Update cursor blink"""
        self.cursor_timer += dt
        if self.cursor_timer >= 500:
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0
        self.glow_timer += dt / 1000.0
            
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle keyboard and mouse events. Returns True if clicked."""
        if event.type == pygame.MOUSEBUTTONDOWN:
            was_active = self.is_active
            self.is_active = self.rect.collidepoint(event.pos)
            return self.is_active and not was_active
            
        if event.type == pygame.KEYDOWN and self.is_active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_v and (event.mod & pygame.KMOD_CTRL):
                # Paste from clipboard
                try:
                    from pygame import scrap
                    scrap.init()
                    clipboard = scrap.get(pygame.SCRAP_TEXT)
                    if clipboard:
                        self.text += clipboard.decode('utf-8').strip('\x00')
                except:
                    pass
            elif event.key not in (pygame.K_RETURN, pygame.K_TAB, pygame.K_ESCAPE):
                if event.unicode and event.unicode.isprintable():
                    if len(self.text) < self.max_length:
                        self.text += event.unicode
        return False


class ScrollableTextArea:
    """A scrollable text area for dialogue history with gothic noir styling"""
    
    def __init__(self, x: int, y: int, width: int, height: int, font: pygame.font.Font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.lines: List[Tuple[str, Tuple[int, int, int], bool]] = []  # (text, color, is_speaker_line)
        self.scroll_offset = 0
        self.line_height = font.get_height() + 5
        self.streaming_speaker = None
        self.streaming_text = ""
        self.streaming_color = COLOR_TEXT
        
    def add_message(self, speaker: str, message: str, color: Tuple[int, int, int]):
        """Add a message to the dialogue"""
        # Word wrap the message
        words = message.split(' ')
        current_line = f"{speaker}: "
        max_width = self.rect.width - 40
        is_first_line = True
        
        for word in words:
            test_line = current_line + word + " "
            if self.font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line.strip():
                    self.lines.append((current_line.strip(), color, is_first_line))
                    is_first_line = False
                current_line = "  " + word + " "  # Indent continuation
        
        if current_line.strip():
            self.lines.append((current_line.strip(), color, is_first_line))
        
        # Add blank line for spacing
        self.lines.append(("", color, False))
        
        # Auto-scroll to bottom
        self.scroll_to_bottom()
    
    def start_streaming(self, speaker: str, color: Tuple[int, int, int]):
        """Start streaming a new message"""
        self.streaming_speaker = speaker
        self.streaming_text = ""
        self.streaming_color = color
    
    def append_streaming(self, text: str):
        """Append text to the streaming message"""
        self.streaming_text += text
        self.scroll_to_bottom()
    
    def finish_streaming(self):
        """Finish streaming and add the complete message"""
        if self.streaming_speaker and self.streaming_text:
            self.add_message(self.streaming_speaker, self.streaming_text, self.streaming_color)
        self.streaming_speaker = None
        self.streaming_text = ""
        self.streaming_color = COLOR_TEXT
        
    def scroll_to_bottom(self):
        """Scroll to the bottom of the text"""
        max_visible_lines = (self.rect.height - 20) // self.line_height
        self.scroll_offset = max(0, len(self.lines) - max_visible_lines)
        
    def draw(self, surface: pygame.Surface):
        """Draw the text area with gothic styling (used as fallback)"""
        # Draw background
        pygame.draw.rect(surface, COLOR_PANEL, self.rect, border_radius=8)
        
        # Draw gothic frame
        pygame.draw.rect(surface, COLOR_BORDER_DARK, self.rect, 3, border_radius=8)
        inner_rect = self.rect.inflate(-4, -4)
        pygame.draw.rect(surface, COLOR_BORDER_LIGHT, inner_rect, 1, border_radius=6)
        
        # Draw inner shadow
        draw_inner_shadow(surface, self.rect, shadow_size=10, alpha=50)
        
        # Draw visible lines with RTL support and shadows
        y_offset = self.rect.y + 12
        max_y = self.rect.y + self.rect.height - 10
        
        # Draw existing lines
        for i in range(self.scroll_offset, len(self.lines)):
            if y_offset + self.line_height > max_y:
                break
            
            text, color, is_speaker_line = self.lines[i] if len(self.lines[i]) == 3 else (*self.lines[i], False)
            if text:
                # Reshape Persian text for RTL
                display_text = reshape_persian_text(text)
                
                # Draw shadow first
                shadow_surface = self.font.render(display_text, True, COLOR_SHADOW)
                text_surface = self.font.render(display_text, True, color)
                
                # Right-align the text
                text_x = self.rect.x + self.rect.width - text_surface.get_width() - 20
                surface.blit(shadow_surface, (text_x + 1, y_offset + 1))
                surface.blit(text_surface, (text_x, y_offset))
            y_offset += self.line_height
        
        # Draw streaming text if active
        if self.streaming_speaker and y_offset < max_y:
            streaming_full = f"{self.streaming_speaker}: {self.streaming_text}▌"
            display_text = reshape_persian_text(streaming_full)
            
            shadow_surface = self.font.render(display_text, True, COLOR_SHADOW)
            text_surface = self.font.render(display_text, True, self.streaming_color)
            
            text_x = self.rect.x + self.rect.width - text_surface.get_width() - 20
            surface.blit(shadow_surface, (text_x + 1, y_offset + 1))
            surface.blit(text_surface, (text_x, y_offset))
    
    def handle_event(self, event: pygame.event.Event):
        """Handle scroll events"""
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll_offset = max(0, min(
                    self.scroll_offset - event.y,
                    len(self.lines) - (self.rect.height - 20) // self.line_height
                ))


class CharacterPortrait:
    """Displays character portraits with emotion-based expressions and gothic styling"""
    
    def __init__(self, x: int, y: int, width: int, height: int):
        """Initialize portrait display"""
        self.rect = pygame.Rect(x, y, width, height)
        self.portraits = {}  # Cache: {suspect_id: {emotion: surface}}
        self.current_suspect = None
        self.current_emotion = "other"
        self.target_emotion = "other"
        
        # Fade animation
        self.fade_progress = 1.0  # 0.0 to 1.0 (1.0 = fully shown)
        self.fade_duration = 0.3  # seconds
        self.is_fading = False
        self.old_surface = None
        self.new_surface = None
        
        # Breathing animation
        self.breath_timer = 0.0
        self.breath_cycle = 4.0  # seconds for full cycle
        self.breath_intensity = 0.005  # 0.5% scale oscillation
        
        # Load all portraits
        self._load_all_portraits()
    
    def _load_all_portraits(self):
        """Load all emotion images for all suspects using Farsi filenames from database"""
        # Use database to get folder names and emotion mappings
        for suspect_id in range(1, 7):
            self.portraits[suspect_id] = {}
            
            # Get character folder from database
            try:
                folder = game_data.get_database().get_character_folder(suspect_id)
                emotion_mapping = game_data.get_emotion_mapping(suspect_id)
                
                # Load each emotion image using the Farsi filename from mapping
                for emotion_name, image_filename in emotion_mapping.items():
                    if emotion_name == "default":
                        continue  # Skip default entry
                    
                    try:
                        path = f"assets/{folder}/{image_filename}"
                        image = pygame.image.load(path)
                        # Scale with smoothscale for anti-aliasing
                        scaled = pygame.transform.smoothscale(image, (self.rect.width, self.rect.height))
                        # Store by image filename (without .jpg)
                        emotion_key = image_filename.replace(".jpg", "")
                        self.portraits[suspect_id][emotion_key] = scaled
                        print(f"  ✓ Loaded: {path}")
                    except Exception as e:
                        print(f"  ⚠ Could not load: {path} - {e}")
                        # Create placeholder
                        placeholder = pygame.Surface((self.rect.width, self.rect.height))
                        placeholder.fill(COLOR_PANEL)
                        emotion_key = image_filename.replace(".jpg", "")
                        self.portraits[suspect_id][emotion_key] = placeholder
                
                # Also load default image
                default_filename = emotion_mapping.get("default", "other.jpg")
                try:
                    path = f"assets/{folder}/{default_filename}"
                    image = pygame.image.load(path)
                    scaled = pygame.transform.smoothscale(image, (self.rect.width, self.rect.height))
                    default_key = default_filename.replace(".jpg", "")
                    self.portraits[suspect_id][default_key] = scaled
                    print(f"  ✓ Loaded default: {path}")
                except:
                    pass
                    
            except Exception as e:
                print(f"⚠ Failed to load portraits for suspect {suspect_id}: {e}")
                # Create placeholder
                placeholder = pygame.Surface((self.rect.width, self.rect.height))
                placeholder.fill(COLOR_PANEL)
                self.portraits[suspect_id] = {"default": placeholder}
    
    def set_suspect_and_emotion(self, suspect_id: int, image_filename: str, immediate: bool = False):
        """Set suspect and emotion using image filename, optionally with fade animation"""
        if suspect_id not in self.portraits:
            return
        
        # Convert image filename to emotion key (remove .jpg extension)
        emotion_key = image_filename.replace(".jpg", "")
        
        # Validate emotion key exists for this suspect
        if emotion_key not in self.portraits[suspect_id]:
            print(f"⚠ Emotion key '{emotion_key}' not found for suspect {suspect_id}, using first available")
            # Use first available emotion as fallback
            if self.portraits[suspect_id]:
                emotion_key = list(self.portraits[suspect_id].keys())[0]
            else:
                return
        
        # Check if we need to change
        if self.current_suspect == suspect_id and self.current_emotion == emotion_key:
            return  # No change needed
        
        if immediate or self.current_suspect != suspect_id:
            # Immediate change (no fade) when switching suspects
            self.current_suspect = suspect_id
            self.current_emotion = emotion_key
            self.target_emotion = emotion_key
            self.is_fading = False
            self.fade_progress = 1.0
        else:
            # Fade animation for emotion change on same suspect
            self.target_emotion = emotion_key
            self.is_fading = True
            self.fade_progress = 0.0
            self.old_surface = self.portraits[suspect_id][self.current_emotion].copy()
            self.new_surface = self.portraits[suspect_id][emotion_key].copy()
    
    def update(self, dt: float):
        """Update fade animation and breathing"""
        # Update fade animation
        if self.is_fading:
            self.fade_progress += dt / 1000.0 / self.fade_duration
            if self.fade_progress >= 1.0:
                self.fade_progress = 1.0
                self.is_fading = False
                self.current_emotion = self.target_emotion
                self.old_surface = None
                self.new_surface = None
        
        # Update breathing animation
        self.breath_timer += dt / 1000.0
        if self.breath_timer >= self.breath_cycle:
            self.breath_timer -= self.breath_cycle
    
    def draw(self, surface: pygame.Surface):
        """Draw the portrait with gothic noir styling"""
        # Calculate breathing scale
        breath_phase = (self.breath_timer / self.breath_cycle) * 2 * math.pi
        breath_scale = 1.0 + math.sin(breath_phase) * self.breath_intensity
        
        # Draw drop shadow behind portrait
        shadow_offset = 8
        shadow_rect = pygame.Rect(
            self.rect.x + shadow_offset, 
            self.rect.y + shadow_offset,
            self.rect.width, 
            self.rect.height
        )
        shadow_surface = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        shadow_surface.fill((0, 0, 0, 80))
        surface.blit(shadow_surface, shadow_rect)
        
        if self.current_suspect is None:
            # Draw placeholder with "Select a suspect" message
            pygame.draw.rect(surface, COLOR_PANEL, self.rect, border_radius=5)
            
            # Gothic frame
            pygame.draw.rect(surface, COLOR_BORDER_DARK, self.rect, 4, border_radius=5)
            inner_rect = self.rect.inflate(-8, -8)
            pygame.draw.rect(surface, COLOR_GOLD, inner_rect, 2, border_radius=3)
            
            # Draw helper text with shadow
            font = pygame.font.Font("assets/Vazirmatn.ttf", 24) if Path("assets/Vazirmatn.ttf").exists() else pygame.font.Font(None, 24)
            draw_text_with_shadow(surface, "یک مظنون انتخاب کنید", font, COLOR_TEXT, 
                                 self.rect.center, shadow_offset=2, center=True)
            return
        
        # Calculate scaled dimensions for breathing effect
        scaled_width = int(self.rect.width * breath_scale)
        scaled_height = int(self.rect.height * breath_scale)
        offset_x = (self.rect.width - scaled_width) // 2
        offset_y = (self.rect.height - scaled_height) // 2
        
        if self.is_fading and self.old_surface and self.new_surface:
            # Draw fade transition with breathing
            temp_surface = pygame.Surface((self.rect.width, self.rect.height))
            
            # Scale old surface
            old_scaled = pygame.transform.smoothscale(self.old_surface, (scaled_width, scaled_height))
            temp_surface.fill(COLOR_PANEL)
            temp_surface.blit(old_scaled, (offset_x, offset_y))
            
            # Scale and blend new surface
            new_scaled = pygame.transform.smoothscale(self.new_surface, (scaled_width, scaled_height))
            new_scaled.set_alpha(int(255 * self.fade_progress))
            temp_surface.blit(new_scaled, (offset_x, offset_y))
            
            surface.blit(temp_surface, (self.rect.x, self.rect.y))
        else:
            # Draw current emotion with breathing
            if self.current_suspect in self.portraits:
                portrait = self.portraits[self.current_suspect][self.current_emotion]
                scaled_portrait = pygame.transform.smoothscale(portrait, (scaled_width, scaled_height))
                surface.blit(scaled_portrait, (self.rect.x + offset_x, self.rect.y + offset_y))
        
        # Draw gothic frame border (dark outer, gold inner)
        pygame.draw.rect(surface, COLOR_BORDER_DARK, self.rect, 5, border_radius=3)
        inner_rect = self.rect.inflate(-6, -6)
        pygame.draw.rect(surface, COLOR_GOLD, inner_rect, 2, border_radius=2)


class NotebookPanel:
    """Multi-page notebook panel for player notes - book-style with two-page spread"""
    
    def __init__(self, x: int, y: int, width: int, height: int, font, game_state: GameState):
        """Initialize notebook panel"""
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.game_state = game_state
        
        # Book-style: current_spread_index is which pair of pages we're viewing
        # Spread 0 = pages 0,1 (days 1,2), Spread 1 = pages 2,3 (days 3,4), etc.
        self.current_spread_index = 0
        
        # Track which side is being edited (0 = right/odd, 1 = left/even)
        self.active_side = 0  # 0 = right page (odd days), 1 = left page (even days)
        
        # Text input area for current editable page
        self.text_lines = []  # List of text lines being edited
        self.cursor_line = 0
        self.cursor_pos = 0
        self.max_chars_per_line = 12  # Max chars before auto-wrap
        self.max_lines = 15
        
        # Navigation buttons - positioned at bottom corners
        button_y = y + height - 45
        button_height = 35
        button_width = int(width * 0.20)
        self.prev_button = Button(x + 15, button_y, button_width, button_height, "قبلی", FONT_FARSI_SMALL, COLOR_BUTTON)
        self.next_button = Button(x + width - button_width - 15, button_y, button_width, button_height, "بعدی", FONT_FARSI_SMALL, COLOR_BUTTON)
        
        # Scroll offset for reading long pages
        self.scroll_offset = 0
        self.line_height = 25
        
        self._load_current_spread()
    
    def _get_right_page_index(self):
        """Get the page index for the right side (odd days: 1, 3, 5...)"""
        return self.current_spread_index * 2
    
    def _get_left_page_index(self):
        """Get the page index for the left side (even days: 2, 4, 6...)"""
        return self.current_spread_index * 2 + 1
    
    def _get_active_page_index(self):
        """Get the currently active (editable) page index"""
        if self.active_side == 0:
            return self._get_right_page_index()
        else:
            return self._get_left_page_index()
    
    def _load_current_spread(self):
        """Load the current spread's editable page content into text_lines"""
        # Find which page is the current day and make it active
        total_pages = self.game_state.get_total_pages()
        right_idx = self._get_right_page_index()
        left_idx = self._get_left_page_index()
        
        # Determine which side should be active based on current day
        right_page = self.game_state.get_page_by_index(right_idx) if right_idx < total_pages else None
        left_page = self.game_state.get_page_by_index(left_idx) if left_idx < total_pages else None
        
        # Default to right side
        self.active_side = 0
        active_page = right_page
        
        # Check if left side is the current day
        if left_page:
            left_day = left_page.get("day")
            if left_day == self.game_state.current_day or left_day == "Final":
                self.active_side = 1
                active_page = left_page
        
        # Check if right side is the current day (takes priority)
        if right_page:
            right_day = right_page.get("day")
            if right_day == self.game_state.current_day or right_day == "Final":
                self.active_side = 0
                active_page = right_page
        
        # Load content from active page
        if active_page:
            content = active_page.get("content", "")
            if content:
                self.text_lines = content.split('\n')
            else:
                self.text_lines = [""]
        else:
            self.text_lines = [""]
        
        self.cursor_line = 0
        self.cursor_pos = 0
        self.scroll_offset = 0
    
    def _save_current_page(self):
        """Save the current text_lines back to game state"""
        content = '\n'.join(self.text_lines)
        page_index = self._get_active_page_index()
        if page_index < self.game_state.get_total_pages():
            page = self.game_state.get_page_by_index(page_index)
            page["content"] = content
    
    def _is_page_editable(self, page_index: int) -> bool:
        """Check if a specific page is editable (current day or final page)"""
        if page_index >= self.game_state.get_total_pages():
            return False
        page = self.game_state.get_page_by_index(page_index)
        page_day = page.get("day")
        return page_day == self.game_state.current_day or page_day == "Final"
    
    def _is_current_page_editable(self) -> bool:
        """Check if the currently active page is editable"""
        return self._is_page_editable(self._get_active_page_index())
    
    def get_page_content(self, page_index: int) -> list:
        """Get the content lines for a specific page"""
        if page_index >= self.game_state.get_total_pages():
            return []
        page = self.game_state.get_page_by_index(page_index)
        content = page.get("content", "")
        if content:
            return content.split('\n')
        return []
    
    def go_to_spread_containing_page(self, page_index: int):
        """Navigate to the spread containing the given page index"""
        self._save_current_page()
        self.current_spread_index = page_index // 2
        self._load_current_spread()
    
    def go_to_latest_page(self):
        """Go to the spread containing the latest page"""
        total = self.game_state.get_total_pages()
        if total > 0:
            self.go_to_spread_containing_page(total - 1)
    
    def handle_event(self, event) -> bool:
        """Handle input events for the notebook"""
        total_pages = self.game_state.get_total_pages()
        max_spread = (total_pages - 1) // 2 if total_pages > 0 else 0
        
        # Navigation buttons - turn pages by 2 (one spread)
        if self.prev_button.handle_event(event):
            if self.current_spread_index > 0:
                self._save_current_page()
                self.current_spread_index -= 1
                self._load_current_spread()
            return True
        
        if self.next_button.handle_event(event):
            if self.current_spread_index < max_spread:
                self._save_current_page()
                self.current_spread_index += 1
                self._load_current_spread()
            return True
        
        # Only handle text input if page is editable
        if not self._is_current_page_editable():
            return False
        
        # Mouse click to position cursor - check which side was clicked
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                # Determine which half was clicked
                mid_x = self.rect.x + self.rect.width // 2
                clicked_left = event.pos[0] < mid_x
                
                # Check if the clicked side is editable
                if clicked_left:
                    left_idx = self._get_left_page_index()
                    if self._is_page_editable(left_idx):
                        if self.active_side != 1:
                            self._save_current_page()
                            self.active_side = 1
                            self._load_current_spread()
                else:
                    right_idx = self._get_right_page_index()
                    if self._is_page_editable(right_idx):
                        if self.active_side != 0:
                            self._save_current_page()
                            self.active_side = 0
                            self._load_current_spread()
                
                # Position cursor
                if self.text_lines:
                    content_y = self.rect.top + 60
                    self.cursor_line = min(len(self.text_lines) - 1, 
                                          (event.pos[1] - content_y) // self.line_height)
                    self.cursor_line = max(0, self.cursor_line)
                return True
        
        # Text input
        if event.type == pygame.KEYDOWN:
            if not self.rect.collidepoint(pygame.mouse.get_pos()):
                return False  # Only handle if mouse is over notebook
            
            if event.key == pygame.K_RETURN:
                # New line
                if len(self.text_lines) < self.max_lines:
                    current_line = self.text_lines[self.cursor_line]
                    before = current_line[:self.cursor_pos]
                    after = current_line[self.cursor_pos:]
                    self.text_lines[self.cursor_line] = before
                    self.text_lines.insert(self.cursor_line + 1, after)
                    self.cursor_line += 1
                    self.cursor_pos = 0
                    self._save_current_page()
                return True
            
            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_pos > 0:
                    # Delete character before cursor
                    line = self.text_lines[self.cursor_line]
                    self.text_lines[self.cursor_line] = line[:self.cursor_pos-1] + line[self.cursor_pos:]
                    self.cursor_pos -= 1
                    self._save_current_page()
                elif self.cursor_line > 0:
                    # Merge with previous line
                    prev_line = self.text_lines[self.cursor_line - 1]
                    current_line = self.text_lines[self.cursor_line]
                    self.cursor_pos = len(prev_line)
                    self.text_lines[self.cursor_line - 1] = prev_line + current_line
                    del self.text_lines[self.cursor_line]
                    self.cursor_line -= 1
                    self._save_current_page()
                return True
            
            elif event.key == pygame.K_UP:
                if self.cursor_line > 0:
                    self.cursor_line -= 1
                    self.cursor_pos = min(self.cursor_pos, len(self.text_lines[self.cursor_line]))
                return True
            
            elif event.key == pygame.K_DOWN:
                if self.cursor_line < len(self.text_lines) - 1:
                    self.cursor_line += 1
                    self.cursor_pos = min(self.cursor_pos, len(self.text_lines[self.cursor_line]))
                return True
            
            elif event.key == pygame.K_LEFT:
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
                return True
            
            elif event.key == pygame.K_RIGHT:
                if self.cursor_pos < len(self.text_lines[self.cursor_line]):
                    self.cursor_pos += 1
                return True
            
            elif event.unicode and event.unicode.isprintable():
                # Add character with auto-wrap
                line = self.text_lines[self.cursor_line]
                if len(line) < self.max_chars_per_line:
                    self.text_lines[self.cursor_line] = line[:self.cursor_pos] + event.unicode + line[self.cursor_pos:]
                    self.cursor_pos += 1
                else:
                    # Line is full, wrap to next line
                    if self.cursor_line < len(self.text_lines) - 1:
                        self.cursor_line += 1
                        self.cursor_pos = 0
                        # Insert character at start of next line
                        next_line = self.text_lines[self.cursor_line]
                        self.text_lines[self.cursor_line] = event.unicode + next_line
                        self.cursor_pos = 1
                    elif len(self.text_lines) < self.max_lines:
                        # Create new line
                        self.text_lines.append(event.unicode)
                        self.cursor_line += 1
                        self.cursor_pos = 1
                self._save_current_page()
                return True
        
        # Scroll wheel
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll_offset = max(0, min(
                    self.scroll_offset - event.y,
                    max(0, len(self.text_lines) - 15)
                ))
                return True
        
        return False
    
    def draw(self, surface):
        """Draw the notebook panel - placeholder, actual drawing done by Game._draw_notebook_with_background"""
        # This method exists for compatibility but the actual book-style drawing
        # is handled by Game._draw_notebook_with_background()
        pass


class DetectiveGame:
    """Main game class"""
    
    def __init__(self):
        """Initialize the game"""
        global SCREEN_WIDTH, SCREEN_HEIGHT
        
        # Fullscreen state
        self.windowed_size = (1280, 720)  # Default windowed size
        
        # Start in fullscreen by default
        self.fullscreen = True
        display_info = pygame.display.Info()
        SCREEN_WIDTH = display_info.current_w
        SCREEN_HEIGHT = display_info.current_h
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        pygame.display.set_caption("AI Detective - قتل گدای بزرگ")
        
        # Enable Unicode input for Farsi text
        pygame.key.set_repeat(500, 50)  # Enable key repeat
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Game state management
        self.game_state = GameState()
        self.game_state.load()  # Load existing save if present
        
        # Game state
        self.state = "loading"  # loading, menu, intro, playing, suspect_selection, accusation, win, lose
        self.current_suspect = 1
        self.current_emotion = "other"  # Current emotion being displayed
        self.day_started = False  # Track if player has selected suspect for current day
        self.ai_thinking = False
        self.ai_response_ready = False
        self.ai_response = ""
        
        # Load menu background
        try:
            self.menu_background = pygame.image.load("assets/Menu.jpg")
            self.menu_background = pygame.transform.scale(self.menu_background, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except:
            self.menu_background = None
            print("⚠ Could not load Menu.jpg")
        
        # Load UI asset images
        try:
            self.notebook_closed_img = pygame.image.load("assets/اشیا/دفترچه بسته.png")
        except:
            self.notebook_closed_img = None
            print("⚠ Could not load دفترچه بسته.png")
        
        try:
            self.notebook_open_img = pygame.image.load("assets/اشیا/دفترچه باز.png")
        except:
            self.notebook_open_img = None
            print("⚠ Could not load دفترچه باز.png")
        
        try:
            self.file_open_img = pygame.image.load("assets/اشیا/پرونده باز.png")
        except:
            self.file_open_img = None
            print("⚠ Could not load پرونده باز.png")
        
        try:
            self.case_files_icon_img = pygame.image.load("assets/اشیا/پرونده ها.png")
        except:
            self.case_files_icon_img = None
            print("⚠ Could not load پرونده ها.png")
        
        try:
            self.clock1_img = pygame.image.load("assets/اشیا/ساعت 1.png")
        except:
            self.clock1_img = None
            print("⚠ Could not load ساعت 1.png")
        
        try:
            self.clock2_img = pygame.image.load("assets/اشیا/ساعت 2.png")
        except:
            self.clock2_img = None
            print("⚠ Could not load ساعت 2.png")
        
        # Load door closed image for end day button
        try:
            self.door_closed_img = pygame.image.load("assets/اشیا/در بسته.png")
        except:
            self.door_closed_img = None
            print("⚠ Could not load در بسته.png")
        
        # Load intro background (for intro and load_recap states - warm up pages)
        try:
            intro_bg = pygame.image.load("assets/intro.jpg")
            intro_bg = pygame.transform.scale(intro_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
            self.intro_background = blur_surface(intro_bg, amount=6)  # Apply blur
        except:
            self.intro_background = None
            print("⚠ Could not load intro.jpg")
        
        # Load accusation background (for accusation state)
        try:
            accusation_bg = pygame.image.load("assets/accusation.jpg")
            accusation_bg = pygame.transform.scale(accusation_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
            self.accusation_background = blur_surface(accusation_bg, amount=6)  # Apply blur
        except:
            self.accusation_background = None
            print("⚠ Could not load accusation.jpg")
        
        # Load win/lose end screen backgrounds
        try:
            self.win_img = pygame.image.load("assets/پایان/برد.jpg")
        except:
            self.win_img = None
            print("⚠ Could not load برد.jpg")
        
        try:
            self.lose_img = pygame.image.load("assets/پایان/باخت.jpg")
        except:
            self.lose_img = None
            print("⚠ Could not load باخت.jpg")
        
        # Load custom cursor
        try:
            cursor_surface = pygame.image.load("assets/اشیا/قلم.png").convert_alpha()
            cursor_surface = pygame.transform.smoothscale(cursor_surface, (32, 32))
            self.custom_cursor = pygame.cursors.Cursor((0, 0), cursor_surface)
            pygame.mouse.set_cursor(self.custom_cursor)
        except Exception as e:
            self.custom_cursor = None
            print(f"⚠ Could not load custom cursor: {e}")
        
        # Initialize fonts
        global FONT_LARGE, FONT_MEDIUM, FONT_SMALL, FONT_FARSI, FONT_FARSI_SMALL
        
        # Try to find a system font that supports Farsi/Arabic
        farsi_font_names = [
            'Vazirmatn',  # If assets/Vazirmatn.ttf exists
            'Arial',
            'Tahoma',
            'Microsoft Sans Serif',
            'Segoe UI',
            'DejaVu Sans'
        ]
        
        farsi_font_path = None
        
        # First try the custom font in assets
        if Path("assets/Vazirmatn.ttf").exists():
            farsi_font_path = "assets/Vazirmatn.ttf"
        else:
            # Try system fonts
            for font_name in farsi_font_names:
                font_path = pygame.font.match_font(font_name)
                if font_path:
                    farsi_font_path = font_path
                    print(f"Using system font for Farsi: {font_name}")
                    break
        
        try:
            FONT_LARGE = pygame.font.Font(None, 48)
            FONT_MEDIUM = pygame.font.Font(None, 32)
            FONT_SMALL = pygame.font.Font(None, 24)
            
            if farsi_font_path:
                FONT_FARSI = pygame.font.Font(farsi_font_path, 30)
                FONT_FARSI_SMALL = pygame.font.Font(farsi_font_path, 24)
                print(f"✓ Loaded Farsi font from: {farsi_font_path}")
            else:
                # Fallback to system default (will show boxes for Farsi but at least won't crash)
                FONT_FARSI = pygame.font.SysFont('tahoma,arial,segoeui', 30)
                FONT_FARSI_SMALL = pygame.font.SysFont('tahoma,arial,segoeui', 24)
                print("⚠ Using fallback font - Farsi text may not display correctly")
                
        except Exception as e:
            print(f"Font loading error: {e}")
            # Last resort fallback
            FONT_LARGE = pygame.font.Font(None, 48)
            FONT_MEDIUM = pygame.font.Font(None, 32)
            FONT_SMALL = pygame.font.Font(None, 24)
            FONT_FARSI = pygame.font.Font(None, 30)
            FONT_FARSI_SMALL = pygame.font.Font(None, 24)
        
        # Initialize AI engine (in a separate thread to not block)
        self.ai_engine = None
        self.ai_init_complete = False
        
        # Animation timer for global effects
        self.animation_timer = 0.0
        
        # Hovered card tracking for suspect selection
        self.hovered_card_index = -1
        self.card_hover_progress = [0.0] * 6  # One for each suspect card
        
        # Music toggle state
        self.music_enabled = True
        
        # Intro streaming state
        self.intro_text = ""
        self.intro_streaming = False
        self.intro_complete = False
        
        # Load recap streaming state (for loading saved games)
        self.load_recap_text = ""
        self.load_recap_streaming = False
        self.load_recap_complete = False
        
        self.init_ai_thread = threading.Thread(target=self._init_ai_engine)
        self.init_ai_thread.daemon = True
        self.init_ai_thread.start()
        
        # Create UI elements
        self._create_ui_elements()
        
        # Create suspect buttons for selection screen
        suspect_names = [
            "أهنگر",
            "راهبه",
            "تاجر",
            "سرباز",
            "پسرک (لوییس)",
            "آشپز"
        ]
        
        self.suspect_buttons = []
        for i, name in enumerate(suspect_names):
            button = Button(0, 0, 400, 100, name, FONT_FARSI_SMALL, COLOR_BUTTON)
            self.suspect_buttons.append(button)
        
        # Load character thumbnails for selection screen
        self.character_thumbnails = []
        thumbnail_files = [
            "assets/انتخاب کاراکتر/آهنگر.png",
            "assets/انتخاب کاراکتر/راهبه.png",
            "assets/انتخاب کاراکتر/تاجر.png",
            "assets/انتخاب کاراکتر/سرباز.png",
            "assets/انتخاب کاراکتر/کودک.png",
            "assets/انتخاب کاراکتر/آشپز.png"
        ]
        for thumb_path in thumbnail_files:
            try:
                thumb = pygame.image.load(thumb_path)
                self.character_thumbnails.append(thumb)
            except Exception as e:
                print(f"⚠ Could not load thumbnail: {thumb_path} - {e}")
                self.character_thumbnails.append(None)
        
        # Add welcome message
        self.dialogue_area.add_message(
            "کارآگاه",
            "پرونده: قتل گدای بزرگ. شش مظنون داریم. تحقیقات خود را با انتخاب یک مظنون و پرسیدن سوالات آغاز کنید.",
            COLOR_TEXT
        )
    
    def _create_settings_ui(self):
        """Create settings screen UI elements"""
        global FONT_FARSI, FONT_FARSI_SMALL, FONT_SMALL
        
        # Initialize status message
        if not hasattr(self, 'settings_status_message'):
            self.settings_status_message = ""
        
        # Settings panel dimensions
        panel_width = min(700, SCREEN_WIDTH - 100)
        panel_height = min(550, SCREEN_HEIGHT - 100)
        panel_x = (SCREEN_WIDTH - panel_width) // 2
        panel_y = (SCREEN_HEIGHT - panel_height) // 2
        self.settings_panel_rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        
        # Load current settings
        current_settings = ai_settings.load_settings()
        
        # Input field dimensions
        input_width = panel_width - 60
        input_height = 35
        input_x = panel_x + 30
        label_x = panel_x + panel_width - 30  # Right-aligned for RTL
        
        # Starting Y position for form elements
        form_y = panel_y + 80
        field_spacing = 65
        
        # API Mode Toggle Button
        self.settings_api_toggle = Button(
            input_x, form_y, input_width, 40,
            "✓ استفاده از API" if current_settings.get("isApiAvailable", False) else "✗ استفاده از Ollama",
            FONT_FARSI_SMALL,
            COLOR_BUTTON_ACTIVE if current_settings.get("isApiAvailable", False) else COLOR_BUTTON
        )
        form_y += field_spacing
        
        # Base URL input
        self.settings_base_url = SettingsTextBox(
            input_x, form_y, input_width, input_height, FONT_SMALL, "https://api.example.com/v1"
        )
        self.settings_base_url.text = current_settings.get("openai_base_url", "")
        form_y += field_spacing
        
        # API Key input
        self.settings_api_key = SettingsTextBox(
            input_x, form_y, input_width, input_height, FONT_SMALL, "sk-..."
        )
        self.settings_api_key.text = current_settings.get("openai_api_key", "")
        self.settings_api_key.is_password = True
        form_y += field_spacing
        
        # Model name input
        self.settings_model = SettingsTextBox(
            input_x, form_y, input_width, input_height, FONT_SMALL, "gpt-4 / gemini-2.0-flash / ..."
        )
        self.settings_model.text = current_settings.get("openai_model", "")
        form_y += field_spacing
        
        # Ollama model name input (for non-API mode)
        self.settings_ollama_model = SettingsTextBox(
            input_x, form_y, input_width, input_height, FONT_SMALL, "gemma3n"
        )
        self.settings_ollama_model.text = current_settings.get("model", "gemma3n")
        form_y += field_spacing + 10
        
        # Save button
        btn_width = 120
        self.settings_save_button = Button(
            panel_x + panel_width // 2 - btn_width - 10, form_y,
            btn_width, 45, "ذخیره", FONT_FARSI, COLOR_BUTTON_ACTIVE
        )
        
        # Back button
        self.settings_back_button = Button(
            panel_x + panel_width // 2 + 10, form_y,
            btn_width, 45, "بازگشت", FONT_FARSI, COLOR_BUTTON
        )
        
        # Track API mode state for the toggle
        self.settings_api_mode = current_settings.get("isApiAvailable", False)
        
    def _init_ai_engine(self):
        """Initialize AI engine in background thread"""
        try:
            print("Initializing AI engine...")
            self.ai_engine = AIDetectiveEngine()
            self.ai_init_complete = True
            self.state = "menu"  # Switch to menu when ready
            print("AI engine ready!")
            # Note: Warm-up is now triggered when player clicks Start
            # to determine if it's a new game (intro) or load (recap)
            
        except Exception as e:
            print(f"Error initializing AI: {e}")
            self.ai_init_complete = False
    
    def _start_intro_streaming(self):
        """Start the intro generation for warming up model on new game"""
        self.intro_text = ""
        self.intro_streaming = True
        self.intro_complete = False
        
        def on_intro_token(token):
            self.intro_text += token
        
        def generate_intro():
            import time
            try:
                # Wait for AI engine to be ready (max 10 seconds)
                wait_time = 0
                while not self.ai_engine and wait_time < 10:
                    time.sleep(0.5)
                    wait_time += 0.5
                
                if not self.ai_engine:
                    raise Exception("AI engine not initialized")
                
                # Try to generate intro (single attempt with implicit timeout from streaming)
                print("Attempting to generate intro...")
                self.ai_engine.generate_game_intro(stream_callback=on_intro_token)
                
                if self.intro_text:
                    self.intro_complete = True
                    self.intro_streaming = False
                    self.game_state.case_files_text = self.intro_text
                    self.game_state.save()
                    print("Story intro generated successfully!")
                else:
                    raise Exception("No intro text generated")
                    
            except Exception as e:
                print(f"Failed to generate intro: {e}")
                print("Using fallback intro text...")
                self._use_fallback_intro()
        
        threading.Thread(target=generate_intro, daemon=True).start()
    
    def _use_fallback_intro(self):
        """Use the fallback intro text"""
        self.intro_streaming = False
        self.intro_complete = True
        self.intro_text = """در اتاق بازجویی سرد و تاریک، شش چهره مرموز نشسته‌اند. لباس‌های قرون وسطایی‌شان با دیوارهای مدرن تضاد عجیبی دارد.

هشتصد سال پیش، در مدجوگوریه، گدایی محبوب به قتل رسید. حالا، به طرز غیرقابل توضیحی، شش مظنون در واشنگتن زنده شده‌اند.

آهنگر، راهبه، تاجر، سرباز، پسرک، و آشپز - همه منتظر سوالات شما هستند. یکی از آنها قاتل است.

زمان آن رسیده که حقیقت را کشف کنید."""
        self.game_state.case_files_text = self.intro_text
        self.game_state.save()
    
    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode"""
        global SCREEN_WIDTH, SCREEN_HEIGHT
        
        self.fullscreen = not self.fullscreen
        
        if self.fullscreen:
            # Get display info for fullscreen resolution
            display_info = pygame.display.Info()
            SCREEN_WIDTH = display_info.current_w
            SCREEN_HEIGHT = display_info.current_h
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        else:
            # Restore windowed size
            SCREEN_WIDTH = self.windowed_size[0]
            SCREEN_HEIGHT = self.windowed_size[1]
            self.screen = pygame.display.set_mode(self.windowed_size)
        
        # Recreate UI elements with new screen size
        self._create_ui_elements()
        
        # Rescale menu background if it exists
        if self.menu_background:
            try:
                original_bg = pygame.image.load("assets/Menu.jpg")
                self.menu_background = pygame.transform.scale(original_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
            except:
                pass
        
        # Rescale intro background if it exists
        if self.intro_background:
            try:
                intro_bg = pygame.image.load("assets/intro.jpg")
                intro_bg = pygame.transform.scale(intro_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
                self.intro_background = blur_surface(intro_bg, amount=6)
            except:
                pass
        
        # Rescale accusation background if it exists
        if self.accusation_background:
            try:
                accusation_bg = pygame.image.load("assets/accusation.jpg")
                accusation_bg = pygame.transform.scale(accusation_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
                self.accusation_background = blur_surface(accusation_bg, amount=6)
            except:
                pass
        
        # Reapply custom cursor after display mode change
        if self.custom_cursor:
            pygame.mouse.set_cursor(self.custom_cursor)
        
        print(f"Fullscreen: {self.fullscreen}, Resolution: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    
    def _end_day(self):
        """End the current day and advance to next day"""
        # Save current notebook page
        self.notebook_panel._save_current_page()
        
        # Advance day in game state
        new_day = self.game_state.advance_day()
        
        # Reset all chat histories
        if self.ai_engine:
            self.ai_engine.reset_all_chats()
        
        # Clear dialogue area
        self.dialogue_area.lines = []
        
        # Save game state
        self.game_state.save()
        
        # Navigate notebook to new page
        self.notebook_panel.go_to_latest_page()
        
        # Reset day started flag
        self.day_started = False
        
        # Transition to suspect selection screen
        self.state = "suspect_selection"
        
        print(f"Advanced to Day {new_day}")
            
    def _create_ui_elements(self):
        """Create all UI elements with responsive sizing"""
        # Menu buttons
        self.menu_start_button = Button(
            SCREEN_WIDTH // 2 - 150,
            SCREEN_HEIGHT // 2 - 50,
            300,
            60,
            "شروع بازی",
            FONT_FARSI,
            COLOR_BUTTON
        )
        # Delete save button - color depends on whether save exists
        import os
        delete_color = COLOR_ACCENT if os.path.exists("savegame.json") else COLOR_PANEL
        self.menu_delete_save_button = Button(
            SCREEN_WIDTH // 2 - 150,
            SCREEN_HEIGHT // 2 + 30,
            300,
            50,
            "حذف ذخیره",
            FONT_FARSI,
            delete_color
        )
        
        # Music toggle button (green when on)
        self.menu_music_button = Button(
            SCREEN_WIDTH // 2 - 150,
            SCREEN_HEIGHT // 2 + 95,
            145,
            50,
            "🎵 موسیقی",
            FONT_FARSI_SMALL,
            (60, 100, 70)  # Muted green for "on" state
        )
        
        # Credits button
        self.menu_credits_button = Button(
            SCREEN_WIDTH // 2 + 5,
            SCREEN_HEIGHT // 2 + 95,
            145,
            50,
            "درباره بازی",
            FONT_FARSI_SMALL,
            COLOR_BUTTON
        )
        
        # Settings button (AI settings)
        self.menu_settings_button = Button(
            SCREEN_WIDTH // 2 - 150,
            SCREEN_HEIGHT // 2 + 160,
            300,
            50,
            "⚙️ تنظیمات",
            FONT_FARSI_SMALL,
            COLOR_BUTTON
        )
        
        self.menu_exit_button = Button(
            SCREEN_WIDTH // 2 - 150,
            SCREEN_HEIGHT // 2 + 225,
            300,
            50,
            "خروج",
            FONT_FARSI,
            COLOR_BUTTON
        )
        
        # Settings screen UI elements
        self._create_settings_ui()
        
        # Credits back button
        self.credits_back_button = Button(
            SCREEN_WIDTH // 2 - 100,
            SCREEN_HEIGHT - 80,
            200,
            50,
            "بازگشت",
            FONT_FARSI,
            COLOR_BUTTON
        )
        
        # Intro skip button
        self.intro_skip_button = Button(
            SCREEN_WIDTH - 150,
            SCREEN_HEIGHT - 60,
            120,
            40,
            "رد شدن",
            FONT_FARSI_SMALL,
            COLOR_BUTTON
        )
        
        # Character portrait (LEFT 2/3 of screen - large visual novel style)
        portrait_width = int(SCREEN_WIDTH * 0.55)
        portrait_x = int(SCREEN_WIDTH * 0.05)  # 5% from left
        portrait_y = 80
        portrait_height = SCREEN_HEIGHT - portrait_y - 20  # Extend to bottom with 20px margin
        self.character_portrait = CharacterPortrait(
            portrait_x,
            portrait_y,
            portrait_width,
            portrait_height
        )
        
        # Notebook panel (POPUP - centered, initially hidden)
        notebook_width = int(SCREEN_WIDTH * 0.6)
        notebook_height = int(SCREEN_HEIGHT * 0.7)
        notebook_x = (SCREEN_WIDTH - notebook_width) // 2
        notebook_y = (SCREEN_HEIGHT - notebook_height) // 2
        self.notebook_panel = NotebookPanel(
            notebook_x,
            notebook_y,
            notebook_width,
            notebook_height,
            FONT_SMALL,
            self.game_state
        )
        self.notebook_visible = False  # Notebook popup state
        self.case_files_visible = False  # Case files popup state
        self.case_files_scroll = 0  # Scroll offset for case files text
        self.credits_scroll = 0  # Scroll offset for credits/about page
        
        # Set sample intro text for debugging if not already set
        if not self.game_state.case_files_text:
            self.game_state.case_files_text = """در اتاق بازجویی سرد و تاریک، شش چهره مرموز نشسته‌اند. لباس‌های قرون وسطایی‌شان با دیوارهای مدرن تضاد عجیبی دارد.

هشتصد سال پیش، در مدجوگوریه، گدایی محبوب به قتل رسید. حالا، به طرز غیرقابل توضیحی، شش مظنون در واشنگتن زنده شده‌اند.

آهنگر، راهبه، تاجر، سرباز، پسرک، و آشپز - همه منتظر سوالات شما هستند. یکی از آنها قاتل است.

زمان آن رسیده که حقیقت را کشف کنید.

مظنونان:

۱. آهنگر (گارون) - سازنده اسلحه، چاقوی قتل شبیه کار اوست. مردی قوی و ساکت که رازهایی در دل دارد.

۲. راهبه (سرا) - زنی مذهبی با رازهای تاریک. آرامش ظاهری‌اش مشکوک است.

۳. تاجر (برانکو) - محبوبیت گدا به تجارتش ضربه زده بود. انگیزه مالی دارد.

۴. سرباز (رونان) - شاید از کاخ دستور گرفته باشد. اطاعت کورکورانه از فرمانده.

۵. پسرک (میکائیل) - ۱۳ ساله که با گدا برای صدقه رقابت می‌کرد. کودکی ترسیده و عصبانی.

۶. آشپز (دراگان) - داروی خواب‌آور تهیه می‌کرد. مردی ساده اما مرموز.

شواهد اولیه:
- چاقویی در صحنه جرم پیدا شد
- قتل در شب اتفاق افتاده
- همه مظنونان در نزدیکی بودند"""
        
        # Dialogue area (RIGHT 1/3 - vertical chat style)
        dialogue_x = portrait_x + portrait_width + 20
        dialogue_width = SCREEN_WIDTH - dialogue_x - 20
        
        # Calculate dialogue height based on remaining space after buttons
        # Bottom margin matches portrait (20px), 2 button rows (45+55=100px), input (45px), spacing (8+10=18px)
        total_bottom_elements = 45 + 8 + 45 + 55 + 45 + 20  # input + spacing + btn1 + spacing + btn2 + margin
        dialogue_height = SCREEN_HEIGHT - portrait_y - total_bottom_elements
        
        self.dialogue_area = ScrollableTextArea(
            dialogue_x, 
            portrait_y, 
            dialogue_width,
            dialogue_height,
            FONT_FARSI_SMALL
        )
        
        # Input box (BELOW DIALOGUE on right side)
        input_x = dialogue_x
        input_y = portrait_y + dialogue_height + 10
        input_width = dialogue_width
        input_height = 45
        self.input_box = TextBox(
            input_x, input_y, input_width, input_height, FONT_FARSI_SMALL
        )
        
        # Buttons (stacked vertically below input)
        button_y = input_y + input_height + 8
        button_width = dialogue_width  # Full width button
        
        # Ask button (now full width)
        self.ask_button = Button(
            input_x, button_y, button_width, 45, "بپرس", FONT_FARSI_SMALL
        )
        
        # Second row buttons
        button_y2 = button_y + 55
        half_button_width = dialogue_width // 2 - 5
        
        # Accuse button
        self.accuse_button = Button(
            input_x, button_y2, half_button_width, 45, "اتهام بزن", FONT_FARSI_SMALL, COLOR_ACCENT
        )
        
        # Menu button (in game)
        self.game_menu_button = Button(
            input_x + half_button_width + 10, button_y2, half_button_width, 45, "بازگشت به منو", FONT_FARSI_SMALL, COLOR_BUTTON
        )
        
        # Door button for end day (top left of portrait)
        # Calculate door button size maintaining aspect ratio
        door_btn_height = 240
        if self.door_closed_img:
            orig_w, orig_h = self.door_closed_img.get_size()
            aspect_ratio = orig_w / orig_h
            door_btn_width = int(door_btn_height * aspect_ratio)
            self.door_btn_img_scaled = pygame.transform.smoothscale(self.door_closed_img, (door_btn_width, door_btn_height))
        else:
            door_btn_width = 100
            self.door_btn_img_scaled = None
        
        self.end_day_door_button = Button(
            portrait_x + 30,
            portrait_y + 40,
            door_btn_width,
            door_btn_height,
            "",  # No text, will use image
            FONT_FARSI_SMALL,
            (0, 0, 0)  # Invisible background
        )
        self.end_day_door_button.hide_background = True
        
        # Notebook toggle button (right side of table area - 1/3 from right edge) - no background, just image
        notebook_btn_size = 80  # Square button for the notebook icon
        self.notebook_toggle_button = Button(
            portrait_x + portrait_width - portrait_width // 3 - notebook_btn_size // 2,  # 1/3 from right edge
            portrait_y + portrait_height - notebook_btn_size - 15,
            notebook_btn_size,
            notebook_btn_size,
            "",  # No text, will use image
            FONT_FARSI_SMALL,
            (0, 0, 0)  # Invisible background
        )
        self.notebook_toggle_button.hide_background = True  # Flag to skip background drawing
        
        # Scale notebook button image if loaded
        if self.notebook_closed_img:
            self.notebook_btn_img_scaled = pygame.transform.smoothscale(self.notebook_closed_img, (notebook_btn_size, notebook_btn_size))
        else:
            self.notebook_btn_img_scaled = None
        
        # Case files toggle button (left side of table area - 1/3 from left edge)
        case_files_btn_size = 80
        self.case_files_toggle_button = Button(
            portrait_x + portrait_width // 3 - case_files_btn_size // 2,  # 1/3 from left edge
            portrait_y + portrait_height - case_files_btn_size - 15,
            case_files_btn_size,
            case_files_btn_size,
            "",  # No text, will use image
            FONT_FARSI_SMALL,
            (0, 0, 0)  # Invisible background
        )
        self.case_files_toggle_button.hide_background = True
        
        # Scale case files button image if loaded
        if self.case_files_icon_img:
            self.case_files_btn_img_scaled = pygame.transform.smoothscale(self.case_files_icon_img, (case_files_btn_size, case_files_btn_size))
        else:
            self.case_files_btn_img_scaled = None
        
        # Close notebook button (shown when notebook is open)
        self.notebook_close_button = Button(
            notebook_x + notebook_width - 100,
            notebook_y + 10,
            80,
            35,
            "بستن",
            FONT_FARSI_SMALL,
            COLOR_ACCENT
        )
        
        # Accusation screen buttons (created but not shown initially)
        self.accusation_buttons = []
        for i in range(6):
            button = Button(
                SCREEN_WIDTH // 2 - 200,
                150 + i * 80,
                400,
                70,
                "",  # Will be filled with suspect names
                FONT_FARSI
            )
            self.accusation_buttons.append(button)
    
    def _select_suspect_for_day(self, suspect_id: int):
        """Select a suspect to interview for the current day"""
        self.current_suspect = suspect_id
        self.day_started = True  # Mark that day has started
        
        # Get default emotion image filename from database
        emotion_mapping = game_data.get_emotion_mapping(suspect_id)
        default_image_filename = emotion_mapping.get("default", "other.jpg")
        
        self.current_emotion = default_image_filename.replace(".jpg", "")
        self.character_portrait.set_suspect_and_emotion(suspect_id, default_image_filename, immediate=True)
        
        # Update button states
        for i, button in enumerate(self.suspect_buttons):
            button.is_active = (i == suspect_id - 1)
        
        # Add message to dialogue
        if self.ai_engine:
            suspect_name = self.ai_engine.get_suspect_name(suspect_id)
            self.dialogue_area.add_message(
                "کارآگاه",
                f"روز {self.game_state.current_day}: بازجویی از {suspect_name}",
                COLOR_ACCENT
            )
        
        # Return to playing state
        self.state = "playing"
    
    def _delete_save(self):
        """Delete the save file and reset game state"""
        import os
        
        # Delete save file if it exists
        if os.path.exists("savegame.json"):
            os.remove("savegame.json")
            print("Save file deleted")
        
        # Reset game state
        self.game_state.reset()
        
        # Reset day_started flag
        self.day_started = False
        
        # Reset notebook to show reset state
        self.notebook_panel.current_spread_index = 0
        self.notebook_panel._load_current_spread()
        
        # Clear dialogue
        self.dialogue_area.lines = []
        self.dialogue_area.add_message(
            "کارآگاه",
            "پرونده: قتل گدای بزرگ. شش مظنون داریم. تحقیقات خود را با انتخاب یک مظنون و پرسیدن سوالات آغاز کنید.",
            COLOR_TEXT        )
        
        # Reset AI chat histories
        if self.ai_engine:
            self.ai_engine.reset_all_chats()
    
    def _save_settings(self):
        """Save AI settings and reinitialize AI engine if needed"""
        # Build settings dictionary
        new_settings = {
            "model": self.settings_ollama_model.text.strip() or "gemma3n",
            "isApiAvailable": self.settings_api_mode,
            "openai_base_url": self.settings_base_url.text.strip(),
            "openai_api_key": self.settings_api_key.text.strip(),
            "openai_model": self.settings_model.text.strip()
        }
        
        # Validate API settings if API mode is enabled
        if self.settings_api_mode:
            if not new_settings["openai_base_url"]:
                self.settings_status_message = "خطا: آدرس API خالی است"
                return
            if not new_settings["openai_api_key"]:
                self.settings_status_message = "خطا: کلید API خالی است"
                return
            if not new_settings["openai_model"]:
                self.settings_status_message = "خطا: نام مدل خالی است"
                return
        
        # Save settings
        if ai_settings.save_settings(new_settings):
            self.settings_status_message = "✓ تنظیمات ذخیره شد - بازی را مجدداً شروع کنید"
            print(f"Settings saved: API Mode = {new_settings['isApiAvailable']}")
            
            # Mark that AI engine needs to be reinitialized
            # This will happen when the game is restarted
        else:
            self.settings_status_message = "خطا در ذخیره تنظیمات"
    
    def _ask_question(self):
        """Ask the current suspect a question"""
        question = self.input_box.text.strip()
        
        if not question:
            return
        
        if not self.ai_init_complete:
            self.dialogue_area.add_message(
                "سیستم",
                "موتور هوش مصنوعی در حال راه‌اندازی است. لطفاً صبر کنید...",
                COLOR_ACCENT
            )
            return
        
        # Disable input and ask button while waiting for response
        self.input_box.is_disabled = True
        self.ask_button.is_disabled = True
        
        # Add player's question to dialogue
        self.dialogue_area.add_message("شما", question, COLOR_PLAYER_TEXT)
        
        # Clear input
        self.input_box.text = ""
        
        # Show thinking message
        self.ai_thinking = True
        
        # Start streaming display
        suspect_name = self.ai_engine.get_suspect_name(self.current_suspect)
        self.dialogue_area.start_streaming(suspect_name, COLOR_SUSPECT_TEXT)
        
        # Get AI response in background thread
        def get_response():
            try:
                print(f"\n[DEBUG] Requesting AI response for suspect {self.current_suspect}")
                print(f"[DEBUG] Question: {question}")
                
                # Callback for streaming tokens
                def on_token(token):
                    self.dialogue_area.append_streaming(token)
                
                response = self.ai_engine.get_suspect_response(
                    self.current_suspect,
                    question,
                    streaming=True,
                    stream_callback=on_token
                )
                print(f"[DEBUG] Got response: {response[:100]}..." if len(response) > 100 else f"[DEBUG] Got response: {response}")
                self.ai_response = response
                self.ai_response_ready = True
                print("[DEBUG] Response ready flag set to True")
            except Exception as e:
                print(f"[ERROR] Exception in get_response thread: {e}")
                import traceback
                traceback.print_exc()
                self.ai_response = f"خطا در دریافت پاسخ: {str(e)}"
                self.ai_response_ready = True
        
        response_thread = threading.Thread(target=get_response)
        response_thread.daemon = True
        response_thread.start()
    
    def _make_accusation(self):
        """Enter accusation mode"""
        # Save current notebook page before accusation
        self.notebook_panel._save_current_page()
        
        # Create final notes page
        self.game_state.create_final_page()
        self.notebook_panel.go_to_latest_page()
        
        # Save game state
        self.game_state.save()
        
        self.state = "accusation"
        
        # Update accusation button texts
        if self.ai_engine:
            for i, button in enumerate(self.accusation_buttons):
                suspect_name = self.ai_engine.get_suspect_name(i + 1)
                button.text = suspect_name
    
    def _start_new_game(self):
        """Start a new game from menu"""
        print(f"DEBUG _start_new_game: current_day={self.game_state.current_day}, intro_shown={self.game_state.intro_shown}, day_started={self.day_started}, game_ended={self.game_state.game_ended}")
        
        # Check if game has already ended
        if self.game_state.game_ended:
            # Go directly to win/lose screen
            self.state = self.game_state.win_state
            return
        
        # Check if day has already started
        if self.day_started:
            # Return to playing state with current suspect
            self.state = "playing"
        else:
            # Show intro on day 1 if we haven't shown it yet (NEW GAME)
            if self.game_state.current_day == 1 and not self.game_state.intro_shown:
                print("DEBUG: Starting intro!")
                self.state = "intro"  # Go to intro first
                self.game_state.intro_shown = True
                self._start_intro_streaming()  # Start warm-up with intro generation
            elif self.game_state.intro_shown and not self.load_recap_complete:
                # Loading from save - show news recap to warm up model
                print("DEBUG: Starting load recap")
                self.state = "load_recap"
                self._start_load_recap()  # Start warm-up with recap generation
            else:
                print("DEBUG: Going to suspect selection")
                self.state = "suspect_selection"  # Go to suspect selection
    
    def _accuse_suspect(self, suspect_id: int):
        """Make final accusation"""
        # Suspect 2 (The Nun - راهبه) is the murderer
        if suspect_id == 2:
            self.state = "win"
            self.game_state.win_state = "win"
        else:
            self.state = "lose"
            self.game_state.win_state = "lose"
        
        # Mark game as ended
        self.game_state.game_ended = True
        self.game_state.save()
    
    def _draw_loading_state(self):
        """Draw loading screen with gothic styling"""
        self.screen.fill(COLOR_BG)
        
        # Pulsing loading text with glow
        pulse = (math.sin(self.animation_timer * 3) + 1) / 2  # 0 to 1
        glow_alpha = int(40 + 30 * pulse)
        
        # Draw glow behind text
        draw_glow(self.screen, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), 80, COLOR_GLOW, glow_alpha)
        
        # Loading text with shadow
        draw_text_with_shadow(self.screen, "در حال بارگذاری ...", FONT_FARSI, COLOR_TEXT,
                             (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), shadow_offset=2, center=True)
        
        # Draw vignette
        draw_vignette(self.screen)
    
    def _draw_menu_state(self):
        """Draw menu screen with gothic styling"""
        if self.menu_background:
            self.screen.blit(self.menu_background, (0, 0))
            
            # Add dark overlay for better button visibility
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 60))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(COLOR_BG)
        
        # Draw vignette
        draw_vignette(self.screen)
        
        # Draw warm tint
        draw_warm_tint(self.screen, alpha=10)
        
        # Update delete button color based on save existence
        import os
        if os.path.exists("savegame.json"):
            self.menu_delete_save_button.color = COLOR_ACCENT
        else:
            self.menu_delete_save_button.color = COLOR_PANEL
        
        # Update music button color (green when on, muted when off)
        if self.music_enabled:
            self.menu_music_button.color = (60, 100, 70)  # Muted green
            self.menu_music_button.text = "🎵 موسیقی"
        else:
            self.menu_music_button.color = COLOR_PANEL  # Muted/off
            self.menu_music_button.text = "🎵 موسیقی"
        
        # Draw buttons
        self.menu_start_button.draw(self.screen)
        self.menu_delete_save_button.draw(self.screen)
        self.menu_music_button.draw(self.screen)
        self.menu_credits_button.draw(self.screen)
        self.menu_settings_button.draw(self.screen)
        self.menu_exit_button.draw(self.screen)
    
    def _draw_credits_state(self):
        """Draw credits/about screen with gothic styling and scrolling"""
        self.screen.fill(COLOR_BG)
        
        # Draw warm tint
        draw_warm_tint(self.screen, alpha=15)
        
        # Game title (fixed at top)
        draw_text_with_shadow(self.screen, "مرگ و گدای بزرگ", FONT_FARSI, COLOR_TEXT,
                             (SCREEN_WIDTH // 2, 80), shadow_offset=2, center=True)
        
        # Subtitle (fixed at top)
        draw_text_with_shadow(self.screen, "نزدیکترین حس به کارآگاه بودن", FONT_FARSI_SMALL, (160, 150, 140),
                             (SCREEN_WIDTH // 2, 120), shadow_offset=1, center=True)
        
        # Credits content
        line_height = 38
        
        credits_lines = [
            ("", None),
            ("نویسنده و کارگردان", COLOR_GOLD),
            ("آرمین آقائی", COLOR_TEXT),
            ("", None),
            ("توسعه", COLOR_GOLD),
            ("امیر علی فتاح پسند", COLOR_TEXT),
            ("محمد طهماسبی", COLOR_TEXT),
            ("عبدالمتین بابکی", COLOR_TEXT),
            ("", None),
            ("گرافیست", COLOR_GOLD),
            ("هلنا نوابی", COLOR_TEXT),
            ("", None),
            ("موسیقی", COLOR_GOLD),
            ("محمد طهماسبی", COLOR_TEXT),
            ("", None),
            ("با تشکر از", COLOR_GOLD),
            ("هادی زارع (طراحی پوستر)", COLOR_TEXT),
            ("محمد مهدی عیسی بیگی (ادیتور تریلر)", COLOR_TEXT),
        ]
        
        # Calculate total content height and max scroll
        total_content_height = len(credits_lines) * line_height
        content_area_top = 160
        content_area_bottom = SCREEN_HEIGHT - 100  # Leave space for back button
        visible_height = content_area_bottom - content_area_top
        max_scroll = max(0, total_content_height - visible_height)
        
        # Clamp scroll value
        self.credits_scroll = max(0, min(self.credits_scroll, max_scroll))
        
        # Set clipping rectangle to prevent text overflow
        old_clip = self.screen.get_clip()
        content_rect = pygame.Rect(0, content_area_top, SCREEN_WIDTH, visible_height)
        self.screen.set_clip(content_rect)
        
        # Draw credits with scroll offset
        credits_y = content_area_top - self.credits_scroll
        
        for text, color in credits_lines:
            if text and color:
                # Only draw if visible
                if content_area_top - line_height < credits_y < content_area_bottom + line_height:
                    draw_text_with_shadow(self.screen, text, FONT_FARSI_SMALL, color,
                                         (SCREEN_WIDTH // 2, credits_y), shadow_offset=1, center=True)
            credits_y += line_height
        
        # Restore original clipping
        self.screen.set_clip(old_clip)
        
        # Draw scroll indicator if content is scrollable
        if max_scroll > 0:
            scroll_bar_width = 6
            scroll_bar_x = SCREEN_WIDTH - 30
            scroll_track_height = visible_height - 20
            scroll_bar_height = max(30, int(scroll_track_height * visible_height / total_content_height))
            scroll_bar_y = content_area_top + 10 + int((scroll_track_height - scroll_bar_height) * self.credits_scroll / max_scroll)
            
            # Draw scroll track
            pygame.draw.rect(self.screen, COLOR_BORDER_DARK, 
                           (scroll_bar_x, content_area_top + 10, scroll_bar_width, scroll_track_height), border_radius=3)
            # Draw scroll bar
            pygame.draw.rect(self.screen, COLOR_GOLD, 
                           (scroll_bar_x, scroll_bar_y, scroll_bar_width, scroll_bar_height), border_radius=3)
        
        # Back button
        self.credits_back_button.draw(self.screen)
        
        # Draw vignette
        draw_vignette(self.screen)
    
    def _draw_settings_state(self):
        """Draw settings screen with gothic styling"""
        # Ensure settings UI exists
        if not hasattr(self, 'settings_panel_rect'):
            self._create_settings_ui()
        
        # Draw menu background if available
        if self.menu_background:
            self.screen.blit(self.menu_background, (0, 0))
            
            # Add dark overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(COLOR_BG)
        
        # Draw settings panel background
        panel = self.settings_panel_rect
        
        # Outer glow
        glow_rect = panel.inflate(20, 20)
        glow_surface = pygame.Surface((glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(glow_surface, (0, 0, 0, 100), glow_surface.get_rect(), border_radius=15)
        self.screen.blit(glow_surface, glow_rect)
        
        # Panel background
        pygame.draw.rect(self.screen, COLOR_PANEL, panel, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_BORDER_LIGHT, panel, 2, border_radius=12)
        
        # Title
        draw_text_with_shadow(self.screen, "تنظیمات", FONT_FARSI, COLOR_GOLD,
                             (SCREEN_WIDTH // 2, panel.y + 35), shadow_offset=2, center=True)
        
        # Get form starting positions
        form_y = panel.y + 80
        label_x = panel.x + panel.width - 30
        field_spacing = 65
        
        # API Mode toggle label and button
        draw_text_with_shadow(self.screen, "حالت اتصال:", FONT_FARSI_SMALL, COLOR_TEXT,
                             (label_x, form_y + 10), shadow_offset=1, center=False)
        self.settings_api_toggle.draw(self.screen)
        form_y += field_spacing
        
        # Only show API fields if API mode is enabled
        if self.settings_api_mode:
            # Base URL label and input
            draw_text_with_shadow(self.screen, "آدرس API:", FONT_FARSI_SMALL, COLOR_TEXT,
                                 (label_x, form_y + 5), shadow_offset=1, center=False)
            self.settings_base_url.draw(self.screen)
            form_y += field_spacing
            
            # API Key label and input
            draw_text_with_shadow(self.screen, "کلید API:", FONT_FARSI_SMALL, COLOR_TEXT,
                                 (label_x, form_y + 5), shadow_offset=1, center=False)
            self.settings_api_key.draw(self.screen)
            form_y += field_spacing
            
            # Model label and input
            draw_text_with_shadow(self.screen, "نام مدل:", FONT_FARSI_SMALL, COLOR_TEXT,
                                 (label_x, form_y + 5), shadow_offset=1, center=False)
            self.settings_model.draw(self.screen)
        else:
            # Ollama model label and input
            form_y += field_spacing  # Skip base URL position
            form_y += field_spacing  # Skip API key position
            form_y += field_spacing  # Skip model position
            
            draw_text_with_shadow(self.screen, "مدل Ollama:", FONT_FARSI_SMALL, COLOR_TEXT,
                                 (label_x, form_y + 5), shadow_offset=1, center=False)
            self.settings_ollama_model.draw(self.screen)
        
        # Draw buttons
        self.settings_save_button.draw(self.screen)
        self.settings_back_button.draw(self.screen)
        
        # Draw status message if any
        if hasattr(self, 'settings_status_message') and self.settings_status_message:
            msg_color = COLOR_GOLD if 'ذخیره شد' in self.settings_status_message else COLOR_ACCENT
            draw_text_with_shadow(self.screen, self.settings_status_message, FONT_FARSI_SMALL, msg_color,
                                 (SCREEN_WIDTH // 2, panel.y + panel.height - 30), shadow_offset=1, center=True)
        
        # Draw vignette
        draw_vignette(self.screen)
    
    def _draw_intro_state(self):
        """Draw intro story screen with gothic styling and warm glow cursor"""
        # Draw blurred background image
        if self.intro_background:
            self.screen.blit(self.intro_background, (0, 0))
            # Add dark overlay for better text readability
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(COLOR_BG)
        
        # Draw warm tint
        draw_warm_tint(self.screen, alpha=12)
        
        # Title with gold color and glow
        draw_glow(self.screen, (SCREEN_WIDTH // 2, 50), 60, COLOR_GLOW, 30)
        draw_text_with_shadow(self.screen, "قتل گدای بزرگ", FONT_FARSI, COLOR_GOLD,
                             (SCREEN_WIDTH // 2, 50), shadow_offset=2, center=True)
        
        # Display the streaming intro text with word wrapping and shadows
        if self.intro_text:
            max_width = SCREEN_WIDTH - 100
            paragraphs = self.intro_text.replace('\r\n', '\n').split('\n')
            
            y_offset = 100
            line_height = 35
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    y_offset += 20
                    continue
                
                words = paragraph.split()
                current_line = ""
                
                for word in words:
                    test_line = current_line + " " + word if current_line else word
                    reshaped_test = reshape_persian_text(test_line)
                    test_surface = FONT_FARSI_SMALL.render(reshaped_test, True, COLOR_TEXT)
                    
                    if test_surface.get_width() > max_width:
                        if current_line:
                            draw_text_with_shadow(self.screen, current_line, FONT_FARSI_SMALL, COLOR_TEXT,
                                                 (SCREEN_WIDTH // 2, y_offset), shadow_offset=1, center=True)
                            y_offset += line_height
                        current_line = word
                    else:
                        current_line = test_line
                
                if current_line:
                    draw_text_with_shadow(self.screen, current_line, FONT_FARSI_SMALL, COLOR_TEXT,
                                         (SCREEN_WIDTH // 2, y_offset), shadow_offset=1, center=True)
                    y_offset += line_height
        
        # Show warm pulsing cursor while streaming
        if self.intro_streaming and not self.intro_complete:
            # Warm pulsing glow cursor
            pulse = (math.sin(self.animation_timer * 6) + 1) / 2  # Faster pulse
            cursor_alpha = int(128 + 127 * pulse)
            cursor_color = lerp_color(COLOR_ACCENT, COLOR_GLOW, pulse * 0.5)
            
            # Draw glow behind cursor
            draw_glow(self.screen, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120), 25, COLOR_GLOW, int(40 * pulse))
            
            cursor_text = "▌"
            reshaped_cursor = reshape_persian_text(cursor_text)
            cursor_surface = FONT_FARSI_SMALL.render(reshaped_cursor, True, cursor_color)
            cursor_rect = cursor_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120))
            self.screen.blit(cursor_surface, cursor_rect)

            # Draw skip button
            self.intro_skip_button.draw(self.screen)
        
        # Show "press any key" when complete
        if self.intro_complete:
            draw_text_with_shadow(self.screen, "(برای ادامه هر دکمه‌ای را فشار دهید)", FONT_FARSI_SMALL, (130, 120, 110),
                                 (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50), shadow_offset=1, center=True)
        
        # Draw vignette
        draw_vignette(self.screen)
    
    def _start_load_recap(self):
        """Start the load recap generation for warming up model when loading a save"""
        self.load_recap_text = ""
        self.load_recap_streaming = True
        self.load_recap_complete = False
        
        def stream_callback(token):
            self.load_recap_text += token
        
        def generate_recap():
            try:
                self.ai_engine.generate_load_recap(
                    self.game_state.current_day,
                    stream_callback=stream_callback
                )
                self.load_recap_streaming = False
                self.load_recap_complete = True
            except Exception as e:
                print(f"Load recap generation failed: {e}")
                self.load_recap_streaming = False
                self.load_recap_complete = True
        
        threading.Thread(target=generate_recap, daemon=True).start()
    
    def _draw_load_recap_state(self):
        """Draw load recap screen with gothic styling and warm glow cursor"""
        # Draw blurred background image
        if self.intro_background:
            self.screen.blit(self.intro_background, (0, 0))
            # Add dark overlay for better text readability
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(COLOR_BG)
        
        # Draw warm tint
        draw_warm_tint(self.screen, alpha=12)
        
        # Title with gold and glow
        draw_glow(self.screen, (SCREEN_WIDTH // 2, 50), 60, COLOR_GLOW, 30)
        draw_text_with_shadow(self.screen, "خبر روز", FONT_FARSI, COLOR_GOLD,
                             (SCREEN_WIDTH // 2, 50), shadow_offset=2, center=True)
        
        # Subtitle with shadow
        draw_text_with_shadow(self.screen, f"روز {self.game_state.current_day} تحقیقات", FONT_FARSI_SMALL, COLOR_TEXT,
                             (SCREEN_WIDTH // 2, 90), shadow_offset=1, center=True)
        
        # Display the streaming recap text with word wrapping and shadows
        if self.load_recap_text:
            max_width = SCREEN_WIDTH - 100
            paragraphs = self.load_recap_text.replace('\r\n', '\n').split('\n')
            
            y_offset = 140
            line_height = 35
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    y_offset += 20
                    continue
                
                words = paragraph.split()
                current_line = ""
                
                for word in words:
                    test_line = current_line + " " + word if current_line else word
                    reshaped_test = reshape_persian_text(test_line)
                    test_surface = FONT_FARSI_SMALL.render(reshaped_test, True, COLOR_TEXT)
                    
                    if test_surface.get_width() > max_width:
                        if current_line:
                            draw_text_with_shadow(self.screen, current_line, FONT_FARSI_SMALL, COLOR_TEXT,
                                                 (SCREEN_WIDTH // 2, y_offset), shadow_offset=1, center=True)
                            y_offset += line_height
                        current_line = word
                    else:
                        current_line = test_line
                
                if current_line:
                    draw_text_with_shadow(self.screen, current_line, FONT_FARSI_SMALL, COLOR_TEXT,
                                         (SCREEN_WIDTH // 2, y_offset), shadow_offset=1, center=True)
                    y_offset += line_height
        
        # Show warm pulsing cursor while streaming
        if self.load_recap_streaming and not self.load_recap_complete:
            pulse = (math.sin(self.animation_timer * 6) + 1) / 2
            cursor_color = lerp_color(COLOR_ACCENT, COLOR_GLOW, pulse * 0.5)
            
            draw_glow(self.screen, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120), 25, COLOR_GLOW, int(40 * pulse))
            
            cursor_text = "▌"
            reshaped_cursor = reshape_persian_text(cursor_text)
            cursor_surface = FONT_FARSI_SMALL.render(reshaped_cursor, True, cursor_color)
            cursor_rect = cursor_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120))
            self.screen.blit(cursor_surface, cursor_rect)

            self.intro_skip_button.draw(self.screen)
        
        # Show "press any key" when complete
        if self.load_recap_complete:
            draw_text_with_shadow(self.screen, "(برای ادامه هر دکمه‌ای را فشار دهید)", FONT_FARSI_SMALL, (130, 120, 110),
                                 (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50), shadow_offset=1, center=True)
        
        # Draw vignette
        draw_vignette(self.screen)

    def _draw_playing_state(self):
        """Draw the main playing state with gothic noir styling"""
        # Background
        self.screen.fill(COLOR_BG)
        
        # Draw warm tint for atmosphere
        draw_warm_tint(self.screen, alpha=10)
        
        # Title (top center) with gold and glow
        draw_glow(self.screen, (SCREEN_WIDTH // 2, 40), 80, COLOR_GLOW, 20)
        draw_text_with_shadow(self.screen, "قتل گدای بزرگ", FONT_FARSI, COLOR_GOLD,
                             (SCREEN_WIDTH // 2, 35), shadow_offset=2, center=True)
        
        # Character portrait (LARGE - 2/3 of screen)
        self.character_portrait.draw(self.screen)
        
        # Show suspect name above portrait if suspect is selected (centered on portrait)
        if self.current_suspect and self.ai_engine:
            suspect_name = self.ai_engine.get_suspect_name(self.current_suspect)
            name_x = self.character_portrait.rect.centerx
            name_y = self.character_portrait.rect.top - 5  # Just above the portrait
            
            # Draw styled name background
            name_text_reshaped = reshape_persian_text(suspect_name)
            name_surf = FONT_FARSI.render(name_text_reshaped, True, COLOR_GOLD)
            name_bg_width = name_surf.get_width() + 40
            name_bg_height = 38
            name_bg_rect = pygame.Rect(name_x - name_bg_width // 2, name_y - name_bg_height // 2, name_bg_width, name_bg_height)
            
            # Background with border
            pygame.draw.rect(self.screen, COLOR_BG, name_bg_rect, border_radius=8)
            pygame.draw.rect(self.screen, COLOR_BORDER_DARK, name_bg_rect, 2, border_radius=8)
            inner_name_rect = name_bg_rect.inflate(-4, -4)
            pygame.draw.rect(self.screen, COLOR_GOLD, inner_name_rect, 1, border_radius=6)
            
            draw_text_with_shadow(self.screen, suspect_name, FONT_FARSI, COLOR_GOLD,
                                 (name_x, name_y), shadow_offset=1, center=True)
        
        # Day counter with clock background (top right of portrait, drawn AFTER portrait)
        clock_size = 80
        clock_x = self.character_portrait.rect.x + self.character_portrait.rect.width - clock_size - 10
        clock_y = self.character_portrait.rect.y + 10
        
        # Choose clock image based on day (clock2 after day 6 or for "Final")
        current_day = self.game_state.current_day
        clock_img = self.clock2_img if isinstance(current_day, str) or current_day > 6 else self.clock1_img
        if clock_img:
            scaled_clock = pygame.transform.smoothscale(clock_img, (clock_size, clock_size))
            self.screen.blit(scaled_clock, (clock_x, clock_y))
        
        # Draw day number centered ON the clock
        day_text_x = clock_x + clock_size // 2
        day_text_y = clock_y + clock_size // 2
        draw_text_with_shadow(self.screen, str(self.game_state.current_day), FONT_FARSI, COLOR_TEXT,
                             (day_text_x, day_text_y), shadow_offset=2, center=True)
        
        # Dialogue area (RIGHT SIDE CHAT) - draw with background image
        self._draw_dialogue_with_background()
        
        # Input box
        self.input_box.draw(self.screen)
        
        # Buttons
        self.ask_button.draw(self.screen)
        self.accuse_button.draw(self.screen)
        self.game_menu_button.draw(self.screen)
        
        # Door button for end day (top left of portrait)
        if self.door_btn_img_scaled:
            img_x = self.end_day_door_button.rect.x
            img_y = self.end_day_door_button.rect.y
            self.screen.blit(self.door_btn_img_scaled, (img_x, img_y))
        
        # Notebook toggle button with image (right side of table)
        if self.notebook_btn_img_scaled:
            # Just draw the image directly at button position
            img_x = self.notebook_toggle_button.rect.x
            img_y = self.notebook_toggle_button.rect.y
            self.screen.blit(self.notebook_btn_img_scaled, (img_x, img_y))
        
        # Case files toggle button with image (left of notebook button)
        if self.case_files_btn_img_scaled:
            img_x = self.case_files_toggle_button.rect.x
            img_y = self.case_files_toggle_button.rect.y
            self.screen.blit(self.case_files_btn_img_scaled, (img_x, img_y))
        
        # Thinking indicator with pulsing glow
        if self.ai_thinking:
            pulse = (math.sin(self.animation_timer * 4) + 1) / 2
            thinking_color = lerp_color(COLOR_ACCENT, COLOR_GLOW, pulse * 0.3)
            thinking_x = self.dialogue_area.rect.x + self.dialogue_area.rect.width // 2
            thinking_y = self.dialogue_area.rect.y - 20
            draw_glow(self.screen, (thinking_x, thinking_y), 30, COLOR_GLOW, int(20 * pulse))
            draw_text_with_shadow(self.screen, "در حال فکر کردن...", FONT_FARSI_SMALL, thinking_color,
                                 (thinking_x, thinking_y), shadow_offset=1, center=True)
        
        # Draw vignette (before notebook popup)
        draw_vignette(self.screen)
        
        # Notebook popup overlay (drawn last, on top of everything)
        if self.notebook_visible:
            # Semi-transparent dark overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(170)
            self.screen.blit(overlay, (0, 0))
            
            # Draw notebook panel with background
            self._draw_notebook_with_background()
            
            # Draw close button
            self.notebook_close_button.draw(self.screen)
        
        # Case files popup overlay (drawn on top of everything)
        if self.case_files_visible:
            # Semi-transparent dark overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(170)
            self.screen.blit(overlay, (0, 0))
            
            # Draw case files panel with background
            self._draw_case_files_panel()
            
            # Draw close button (reusing notebook close button)
            self.notebook_close_button.draw(self.screen)
    
    def _draw_dialogue_with_background(self):
        """Draw dialogue area with gothic styling (no background image)"""
        rect = self.dialogue_area.rect
        
        # Draw darker panel background for better readability
        pygame.draw.rect(self.screen, (30, 28, 25), rect, border_radius=8)
        
        # Draw gothic frame border
        pygame.draw.rect(self.screen, COLOR_BORDER_DARK, rect, 3, border_radius=8)
        inner_rect = rect.inflate(-6, -6)
        pygame.draw.rect(self.screen, COLOR_BORDER_LIGHT, inner_rect, 1, border_radius=6)
        
        # Draw inner shadow
        draw_inner_shadow(self.screen, rect, shadow_size=8, alpha=40)
        
        # Set clipping rectangle to prevent text overflow
        old_clip = self.screen.get_clip()
        content_rect = pygame.Rect(rect.x + 8, rect.y + 8, rect.width - 16, rect.height - 16)
        self.screen.set_clip(content_rect)
        
        # Draw the dialogue content on top
        y_offset = rect.y + 12
        max_y = rect.y + rect.height - 12
        line_height = self.dialogue_area.line_height
        max_text_width = rect.width - 35
        
        # Draw existing lines with shadows
        for i in range(self.dialogue_area.scroll_offset, len(self.dialogue_area.lines)):
            if y_offset + line_height > max_y:
                break
            
            line_data = self.dialogue_area.lines[i]
            text = line_data[0]
            color = line_data[1]
            
            if text:
                display_text = reshape_persian_text(text)
                
                # Draw shadow
                shadow_surface = self.dialogue_area.font.render(display_text, True, COLOR_SHADOW)
                text_surface = self.dialogue_area.font.render(display_text, True, color)
                
                # Clip text surface if too wide
                if text_surface.get_width() > max_text_width:
                    text_surface = text_surface.subsurface((text_surface.get_width() - max_text_width, 0, max_text_width, text_surface.get_height()))
                    shadow_surface = shadow_surface.subsurface((shadow_surface.get_width() - max_text_width, 0, max_text_width, shadow_surface.get_height()))
                
                text_x = rect.x + rect.width - text_surface.get_width() - 18
                self.screen.blit(shadow_surface, (text_x + 1, y_offset + 1))
                self.screen.blit(text_surface, (text_x, y_offset))
            y_offset += line_height
        
        # Draw streaming text if active - with word wrapping and shadows
        if self.dialogue_area.streaming_speaker and y_offset < max_y:
            streaming_full = f"{self.dialogue_area.streaming_speaker}: {self.dialogue_area.streaming_text}▌"
            # Wrap streaming text into multiple lines
            words = streaming_full.split(' ')
            current_line = ""
            streaming_lines = []
            
            for word in words:
                test_line = current_line + word + " "
                test_surface = self.dialogue_area.font.render(reshape_persian_text(test_line), True, self.dialogue_area.streaming_color)
                if test_surface.get_width() <= max_text_width:
                    current_line = test_line
                else:
                    if current_line.strip():
                        streaming_lines.append(current_line.strip())
                    current_line = word + " "
            if current_line.strip():
                streaming_lines.append(current_line.strip())
            
            # Draw wrapped streaming lines with shadows
            for line in streaming_lines:
                if y_offset + line_height > max_y:
                    break
                display_text = reshape_persian_text(line)
                
                shadow_surface = self.dialogue_area.font.render(display_text, True, COLOR_SHADOW)
                text_surface = self.dialogue_area.font.render(display_text, True, self.dialogue_area.streaming_color)
                
                text_x = rect.x + rect.width - text_surface.get_width() - 18
                self.screen.blit(shadow_surface, (text_x + 1, y_offset + 1))
                self.screen.blit(text_surface, (text_x, y_offset))
                y_offset += line_height
        
        # Restore original clipping
        self.screen.set_clip(old_clip)
    
    def _draw_notebook_with_background(self):
        """Draw notebook panel with two-page book spread and gothic styling"""
        rect = self.notebook_panel.rect
        
        # Draw background image if available
        if self.notebook_open_img:
            scaled_bg = pygame.transform.smoothscale(self.notebook_open_img, (rect.width, rect.height))
            self.screen.blit(scaled_bg, (rect.x, rect.y))
            
            # Add dark overlay for text readability
            overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 80))
            self.screen.blit(overlay, (rect.x, rect.y))
        else:
            # Fallback to solid color with border
            pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=5)
            pygame.draw.rect(self.screen, COLOR_BORDER_DARK, rect, 4, border_radius=5)
            inner_rect = rect.inflate(-6, -6)
            pygame.draw.rect(self.screen, COLOR_GOLD, inner_rect, 1, border_radius=4)
        
        # Calculate page dimensions (two halves)
        mid_x = rect.x + rect.width // 2
        page_width = rect.width // 2 - 20
        content_y = rect.top + 90
        content_height = rect.height - 140
        line_height = self.notebook_panel.line_height
        
        total_pages = self.game_state.get_total_pages()
        right_page_idx = self.notebook_panel._get_right_page_index()
        left_page_idx = self.notebook_panel._get_left_page_index()
        
        # Draw center divider line with gold tint
        pygame.draw.line(self.screen, COLOR_BORDER_DARK, (mid_x, rect.top + 40), (mid_x, rect.bottom - 50), 2)
        pygame.draw.line(self.screen, COLOR_GOLD, (mid_x + 1, rect.top + 42), (mid_x + 1, rect.bottom - 52), 1)
        
        # ========== RIGHT PAGE (odd days: 1, 3, 5...) ==========
        if right_page_idx < total_pages:
            right_page = self.game_state.get_page_by_index(right_page_idx)
            right_day = right_page.get('day', '')
            right_editable = self.notebook_panel._is_page_editable(right_page_idx)
            is_right_active = self.notebook_panel.active_side == 0
            
            # Right page header with shadow
            if right_day == "Final":
                day_text = "یادداشت نهایی"
            else:
                day_text = f"روز {right_day}"
            header_color = COLOR_GOLD if right_editable else (120, 110, 100)
            header_x = mid_x + (page_width) // 2 + 10
            draw_text_with_shadow(self.screen, day_text, FONT_FARSI_SMALL, header_color,
                                 (header_x, rect.top + 60), shadow_offset=1, center=True)
            
            # Right page content
            if is_right_active and right_editable:
                lines = self.notebook_panel.text_lines
            else:
                lines = self.notebook_panel.get_page_content(right_page_idx)
            
            for i, line in enumerate(lines):
                if i * line_height >= content_height:
                    break
                y = content_y + i * line_height
                
                if line:
                    has_farsi = any(ord(c) >= 0x0600 and ord(c) <= 0x06FF for c in line)
                    if has_farsi:
                        display_text = reshape_persian_text(line)
                        shadow_surf = FONT_FARSI_SMALL.render(display_text, True, COLOR_SHADOW)
                        text_surf = FONT_FARSI_SMALL.render(display_text, True, COLOR_TEXT)
                        # Right-align RTL text: start from right edge with large margin
                        text_x = rect.right - 150 - text_surf.get_width()
                        # Clamp to not go past center divider
                        text_x = max(text_x, mid_x + 40)
                        self.screen.blit(shadow_surf, (text_x + 1, y + 1))
                        self.screen.blit(text_surf, (text_x, y))
                    else:
                        shadow_surf = self.notebook_panel.font.render(line, True, COLOR_SHADOW)
                        text_surf = self.notebook_panel.font.render(line, True, COLOR_TEXT)
                        self.screen.blit(shadow_surf, (mid_x + 41, y + 1))
                        self.screen.blit(text_surf, (mid_x + 40, y))
                
                # Draw cursor on right page if active and editable
                if is_right_active and right_editable and i == self.notebook_panel.cursor_line:
                    if pygame.time.get_ticks() % 1000 < 500:
                        cursor_surf = FONT_FARSI_SMALL.render("|", True, COLOR_GOLD)
                        has_farsi = any(ord(c) >= 0x0600 and ord(c) <= 0x06FF for c in line) if line else False
                        if has_farsi:
                            # Cursor at right edge for RTL
                            self.screen.blit(cursor_surf, (rect.right - 155, y))
                        else:
                            cursor_x = mid_x + 40 + self.notebook_panel.font.size(line[:self.notebook_panel.cursor_pos])[0] if line else mid_x + 40
                            self.screen.blit(cursor_surf, (cursor_x, y))
        
        # ========== LEFT PAGE (even days: 2, 4, 6...) ==========
        if left_page_idx < total_pages:
            left_page = self.game_state.get_page_by_index(left_page_idx)
            left_day = left_page.get('day', '')
            left_editable = self.notebook_panel._is_page_editable(left_page_idx)
            is_left_active = self.notebook_panel.active_side == 1
            
            # Left page header with shadow
            if left_day == "Final":
                day_text = "یادداشت نهایی"
            else:
                day_text = f"روز {left_day}"
            header_color = COLOR_GOLD if left_editable else (120, 110, 100)
            header_x = rect.x + (page_width) // 2 + 10
            draw_text_with_shadow(self.screen, day_text, FONT_FARSI_SMALL, header_color,
                                 (header_x, rect.top + 60), shadow_offset=1, center=True)
            
            # Left page content
            if is_left_active and left_editable:
                lines = self.notebook_panel.text_lines
            else:
                lines = self.notebook_panel.get_page_content(left_page_idx)
            
            for i, line in enumerate(lines):
                if i * line_height >= content_height:
                    break
                y = content_y + i * line_height
                
                if line:
                    has_farsi = any(ord(c) >= 0x0600 and ord(c) <= 0x06FF for c in line)
                    if has_farsi:
                        display_text = reshape_persian_text(line)
                        shadow_surf = FONT_FARSI_SMALL.render(display_text, True, COLOR_SHADOW)
                        text_surf = FONT_FARSI_SMALL.render(display_text, True, COLOR_TEXT)
                        # Right-align RTL text: fixed right edge (near center), text extends leftward
                        text_x = mid_x - 30 - text_surf.get_width()
                        self.screen.blit(shadow_surf, (text_x + 1, y + 1))
                        self.screen.blit(text_surf, (text_x, y))
                    else:
                        shadow_surf = self.notebook_panel.font.render(line, True, COLOR_SHADOW)
                        text_surf = self.notebook_panel.font.render(line, True, COLOR_TEXT)
                        self.screen.blit(shadow_surf, (rect.x + 51, y + 1))
                        self.screen.blit(text_surf, (rect.x + 50, y))
                
                # Draw cursor on left page if active and editable
                if is_left_active and left_editable and i == self.notebook_panel.cursor_line:
                    if pygame.time.get_ticks() % 1000 < 500:
                        cursor_surf = FONT_FARSI_SMALL.render("|", True, COLOR_GOLD)
                        has_farsi = any(ord(c) >= 0x0600 and ord(c) <= 0x06FF for c in line) if line else False
                        if has_farsi:
                            # Cursor at right edge for RTL (near center divider)
                            self.screen.blit(cursor_surf, (mid_x - 55, y))
                        else:
                            cursor_x = rect.x + 50 + self.notebook_panel.font.size(line[:self.notebook_panel.cursor_pos])[0] if line else rect.x + 50
                            self.screen.blit(cursor_surf, (cursor_x, y))
        
        # Draw spread indicator below the notebook
        spread_num = self.notebook_panel.current_spread_index + 1
        max_spreads = (total_pages + 1) // 2
        spread_text = f"صفحات {spread_num}/{max_spreads}"
        draw_text_with_shadow(self.screen, spread_text, FONT_FARSI_SMALL, (200, 190, 170),
                             (rect.centerx, rect.bottom + 25), shadow_offset=1, center=True)
        
        # Draw navigation buttons
        self.notebook_panel.prev_button.draw(self.screen)
        self.notebook_panel.next_button.draw(self.screen)
    
    def _draw_case_files_panel(self):
        """Draw case files panel with پرونده باز background, title, and intro text"""
        # Use original image aspect ratio (598x663 = 0.902)
        original_aspect = 598 / 663  # width / height = 0.902
        
        # Calculate size based on screen height while maintaining aspect ratio
        panel_height = int(SCREEN_HEIGHT * 0.75)
        panel_width = int(panel_height * original_aspect)
        
        # Center the panel on screen
        panel_x = (SCREEN_WIDTH - panel_width) // 2
        panel_y = (SCREEN_HEIGHT - panel_height) // 2
        rect = pygame.Rect(panel_x, panel_y, panel_width, panel_height)
        
        # Store rect for scroll event handling
        self.case_files_rect = rect
        
        # Draw background image if available
        if self.file_open_img:
            scaled_bg = pygame.transform.smoothscale(self.file_open_img, (rect.width, rect.height))
            self.screen.blit(scaled_bg, (rect.x, rect.y))
        else:
            # Fallback to solid color with border
            pygame.draw.rect(self.screen, COLOR_PANEL, rect, border_radius=5)
            pygame.draw.rect(self.screen, COLOR_BORDER_DARK, rect, 4, border_radius=5)
            inner_rect = rect.inflate(-6, -6)
            pygame.draw.rect(self.screen, COLOR_GOLD, inner_rect, 1, border_radius=4)
        
        # Draw title with gold glow - positioned lower on the white paper area
        title_y = rect.top + 100
        draw_glow(self.screen, (rect.centerx, title_y), 50, COLOR_GLOW, 25)
        draw_text_with_shadow(self.screen, "گزارش پرونده", FONT_FARSI, COLOR_GOLD,
                             (rect.centerx, title_y), shadow_offset=2, center=True)
        
        # Draw case files text with word wrapping and scrolling
        case_text = self.game_state.case_files_text
        if case_text:
            margin_left = 80
            margin_right = 60
            max_width = rect.width - margin_left - margin_right
            content_y = rect.top + 150  # Start lower after title
            content_bottom = rect.bottom - 60
            visible_height = content_bottom - content_y
            line_height = 30
            
            # Pre-calculate all lines for scrolling
            all_lines = []
            paragraphs = case_text.replace('\r\n', '\n').split('\n')
            
            for paragraph in paragraphs:
                if not paragraph.strip():
                    all_lines.append('')  # Empty line for paragraph break
                    continue
                
                words = paragraph.split()
                current_line = ""
                
                for word in words:
                    test_line = current_line + " " + word if current_line else word
                    reshaped_test = reshape_persian_text(test_line)
                    test_surface = FONT_FARSI_SMALL.render(reshaped_test, True, COLOR_TEXT)
                    
                    if test_surface.get_width() > max_width:
                        if current_line:
                            all_lines.append(current_line)
                        current_line = word
                    else:
                        current_line = test_line
                
                if current_line:
                    all_lines.append(current_line)
            
            # Calculate max scroll
            total_content_height = len(all_lines) * line_height
            max_scroll = max(0, total_content_height - visible_height)
            self.case_files_scroll = max(0, min(self.case_files_scroll, max_scroll))
            
            # Create clipping rect for content area
            clip_rect = pygame.Rect(rect.x + margin_left, content_y, rect.width - margin_left - margin_right, visible_height)
            
            # Draw visible lines with scroll offset
            y_offset = content_y - self.case_files_scroll
            
            for line in all_lines:
                # Skip lines above visible area
                if y_offset + line_height < content_y:
                    y_offset += line_height
                    continue
                # Stop if below visible area
                if y_offset >= content_bottom:
                    break
                
                if line:  # Non-empty line
                    display_text = reshape_persian_text(line)
                    shadow_surf = FONT_FARSI_SMALL.render(display_text, True, COLOR_SHADOW)
                    text_surf = FONT_FARSI_SMALL.render(display_text, True, COLOR_TEXT)
                    # RTL: align from right, but clamp to left margin
                    text_x = rect.right - margin_right - text_surf.get_width()
                    text_x = max(text_x, rect.x + margin_left)  # Left margin clamp
                    
                    # Only draw if within visible area
                    if y_offset >= content_y and y_offset < content_bottom:
                        self.screen.blit(shadow_surf, (text_x + 1, y_offset + 1))
                        self.screen.blit(text_surf, (text_x, y_offset))
                
                y_offset += line_height
            
            # Draw scroll indicator if content is scrollable
            if max_scroll > 0:
                scroll_bar_height = max(20, int(visible_height * visible_height / total_content_height))
                scroll_bar_y = content_y + int((visible_height - scroll_bar_height) * self.case_files_scroll / max_scroll)
                scroll_bar_rect = pygame.Rect(rect.x + 15, scroll_bar_y, 6, scroll_bar_height)
                pygame.draw.rect(self.screen, (150, 140, 120), scroll_bar_rect, border_radius=3)
        else:
            # Show message if no case files text
            draw_text_with_shadow(self.screen, "پرونده‌ای موجود نیست", FONT_FARSI_SMALL, (120, 110, 100),
                                 (rect.centerx, rect.centery), shadow_offset=1, center=True)
    
    def _draw_accusation_state(self):
        """Draw the accusation selection screen with gothic styling"""
        # Draw blurred background image
        if self.accusation_background:
            self.screen.blit(self.accusation_background, (0, 0))
            # Add dark overlay for better text readability
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(COLOR_BG)
        
        # Draw warm tint
        draw_warm_tint(self.screen, alpha=12)
        
        # Title with gold and glow
        draw_glow(self.screen, (SCREEN_WIDTH // 2, 60), 80, COLOR_ACCENT, 40)
        draw_text_with_shadow(self.screen, "قاتل کیست؟", FONT_FARSI, COLOR_GOLD,
                             (SCREEN_WIDTH // 2, 55), shadow_offset=2, center=True)
        
        # Subtitle with shadow
        draw_text_with_shadow(self.screen, "با دقت انتخاب کنید - فقط یک شانس دارید!", FONT_FARSI_SMALL, COLOR_TEXT,
                             (SCREEN_WIDTH // 2, 120), shadow_offset=1, center=True)
        
        # Accusation buttons
        for button in self.accusation_buttons:
            button.draw(self.screen)
        
        # Draw vignette
        draw_vignette(self.screen)
    
    def _draw_suspect_selection_state(self):
        """Draw the suspect selection screen with gothic styling and hover effects"""
        self.screen.fill(COLOR_BG)
        
        # Draw warm tint
        draw_warm_tint(self.screen, alpha=10)
        
        # Day counter with gold glow
        day_num = to_persian_number(self.game_state.current_day)
        draw_glow(self.screen, (SCREEN_WIDTH // 2, 40), 60, COLOR_GLOW, 30)
        draw_text_with_shadow(self.screen, f"روز {day_num}", FONT_FARSI, COLOR_GOLD,
                             (SCREEN_WIDTH // 2, 35), shadow_offset=2, center=True)
        
        # Title with shadow
        draw_text_with_shadow(self.screen, "امروز با چه کسی صحبت می‌کنید؟", FONT_FARSI, COLOR_TEXT,
                             (SCREEN_WIDTH // 2, 80), shadow_offset=2, center=True)
        
        # Subtitle
        draw_text_with_shadow(self.screen, "یک مظنون را برای بازجویی انتخاب کنید", FONT_FARSI_SMALL, (160, 150, 140),
                             (SCREEN_WIDTH // 2, 120), shadow_offset=1, center=True)
        
        # Draw suspect cards in a grid (3 columns, 2 rows) with thumbnails
        thumb_width = int(SCREEN_WIDTH * 0.18)
        thumb_height = int(SCREEN_HEIGHT * 0.28)
        card_width = thumb_width + 20
        card_height = thumb_height + 50
        spacing_x = int(SCREEN_WIDTH * 0.04)
        spacing_y = int(SCREEN_HEIGHT * 0.03)
        
        total_width = 3 * card_width + 2 * spacing_x
        start_x = (SCREEN_WIDTH - total_width) // 2
        start_y = int(SCREEN_HEIGHT * 0.22)
        
        suspect_names = [
            "آهنگر",
            "راهبه",
            "تاجر",
            "سرباز",
            "پسرک",
            "آشپز"
        ]
        
        # Get mouse position for hover detection
        mouse_pos = pygame.mouse.get_pos()
        
        for i, button in enumerate(self.suspect_buttons):
            col = i % 3
            row = i // 3
            
            x = start_x + col * (card_width + spacing_x)
            y = start_y + row * (card_height + spacing_y)
            
            card_rect = pygame.Rect(x, y, card_width, card_height)
            is_hovered = card_rect.collidepoint(mouse_pos)
            
            # Update hover progress for this card
            if is_hovered:
                self.card_hover_progress[i] = min(1.0, self.card_hover_progress[i] + 0.15)
            else:
                self.card_hover_progress[i] = max(0.0, self.card_hover_progress[i] - 0.1)
            
            hover_progress = self.card_hover_progress[i]
            
            # Calculate scaled card size for hover effect
            scale_factor = 1.0 + hover_progress * 0.05
            scaled_card_width = int(card_width * scale_factor)
            scaled_card_height = int(card_height * scale_factor)
            scaled_x = x - (scaled_card_width - card_width) // 2
            scaled_y = y - (scaled_card_height - card_height) // 2
            scaled_rect = pygame.Rect(scaled_x, scaled_y, scaled_card_width, scaled_card_height)
            
            # Draw glow behind hovered card
            if hover_progress > 0:
                glow_alpha = int(40 * hover_progress)
                draw_glow(self.screen, (scaled_rect.centerx, scaled_rect.centery), 
                         scaled_card_width // 2 + 20, COLOR_GLOW, glow_alpha)
            
            # Draw card background with gothic styling
            bg_color = lerp_color(COLOR_PANEL, (60, 55, 50), hover_progress)
            pygame.draw.rect(self.screen, bg_color, scaled_rect, border_radius=12)
            
            # Draw gothic border
            border_color = lerp_color(COLOR_BORDER_DARK, COLOR_GOLD, hover_progress)
            pygame.draw.rect(self.screen, COLOR_BORDER_DARK, scaled_rect, 4, border_radius=12)
            inner_border_rect = scaled_rect.inflate(-6, -6)
            pygame.draw.rect(self.screen, border_color, inner_border_rect, 2, border_radius=10)
            
            # Draw thumbnail
            if i < len(self.character_thumbnails) and self.character_thumbnails[i]:
                thumb = self.character_thumbnails[i]
                scaled_thumb_width = int(thumb_width * scale_factor)
                scaled_thumb_height = int(thumb_height * scale_factor)
                scaled_thumb = pygame.transform.smoothscale(thumb, (scaled_thumb_width, scaled_thumb_height))
                thumb_x = scaled_x + (scaled_card_width - scaled_thumb_width) // 2
                thumb_y = scaled_y + int(10 * scale_factor)
                self.screen.blit(scaled_thumb, (thumb_x, thumb_y))
            
            # Draw character name with shadow
            name_center_x = scaled_x + scaled_card_width // 2
            name_area_top = scaled_y + int(10 * scale_factor) + int(thumb_height * scale_factor)
            name_area_bottom = scaled_y + scaled_card_height
            name_y = name_area_top + (name_area_bottom - name_area_top) // 2
            
            name_color = lerp_color(COLOR_TEXT, COLOR_GOLD, hover_progress)
            draw_text_with_shadow(self.screen, suspect_names[i], FONT_FARSI_SMALL, name_color,
                                 (name_center_x, name_y), shadow_offset=1, center=True)
            
            # Update button rect for click detection
            button.rect = card_rect
        
        # Draw vignette
        draw_vignette(self.screen)
    
    def _draw_end_state(self):
        """Draw win or lose screen with gothic styling"""
        # Draw win/lose image as full-screen background (no blur)
        if self.state == "win" and self.win_img:
            scaled_bg = pygame.transform.smoothscale(self.win_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
            self.screen.blit(scaled_bg, (0, 0))
            # Add dark overlay for better text readability
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            self.screen.blit(overlay, (0, 0))
        elif self.state == "lose" and self.lose_img:
            scaled_bg = pygame.transform.smoothscale(self.lose_img, (SCREEN_WIDTH, SCREEN_HEIGHT))
            self.screen.blit(scaled_bg, (0, 0))
            # Add dark overlay for better text readability
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 100))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill(COLOR_BG)
        
        # Draw warm tint
        draw_warm_tint(self.screen, alpha=15)
        
        # Position text in center of screen
        text_start_y = SCREEN_HEIGHT // 2 - 50
        
        if self.state == "win":
            # Win state - gold styling
            draw_glow(self.screen, (SCREEN_WIDTH // 2, text_start_y + 15), 150, COLOR_GOLD, 40)
            draw_text_with_shadow(self.screen, "پرونده حل شد", 
                                 pygame.font.Font("assets/Vazirmatn.ttf", 48), (150, 220, 130),
                                 (SCREEN_WIDTH // 2, text_start_y), shadow_offset=3, center=True)
            draw_text_with_shadow(self.screen, "راهبه با انگیزه‌های افراطی، گدا را به قتل رساند تا شهر را نجات دهد", 
                                 FONT_FARSI_SMALL, (180, 170, 150),
                                 (SCREEN_WIDTH // 2, text_start_y + 95), shadow_offset=1, center=True)
        else:
            # Lose state - burgundy styling
            draw_glow(self.screen, (SCREEN_WIDTH // 2, text_start_y + 15), 150, COLOR_ACCENT, 40)
            draw_text_with_shadow(self.screen, "پرونده حل نشد", 
                                 pygame.font.Font("assets/Vazirmatn.ttf", 48), (220, 100, 100),
                                 (SCREEN_WIDTH // 2, text_start_y), shadow_offset=3, center=True)
            draw_text_with_shadow(self.screen, ".قاتل به خاطر اتهام اشتباه شما از مجازات فرار کرد", 
                                 FONT_FARSI_SMALL, (180, 170, 150),
                                 (SCREEN_WIDTH // 2, text_start_y + 95), shadow_offset=1, center=True)
        
        # Case files button (bottom left corner)
        end_btn_size = 80
        case_files_end_x = 20
        case_files_end_y = SCREEN_HEIGHT - end_btn_size - 20
        if self.case_files_btn_img_scaled:
            self.screen.blit(self.case_files_btn_img_scaled, (case_files_end_x, case_files_end_y))
        
        # Notebook button (to the right of case files)
        notebook_end_x = case_files_end_x + end_btn_size + 15
        notebook_end_y = case_files_end_y
        if self.notebook_btn_img_scaled:
            self.screen.blit(self.notebook_btn_img_scaled, (notebook_end_x, notebook_end_y))
        
        # Store positions for click detection on end screen
        self._end_case_files_rect = pygame.Rect(case_files_end_x, case_files_end_y, end_btn_size, end_btn_size)
        self._end_notebook_rect = pygame.Rect(notebook_end_x, notebook_end_y, end_btn_size, end_btn_size)
        
        # Return to menu button (bottom right)
        menu_button_x = SCREEN_WIDTH - 220
        menu_button_y = SCREEN_HEIGHT - 70
        if not hasattr(self, 'end_menu_button') or self.end_menu_button is None:
            self.end_menu_button = Button(
                menu_button_x,
                menu_button_y,
                200,
                50,
                "بازگشت به منو",
                FONT_FARSI_SMALL,
                COLOR_ACCENT
            )
        self.end_menu_button.draw(self.screen)
        
        # Draw vignette
        draw_vignette(self.screen)
        
        # Notebook popup overlay (if visible) - READ ONLY
        if self.notebook_visible:
            # Semi-transparent dark overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(150)
            self.screen.blit(overlay, (0, 0))
            
            # Draw notebook panel with background
            self._draw_notebook_with_background()
            
            # Draw close button
            self.notebook_close_button.draw(self.screen)
            
            # Draw "read only" indicator
            readonly_text = reshape_persian_text("(فقط خواندنی)")
            readonly_surf = FONT_FARSI_SMALL.render(readonly_text, True, (150, 150, 150))
            readonly_x = self.notebook_panel.rect.centerx - readonly_surf.get_width() // 2
            readonly_y = self.notebook_panel.rect.bottom + 10
            self.screen.blit(readonly_surf, (readonly_x, readonly_y))
        
        # Case files popup overlay (if visible)
        if self.case_files_visible:
            # Semi-transparent dark overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.fill((0, 0, 0))
            overlay.set_alpha(150)
            self.screen.blit(overlay, (0, 0))
            
            # Draw case files panel with background
            self._draw_case_files_panel()
            
            # Draw close button (reusing notebook close button)
            self.notebook_close_button.draw(self.screen)
    
    def handle_events(self):
        """Handle all events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == "credits":
                        self.state = "menu"
                    else:
                        self.running = False
                elif event.key == pygame.K_F11:
                    self.toggle_fullscreen()
            
            if self.state == "menu":
                if self.menu_start_button.handle_event(event):
                    self._start_new_game()
                if self.menu_delete_save_button.handle_event(event):
                    # Only delete if save exists
                    import os
                    if os.path.exists("savegame.json"):
                        self._delete_save()
                if self.menu_music_button.handle_event(event):
                    self.music_enabled = not self.music_enabled
                    # Music functionality placeholder - would control audio here
                if self.menu_credits_button.handle_event(event):
                    self.state = "credits"
                if self.menu_settings_button.handle_event(event):
                    self.state = "settings"
                    self.settings_status_message = ""
                    # Reload settings when entering settings screen
                    self._create_settings_ui()
                if self.menu_exit_button.handle_event(event):
                    self.running = False
            
            elif self.state == "settings":
                # Ensure settings UI is initialized
                if not hasattr(self, 'settings_api_toggle'):
                    self._create_settings_ui()
                
                # Handle escape to go back
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.state = "menu"
                    continue
                
                # Handle API toggle
                if self.settings_api_toggle.handle_event(event):
                    self.settings_api_mode = not self.settings_api_mode
                    if self.settings_api_mode:
                        self.settings_api_toggle.text = "✓ استفاده از API"
                        self.settings_api_toggle.color = COLOR_BUTTON_ACTIVE
                    else:
                        self.settings_api_toggle.text = "✗ استفاده از Ollama"
                        self.settings_api_toggle.color = COLOR_BUTTON
                
                # Handle text inputs
                self.settings_base_url.handle_event(event)
                self.settings_api_key.handle_event(event)
                self.settings_model.handle_event(event)
                self.settings_ollama_model.handle_event(event)
                
                # Handle save button
                if self.settings_save_button.handle_event(event):
                    self._save_settings()
                
                # Handle back button
                if self.settings_back_button.handle_event(event):
                    self.state = "menu"
            
            elif self.state == "credits":
                if self.credits_back_button.handle_event(event):
                    self.credits_scroll = 0  # Reset scroll when leaving
                    self.state = "menu"
                # Handle scroll wheel
                if event.type == pygame.MOUSEWHEEL:
                    self.credits_scroll -= event.y * 30  # Scroll 30px per wheel tick
                    self.credits_scroll = max(0, self.credits_scroll)
            
            elif self.state == "intro":
                # Handle skip button while streaming - skip directly to suspect selection
                if not self.intro_complete:
                    if self.intro_skip_button.handle_event(event):
                        self.intro_complete = True
                        self.intro_streaming = False
                        # Go directly to suspect selection
                        self.state = "suspect_selection"
                        self.ai_thinking = False
                        self.ai_response_ready = False
                        self.ai_response = ""
                        self.input_box.text = ""
                        continue
                
                # Allow proceeding when intro is complete (only on new clicks/keys)
                elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    self.state = "suspect_selection"
                    # Initialize game state
                    self.ai_thinking = False
                    self.ai_response_ready = False
                    self.ai_response = ""
                    
                    # Clear input
                    self.input_box.text = ""
            
            elif self.state == "load_recap":
                # Handle skip button while streaming - skip directly to suspect selection
                if not self.load_recap_complete:
                    if self.intro_skip_button.handle_event(event):
                        self.load_recap_complete = True
                        self.load_recap_streaming = False
                        self.state = "suspect_selection"
                        self.ai_thinking = False
                        self.ai_response_ready = False
                        self.ai_response = ""
                        self.input_box.text = ""
                        continue
                
                # Allow proceeding when recap is complete (only on new clicks/keys)
                elif event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    self.state = "suspect_selection"
                    self.ai_thinking = False
                    self.ai_response_ready = False
                    self.ai_response = ""
                    self.input_box.text = ""
            
            elif self.state == "playing":
                # If notebook is visible, handle notebook events first
                if self.notebook_visible:
                    # Close button
                    if self.notebook_close_button.handle_event(event):
                        self.notebook_visible = False
                        continue
                    
                    # Notebook panel events
                    if self.notebook_panel.handle_event(event):
                        continue
                    
                    # Click outside notebook to close
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if not self.notebook_panel.rect.collidepoint(event.pos):
                            self.notebook_visible = False
                        continue
                    
                    # ESC to close notebook
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.notebook_visible = False
                        continue
                    
                    continue  # Block other events while notebook is open
                
                # If case files is visible, handle case files events first
                if self.case_files_visible:
                    # Close button (reusing notebook close button)
                    if self.notebook_close_button.handle_event(event):
                        self.case_files_visible = False
                        self.case_files_scroll = 0  # Reset scroll when closing
                        continue
                    
                    # Mouse wheel scrolling for case files
                    if event.type == pygame.MOUSEWHEEL:
                        if hasattr(self, 'case_files_rect') and self.case_files_rect.collidepoint(pygame.mouse.get_pos()):
                            self.case_files_scroll -= event.y * 30  # Scroll 30px per wheel tick
                            self.case_files_scroll = max(0, self.case_files_scroll)
                        continue
                    
                    # Click outside case files panel to close
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if hasattr(self, 'case_files_rect') and not self.case_files_rect.collidepoint(event.pos):
                            self.case_files_visible = False
                            self.case_files_scroll = 0  # Reset scroll when closing
                        continue
                    
                    # ESC to close case files
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.case_files_visible = False
                        self.case_files_scroll = 0  # Reset scroll when closing
                        continue
                    
                    continue  # Block other events while case files is open
                
                # Notebook toggle button
                if self.notebook_toggle_button.handle_event(event):
                    self.notebook_visible = True
                    continue
                
                # Case files toggle button
                if self.case_files_toggle_button.handle_event(event):
                    self.case_files_visible = True
                    continue
                
                # Input box
                result = self.input_box.handle_event(event)
                if result == "submit":
                    self._ask_question()
                
                # Ask button
                if self.ask_button.handle_event(event):
                    self._ask_question()
                
                # End Day door button
                if self.end_day_door_button.handle_event(event):
                    self._end_day()
                
                # Accuse button
                if self.accuse_button.handle_event(event):
                    self._make_accusation()
                
                # Menu button
                if self.game_menu_button.handle_event(event):
                    self.state = "menu"
                
                # Dialogue scroll
                self.dialogue_area.handle_event(event)
            
            elif self.state == "suspect_selection":
                # Handle suspect selection with card layout (3 columns, 2 rows with thumbnails)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    
                    # Match the layout from _draw_suspect_selection_state
                    thumb_width = int(SCREEN_WIDTH * 0.18)
                    thumb_height = int(SCREEN_HEIGHT * 0.28)
                    card_width = thumb_width + 20
                    card_height = thumb_height + 50
                    spacing_x = int(SCREEN_WIDTH * 0.04)
                    spacing_y = int(SCREEN_HEIGHT * 0.03)
                    
                    total_width = 3 * card_width + 2 * spacing_x
                    start_x = (SCREEN_WIDTH - total_width) // 2
                    start_y = int(SCREEN_HEIGHT * 0.22)
                    
                    for i in range(6):
                        col = i % 3
                        row = i // 3
                        x = start_x + col * (card_width + spacing_x)
                        y = start_y + row * (card_height + spacing_y)
                        rect = pygame.Rect(x, y, card_width, card_height)
                        
                        if rect.collidepoint(mouse_pos):
                            self._select_suspect_for_day(i + 1)
                            break
            
            elif self.state == "accusation":
                # Accusation buttons
                for i, button in enumerate(self.accusation_buttons):
                    if button.handle_event(event):
                        self._accuse_suspect(i + 1)
            
            elif self.state in ["win", "lose"]:
                # If notebook is visible, handle notebook events (read-only, only navigation)
                if self.notebook_visible:
                    # Close button
                    if self.notebook_close_button.handle_event(event):
                        self.notebook_visible = False
                        continue
                    
                    # Only handle navigation buttons (prev/next), not text input
                    if self.notebook_panel.prev_button.handle_event(event):
                        total_pages = self.game_state.get_total_pages()
                        if self.notebook_panel.current_spread_index > 0:
                            self.notebook_panel.current_spread_index -= 1
                            self.notebook_panel._load_current_spread()
                        continue
                    
                    if self.notebook_panel.next_button.handle_event(event):
                        total_pages = self.game_state.get_total_pages()
                        max_spread = (total_pages - 1) // 2 if total_pages > 0 else 0
                        if self.notebook_panel.current_spread_index < max_spread:
                            self.notebook_panel.current_spread_index += 1
                            self.notebook_panel._load_current_spread()
                        continue
                    
                    # Click outside notebook to close
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if not self.notebook_panel.rect.collidepoint(event.pos):
                            self.notebook_visible = False
                        continue
                    
                    # ESC to close notebook
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.notebook_visible = False
                        continue
                    
                    continue  # Block other events while notebook is open
                
                # If case files is visible, handle case files events
                if self.case_files_visible:
                    # Close button (reusing notebook close button)
                    if self.notebook_close_button.handle_event(event):
                        self.case_files_visible = False
                        continue
                    
                    # Click outside case files panel to close
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if not self.notebook_panel.rect.collidepoint(event.pos):
                            self.case_files_visible = False
                        continue
                    
                    # ESC to close case files
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.case_files_visible = False
                        continue
                    
                    continue  # Block other events while case files is open
                
                # Notebook toggle button (use end screen position)
                if event.type == pygame.MOUSEBUTTONDOWN and hasattr(self, '_end_notebook_rect') and self._end_notebook_rect.collidepoint(event.pos):
                    self.notebook_visible = True
                    continue
                
                # Case files toggle button (use end screen position)
                if event.type == pygame.MOUSEBUTTONDOWN and hasattr(self, '_end_case_files_rect') and self._end_case_files_rect.collidepoint(event.pos):
                    self.case_files_visible = True
                    continue
                
                # Return to menu button
                if hasattr(self, 'end_menu_button') and self.end_menu_button and self.end_menu_button.handle_event(event):
                    self.game_state.save()
                    self.state = "menu"
    
    def update(self, dt: float):
        """Update game state and animations"""
        # Update global animation timer (convert ms to seconds)
        dt_seconds = dt / 1000.0
        self.animation_timer += dt_seconds
        
        # Update all buttons for hover animations
        if hasattr(self, 'menu_start_button'):
            self.menu_start_button.update(dt_seconds)
        if hasattr(self, 'menu_quit_button'):
            self.menu_quit_button.update(dt_seconds)
        if hasattr(self, 'intro_start_button'):
            self.intro_start_button.update(dt_seconds)
        if hasattr(self, 'recap_continue_button'):
            self.recap_continue_button.update(dt_seconds)
        if hasattr(self, 'notebook_toggle_button'):
            self.notebook_toggle_button.update(dt_seconds)
        if hasattr(self, 'case_files_toggle_button'):
            self.case_files_toggle_button.update(dt_seconds)
        if hasattr(self, 'notebook_close_button'):
            self.notebook_close_button.update(dt_seconds)
        if hasattr(self, 'ask_button'):
            self.ask_button.update(dt_seconds)
        if hasattr(self, 'accuse_button'):
            self.accuse_button.update(dt_seconds)
        if hasattr(self, 'back_button'):
            self.back_button.update(dt_seconds)
        if hasattr(self, 'end_day_button'):
            self.end_day_button.update(dt_seconds)
        if hasattr(self, 'end_menu_button'):
            self.end_menu_button.update(dt_seconds)
        if hasattr(self, 'menu_music_button'):
            self.menu_music_button.update(dt_seconds)
        if hasattr(self, 'menu_credits_button'):
            self.menu_credits_button.update(dt_seconds)
        if hasattr(self, 'menu_settings_button'):
            self.menu_settings_button.update(dt_seconds)
        if hasattr(self, 'credits_back_button'):
            self.credits_back_button.update(dt_seconds)
        if hasattr(self, 'settings_save_button'):
            self.settings_save_button.update(dt_seconds)
        if hasattr(self, 'settings_back_button'):
            self.settings_back_button.update(dt_seconds)
        if hasattr(self, 'settings_api_toggle'):
            self.settings_api_toggle.update(dt_seconds)
        
        # Update accusation buttons
        if hasattr(self, 'accusation_buttons'):
            for button in self.accusation_buttons:
                button.update(dt_seconds)
        
        if self.state == "settings":
            # Update settings text boxes
            if hasattr(self, 'settings_base_url'):
                self.settings_base_url.update(dt)
            if hasattr(self, 'settings_api_key'):
                self.settings_api_key.update(dt)
            if hasattr(self, 'settings_model'):
                self.settings_model.update(dt)
            if hasattr(self, 'settings_ollama_model'):
                self.settings_ollama_model.update(dt)
        
        if self.state == "playing":
            self.input_box.update(dt)
            
            # Update portrait fade animation
            self.character_portrait.update(dt)
              # Check if AI response is ready
            if self.ai_response_ready:
                self.ai_thinking = False                
                self.ai_response_ready = False
                
                # Re-enable input and ask button after response is complete
                self.input_box.is_disabled = False
                self.ask_button.is_disabled = False
                
                # Finish streaming display
                self.dialogue_area.finish_streaming()
                
                # Parse emotion tag from response using new Farsi-aware parser
                from ai_handler import parse_emotion_tag
                image_filename, cleaned_response, emotion_tag = parse_emotion_tag(
                    self.ai_response, 
                    self.current_suspect
                )
                
                # Convert to emotion key for comparison (remove .jpg extension)
                emotion_key = image_filename.replace(".jpg", "")
                
                print(f"[DEBUG] Current emotion: '{self.current_emotion}'")
                print(f"[DEBUG] New emotion key: '{emotion_key}'")
                print(f"[DEBUG] Image filename: '{image_filename}'")
                print(f"[Portrait Update] Suspect {self.current_suspect}: '{emotion_tag}' → '{image_filename}'")
                
                # Update portrait with image filename (with fade animation)
                if emotion_key != self.current_emotion:
                    print(f"[EMOTION CHANGE] '{self.current_emotion}' → '{emotion_key}'")
                    self.character_portrait.set_suspect_and_emotion(
                        self.current_suspect, 
                        image_filename, 
                        immediate=False  # Use fade animation
                    )
                    # Update tracked emotion
                    self.current_emotion = emotion_key
                else:
                    print(f"[NO CHANGE] Emotion remains '{self.current_emotion}'")

    
    def draw(self):
        """Draw everything"""
        if self.state == "loading":
            self._draw_loading_state()
        elif self.state == "menu":
            self._draw_menu_state()
        elif self.state == "credits":
            self._draw_credits_state()
        elif self.state == "settings":
            self._draw_settings_state()
        elif self.state == "intro":
            self._draw_intro_state()
        elif self.state == "load_recap":
            self._draw_load_recap_state()
        elif self.state == "playing":
            self._draw_playing_state()
        elif self.state == "suspect_selection":
            self._draw_suspect_selection_state()
        elif self.state == "accusation":
            self._draw_accusation_state()
        elif self.state in ["win", "lose"]:
            self._draw_end_state()
        
        pygame.display.flip()
    
    def run(self):
        """Main game loop"""
        while self.running:
            dt = self.clock.tick(FPS)
            
            self.handle_events()
            self.update(dt)
            self.draw()
        
        pygame.quit()
        sys.exit()


def main():
    """Entry point"""
    # Set UTF-8 encoding for console output
    import sys
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("بازی کارآگاهی هوش مصنوعی - قتل گدای بزرگ")
    print("AI DETECTIVE GAME - The Beggar's Murder")
    print("=" * 60)
    print("\nشروع بازی... | Starting game...")
    print("توجه: راه‌اندازی موتور هوش مصنوعی ممکن است چند لحظه طول بکشد.")
    print("Note: AI engine initialization may take a moment.")
    print("\nاستفاده از مدل Ollama (gemma3n)")
    print("Using Ollama model (gemma3n)")
    print("=" * 60)
    
    game = DetectiveGame()
    game.run()


if __name__ == "__main__":
    main()
