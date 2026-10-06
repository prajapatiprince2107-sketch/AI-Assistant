import os
from pathlib import Path

OLLAMA_MODEL = "llama3.2:3b"

MAX_HISTORY = 20

PROJECT_DIR = Path(__file__).parent
MEMORY_FILE = PROJECT_DIR / "memory.json"
CONVERSATION_FILE = PROJECT_DIR / "conversation_history.json"
VOICE_INPUT_FILE = PROJECT_DIR / "voice_input.wav"

VOICES = {
    "gu": "gu-IN-DhwaniNeural",
    "hi": "hi-IN-SwaraNeural",
    "en": "en-IN-NeerjaNeural",
}

BG = "#0b1020"
PANEL = "#11182b"
CHAT_BG = "#080d18"
TEXT = "#f5f7ff"
MUTED = "#9ba7c0"
ACCENT = "#6c63ff"
CYAN = "#00d4ff"
GREEN = "#35e08f"
RED = "#ff5c70"

WAKE_WORDS = [
    "hey shalu",
    "hi shalu",
    "hello shalu",
    "hey shalu ji",
]

JOKES = [
    "Why did the computer go to the doctor? Because it had a virus!",
    "Why was the math book sad? Because it had too many problems!",
    "Why did the bicycle fall over? Because it was two-tired!",
    "What do you call a fake noodle? An impasta!",
    "Why did the programmer quit his job? Because he didn't get arrays!",
]
