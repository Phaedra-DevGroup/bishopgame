"""
AI Handler Module for Detective Game
Manages persona-driven chat using LlamaIndex and Ollama or OpenAI-compatible API
Character data is loaded from character_database.json via game_data module
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import urllib.request
import urllib.error
import re
import httpx
import game_data
import settings as ai_settings
from llama_index.core import Settings
from llama_index.core.chat_engine import SimpleChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.llms.ollama import Ollama
from typing import Any

# Import OpenAI SDK for API mode
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai package not installed. API mode will not work.")
    print("Install with: pip install openai")

# Import specific Ollama ResponseError for better error handling
try:
    from ollama._types import ResponseError
except Exception:
    ResponseError = None


def check_ollama_health(base_url: str = "http://localhost:11434", timeout: float = 5.0) -> tuple[bool, str]:
    """
    Check if Ollama server is running and responsive
    
    Args:
        base_url: URL of the Ollama server
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (is_healthy, status_message)
    """
    try:
        import time
        client = httpx.Client(timeout=httpx.Timeout(timeout))
        
        # Try to ping the server
        response = client.get(base_url)
        
        if response.status_code == 200:
            return True, "Ollama server is running"
        else:
            return False, f"Ollama server returned status {response.status_code}"
    except httpx.ConnectError:
        return False, "Cannot connect to Ollama server - is it running?"
    except httpx.TimeoutException:
        return False, "Ollama server is not responding (timeout)"
    except Exception as e:
        return False, f"Ollama health check failed: {e}"


def parse_emotion_tag(response: str, suspect_id: int) -> Tuple[str, str, str]:
    """
    Parse emotion tag from response and map to image filename
    
    Args:
        response: AI response text
        suspect_id: Character ID (1-6)
        
    Returns:
        Tuple of (image_filename, cleaned_response, emotion_tag)
        - image_filename: The .jpg filename to use for portrait
        - cleaned_response: Response text without emotion tag
        - emotion_tag: The extracted emotion name (for logging)    """
    print(f"\n[EMOTION PARSER] Analyzing response for suspect {suspect_id}")
    print(f"[EMOTION PARSER] Response length: {len(response)} chars")
    
    # CLEAN MALFORMED AI OUTPUT FIRST
    # Remove Python formatting artifacts that AI sometimes copies
    response = re.sub(r"\{'='[*]\d+\}", "", response)  # Remove {'='*60}
    response = re.sub(r'\{["\']=["\'][*]\d+\}', "", response)  # Remove other variants
    response = response.strip()
    
    print(f"[EMOTION PARSER] Last 100 chars: ...{response[-100:]}")
    
    # Look for [emotion] tag anywhere in response (Farsi or English)
    # Some AIs put tags at the end, others put them mid-response like stage directions
    # Strategy: Try end first, then search anywhere, prioritize last occurrence
    
    # Pattern 1: Try to find tag at the very end (most common)
    pattern_end = r'\[([^\]]+)\]\s*["\']?\s*$'
    match = re.search(pattern_end, response)
    
    # Pattern 2: If not found at end, find ALL tags and use the LAST one
    if not match:
        pattern_any = r'\[([^\]]+)\]'
        all_matches = list(re.finditer(pattern_any, response))
        if all_matches:
            match = all_matches[-1]  # Use last match
            print(f"[EMOTION PARSER] Found tag mid-response (using last occurrence)")
    
    if match:
        emotion_tag = match.group(1).strip()
        # Remove the tag from response - handle both end and mid-response positions
        cleaned = response[:match.start()] + response[match.end():]
        cleaned = cleaned.strip()
        
        print(f"[EMOTION PARSER] ✓ Found tag: '{emotion_tag}'")
        
        # Try to map this emotion to an image filename
        image_filename, is_valid = game_data.map_emotion_to_image(suspect_id, emotion_tag)
        
        if is_valid:
            print(f"[Emotion Detected] ✓ '{emotion_tag}' → {image_filename}")
        else:
            print(f"[Emotion Fallback] ⚠ Invalid '{emotion_tag}', using default: {image_filename}")
            # Show available emotions
            emotion_mapping = game_data.get_emotion_mapping(suspect_id)
            print(f"[Available Emotions] {list(emotion_mapping.keys())}")
        
        return image_filename, cleaned, emotion_tag
    
    # No tag found - use character's default emotion
    print(f"[EMOTION PARSER] ⚠ No emotion tag found in response!")
    print(f"[No Emotion Tag] Using default for suspect {suspect_id}")
    from game_state import get_default_emotion
    default_emotion_code = get_default_emotion(suspect_id)
    
    # Map default emotion code to image filename
    # Create reverse mapping from English codes to Farsi
    emotion_mapping = game_data.get_emotion_mapping(suspect_id)
    default_image = emotion_mapping.get("default", "other.jpg")
    
    print(f"[EMOTION PARSER] Default image: {default_image}")
    
    return default_image, response, "default"


def clean_response(response: str) -> str:
    """Remove emotion tag from response"""
    _, cleaned = parse_emotion_tag(response)
    return cleaned


class AIDetectiveEngine:
    """Handles all AI operations for the detective game"""
    
    def __init__(self, model_name: str = None, base_url: str = "http://localhost:11434"):
        """
        Initialize the AI engine with persona-driven chat capabilities
        Automatically detects whether to use Ollama or OpenAI API based on settings.
        
        Args:
            model_name: Name of the Ollama model to use (default: from settings)
            base_url: URL of the Ollama server (default: http://localhost:11434)
        """
        # Load settings
        self.use_api = ai_settings.is_api_mode()
        self.api_config = ai_settings.get_api_config()
        
        # Get model name from settings if not provided
        if model_name is None:
            model_name = ai_settings.get_ollama_model()
        
        self.model_name = model_name
        self.openai_client = None
        self.llm = None
        
        print("\n" + "="*60)
        print("AI DETECTIVE ENGINE INITIALIZATION")
        print("="*60)
        
        # Initialize generated_intro storage
        self.generated_intro = ""
        
        # Initialize chat history for API mode
        self.api_chat_histories = {}  # Store chat histories per suspect for API mode
        
        if self.use_api and OPENAI_AVAILABLE:
            self._init_openai_api()
        else:
            self._init_ollama(model_name, base_url)
        
        # Initialize chat engines storage (for Ollama mode)
        self.chat_engines = {}  # Store chat engines per suspect
        
        print("\n" + "="*60)
        print("✓ AI ENGINE INITIALIZED SUCCESSFULLY!")
        print("  Character data loaded from character_database.json")
        print("="*60 + "\n")
    
    def _init_openai_api(self):
        """Initialize OpenAI-compatible API client"""
        print(f"\n[1/2] Initializing OpenAI-compatible API...")
        print(f"      Base URL: {self.api_config['base_url']}")
        print(f"      Model: {self.api_config['model']}")
        
        try:
            self.openai_client = OpenAI(
                base_url=self.api_config['base_url'],
                api_key=self.api_config['api_key']
            )
            self.api_model = self.api_config['model']
            print("      [OK] OpenAI API client initialized successfully")
            
        except Exception as e:
            print(f"      ⚠ Failed to initialize OpenAI API: {e}")
            print("      Falling back to Ollama...")
            self.use_api = False
            self._init_ollama(self.model_name, "http://localhost:11434")
            return
        
        # Configure global settings (minimal for API mode)
        print(f"\n[2/2] Configuring settings...")
        Settings.chunk_size = 256
        Settings.chunk_overlap = 25
        print("      ✓ Settings configured")
    
    def _init_ollama(self, model_name: str, base_url: str):
        """Initialize Ollama LLM"""
        print(f"\n[1/2] Initializing Ollama LLM...")
        print(f"      Model: {model_name}")
        print(f"      URL: {base_url}")
        print(f"      Context Window: 4096 tokens (optimized)")
        
        try:
            # Create custom httpx client with extended timeout
            http_client = httpx.Client(timeout=httpx.Timeout(300.0, connect=60.0))
            
            self.llm = Ollama(
                model=model_name,
                base_url=base_url,
                request_timeout=300.0,  # 5 minutes timeout for large context
                temperature=0.7,
                context_window=4096,  # Optimized for performance
                keep_alive="1h",  # Keep model loaded for 1 hour
                num_predict=150,  # Balanced response length (~150 tokens)
                additional_kwargs={
                    "num_ctx": 4096,  # Match context window
                },
                http_client=http_client  # Use custom client with long timeout
            )
            print("      [OK] LLM initialized successfully")
            
        except Exception as e:
            print(f"      ⚠ Failed to initialize Ollama: {e}")
            print("      Make sure Ollama is running and the model is pulled!")
            raise e
        
        # Configure global settings
        print(f"\n[2/2] Configuring LlamaIndex settings...")
        Settings.llm = self.llm
        Settings.chunk_size = 256
        Settings.chunk_overlap = 25
        print("      ✓ Settings configured")
    
    def _openai_complete(self, prompt: str, max_tokens: int = 400, stream_callback=None) -> str:
        """
        Generate completion using OpenAI-compatible API
        
        Args:
            prompt: The prompt text
            max_tokens: Maximum tokens to generate
            stream_callback: Optional callback for streaming
            
        Returns:
            Generated text
        """
        messages = [{"role": "user", "content": prompt}]
        
        if stream_callback:
            # Streaming mode
            response = self.openai_client.chat.completions.create(
                model=self.api_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
                stream=True
            )
            full_response = ""
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_response += token
                    stream_callback(token)
            return full_response
        else:
            # Non-streaming mode
            response = self.openai_client.chat.completions.create(
                model=self.api_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content
    
    def _openai_chat(self, system_prompt: str, user_message: str, chat_history: list = None, 
                     max_tokens: int = 200, stream_callback=None) -> str:
        """
        Generate chat completion using OpenAI-compatible API
        
        Args:
            system_prompt: System prompt for the character
            user_message: User's message
            chat_history: Previous chat messages
            max_tokens: Maximum tokens to generate
            stream_callback: Optional callback for streaming
            
        Returns:
            Generated response
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat history if provided
        if chat_history:
            messages.extend(chat_history)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        if stream_callback:
            # Streaming mode
            response = self.openai_client.chat.completions.create(
                model=self.api_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
                stream=True
            )
            full_response = ""
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_response += token
                    stream_callback(token)
            return full_response
        else:
            # Non-streaming mode
            response = self.openai_client.chat.completions.create(
                model=self.api_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content
    
    def generate_game_intro(self, stream_callback=None) -> str:
        """
        Generate an AI-powered story intro for the game.
        This also serves as a warm-up for the model.
        
        Args:
            stream_callback: Optional callback function to receive streaming tokens
            
        Returns:
            The generated intro text in Persian
        """
        intro_prompt = """تو یک نویسنده داستان جنایی هستی. یک مقدمه کوتاه و جذاب برای یک بازی کارآگاهی بنویس.

داستان:
- یک گدای محبوب در قرن دوازدهم در مدجوگوریه (بوسنی) به قتل رسیده است
- گدا به روشنگری معنوی رسیده بود و مردم او را دوست داشتند
- ۸۰۰ سال بعد، شش مظنون به طرز مرموزی در یک اتاق بازجویی مدرن در واشنگتن زنده شده‌اند
- آنها هنوز لباس‌های قرون وسطایی به تن دارند و گیج هستند
- کارآگاه باید با بازجویی از آنها قاتل را پیدا کند

مظنونان:
۱. آهنگر (گارون) - سازنده اسلحه، چاقوی قتل شبیه کار اوست
۲. راهبه (سرا) - زنی مذهبی با رازهای تاریک
۳. تاجر (برانکو) - محبوبیت گدا به تجارتش ضربه زده بود
۴. سرباز (رونان) - شاید از کاخ دستور گرفته باشد
۵. پسرک (میکائیل) - ۱۳ ساله که با گدا برای صدقه رقابت می‌کرد
۶. آشپز (دراگان) - داروی خواب‌آور تهیه می‌کرد

دستورالعمل:
- ۳ یا ۴ پاراگراف کوتاه بنویس
- لحن مرموز و جذاب باشد
- از دید سوم شخص بنویس
- فقط متن داستان را بنویس، بدون عنوان یا توضیح اضافی
- به فارسی بنویس"""

        print("      Generating story intro (warming up model)...")
        sys.stdout.flush()
        
        try:
            if self.use_api and self.openai_client:
                # Use OpenAI API
                self.generated_intro = self._openai_complete(intro_prompt, max_tokens=400, stream_callback=stream_callback)
            else:
                # Use Ollama
                if stream_callback:
                    # Streaming mode
                    response_stream = self.llm.stream_complete(intro_prompt, num_predict=400)
                    full_response = ""
                    for token in response_stream:
                        token_text = token.delta if hasattr(token, 'delta') else str(token)
                        full_response += token_text
                        stream_callback(token_text)
                    self.generated_intro = full_response
                else:
                    # Non-streaming mode
                    response = self.llm.complete(intro_prompt, num_predict=400)
                    self.generated_intro = str(response)
            
            print("      ✓ Story intro generated")
            return self.generated_intro
            
        except Exception as e:
            print(f"      ⚠ Failed to generate intro: {e}")
            raise e
    
    def generate_load_recap(self, current_day: int, stream_callback=None) -> str:
        """
        Generate an AI-powered news update when loading a saved game.
        This also serves as a warm-up for the model.
        
        Args:
            current_day: The current day number from the save file
            stream_callback: Optional callback function to receive streaming tokens
            
        Returns:
            The generated news recap text in Persian
        """
        recap_prompt = f"""تو یک روزنامه‌نگار هستی. یک خبر کوتاه درباره روز {current_day} تحقیقات پرونده قتل بنویس.

پرونده:
- یک گدای محبوب در قرن دوازدهم در مدجوگوریه (بوسنی) به قتل رسیده بود
- گدا به روشنگری معنوی رسیده بود و مردم او را دوست داشتند
- ۸۰۰ سال بعد، شش مظنون به طرز مرموزی در واشنگتن زنده شده‌اند
- کارآگاهی غریبه در حال بازجویی از آنهاست

مظنونان: آهنگر، راهبه، تاجر، سرباز، پسرک، و آشپز

دستورالعمل:
- ۲ پاراگراف کوتاه بنویس
- شامل شایعات و حدس‌های مردم درباره قاتل باشد
- لحن خبری و مرموز باشد
- اشاره کن که این روز {current_day} تحقیقات است
- فقط متن خبر را بنویس، به فارسی"""

        print(f"      Generating load recap for day {current_day} (warming up model)...")
        sys.stdout.flush()
        
        try:
            if self.use_api and self.openai_client:
                # Use OpenAI API
                return self._openai_complete(recap_prompt, max_tokens=300, stream_callback=stream_callback)
            else:
                # Use Ollama
                if stream_callback:
                    # Streaming mode
                    response_stream = self.llm.stream_complete(recap_prompt, num_predict=300)
                    full_response = ""
                    for token in response_stream:
                        token_text = token.delta if hasattr(token, 'delta') else str(token)
                        full_response += token_text
                        stream_callback(token_text)
                    return full_response
                else:
                    # Non-streaming mode
                    response = self.llm.complete(recap_prompt, num_predict=300)
                    return str(response)
            
        except Exception as e:
            print(f"      ⚠ Failed to generate load recap: {e}")
            raise e

    def _get_suspect_persona(self, suspect_id: int) -> str:
        """
        Return the complete system prompt for the given suspect ID.
        Now uses the character database instead of hardcoded personas.
        """
        try:
            return game_data.get_character_system_prompt(suspect_id)
        except Exception as e:
            print(f"ERROR: Failed to get character prompt for suspect {suspect_id}: {e}")
            # Fallback to minimal prompt
            return "You are a suspect in a murder investigation. Answer carefully."
    
    def _create_system_prompt(self, suspect_id: int) -> str:
        """
        Create a system prompt for a specific suspect
        Now just returns the full database prompt (backward compatibility wrapper)
        
        Args:
            suspect_id: ID of the suspect (1-6)
            
        Returns:
            System prompt string
        """
        return self._get_suspect_persona(suspect_id)
    
    def get_suspect_response(
        self, 
        suspect_id: int, 
        player_question: str,
        chat_history: Optional[List[Dict[str, str]]] = None,
        streaming: bool = False,
        stream_callback = None
    ) -> str:
        """
        Get a response from a suspect using RAG and persona-driven chat
        
        Args:
            suspect_id: ID of the suspect (1-4)
            player_question: The player's question
            chat_history: Previous chat history (optional)
            streaming: If True, stream the response token by token
            stream_callback: Function to call with each token (if streaming)
            
        Returns:
            The suspect's response
        """
        try:
            # First, retrieve relevant context from the knowledge base
            print("\n" + "="*60)
            print("AI RESPONSE GENERATION")
            print("="*60)
            print(f"\n[Step 1/2] Player Question:")
            print(f"           {player_question}")
            
            # Check if using API mode
            if self.use_api and self.openai_client:
                return self._get_suspect_response_api(suspect_id, player_question, streaming, stream_callback)
            else:
                return self._get_suspect_response_ollama(suspect_id, player_question, streaming, stream_callback)
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"\n{'='*50}")
            print(f"ERROR in get_suspect_response:")
            print(f"{'='*50}")
            print(error_trace)
            print(f"{'='*50}\n")
            # Fallback response that includes the error type
            error_type = type(e).__name__
            return f"*شخصیت عصبی به نظر می‌رسد* من... من... ({error_type}: {str(e)[:100]})"
    
    def _get_suspect_response_api(self, suspect_id: int, player_question: str, 
                                   streaming: bool, stream_callback) -> str:
        """Get response using OpenAI-compatible API"""
        print(f"\n[Step 2/2] Preparing API chat for suspect #{suspect_id}...")
        
        system_prompt = self._create_system_prompt(suspect_id)
        
        # DEBUG: Save full system prompt to file for verification
        debug_file = f"debug_prompt_suspect_{suspect_id}.txt"
        try:
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"=== SYSTEM PROMPT FOR SUSPECT {suspect_id} ===\n")
                f.write(f"Length: {len(system_prompt)} characters\n")
                f.write("="*60 + "\n\n")
                f.write(system_prompt)
            print(f"           [DEBUG] Saved full prompt to {debug_file}")
        except Exception as e:
            print(f"           [DEBUG] Could not save prompt: {e}")
        
        # Initialize chat history for this suspect if needed
        if suspect_id not in self.api_chat_histories:
            self.api_chat_histories[suspect_id] = []
            print(f"           Creating NEW chat history (first conversation)")
        else:
            print(f"           ✓ Using existing chat history (conversation continues)")
        
        chat_history = self.api_chat_histories[suspect_id]
        prompt_preview = system_prompt[:150].replace('\n', ' ')
        print(f"           System prompt: {prompt_preview}...")
        
        print(f"\n           Generating AI response via API...")
        print(f"           Mode: {'STREAMING' if streaming else 'STANDARD'}")
        sys.stdout.flush()
        
        # Get response
        if streaming and stream_callback:
            print(f"           Streaming response", end="", flush=True)
            response_text = self._openai_chat(
                system_prompt, player_question, chat_history, 
                max_tokens=200, stream_callback=stream_callback
            )
            print()  # New line after streaming
        else:
            print(f"           Waiting for response", end="", flush=True)
            response_text = self._openai_chat(
                system_prompt, player_question, chat_history, 
                max_tokens=200
            )
            print(" done.")
        
        # Store the conversation in history
        chat_history.append({"role": "user", "content": player_question})
        chat_history.append({"role": "assistant", "content": response_text})
        
        # Keep history manageable (last 10 exchanges = 20 messages)
        if len(chat_history) > 20:
            self.api_chat_histories[suspect_id] = chat_history[-20:]
        
        print(f"\n           ✓ Response received ({len(response_text)} characters)")
        print(f"\n" + "="*60)
        print(f"RESPONSE: {response_text}")
        print("="*60 + "\n")
        
        return response_text
    
    def _get_suspect_response_ollama(self, suspect_id: int, player_question: str,
                                      streaming: bool, stream_callback) -> str:
        """Get response using Ollama (original implementation)"""
        # Create or get chat engine for this suspect
        print(f"\n[Step 2/2] Preparing chat engine for suspect #{suspect_id}...")
        if suspect_id not in self.chat_engines:
            print(f"           Creating NEW chat engine (first conversation)")
            system_prompt = self._create_system_prompt(suspect_id)
            
            # DEBUG: Save full system prompt to file for verification
            debug_file = f"debug_prompt_suspect_{suspect_id}.txt"
            try:
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(f"=== SYSTEM PROMPT FOR SUSPECT {suspect_id} ===\n")
                    f.write(f"Length: {len(system_prompt)} characters\n")
                    f.write("="*60 + "\n\n")
                    f.write(system_prompt)
                print(f"           [DEBUG] Saved full prompt to {debug_file}")
            except Exception as e:
                print(f"           [DEBUG] Could not save prompt: {e}")
            
            prompt_preview = system_prompt[:150].replace('\n', ' ')
            print(f"           System prompt: {prompt_preview}...")
            
            # Create a simple chat engine (only 1 LLM call instead of 3+)
            print(f"           Building SimpleChatEngine (fast mode)...")
            memory = ChatMemoryBuffer.from_defaults(token_limit=4500)  # Leave room for system prompt (~1200 tokens)
            self.chat_engines[suspect_id] = SimpleChatEngine.from_defaults(
                llm=self.llm,
                memory=memory,
                system_prompt=system_prompt,
            )
            print(f"           ✓ Chat engine created (1 LLM call per response)")
            sys.stdout.flush()
        else:
            print(f"           ✓ Using existing chat engine (conversation continues)")
            sys.stdout.flush()
        
        chat_engine = self.chat_engines[suspect_id]
        
        # Get response from the chat engine
        print(f"\n           Generating AI response...")
        print(f"           Sending question to LLM (1 call)...")
        print(f"           Mode: {'STREAMING' if streaming else 'STANDARD'}")
        
        if suspect_id not in self.chat_engines or len(self.chat_engines) == 1:
            print(f"           ⏱️  FIRST RESPONSE: This may take 60-120 seconds due to large context")
        else:
            print(f"           ⏱️  Subsequent responses: 15-45 seconds")
        
        sys.stdout.flush()
        if streaming and stream_callback:
            # Stream response token by token with retry logic
            print(f"           Streaming response", end="", flush=True)
            
            max_retries = 3
            backoff = 1.0
            full_response = ""
            success = False
            
            for attempt in range(max_retries):
                try:
                    response_stream = chat_engine.stream_chat(player_question)
                    full_response = ""
                    
                    for token in response_stream.response_gen:
                        print(".", end="", flush=True)
                        full_response += token
                        stream_callback(token)
                    
                    success = True
                    break
                except Exception as e:
                    if ResponseError is not None and isinstance(e, ResponseError):
                        print(f"\n           ⚠ Ollama ResponseError on streaming attempt {attempt+1}/{max_retries}: {e}")
                    else:
                        print(f"\n           ⚠ Error on streaming attempt {attempt+1}/{max_retries}: {e}")
                    
                    if attempt < max_retries - 1:
                        import time
                        print(f"           Retrying in {backoff:.1f}s...")
                        time.sleep(backoff)
                        backoff *= 2
                    else:
                        # Final attempt failed - re-raise
                        raise
            
            print()  # New line after dots
            response_text = full_response
        else:
            # Standard non-streaming response
            print(f"           Waiting for response", end="", flush=True)
            
            # Show dots while waiting
            import threading
            stop_dots = threading.Event()
            def print_dots():
                while not stop_dots.is_set():
                    print(".", end="", flush=True)
                    stop_dots.wait(2)
            
            dot_thread = threading.Thread(target=print_dots, daemon=True)
            dot_thread.start()
            
            try:
                # Retry logic for transient Ollama server errors (503)
                max_retries = 3
                backoff = 1.0
                response = None
                for attempt in range(max_retries):
                    try:
                        response = chat_engine.chat(player_question)
                        break
                    except Exception as e:
                        # If we have ResponseError type, check status
                        if ResponseError is not None and isinstance(e, ResponseError):
                            print(f"           ⚠ Ollama ResponseError on attempt {attempt+1}: {e}")
                        else:
                            print(f"           ⚠ Error on attempt {attempt+1}: {e}")
                        if attempt < max_retries - 1:
                            import time
                            time.sleep(backoff)
                            backoff *= 2
                        else:
                            # If final attempt failed, re-raise to be handled by outer except
                            raise
            finally:
                stop_dots.set()
                dot_thread.join(timeout=0.1)
                print()  # New line after dots
            
            response_text = str(response)
        
        print(f"\n           ✓ Response received ({len(response_text)} characters)")
        print(f"\n" + "="*60)
        print(f"RESPONSE: {response_text}")
        print("="*60 + "\n")
        
        return response_text
    
    def reset_chat(self, suspect_id: int):
        """
        Reset the chat history for a specific suspect
        
        Args:
            suspect_id: ID of the suspect to reset
        """
        if suspect_id in self.chat_engines:
            del self.chat_engines[suspect_id]
        if suspect_id in self.api_chat_histories:
            del self.api_chat_histories[suspect_id]
            
    def reset_all_chats(self):
        """Reset all chat histories"""
        self.chat_engines.clear()
        self.api_chat_histories.clear()
    
    def get_suspect_name(self, suspect_id: int) -> str:
        """Get the name of a suspect by ID"""
        names = {
            1: "آهنگر",
            2: "راهبه",
            3: "تاجر",
            4: "سرباز",
            5: "پسرک",
            6: "آشپز"
        }
        return names.get(suspect_id, "Unknown")


# Test function
if __name__ == "__main__":
    print("Testing AI Detective Engine...")
    engine = AIDetectiveEngine()
    
    # Test with suspect 2 (the murderer)
    print("\nTesting with The Nun (the murderer):")
    response = engine.get_suspect_response(2, "شما دیشب کجا بودید؟")
    print(f"Response: {response}")
    
    print("\nTest complete!")
