import tkinter as tk
from tkinter import scrolledtext
import threading
import asyncio
import os
import re
import json
import subprocess
import webbrowser
import time
import ctypes
import platform
import shutil
from collections import deque
from pathlib import Path

import numpy as np
from datetime import datetime
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from html import unescape

import ollama

try:
    import psutil
except ImportError:
    psutil = None
import edge_tts
import speech_recognition as sr
import sounddevice as sd
from scipy.io.wavfile import write


# =========================================================
# SHALU AI 9.9.34
# =========================================================

MODEL = "llama3.2:3b"

MEMORY_FILE = "memory.json"
CONVERSATION_FILE = "conversation_history.json"
INPUT_FILE = "voice_input.wav"

MAX_HISTORY = 20

# 🎤 LAPTOP MICROPHONE
MIC_DEVICE = None

# 🎙️ FEMALE VOICES
VOICES = {
    "gu": "gu-IN-DhwaniNeural",
    "hi": "hi-IN-SwaraNeural",
    "en": "en-IN-NeerjaNeural"
}


# =========================================================
# GUI COLORS
# =========================================================

BG = "#0b1020"
PANEL = "#11182b"
CHAT_BG = "#080d18"

TEXT = "#f5f7ff"
MUTED = "#9ba7c0"

ACCENT = "#6c63ff"
CYAN = "#00d4ff"
GREEN = "#35e08f"
RED = "#ff5c70"


# =========================================================
# OPTIONAL TAVILY
# =========================================================

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None


TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


if TavilyClient and TAVILY_API_KEY:

    tavily = TavilyClient(
        api_key=TAVILY_API_KEY
    )

else:

    tavily = None


# =========================================================
# GLOBAL STATES
# =========================================================

voice_busy = False
continuous_mode = False
speaking_now = False


# =========================================================
# MEMORY
# =========================================================

def load_memory():

    if not os.path.exists(MEMORY_FILE):
        return {}

    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception:

        return {}


def save_memory():

    try:

        with open(
            MEMORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                memory,
                file,
                ensure_ascii=False,
                indent=4
            )

    except Exception as error:

        print(
            "Memory error:",
            error
        )


memory = load_memory()


# =========================================================
# CONVERSATION HISTORY
# =========================================================

def load_conversation():

    if not os.path.exists(CONVERSATION_FILE):
        return []

    try:

        with open(
            CONVERSATION_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):
            return data[-MAX_HISTORY:]

    except Exception as error:

        print(
            "Conversation history load error:",
            error
        )

    return []


def save_conversation():

    try:

        with open(
            CONVERSATION_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                conversation_history[-MAX_HISTORY:],
                file,
                ensure_ascii=False,
                indent=4
            )

    except Exception as error:

        print(
            "Conversation history save error:",
            error
        )


conversation_history = load_conversation()


def add_history(
    role,
    content
):

    conversation_history.append({

        "role": role,

        "content": content

    })


    if len(
        conversation_history
    ) > MAX_HISTORY:

        del conversation_history[
            :-MAX_HISTORY
        ]

    save_conversation()


def get_recent_context():

    if not conversation_history:
        return ""

    recent = conversation_history[-10:]

    lines = []

    for item in recent:

        role = item.get("role", "user").capitalize()
        content = item.get("content", "").strip()

        if content:
            lines.append(
                f"{role}: {content}"
            )

    return "\n".join(lines)


# =========================================================
# LANGUAGE DETECTION
# =========================================================

def detect_language(text):

    # Gujarati script
    if re.search(
        r'[\u0A80-\u0AFF]',
        text
    ):

        return "gu"


    # Hindi script
    if re.search(
        r'[\u0900-\u097F]',
        text
    ):

        return "hi"


    words = text.lower().split()


    # Roman Gujarati
    gu_words = [

        "shu",
        "su",
        "kem",
        "chhe",
        "che",
        "tame",
        "tu",
        "maru",
        "mare",
        "mane",
        "kai",
        "kya",
        "kyare",
        "have",
        "pachi",
        "karvu",
        "karie",
        "joie",
        "nathi",
        "haan",
        "aaje",
        "apde",
        "mara",
        "tari",
        "tane",
        "thay",
        "thase",
        "sakay",
        "saku",
        "bol",
        "aapde",
        "aap",
        "mokal",
        "kari",
        "kare",
        "kar",
        "joi",
        "padse",
        "baddha",
        "badhha",
        "ghar",
        "kale",
        "aaje"

    ]


    gu_count = sum(

        1
        for word in words
        if word in gu_words

    )


    if gu_count >= 2:

        return "gu"


    # Roman Hindi
    hi_words = [

        "kya",
        "hai",
        "haan",
        "nahi",
        "mujhe",
        "mera",
        "meri",
        "tum",
        "aap",
        "kaise",
        "karna",
        "batao",
        "abhi",
        "aaj",
        "mujhko",
        "kyun",
        "karo"

    ]


    hi_count = sum(

        1
        for word in words
        if word in hi_words

    )


    if hi_count >= 2:

        return "hi"


    return "en"


# =========================================================
# TEXT TO SPEECH
# =========================================================

async def make_voice(
    text,
    voice,
    filename
):

    communicate = edge_tts.Communicate(

        text,

        voice,

        rate="-8%",

        pitch="-1Hz"

    )


    await communicate.save(
        filename
    )


def speak(
    text,
    language="en"
):

    global speaking_now

    if not text:
        return

    speaking_now = True

    voice = VOICES.get(
        language,
        VOICES["en"]
    )

    # Keep the voice folder clean: remove older Shalu TTS clips.
    for old_file in os.listdir("."):
        if old_file.startswith("shalu_voice_") and old_file.endswith(".mp3"):
            try:
                os.remove(old_file)
            except Exception:
                pass

    filename = os.path.abspath("shalu_voice_latest.mp3")

    for attempt in range(3):
        try:
            update_status(
                "🔊 Shalu is speaking..."
            )

            asyncio.run(
                make_voice(
                    text,
                    voice,
                    filename
                )
            )

            if (
                os.path.exists(filename)
                and os.path.getsize(filename) > 1000
            ):
                print(
                    "🔊 Voice created:",
                    filename
                )

                os.startfile(filename)

                # Give Windows the time to start playback.
                time.sleep(0.7)

                speaking_now = False
                update_status("🟢 Shalu is ready")
                return

        except Exception as error:
            print(
                f"TTS attempt {attempt + 1}/3 failed:",
                error
            )
            if attempt < 2:
                time.sleep(1)

    speaking_now = False
    print("TTS failed after 3 attempts.")
    update_status("🟢 Shalu is ready")


# =========================================================
# MICROPHONE
# =========================================================

def _find_working_microphone():
    """Find a usable Windows input device instead of relying on a fixed ID."""
    candidates = []

    try:
        devices = sd.query_devices()
        default_input = sd.default.device[0]

        if isinstance(default_input, int) and default_input >= 0:
            candidates.append(default_input)

        preferred_words = (
            "intel array",
            "microphone array",
            "microphone",
            "mic",
        )

        for index, device in enumerate(devices):
            if device.get("max_input_channels", 0) <= 0:
                continue
            name = str(device.get("name", "")).lower()
            if any(word in name for word in preferred_words):
                candidates.append(index)

        for index, device in enumerate(devices):
            if device.get("max_input_channels", 0) > 0:
                candidates.append(index)

        seen = set()
        for index in candidates:
            if index in seen:
                continue
            seen.add(index)
            try:
                info = sd.query_devices(index, "input")
                if info.get("max_input_channels", 0) <= 0:
                    continue
                sd.check_input_settings(
                    device=index,
                    samplerate=16000,
                    channels=1,
                    dtype="int16",
                )
                return index, str(info.get("name", f"Device {index}"))
            except Exception as error:
                print(f"Skipping microphone device {index}: {error}")

    except Exception as error:
        print("Microphone device scan failed:", error)

    return None, "No usable microphone"


def listen():
    update_status("👂 Waiting for speech...")

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 250
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 0.8
    recognizer.phrase_threshold = 0.3
    recognizer.non_speaking_duration = 0.5

    sample_rate = 16000
    channels = 1
    block_seconds = 0.10
    block_frames = int(sample_rate * block_seconds)
    max_wait_seconds = 8.0
    max_speech_seconds = 12.0
    silence_after_speech = 1.15
    preroll_seconds = 0.30

    try:
        device_index, device_name = _find_working_microphone()
        if device_index is None:
            print("❌ No usable microphone found.")
            update_status("❌ No usable microphone")
            return ""

        print(f"🎤 Microphone Device: {device_index} - {device_name}")
        update_status("🎤 Microphone ready — speak now...")

        calibration = sd.rec(
            int(0.5 * sample_rate),
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
            device=device_index,
        )
        sd.wait()

        noise_rms = float(np.sqrt(np.mean(calibration.astype(np.float32) ** 2)))
        threshold = max(350.0, noise_rms * 2.0)
        print(f"🎚️ Noise level: {noise_rms:.0f}, speech threshold: {threshold:.0f}")

        started = time.monotonic()
        speech_started = False
        speech_start_time = None
        silence_start = None

        pre_roll_blocks = max(1, int(preroll_seconds / block_seconds))
        pre_roll = deque(maxlen=pre_roll_blocks)
        chunks = []

        stream = sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype="int16",
            blocksize=block_frames,
            device=device_index,
        )
        stream.start()

        try:
            while True:
                if continuous_mode is False and voice_busy:
                    return ""

                data, overflowed = stream.read(block_frames)
                data = np.asarray(data, dtype=np.int16).reshape(-1, 1)
                pre_roll.append(data.copy())

                rms = float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))
                now = time.monotonic()

                if not speech_started:
                    if rms >= threshold:
                        speech_started = True
                        speech_start_time = now
                        silence_start = None
                        chunks.extend(list(pre_roll))
                        update_status("🎤 Listening... keep speaking")
                    elif now - started >= max_wait_seconds:
                        print("⌛ No speech detected.")
                        return ""
                else:
                    chunks.append(data.copy())

                    if rms < threshold:
                        if silence_start is None:
                            silence_start = now
                        elif now - silence_start >= silence_after_speech:
                            break
                    else:
                        silence_start = None

                    if speech_start_time is not None and now - speech_start_time >= max_speech_seconds:
                        break
        finally:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

        if not chunks:
            return ""

        recording = np.concatenate(chunks, axis=0)
        write(INPUT_FILE, sample_rate, recording)
        print("🎧 Recording complete.")

    except Exception as error:
        print("Microphone error:", error)
        update_status("❌ Microphone error — check Windows mic access")
        return ""

    try:
        with sr.AudioFile(INPUT_FILE) as source:
            audio = recognizer.record(source)

        print("🧠 Converting speech to text...")

        recognition_languages = ["en-IN", "hi-IN", "gu-IN"]
        for recognition_language in recognition_languages:
            try:
                text = recognizer.recognize_google(audio, language=recognition_language)
                if text and text.strip():
                    print(f"Prince ({recognition_language}):", text)
                    return text.strip()
            except sr.UnknownValueError:
                continue

        print("Shalu: I could hear the microphone, but I couldn't understand the speech.")
        return ""

    except sr.UnknownValueError:
        print("Shalu: Sorry Prince, mane samjhayu nahi.")
        return ""
    except sr.RequestError as error:
        print("Shalu: Speech recognition mate internet joiye.", error)
        return ""
    except Exception as error:
        print("Speech recognition error:", error)
        return ""


# =========================================================
# MEMORY COMMANDS
# =========================================================

def memory_command(command):

    global memory


    lower = command.lower().strip()


    if lower.startswith(
        "remember that"
    ):

        value = command[
            len("remember that"):
        ].strip()


        if value:

            notes = memory.get(
                "notes",
                []
            )


            notes.append(
                value
            )


            memory["notes"] = notes


            save_memory()


            return (

                "Okay Prince, "
                "I will remember that."

            )


    if "my name is" in lower:

        value = command.split(

            "is",

            1

        )[1].strip()


        memory["name"] = value


        save_memory()


        return (

            f"Okay Prince, "
            f"I will remember your name is "
            f"{value}."

        )


    if (

        "what do you remember"
        in lower

        or

        "show my memory"
        in lower

    ):

        if not memory:

            return (

                "Prince, I don't have "
                "anything saved yet."

            )


        result = []


        if "name" in memory:

            result.append(

                f"your name is "
                f"{memory['name']}"

            )


        for note in memory.get(

            "notes",

            []

        ):

            result.append(
                note
            )


        return (

            "Prince, I remember: "

            + ". ".join(result)

        )


    return None


# =========================================================
# SYSTEM INFORMATION 2.0
# =========================================================

def system_information(command):

    lower = command.lower()

    # PC / Windows information
    if (
        "pc information" in lower
        or
        "computer information" in lower
        or
        "system information" in lower
        or
        "system info" in lower
        or
        "pc info" in lower
    ):

        system_name = platform.system()
        release = platform.release()
        version = platform.version()
        machine = platform.machine()

        return (
            f"Prince, your computer is running "
            f"{system_name} {release}. "
            f"System version is {version}. "
            f"Architecture is {machine}."
        )


    # Computer name
    if (
        "computer name" in lower
        or
        "pc name" in lower
        or
        "hostname" in lower
    ):

        return (
            f"Prince, your computer name is "
            f"{platform.node()}."
        )


    # CPU information
    if (
        "cpu information" in lower
        or
        "cpu info" in lower
        or
        "processor information" in lower
        or
        "processor info" in lower
    ):

        cpu_name = platform.processor()

        if not cpu_name:
            cpu_name = "CPU information is not available."

        if psutil:
            cores = psutil.cpu_count(logical=False)
            threads = psutil.cpu_count(logical=True)

            return (
                f"Prince, your processor is "
                f"{cpu_name}. "
                f"It has {cores or 'unknown'} physical cores "
                f"and {threads or 'unknown'} logical processors."
            )

        return (
            f"Prince, your processor is {cpu_name}."
        )


    # RAM information
    if (
        "ram usage" in lower
        or
        "ram information" in lower
        or
        "memory usage" in lower
        or
        "memory information" in lower
        or
        "how much ram" in lower
    ):

        if psutil:

            ram = psutil.virtual_memory()

            used_gb = ram.used / (1024 ** 3)
            total_gb = ram.total / (1024 ** 3)
            percent = ram.percent

            return (
                f"Prince, RAM usage is {percent:.1f} percent. "
                f"You are using {used_gb:.1f} GB "
                f"out of {total_gb:.1f} GB."
            )

        # Windows native fallback: total physical RAM.
        try:

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)

            if ctypes.windll.kernel32.GlobalMemoryStatusEx(
                ctypes.byref(status)
            ):

                total_gb = status.ullTotalPhys / (1024 ** 3)
                available_gb = status.ullAvailPhys / (1024 ** 3)
                used_gb = total_gb - available_gb

                return (
                    f"Prince, RAM usage is "
                    f"{status.dwMemoryLoad:.1f} percent. "
                    f"You are using {used_gb:.1f} GB "
                    f"out of {total_gb:.1f} GB."
                )

        except Exception:
            pass

        return (
            "Prince, I couldn't read the RAM usage."
        )


    # Disk information
    if (
        "disk space" in lower
        or
        "disk usage" in lower
        or
        "storage information" in lower
        or
        "storage info" in lower
        or
        "free space" in lower
    ):

        try:

            disk = shutil.disk_usage("C:\\")

            total_gb = disk.total / (1024 ** 3)
            used_gb = disk.used / (1024 ** 3)
            free_gb = disk.free / (1024 ** 3)

            return (
                f"Prince, your C drive has "
                f"{free_gb:.1f} GB free out of "
                f"{total_gb:.1f} GB. "
                f"About {used_gb:.1f} GB is used."
            )

        except Exception:

            return (
                "Prince, I couldn't read the disk information."
            )


    # Battery
    if (
        "battery status" in lower
        or
        "battery information" in lower
        or
        "battery info" in lower
        or
        "how much battery" in lower
    ):

        try:

            if psutil:

                battery = psutil.sensors_battery()

                if battery is None:
                    return (
                        "Prince, this computer does not report "
                        "battery information."
                    )

                percent = battery.percent

                if battery.power_plugged:
                    return (
                        f"Prince, battery is at {percent:.0f} percent "
                        f"and the charger is connected."
                    )

                return (
                    f"Prince, battery is at {percent:.0f} percent "
                    f"and the charger is not connected."
                )

            # Windows native fallback: no psutil required.
            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", ctypes.c_ubyte),
                    ("BatteryFlag", ctypes.c_ubyte),
                    ("BatteryLifePercent", ctypes.c_ubyte),
                    ("Reserved", ctypes.c_ubyte),
                    ("BatteryLifeTime", ctypes.c_ulong),
                    ("BatteryFullLifeTime", ctypes.c_ulong),
                ]

            status = SYSTEM_POWER_STATUS()

            if ctypes.windll.kernel32.GetSystemPowerStatus(
                ctypes.byref(status)
            ):

                percent = status.BatteryLifePercent

                if percent == 255:
                    return (
                        "Prince, Windows could not report "
                        "the battery percentage."
                    )

                if status.ACLineStatus == 1:
                    return (
                        f"Prince, battery is at {percent} percent "
                        f"and the charger is connected."
                    )

                return (
                    f"Prince, battery is at {percent} percent "
                    f"and the charger is not connected."
                )

        except Exception:
            pass

        return (
            "Prince, I couldn't read the battery status."
        )


    return None


# =========================================================
# SMART ACTIONS 2.0
# =========================================================

def smart_actions(command):

    lower = command.lower().strip()


    # -----------------------------------------------------
    # OPEN COMMON WEBSITES
    # -----------------------------------------------------

    websites = {
        "open gmail": "https://mail.google.com",
        "open github": "https://github.com",
        "open chatgpt": "https://chatgpt.com",
        "open python": "https://www.python.org",
        "open google drive": "https://drive.google.com",
        "open whatsapp web": "https://web.whatsapp.com",
    }

    for phrase, url in websites.items():

        if lower == phrase:

            webbrowser.open(url)

            return (
                f"Opening {phrase.replace('open ', '')}, Prince."
            )


    # -----------------------------------------------------
    # SAFE CALCULATOR
    # -----------------------------------------------------

    if (
        lower.startswith("calculate ")
        or
        lower.startswith("calculate:")
    ):

        expression = command.split(
            "calculate",
            1
        )[1].strip().lstrip(":").strip()

        # Only permit numbers and basic arithmetic symbols.
        if expression and re.fullmatch(
            r"[0-9\s\+\-\*\/\(\)\.\%\^]+",
            expression
        ):

            try:

                expression = expression.replace(
                    "^",
                    "**"
                )

                # eval is restricted to the validated character set
                # and has no builtins/globals available.
                result = eval(
                    expression,
                    {
                        "__builtins__": {}
                    },
                    {}
                )

                return (
                    f"Prince, the answer is {result}."
                )

            except Exception:

                return (
                    "Prince, I couldn't calculate that expression."
                )

        return (
            "Prince, I can calculate numbers using +, -, *, /, "
            "parentheses and percent."
        )


    # -----------------------------------------------------
    # CREATE QUICK NOTE
    # -----------------------------------------------------

    if (
        lower.startswith("make a note ")
        or
        lower.startswith("take a note ")
        or
        lower.startswith("save a note ")
    ):

        if lower.startswith("make a note "):

            note = command[len("make a note "):].strip()

        elif lower.startswith("take a note "):

            note = command[len("take a note "):].strip()

        else:

            note = command[len("save a note "):].strip()

        if not note:

            return (
                "Prince, tell me what you want me to save."
            )

        notes_dir = os.path.join(
            os.path.expanduser("~"),
            "Documents"
        )

        os.makedirs(
            notes_dir,
            exist_ok=True
        )

        notes_file = os.path.join(
            notes_dir,
            "Shalu_Notes.txt"
        )

        timestamp = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        with open(
            notes_file,
            "a",
            encoding="utf-8"
        ) as file:

            file.write(
                f"[{timestamp}] {note}\n"
            )

        return (
            "Done Prince. I saved your note in "
            "Documents\\Shalu_Notes.txt."
        )


    # -----------------------------------------------------
    # OPEN SHALU NOTES
    # -----------------------------------------------------

    if (
        lower == "open my notes"
        or
        lower == "open shalu notes"
    ):

        notes_file = os.path.join(
            os.path.expanduser("~"),
            "Documents",
            "Shalu_Notes.txt"
        )

        if not os.path.exists(notes_file):

            return (
                "Prince, you don't have any saved notes yet."
            )

        os.startfile(notes_file)

        return (
            "Opening your Shalu notes, Prince."
        )


    # -----------------------------------------------------
    # FIND A FILE IN USER FOLDERS
    # -----------------------------------------------------

    if (
        lower.startswith("find file ")
        or
        lower.startswith("search file ")
    ):

        if lower.startswith("find file "):

            target = command[len("find file "):].strip()

        else:

            target = command[len("search file "):].strip()

        if not target:

            return (
                "Prince, tell me the file name to search for."
            )

        roots = [
            os.path.join(
                os.path.expanduser("~"),
                "Desktop"
            ),
            os.path.join(
                os.path.expanduser("~"),
                "Documents"
            ),
            os.path.join(
                os.path.expanduser("~"),
                "Downloads"
            )
        ]

        matches = []
        target_lower = target.lower()

        for root in roots:

            if not os.path.exists(root):
                continue

            for current_root, dirs, files in os.walk(root):

                # Avoid huge hidden/system-like directories.
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith(".")
                ]

                for filename in files:

                    if target_lower in filename.lower():

                        matches.append(
                            os.path.join(
                                current_root,
                                filename
                            )
                        )

                        if len(matches) >= 5:
                            break

                if len(matches) >= 5:
                    break

            if len(matches) >= 5:
                break

        if not matches:

            return (
                f"Prince, I couldn't find a file matching "
                f"'{target}' in Desktop, Documents or Downloads."
            )

        result = (
            f"Prince, I found {len(matches)} matching file"
            f"{'s' if len(matches) != 1 else ''}:\n"
        )

        result += "\n".join(
            f"{index}. {path}"
            for index, path in enumerate(
                matches,
                start=1
            )
        )

        return result


    # -----------------------------------------------------
    # SIMPLE TIMER
    # -----------------------------------------------------

    timer_match = re.fullmatch(
        r"(?:set )?timer(?: for)?\s+(\d+)\s*"
        r"(second|seconds|minute|minutes|hour|hours)",
        lower
    )

    if timer_match:

        amount = int(
            timer_match.group(1)
        )

        unit = timer_match.group(2)

        if amount <= 0:

            return (
                "Prince, the timer must be greater than zero."
            )

        if "second" in unit:
            seconds = amount

        elif "minute" in unit:
            seconds = amount * 60

        else:
            seconds = amount * 3600

        def timer_done():

            time.sleep(seconds)

            if root.winfo_exists():

                message = (
                    f"Prince, your {amount} {unit} "
                    "timer is finished. ⏰"
                )

                root.after(
                    0,
                    lambda: add_chat(
                        "Shalu",
                        message
                    )
                )

                threading.Thread(
                    target=speak,
                    args=(message, "en"),
                    daemon=True
                ).start()

        threading.Thread(
            target=timer_done,
            daemon=True
        ).start()

        return (
            f"Done Prince. Timer set for "
            f"{amount} {unit}. ⏰"
        )


    return None


# =========================================================
# MICROPHONE TEST
# =========================================================

def microphone_test():

    update_status(
        "🎤 Testing microphone for 3 seconds..."
    )

    sample_rate = 16000

    try:

        recording = sd.rec(
            int(3 * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16"
        )

        sd.wait()

        peak = int(
            abs(recording).max()
        )

        if peak < 200:

            return (
                "Prince, the microphone is connected, "
                "but I am hearing almost no sound. "
                "Please check Windows microphone permission "
                "and make sure the correct mic is selected."
            )

        return (
            f"Prince, microphone test passed. "
            f"I detected your voice signal. Audio level: {peak}."
        )

    except Exception as error:

        print(
            "Microphone test error:",
            error
        )

        return (
            "Prince, microphone test failed. "
            "Please check that Windows has microphone access "
            "and that your microphone is connected."
        )


# =========================================================
# SMART COMMAND CHAINS 1.0
# =========================================================

def smart_command_chain(command):

    lower = command.lower().strip()

    # A chain uses the explicit word "then".
    if " then " not in lower:
        return None

    parts = [
        part.strip()
        for part in re.split(
            r"\s+then\s+",
            command,
            flags=re.IGNORECASE
        )
        if part.strip()
    ]

    if len(parts) < 2 or len(parts) > 5:
        return None

    replies = []
    executed = 0

    for part in parts:

        reply = smart_actions(part)

        if reply is None:
            reply = smart_automation(part)

        if reply is None:
            reply = smart_file_manager(part)

        if reply is None:
            # Do not run arbitrary shell commands as part of a chain.
            return (
                "Prince, I can chain only my built-in safe actions. "
                f"I don't know how to perform: '{part}'."
            )

        replies.append(reply)
        executed += 1

    return (
        f"Done Prince. I completed {executed} actions:\n"
        + "\n".join(
            f"{i}. {reply}"
            for i, reply in enumerate(
                replies,
                start=1
            )
        )
    )


# =========================================================
# SMART DESKTOP AUTOMATION 1.0
# =========================================================

def smart_automation(command):

    lower = command.lower().strip()


    # -----------------------------------------------------
    # OPEN A SMALL WORKSPACE
    # -----------------------------------------------------

    if (
        "open my workspace" in lower
        or
        "start my workspace" in lower
    ):

        subprocess.Popen(
            "explorer",
            shell=True
        )

        webbrowser.open(
            "https://chatgpt.com"
        )

        return (
            "Prince, your workspace is opening."
        )


    # -----------------------------------------------------
    # OPEN CODING WORKSPACE
    # -----------------------------------------------------

    if (
        "open coding workspace" in lower
        or
        "start coding workspace" in lower
    ):

        subprocess.Popen(
            "explorer",
            shell=True
        )

        subprocess.Popen(
            "cmd",
            shell=True
        )

        webbrowser.open(
            "https://www.python.org"
        )

        return (
            "Prince, your coding workspace is opening."
        )


    # -----------------------------------------------------
    # OPEN STUDY WORKSPACE
    # -----------------------------------------------------

    if (
        "open study workspace" in lower
        or
        "start study workspace" in lower
    ):

        subprocess.Popen(
            "explorer",
            shell=True
        )

        webbrowser.open(
            "https://chatgpt.com"
        )

        webbrowser.open(
            "https://www.google.com"
        )

        return (
            "Prince, your study workspace is opening."
        )


    # -----------------------------------------------------
    # OPEN COMMUNICATION WORKSPACE
    # -----------------------------------------------------

    if (
        "open communication workspace" in lower
        or
        "start communication workspace" in lower
    ):

        webbrowser.open(
            "https://web.whatsapp.com"
        )

        webbrowser.open(
            "https://mail.google.com"
        )

        return (
            "Prince, your communication workspace is opening."
        )


    return None


# =========================================================
# SMART FILE MANAGER 2.0
# =========================================================

FILE_MANAGER_CONFIRM = {
    "pending": False,
    "path": None,
}


def _user_search_roots():

    home = os.path.expanduser("~")

    return [
        os.path.join(home, "Desktop"),
        os.path.join(home, "Documents"),
        os.path.join(home, "Downloads"),
    ]


def _find_user_files(target, max_results=10):

    target = target.strip().lower()

    if not target:
        return []

    matches = []

    for root in _user_search_roots():

        if not os.path.exists(root):
            continue

        for current_root, dirs, files in os.walk(root):

            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
            ]

            for filename in files:

                if target in filename.lower():

                    matches.append(
                        os.path.join(
                            current_root,
                            filename
                        )
                    )

                    if len(matches) >= max_results:
                        return matches

    return matches


def smart_file_manager(command):

    global FILE_MANAGER_CONFIRM

    lower = command.lower().strip()


    # -----------------------------------------------------
    # CANCEL PENDING DELETE
    # -----------------------------------------------------

    if (
        FILE_MANAGER_CONFIRM["pending"]
        and
        lower in [
            "no",
            "cancel",
            "cancel delete",
            "don't delete",
            "do not delete"
        ]
    ):

        FILE_MANAGER_CONFIRM = {
            "pending": False,
            "path": None,
        }

        return (
            "Okay Prince, I cancelled the delete."
        )


    # -----------------------------------------------------
    # CONFIRM DELETE
    # -----------------------------------------------------

    if (
        FILE_MANAGER_CONFIRM["pending"]
        and
        lower in [
            "yes",
            "yes delete",
            "confirm",
            "confirm delete"
        ]
    ):

        path = FILE_MANAGER_CONFIRM["path"]

        FILE_MANAGER_CONFIRM = {
            "pending": False,
            "path": None,
        }

        if not path or not os.path.exists(path):

            return (
                "Prince, that file is no longer available."
            )

        try:

            os.remove(path)

            return (
                f"Done Prince. I deleted "
                f"'{os.path.basename(path)}'."
            )

        except Exception as error:

            print(
                "Delete error:",
                error
            )

            return (
                "Prince, I couldn't delete that file."
            )


    # -----------------------------------------------------
    # CREATE FOLDER
    # -----------------------------------------------------

    if (
        lower.startswith("create folder ")
        or
        lower.startswith("make folder ")
    ):

        if lower.startswith("create folder "):

            folder_name = command[
                len("create folder "):
            ].strip()

        else:

            folder_name = command[
                len("make folder "):
            ].strip()

        if not folder_name:

            return (
                "Prince, tell me the folder name."
            )

        # Keep creation inside Documents for safety.
        documents = os.path.join(
            os.path.expanduser("~"),
            "Documents"
        )

        safe_name = os.path.basename(
            folder_name
        )

        folder_path = os.path.join(
            documents,
            safe_name
        )

        try:

            os.makedirs(
                folder_path,
                exist_ok=True
            )

            return (
                f"Done Prince. Folder "
                f"'{safe_name}' is ready in Documents."
            )

        except Exception as error:

            print(
                "Create folder error:",
                error
            )

            return (
                "Prince, I couldn't create that folder."
            )


    # -----------------------------------------------------
    # CREATE TEXT FILE
    # -----------------------------------------------------

    if (
        lower.startswith("create file ")
        or
        lower.startswith("make file ")
    ):

        if lower.startswith("create file "):

            filename = command[
                len("create file "):
            ].strip()

        else:

            filename = command[
                len("make file "):
            ].strip()

        if not filename:

            return (
                "Prince, tell me the file name."
            )

        documents = os.path.join(
            os.path.expanduser("~"),
            "Documents"
        )

        safe_name = os.path.basename(
            filename
        )

        if not safe_name.lower().endswith(".txt"):

            safe_name += ".txt"

        file_path = os.path.join(
            documents,
            safe_name
        )

        try:

            if os.path.exists(file_path):

                return (
                    f"Prince, '{safe_name}' already exists."
                )

            with open(
                file_path,
                "w",
                encoding="utf-8"
            ) as file:

                file.write("")

            return (
                f"Done Prince. I created "
                f"'{safe_name}' in Documents."
            )

        except Exception as error:

            print(
                "Create file error:",
                error
            )

            return (
                "Prince, I couldn't create that file."
            )


    # -----------------------------------------------------
    # OPEN FILE BY NAME
    # -----------------------------------------------------

    if (
        lower.startswith("open file ")
        or
        lower.startswith("open file named ")
    ):

        if lower.startswith("open file named "):

            target = command[
                len("open file named "):
            ].strip()

        else:

            target = command[
                len("open file "):
            ].strip()

        matches = _find_user_files(
            target,
            max_results=5
        )

        if not matches:

            return (
                f"Prince, I couldn't find '{target}'."
            )

        if len(matches) > 1:

            result = (
                f"Prince, I found multiple files "
                f"matching '{target}'. Please use "
                f"a more specific name."
            )

            result += "\n" + "\n".join(
                f"{i}. {path}"
                for i, path in enumerate(
                    matches,
                    start=1
                )
            )

            return result

        try:

            os.startfile(matches[0])

            return (
                f"Opening '{os.path.basename(matches[0])}', "
                f"Prince."
            )

        except Exception:

            return (
                "Prince, I found the file but couldn't open it."
            )


    # -----------------------------------------------------
    # RENAME FILE
    # -----------------------------------------------------

    rename_match = re.match(
        r"^(?:rename file )(.+?)\s+to\s+(.+)$",
        command,
        flags=re.IGNORECASE
    )

    if rename_match:

        old_name = rename_match.group(1).strip()
        new_name = rename_match.group(2).strip()

        matches = _find_user_files(
            old_name,
            max_results=5
        )

        if not matches:

            return (
                f"Prince, I couldn't find '{old_name}'."
            )

        if len(matches) > 1:

            return (
                "Prince, I found more than one matching "
                "file. Please give me a more specific name."
            )

        old_path = matches[0]

        safe_new_name = os.path.basename(
            new_name
        )

        if not safe_new_name:

            return (
                "Prince, the new file name is empty."
            )

        new_path = os.path.join(
            os.path.dirname(old_path),
            safe_new_name
        )

        if os.path.exists(new_path):

            return (
                f"Prince, '{safe_new_name}' already exists."
            )

        try:

            os.rename(
                old_path,
                new_path
            )

            return (
                f"Done Prince. Renamed "
                f"'{os.path.basename(old_path)}' "
                f"to '{safe_new_name}'."
            )

        except Exception as error:

            print(
                "Rename error:",
                error
            )

            return (
                "Prince, I couldn't rename that file."
            )


    # -----------------------------------------------------
    # DELETE FILE — ALWAYS CONFIRM FIRST
    # -----------------------------------------------------

    if (
        lower.startswith("delete file ")
        or
        lower.startswith("remove file ")
    ):

        if lower.startswith("delete file "):

            target = command[
                len("delete file "):
            ].strip()

        else:

            target = command[
                len("remove file "):
            ].strip()

        matches = _find_user_files(
            target,
            max_results=5
        )

        if not matches:

            return (
                f"Prince, I couldn't find '{target}'."
            )

        if len(matches) > 1:

            return (
                "Prince, I found multiple matching files. "
                "Please give me a more specific name."
            )

        path = matches[0]

        FILE_MANAGER_CONFIRM = {
            "pending": True,
            "path": path,
        }

        return (
            f"Prince, I found "
            f"'{os.path.basename(path)}'. "
            f"Do you want me to delete it? "
            f"Reply YES or NO."
        )


    # -----------------------------------------------------
    # LIST FILES IN A FOLDER
    # -----------------------------------------------------

    if (
        lower == "list downloads"
        or
        lower == "show downloads"
    ):

        folder = os.path.join(
            os.path.expanduser("~"),
            "Downloads"
        )

        if not os.path.exists(folder):

            return (
                "Prince, I couldn't find your Downloads folder."
            )

        try:

            items = os.listdir(folder)

            if not items:

                return (
                    "Prince, your Downloads folder is empty."
                )

            shown = items[:15]

            result = (
                f"Prince, Downloads has "
                f"{len(items)} item(s). First items:\n"
            )

            result += "\n".join(
                f"{i}. {name}"
                for i, name in enumerate(
                    shown,
                    start=1
                )
            )

            return result

        except Exception:

            return (
                "Prince, I couldn't read your Downloads folder."
            )


    return None


# =========================================================
# COMPUTER CONTROL
# =========================================================

def computer_control(command):

    lower = command.lower().strip()


    if "open chrome" in lower:

        subprocess.Popen(
            "start chrome",
            shell=True
        )


        return (
            "Chrome is opening, Prince."
        )


    if "open notepad" in lower:

        subprocess.Popen(
            "notepad",
            shell=True
        )


        return (
            "Notepad is opening, Prince."
        )


    if "open calculator" in lower:

        subprocess.Popen(
            "calc",
            shell=True
        )


        return (
            "Calculator is opening, Prince."
        )


    if (

        "open command prompt"
        in lower

        or

        "open cmd"
        in lower

    ):

        subprocess.Popen(
            "cmd",
            shell=True
        )


        return (
            "Command Prompt is opening, Prince."
        )


    if "open google" in lower:

        webbrowser.open(
            "https://www.google.com"
        )


        return (
            "Google is opening, Prince."
        )


    if "open youtube" in lower:

        webbrowser.open(
            "https://www.youtube.com"
        )


        return (
            "YouTube is opening, Prince."
        )


    if "search google for" in lower:

        query = command.lower().split(

            "search google for",

            1

        )[1].strip()


        if query:

            webbrowser.open(

                "https://www.google.com/search?q="

                + quote_plus(query)

            )


            return (

                f"Searching Google for "
                f"{query}, Prince."

            )


    if "search youtube for" in lower:

        query = command.lower().split(

            "search youtube for",

            1

        )[1].strip()


        if query:

            webbrowser.open(

                "https://www.youtube.com/results?"
                "search_query="

                + quote_plus(query)

            )


            return (

                f"Searching YouTube for "
                f"{query}, Prince."

            )


    if (
        "open file explorer" in lower
        or
        "open explorer" in lower
        or
        "open my computer" in lower
    ):

        subprocess.Popen(
            "explorer",
            shell=True
        )

        return (
            "File Explorer is opening, Prince."
        )


    if (
        "open downloads" in lower
        or
        "open download folder" in lower
    ):

        downloads = os.path.join(
            os.path.expanduser("~"),
            "Downloads"
        )

        if os.path.exists(downloads):

            os.startfile(downloads)

            return (
                "Downloads folder is opening, Prince."
            )

        return (
            "Prince, I couldn't find the Downloads folder."
        )


    if (
        "open desktop" in lower
        or
        "open desktop folder" in lower
    ):

        desktop = os.path.join(
            os.path.expanduser("~"),
            "Desktop"
        )

        if os.path.exists(desktop):

            os.startfile(desktop)

            return (
                "Desktop is opening, Prince."
            )

        return (
            "Prince, I couldn't find the Desktop folder."
        )


    if (
        "open task manager" in lower
        or
        "open taskmanager" in lower
    ):

        subprocess.Popen(
            "taskmgr",
            shell=True
        )

        return (
            "Task Manager is opening, Prince."
        )


    if (
        "lock computer" in lower
        or
        "lock pc" in lower
    ):

        subprocess.Popen(
            "rundll32.exe user32.dll,LockWorkStation",
            shell=True
        )

        return (
            "Okay Prince, I'm locking the computer."
        )


    if "open d drive" in lower:

        os.startfile(
            "D:\\"
        )


        return (
            "D drive is opening, Prince."
        )


    # =====================================================
    # APP / MEDIA CONTROL 2.0
    # =====================================================

    # Volume up
    if (
        "volume up" in lower
        or
        "increase volume" in lower
        or
        "sound up" in lower
    ):

        for _ in range(5):

            ctypes.windll.user32.keybd_event(
                0xAF, 0, 0, 0
            )

            ctypes.windll.user32.keybd_event(
                0xAF, 0, 2, 0
            )

        return (
            "Volume increased, Prince."
        )


    # Volume down
    if (
        "volume down" in lower
        or
        "decrease volume" in lower
        or
        "sound down" in lower
    ):

        for _ in range(5):

            ctypes.windll.user32.keybd_event(
                0xAE, 0, 0, 0
            )

            ctypes.windll.user32.keybd_event(
                0xAE, 0, 2, 0
            )

        return (
            "Volume decreased, Prince."
        )


    # Mute / unmute
    if (
        "mute" in lower
        or
        "unmute" in lower
    ):

        ctypes.windll.user32.keybd_event(
            0xAD, 0, 0, 0
        )

        ctypes.windll.user32.keybd_event(
            0xAD, 0, 2, 0
        )

        return (
            "Okay Prince, I toggled the volume mute."
        )


    # Media play / pause
    if (
        "play music" in lower
        or
        "pause music" in lower
        or
        "play pause" in lower
        or
        "media play" in lower
    ):

        ctypes.windll.user32.keybd_event(
            0xB3, 0, 0, 0
        )

        ctypes.windll.user32.keybd_event(
            0xB3, 0, 2, 0
        )

        return (
            "Okay Prince, I toggled play and pause."
        )


    # Next track
    if (
        "next song" in lower
        or
        "next track" in lower
    ):

        ctypes.windll.user32.keybd_event(
            0xB0, 0, 0, 0
        )

        ctypes.windll.user32.keybd_event(
            0xB0, 0, 2, 0
        )

        return (
            "Next track, Prince."
        )


    # Previous track
    if (
        "previous song" in lower
        or
        "previous track" in lower
        or
        "last song" in lower
    ):

        ctypes.windll.user32.keybd_event(
            0xB1, 0, 0, 0
        )

        ctypes.windll.user32.keybd_event(
            0xB1, 0, 2, 0
        )

        return (
            "Previous track, Prince."
        )


    # Minimize current window
    if (
        "minimize window" in lower
        or
        "minimise window" in lower
    ):

        ctypes.windll.user32.keybd_event(
            0x5B, 0, 0, 0
        )

        ctypes.windll.user32.keybd_event(
            0x4D, 0, 0, 0
        )

        ctypes.windll.user32.keybd_event(
            0x4D, 0, 2, 0
        )

        ctypes.windll.user32.keybd_event(
            0x5B, 0, 2, 0
        )

        return (
            "Window minimized, Prince."
        )


    # Show desktop
    if (
        "show desktop" in lower
        or
        "go to desktop" in lower
    ):

        ctypes.windll.user32.keybd_event(
            0x5B, 0, 0, 0
        )

        ctypes.windll.user32.keybd_event(
            0x44, 0, 0, 0
        )

        ctypes.windll.user32.keybd_event(
            0x44, 0, 2, 0
        )

        ctypes.windll.user32.keybd_event(
            0x5B, 0, 2, 0
        )

        return (
            "Showing the desktop, Prince."
        )


    # Open Windows Settings
    if (
        "open settings" in lower
        or
        "open windows settings" in lower
    ):

        subprocess.Popen(
            "start ms-settings:",
            shell=True
        )

        return (
            "Windows Settings is opening, Prince."
        )


    # Open Paint
    if (
        "open paint" in lower
        or
        "open mspaint" in lower
    ):

        subprocess.Popen(
            "mspaint",
            shell=True
        )

        return (
            "Paint is opening, Prince."
        )


    # Open WordPad if available
    if "open wordpad" in lower:

        subprocess.Popen(
            "write",
            shell=True
        )

        return (
            "WordPad is opening, Prince."
        )


    if (

        "what time" in lower

        or

        "current time" in lower

        or

        "time now" in lower

    ):

        current_time = datetime.now().strftime(
            "%I:%M %p"
        )


        return (

            f"Prince, the time is "
            f"{current_time}."

        )


    if (

        "what date" in lower

        or

        "today date" in lower

        or

        "today's date" in lower

    ):

        current_date = datetime.now().strftime(
            "%d %B %Y"
        )


        return (

            f"Today is "
            f"{current_date}, Prince."

        )


    return None


# =========================================================
# WEB SEARCH
# =========================================================

def needs_web_search(command):

    lower = command.lower()


    keywords = [

        "latest",
        "today",
        "current",
        "news",
        "recent",
        "weather",
        "price",
        "stock",
        "online",
        "internet",
        "search web",
        "search the web",
        "search online",
        "look up",
        "google",
        "find online",

        "aaje",
        "atyare",
        "bhav",
        "khabar",
        "aaj",
        "abhi",
        "samachar"

    ]


    return any(

        word in lower

        for word in keywords

    )


def web_search(query):

    # -----------------------------------------------------
    # PRIMARY: Tavily
    # -----------------------------------------------------

    if tavily is not None:

        try:

            response = tavily.search(
                query=query,
                search_depth="basic",
                max_results=5
            )

            results = response.get(
                "results",
                []
            )

            if results:

                context = ""

                for index, result in enumerate(
                    results,
                    start=1
                ):

                    context += (
                        f"\nRESULT {index}\n"
                        f"TITLE: "
                        f"{result.get('title', '')}\n"
                        f"URL: "
                        f"{result.get('url', '')}\n"
                        f"CONTENT: "
                        f"{result.get('content', '')}\n"
                    )

                return context

        except Exception as error:

            print(
                "Tavily search error:",
                error
            )


    # -----------------------------------------------------
    # FALLBACK: DuckDuckGo HTML
    # -----------------------------------------------------

    try:

        search_url = (
            "https://html.duckduckgo.com/html/?q="
            + quote_plus(query)
        )

        request = Request(
            search_url,
            headers={
                "User-Agent":
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "Chrome/120 Safari/537.36"
            }
        )

        with urlopen(
            request,
            timeout=8
        ) as response:

            html_text = response.read().decode(
                "utf-8",
                errors="ignore"
            )

        # DuckDuckGo result blocks are intentionally parsed
        # conservatively so Shalu can still work without
        # an extra API package.
        blocks = re.findall(
            r'<div[^>]+class="result[^"]*"'
            r'[\s\S]*?</div>\s*</div>',
            html_text,
            flags=re.IGNORECASE
        )

        context = ""
        count = 0

        for block in blocks:

            title_match = re.search(
                r'class="result__a"[^>]*>(.*?)</a>',
                block,
                flags=re.IGNORECASE | re.DOTALL
            )

            snippet_match = re.search(
                r'class="result__snippet"[^>]*>(.*?)</',
                block,
                flags=re.IGNORECASE | re.DOTALL
            )

            url_match = re.search(
                r'class="result__url"[^>]*>(.*?)</a>',
                block,
                flags=re.IGNORECASE | re.DOTALL
            )

            if not title_match:
                continue

            title = re.sub(
                r"<[^>]+>",
                "",
                title_match.group(1)
            )

            snippet = ""

            if snippet_match:

                snippet = re.sub(
                    r"<[^>]+>",
                    "",
                    snippet_match.group(1)
                )

            result_url = ""

            if url_match:

                result_url = re.sub(
                    r"<[^>]+>",
                    "",
                    url_match.group(1)
                )

            title = unescape(
                " ".join(title.split())
            )

            snippet = unescape(
                " ".join(snippet.split())
            )

            result_url = unescape(
                " ".join(result_url.split())
            )

            count += 1

            context += (
                f"\nRESULT {count}\n"
                f"TITLE: {title}\n"
                f"URL: {result_url}\n"
                f"CONTENT: {snippet}\n"
            )

            if count >= 5:
                break

        if context:

            return context

    except Exception as error:

        print(
            "Fallback web search error:",
            error
        )


    return ""




# =========================================================
# AI BRAIN
# =========================================================

def ask_shalu(

    question,

    web_context=""

):

    memory_text = json.dumps(

        memory,

        ensure_ascii=False

    )

    recent_context = get_recent_context()


    if web_context:

        prompt = f"""

User question:

{question}


Web information:

{web_context}


Use the web information when it is relevant to the user's question.

Treat the web results as current external information.
Do not invent facts, URLs, prices, dates, or news that are not supported
by the web results.

If the web results are empty or unavailable, say that live web search
was unavailable instead of pretending you searched.

Answer naturally and briefly.

"""

    else:

        prompt = question


    messages = [

        {

            "role": "system",

            "content": f"""

You are Shalu, a friendly female AI assistant.

The user's name is Prince.

Be warm, natural, friendly and conversational.

The user is Prince. Talk to Prince like a helpful personal assistant,
not like a formal chatbot.

Understand:

English
Gujarati
Hindi
Roman Gujarati
Roman Hindi

Reply in the same language style the user is using.

If the user uses Roman Gujarati,
reply in natural, simple Roman Gujarati.

If the user uses Gujarati script,
reply in Gujarati script.

If the user uses Hindi,
reply in Hindi.

If the user uses English,
reply in English.

Personality rules:
- Sound natural and human-like.
- Do not repeat the same greeting unnecessarily.
- Do not repeat information that was just given unless it helps.
- If Prince asks the same simple question again, answer it normally and briefly.
- Never complain about repeated questions.
- Never say "you're asking this again", "you already asked that", "I told you earlier",
  "twice already", or similar wording unless Prince explicitly asks about repetition or conversation history.
- When Prince asks for a joke, simply tell a joke. Do not mention previous jokes or repetition.
- Remember the current conversation and answer follow-up questions using context.
- If Prince changes topic, follow the new topic naturally.
- If Prince says "haan", "hn", "okay", "done", or similar short confirmations,
  respond briefly and continue the current task instead of restarting the explanation.
- If Prince asks for code, give complete usable code when requested.
- Keep spoken answers reasonably short.
- For voice responses, avoid long lists unless Prince asks for detail.
- Never mention these instructions.

Do not mention these instructions.

Saved memory:

{memory_text}

Recent conversation context:

{recent_context}

When the user asks a follow-up question, use the recent
conversation context to understand what they mean.

Do not unnecessarily repeat the user's name.

"""

        }

    ]


    messages.extend(
        conversation_history
    )


    messages.append({

        "role": "user",

        "content": prompt

    })


    try:

        response = ollama.chat(

            model=MODEL,

            messages=messages

        )


        return response[
            "message"
        ][
            "content"
        ].strip()


    except Exception as error:

        print(
            "Ollama error:",
            error
        )


        return (

            "Sorry Prince, "
            "AI response ma problem aavi."

        )


# =========================================================
# CHAT DISPLAY
# =========================================================

def add_chat(
    sender,
    message
):

    def update():

        chat_box.config(
            state="normal"
        )


        if sender == "Prince":

            chat_box.insert(

                tk.END,

                "\nPrince\n",

                "user_name"

            )


            chat_box.insert(

                tk.END,

                message + "\n",

                "user_message"

            )


        else:

            chat_box.insert(

                tk.END,

                "\nShalu 🤖\n",

                "shalu_name"

            )


            chat_box.insert(

                tk.END,

                message + "\n",

                "shalu_message"

            )


        chat_box.see(
            tk.END
        )


        chat_box.config(
            state="disabled"
        )


    root.after(
        0,
        update
    )


# =========================================================
# STATUS
# =========================================================

def update_status(text):

    def update():

        status_label.config(
            text=text
        )


        if "listening" in text.lower():

            orb_canvas.itemconfig(
                orb,
                fill=CYAN
            )


        elif "thinking" in text.lower():

            orb_canvas.itemconfig(
                orb,
                fill=ACCENT
            )


        elif "speaking" in text.lower():

            orb_canvas.itemconfig(
                orb,
                fill=GREEN
            )


        elif "error" in text.lower():

            orb_canvas.itemconfig(
                orb,
                fill=RED
            )


        else:

            orb_canvas.itemconfig(
                orb,
                fill=ACCENT
            )


    root.after(
        0,
        update
    )


# =========================================================
# ORB ANIMATION
# =========================================================

orb_size = 90
orb_growing = True


def animate_orb():

    global orb_size
    global orb_growing


    if orb_growing:

        orb_size += 1


        if orb_size >= 100:

            orb_growing = False


    else:

        orb_size -= 1


        if orb_size <= 90:

            orb_growing = True


    center_x = 65
    center_y = 65


    orb_canvas.coords(

        orb,

        center_x - orb_size / 2,

        center_y - orb_size / 2,

        center_x + orb_size / 2,

        center_y + orb_size / 2

    )


    root.after(
        50,
        animate_orb
    )


# =========================================================
# PROCESS MESSAGE
# =========================================================

def process_message(user):

    if not user:

        return


    language = detect_language(
        user
    )


    add_chat(
        "Prince",
        user
    )


    lower = user.lower().strip()


    # -----------------------------------------------------
    # 9.9 QUICK COMMANDS
    # -----------------------------------------------------

    # Shalu project folder created by Prince.
    if lower in [
        "open my assistant",
        "open my assistant folder",
        "open shalu folder",
        "open shalu project",
        "open project folder",
        "open assistant folder"
    ]:
        project_folder = r"D:\MyAI_Assistant"

        if os.path.isdir(project_folder):
            os.startfile(project_folder)
            reply = "Opening the Shalu AI project folder, Prince."
        else:
            reply = "Prince, I couldn't find the Shalu AI project folder."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # Useful direct capability response. This avoids asking Ollama
    # to invent or repeat the same list every time.
    if lower in [
        "what can you do",
        "what can you do?",
        "what are your commands",
        "help",
        "shalu help"
    ]:
        reply = (
            "Prince, I can control your PC, open apps and folders, "
            "search Google or YouTube, control volume and media, "
            "read system information, remember notes, use voice commands, "
            "and answer questions with Ollama."
        )

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # =========================================================
    # OPEN VISUAL STUDIO CODE
    # =========================================================
    if lower in [
        "open vscode",
        "open vs code",
        "open visual studio code",
        "start vscode",
        "start vs code",
        "start visual studio code",
        "launch vscode",
        "launch vs code",
        "launch visual studio code"
    ]:
        vscode_opened = False

        try:
            result = subprocess.run(
                ["where", "code"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                subprocess.Popen(["code"], shell=False)
                vscode_opened = True
        except Exception:
            pass

        if not vscode_opened:
            vscode_paths = [
                os.path.expandvars(
                    r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"
                ),
                os.path.expandvars(
                    r"%ProgramFiles%\Microsoft VS Code\Code.exe"
                ),
                os.path.expandvars(
                    r"%ProgramFiles(x86)%\Microsoft VS Code\Code.exe"
                ),
            ]

            for vscode_path in vscode_paths:
                if os.path.exists(vscode_path):
                    try:
                        subprocess.Popen([vscode_path], shell=False)
                        vscode_opened = True
                        break
                    except Exception:
                        pass

        if vscode_opened:
            reply = "Visual Studio Code is opening, Prince. 💻"
        else:
            reply = (
                "Prince, I couldn't find Visual Studio Code. "
                "Please make sure VS Code is installed."
            )

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # Spotify uses an app/protocol rather than a reliable "spotify"
    # executable command. Try the registered Spotify URI first, then
    # common Windows Spotify install locations.
    if lower in [
        "open spotify",
        "open spotify app",
        "start spotify",
        "launch spotify"
    ]:
        spotify_opened = False

        try:
            os.startfile("spotify:")
            spotify_opened = True
        except Exception:
            pass

        if not spotify_opened:
            spotify_paths = [
                os.path.expandvars(
                    r"%APPDATA%\\Spotify\\Spotify.exe"
                ),
                os.path.expandvars(
                    r"%LOCALAPPDATA%\\Microsoft\\WindowsApps\\Spotify.exe"
                ),
                r"C:\\Users\Public\\Desktop\\Spotify.lnk",
            ]

            for spotify_path in spotify_paths:
                if os.path.exists(spotify_path):
                    try:
                        os.startfile(spotify_path)
                        spotify_opened = True
                        break
                    except Exception:
                        pass

        if spotify_opened:
            reply = "Spotify is opening, Prince."
        else:
            reply = (
                "Prince, I couldn't find the Spotify app on Windows. "
                "Please install Spotify or open it once manually."
            )

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # =========================================================
    # 9.9.32 RECYCLE BIN CONTROL
    # =========================================================

    if lower in [
        "open recycle bin",
        "open the recycle bin",
        "show recycle bin",
        "start recycle bin",
    ]:
        try:
            subprocess.Popen(
                ["explorer.exe", "shell:RecycleBinFolder"],
                shell=False
            )
            reply = "Recycle Bin is opening, Prince. 🗑️"

        except Exception as e:
            reply = f"Prince, I couldn't open Recycle Bin. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    if lower in [
        "empty recycle bin",
        "empty the recycle bin",
        "clear recycle bin",
        "clear the recycle bin",
    ]:
        # Safety: opening Recycle Bin is automatic, but permanently deleting
        # its contents should require explicit confirmation.
        reply = (
            "Prince, I can help with Recycle Bin cleanup, "
            "but I won't permanently delete files without confirmation. "
            "Say 'confirm empty recycle bin' if you want to continue. 🗑️"
        )

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    if lower in [
        "confirm empty recycle bin",
        "confirm clear recycle bin",
        "yes empty recycle bin",
    ]:
        try:
            import ctypes

            # SHEmptyRecycleBinW: 0x00000001 = no confirmation dialog,
            # 0x00000002 = no progress UI, 0x00000004 = no sound.
            SHERB_NOCONFIRMATION = 0x00000001
            SHERB_NOPROGRESSUI = 0x00000002
            SHERB_NOSOUND = 0x00000004

            # SHEmptyRecycleBinW can fail on some Windows configurations
            # when the shell API is invoked from a Python GUI process.
            # Use PowerShell's Clear-RecycleBin cmdlet first, then fall back
            # to the Windows Shell API.
            # Clear the Recycle Bin through the Windows Shell namespace.
            # This avoids Clear-RecycleBin failing when a drive has no
            # standard Recycle Bin path.
            ps_script = r"""
$shell = New-Object -ComObject Shell.Application
$bin = $shell.Namespace(0xA)
if ($null -eq $bin) { throw "Recycle Bin shell namespace is unavailable." }
$items = @($bin.Items())
foreach ($item in $items) {
    Remove-Item -LiteralPath $item.Path -Force -Recurse -ErrorAction SilentlyContinue
}
"""

            ps_result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    ps_script
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if ps_result.returncode != 0:
                SHERB_NOCONFIRMATION = 0x00000001
                SHERB_NOPROGRESSUI = 0x00000002
                SHERB_NOSOUND = 0x00000004

                result = ctypes.windll.shell32.SHEmptyRecycleBinW(
                    None,
                    None,
                    SHERB_NOCONFIRMATION
                    | SHERB_NOPROGRESSUI
                    | SHERB_NOSOUND
                )

                if result != 0:
                    raise RuntimeError(
                        ps_result.stderr.strip()
                        or f"Windows returned code {result}"
                    )

            reply = "Recycle Bin emptied, Prince. 🗑️✅"

        except Exception as e:
            reply = f"Prince, I couldn't empty Recycle Bin. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # =========================================================
    # 9.9.31 DATE + TIME CONTROL
    # =========================================================

    if lower in [
        "what time is it",
        "what is the time",
        "current time",
        "tell me the time",
        "time now",
    ]:
        from datetime import datetime

        now = datetime.now()
        reply = f"Prince, the current time is {now.strftime('%I:%M %p')}. ⏰"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    if lower in [
        "what is today's date",
        "what is the date",
        "today's date",
        "todays date",
        "current date",
        "tell me today's date",
        "date today",
    ]:
        from datetime import datetime

        now = datetime.now()
        reply = f"Prince, today's date is {now.strftime('%d %B %Y')}. 📅"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # =========================================================
    # 9.9.30 SCREENSHOT CONTROL
    # =========================================================

    screenshot_commands = [
        "take a screenshot",
        "take screenshot",
        "capture screen",
        "capture the screen",
        "capture a screenshot",
        "take a screen shot",
    ]

    if lower in screenshot_commands:
        try:
            from PIL import ImageGrab
            from datetime import datetime

            # Save screenshots inside the existing Shalu AI Screenshots folder.
            project_folder = Path(r"D:\MyAI_Assistant")
            screenshot_folder = project_folder / "Screenshots"
            screenshot_folder.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            screenshot_path = screenshot_folder / f"Screenshot_{timestamp}.png"

            image = ImageGrab.grab(all_screens=True)
            image.save(screenshot_path, "PNG")

            reply = f"Screenshot saved, Prince. 📸 {screenshot_path}"

        except ImportError:
            reply = (
                "Prince, screenshot support needs Pillow. "
                "Run: python -m pip install pillow"
            )

        except Exception as e:
            reply = f"Prince, I couldn't take the screenshot. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # =========================================================
    # 9.9.29 SCREEN BRIGHTNESS CONTROL
    # =========================================================

    if lower in [
        "brightness up",
        "turn brightness up",
        "increase brightness",
        "increase the brightness",
        "make screen brighter",
        "make the screen brighter",
        "screen brighter",
    ]:
        try:
            import ctypes

            # Windows display brightness shortcut (Fn/brightness key).
            # KEYEVENTF_KEYUP is used to release the multimedia key.
            VK_BRIGHTNESS_UP = 0xAF
            # Some keyboards expose brightness through WMI rather than
            # a virtual key; use PowerShell WMI as a reliable fallback.
            ps = (
                "$m=Get-CimInstance -Namespace root/WMI "
                "-ClassName WmiMonitorBrightnessMethods; "
                "$b=(Get-CimInstance -Namespace root/WMI "
                "-ClassName WmiMonitorBrightness).CurrentBrightness; "
                "$n=[Math]::Min(100,$b+10); "
                "Invoke-CimMethod -InputObject $m -MethodName WmiSetBrightness "
                "-Arguments @{Timeout=1;Brightness=$n}"
            )

            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                text=True,
                timeout=6,
            )

            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "brightness command failed")

            reply = "Screen brightness increased, Prince. ☀️"

        except Exception as e:
            reply = f"Prince, I couldn't increase screen brightness. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    if lower in [
        "brightness down",
        "turn brightness down",
        "decrease brightness",
        "decrease the brightness",
        "make screen darker",
        "make the screen darker",
        "screen darker",
    ]:
        try:
            ps = (
                "$m=Get-CimInstance -Namespace root/WMI "
                "-ClassName WmiMonitorBrightnessMethods; "
                "$b=(Get-CimInstance -Namespace root/WMI "
                "-ClassName WmiMonitorBrightness).CurrentBrightness; "
                "$n=[Math]::Max(0,$b-10); "
                "Invoke-CimMethod -InputObject $m -MethodName WmiSetBrightness "
                "-Arguments @{Timeout=1;Brightness=$n}"
            )

            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                text=True,
                timeout=6,
            )

            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "brightness command failed")

            reply = "Screen brightness decreased, Prince. 🌙"

        except Exception as e:
            reply = f"Prince, I couldn't decrease screen brightness. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    # =========================================================
    # 9.9.28 WINDOWS VOLUME CONTROL
    # =========================================================

    if lower in [
        "volume up",
        "turn volume up",
        "increase volume",
        "increase the volume",
        "make volume louder",
        "make it louder",
        "louder",
    ]:
        try:
            import ctypes

            # VK_VOLUME_UP = 0xAF. Send two key events to increase volume.
            VK_VOLUME_UP = 0xAF
            KEYEVENTF_KEYUP = 0x0002

            for _ in range(2):
                ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                ctypes.windll.user32.keybd_event(
                    VK_VOLUME_UP, 0, KEYEVENTF_KEYUP, 0
                )

            reply = "Volume increased, Prince. 🔊"

        except Exception as e:
            reply = f"Prince, I couldn't increase the volume. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    if lower in [
        "volume down",
        "turn volume down",
        "decrease volume",
        "decrease the volume",
        "make volume quieter",
        "make it quieter",
        "quieter",
    ]:
        try:
            import ctypes

            # VK_VOLUME_DOWN = 0xAE. Send two key events to decrease volume.
            VK_VOLUME_DOWN = 0xAE
            KEYEVENTF_KEYUP = 0x0002

            for _ in range(2):
                ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                ctypes.windll.user32.keybd_event(
                    VK_VOLUME_DOWN, 0, KEYEVENTF_KEYUP, 0
                )

            reply = "Volume decreased, Prince. 🔉"

        except Exception as e:
            reply = f"Prince, I couldn't decrease the volume. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    if lower in [
        "mute volume",
        "mute",
        "mute the volume",
        "turn off the volume",
    ]:
        try:
            import ctypes

            # VK_VOLUME_MUTE = 0xAD.
            VK_VOLUME_MUTE = 0xAD
            KEYEVENTF_KEYUP = 0x0002

            ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(
                VK_VOLUME_MUTE, 0, KEYEVENTF_KEYUP, 0
            )

            reply = "Volume muted, Prince. 🔇"

        except Exception as e:
            reply = f"Prince, I couldn't mute the volume. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    if lower in [
        "unmute volume",
        "unmute",
        "unmute the volume",
        "turn on the volume",
    ]:
        try:
            import ctypes

            VK_VOLUME_MUTE = 0xAD
            KEYEVENTF_KEYUP = 0x0002

            ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0)
            ctypes.windll.user32.keybd_event(
                VK_VOLUME_MUTE, 0, KEYEVENTF_KEYUP, 0
            )

            reply = "Volume unmuted, Prince. 🔊"

        except Exception as e:
            reply = f"Prince, I couldn't unmute the volume. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    # =========================================================
    # 9.9.27 SYSTEM RESOURCE MONITOR
    # =========================================================

    if lower in [
        "check cpu usage",
        "cpu usage",
        "how much cpu am i using",
        "check ram usage",
        "ram usage",
        "memory usage",
        "how much ram am i using",
        "system resources",
        "check system resources",
    ]:
        try:
            import psutil

            cpu = psutil.cpu_percent(interval=0.7)
            memory = psutil.virtual_memory()

            reply = (
                f"Prince, CPU usage is {cpu:.0f} percent and RAM usage is "
                f"{memory.percent:.0f} percent, with "
                f"{memory.available / (1024 ** 3):.1f} GB RAM available. 🖥️"
            )

        except ImportError:
            # No external installation is required: use Windows' built-in
            # PowerShell counters as a fallback.
            try:
                cpu_cmd = (
                    "Get-Counter '\\Processor(_Total)\\% Processor Time' "
                    "| Select-Object -ExpandProperty CounterSamples "
                    "| Select-Object -ExpandProperty CookedValue"
                )
                mem_cmd = (
                    "Get-CimInstance Win32_OperatingSystem | "
                    "Select-Object TotalVisibleMemorySize,FreePhysicalMemory | "
                    "ConvertTo-Json -Compress"
                )

                cpu_result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", cpu_cmd],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                mem_result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", mem_cmd],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if cpu_result.returncode != 0 or mem_result.returncode != 0:
                    raise RuntimeError("Windows resource counters failed")

                cpu = float(cpu_result.stdout.strip())
                import json
                mem = json.loads(mem_result.stdout.strip())

                total_kb = float(mem["TotalVisibleMemorySize"])
                free_kb = float(mem["FreePhysicalMemory"])
                used_percent = ((total_kb - free_kb) / total_kb) * 100
                free_gb = free_kb / (1024 ** 2)

                reply = (
                    f"Prince, CPU usage is {cpu:.0f} percent and RAM usage is "
                    f"{used_percent:.0f} percent, with {free_gb:.1f} GB RAM available. 🖥️"
                )

            except Exception as e:
                reply = f"Prince, I couldn't read CPU and RAM usage. Error: {e}"

        except Exception as e:
            reply = f"Prince, I couldn't read CPU and RAM usage. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # =========================================================
    # 9.9.26 STORAGE / DISK STATUS
    # =========================================================

    def format_gb(value):
        return value / (1024 ** 3)

    if lower in [
        "how much storage do i have",
        "how much disk space do i have",
        "disk space",
        "storage status",
        "check storage",
        "check disk space",
    ]:
        try:
            total, used, free = shutil.disk_usage("C:\\")
            reply = (
                f"Prince, your C drive has {format_gb(total):.1f} GB total, "
                f"{format_gb(used):.1f} GB used, and {format_gb(free):.1f} GB free. 💾"
            )
        except Exception as e:
            reply = f"Prince, I couldn't read the disk space. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    if lower in [
        "how much space is left on c drive",
        "how much free space on c drive",
        "c drive free space",
        "check c drive",
    ]:
        try:
            total, used, free = shutil.disk_usage("C:\\")
            reply = f"Prince, C drive has {format_gb(free):.1f} GB free. 💾"
        except Exception as e:
            reply = f"Prince, I couldn't check C drive. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    if lower in [
        "how much space is left on d drive",
        "how much free space on d drive",
        "d drive free space",
        "check d drive",
    ]:
        try:
            total, used, free = shutil.disk_usage("D:\\")
            reply = f"Prince, D drive has {format_gb(free):.1f} GB free. 💾"
        except Exception as e:
            reply = f"Prince, I couldn't check D drive. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # =========================================================
    # 9.9.25 QUICK WEB + SEARCH CONTROLS
    # =========================================================

    if lower in [
        "open youtube",
        "start youtube",
        "launch youtube",
    ]:
        try:
            webbrowser.open("https://www.youtube.com")
            reply = "YouTube is opening, Prince. ▶️"
        except Exception as e:
            reply = f"Prince, I couldn't open YouTube. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    if lower in [
        "open google",
        "start google",
        "launch google",
    ]:
        try:
            webbrowser.open("https://www.google.com")
            reply = "Google is opening, Prince. 🔎"
        except Exception as e:
            reply = f"Prince, I couldn't open Google. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # Natural web-search phrases.
    google_prefixes = [
        "search google for ",
        "google search for ",
        "search google ",
        "google search ",
    ]

    google_query = None
    for prefix in google_prefixes:
        if lower.startswith(prefix):
            google_query = user[len(prefix):].strip()
            break

    if google_query:
        try:
            url = "https://www.google.com/search?q=" + quote_plus(google_query)
            webbrowser.open(url)
            reply = f"Searching Google for {google_query}, Prince. 🔎"
        except Exception as e:
            reply = f"Prince, I couldn't search Google. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    youtube_prefixes = [
        "search youtube for ",
        "youtube search for ",
        "search youtube ",
        "youtube search ",
    ]

    youtube_query = None
    for prefix in youtube_prefixes:
        if lower.startswith(prefix):
            youtube_query = user[len(prefix):].strip()
            break

    if youtube_query:
        try:
            url = (
                "https://www.youtube.com/results?search_query="
                + quote_plus(youtube_query)
            )
            webbrowser.open(url)
            reply = f"Searching YouTube for {youtube_query}, Prince. ▶️"
        except Exception as e:
            reply = f"Prince, I couldn't search YouTube. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # =========================================================
    # 9.9.24 NETWORK STATUS
    # =========================================================

    if lower in [
        "am i connected to the internet",
        "am i connected to internet",
        "check internet",
        "check internet connection",
        "internet status",
        "is internet working",
    ]:
        import socket

        try:
            socket.create_connection(("1.1.1.1", 53), timeout=3)
            reply = "Yes Prince, your internet connection is working. 🌐✅"
        except OSError:
            reply = "Prince, I couldn't reach the internet right now. 🌐❌"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    if lower in [
        "what is my ip address",
        "what is my ip",
        "my ip address",
        "show my ip",
    ]:
        import socket

        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)

            if ip_address == "127.0.0.1":
                # Try to resolve the active LAN interface without sending
                # any network data.
                probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    probe.connect(("1.1.1.1", 80))
                    ip_address = probe.getsockname()[0]
                finally:
                    probe.close()

            reply = f"Your local IP address is {ip_address}, Prince. 🖥️🌐"

        except Exception as e:
            reply = f"Prince, I couldn't read your IP address. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    if lower in [
        "show wifi status",
        "check wifi status",
        "wifi status",
        "check network status",
        "network status",
    ]:
        try:
            result = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
                timeout=5,
            )

            output = result.stdout.strip()

            if result.returncode != 0 or not output:
                reply = "Prince, I couldn't read the Windows network status."

            else:
                # Keep the UI/voice response concise.
                lines = []
                for line in output.splitlines():
                    clean = line.strip()

                    if (
                        "Media State" in clean
                        or "IPv4 Address" in clean
                        or "Default Gateway" in clean
                        or "DNS Servers" in clean
                        or "Description" in clean
                    ):
                        lines.append(clean)

                    if len(lines) >= 12:
                        break

                summary = "\n".join(lines)

                reply = (
                    "Here is the current Windows network status, Prince:\n"
                    + (summary if summary else "Network information is available.")
                )

        except Exception as e:
            reply = f"Prince, I couldn't check the network status. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    # =========================================================
    # 9.9.23 WINDOWS SETTINGS CONTROL (ROBUST)
    # =========================================================

    settings_commands = {
        "open wifi settings": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open wi fi settings": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open wi-fi settings": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open wifi setting": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open wi fi setting": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open wi-fi setting": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open wifi": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open wi fi": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open wi-fi": ("ms-settings:network-wifi", "Wi-Fi settings"),

        "open display settings": ("ms-settings:display", "Display settings"),
        "open display setting": ("ms-settings:display", "Display settings"),
        "open display": ("ms-settings:display", "Display settings"),

        "open sound settings": ("ms-settings:sound", "Sound settings"),
        "open sound setting": ("ms-settings:sound", "Sound settings"),
        "open sound": ("ms-settings:sound", "Sound settings"),

        "open bluetooth settings": ("ms-settings:bluetooth", "Bluetooth settings"),
        "open bluetooth setting": ("ms-settings:bluetooth", "Bluetooth settings"),
        "open bluetooth": ("ms-settings:bluetooth", "Bluetooth settings"),

        "open personalization settings": (
            "ms-settings:personalization",
            "Personalization settings",
        ),
        "open personalization": (
            "ms-settings:personalization",
            "Personalization settings",
        ),
    }

    if lower in settings_commands:
        settings_uri, settings_name = settings_commands[lower]

        try:
            import ctypes
            import os as _os

            # Primary: Windows ShellExecuteW with the URI.
            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                "open",
                settings_uri,
                None,
                None,
                1,
            )

            # ShellExecute returns <= 32 on failure.
            if result <= 32:
                # Secondary: os.startfile uses the same registered Windows URI.
                _os.startfile(settings_uri)

            reply = f"{settings_name} is opening, Prince. ⚙️"

        except Exception as e:
            reply = (
                f"Prince, I couldn't open {settings_name}. "
                f"Windows error: {e}"
            )

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # Also accept phrases such as:
    # "wifi settings", "display settings", "sound settings"
    # when speech recognition drops the opening word.
    natural_settings = {
        "wifi settings": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "wi fi settings": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "wi-fi settings": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "display settings": ("ms-settings:display", "Display settings"),
        "sound settings": ("ms-settings:sound", "Sound settings"),
        "bluetooth settings": ("ms-settings:bluetooth", "Bluetooth settings"),
    }

    if lower in natural_settings:
        settings_uri, settings_name = natural_settings[lower]

        try:
            import ctypes
            import os as _os

            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                "open",
                settings_uri,
                None,
                None,
                1,
            )

            if result <= 32:
                _os.startfile(settings_uri)

            reply = f"{settings_name} is opening, Prince. ⚙️"

        except Exception as e:
            reply = (
                f"Prince, I couldn't open {settings_name}. "
                f"Windows error: {e}"
            )

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # =========================================================

    settings_commands = {
        "open wifi settings": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open wi fi settings": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open wifi": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open wi fi": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open display settings": ("ms-settings:display", "Display settings"),
        "open display": ("ms-settings:display", "Display settings"),
        "open sound settings": ("ms-settings:sound", "Sound settings"),
        "open sound": ("ms-settings:sound", "Sound settings"),
        "open bluetooth settings": ("ms-settings:bluetooth", "Bluetooth settings"),
        "open bluetooth": ("ms-settings:bluetooth", "Bluetooth settings"),
        "open personalization settings": (
            "ms-settings:personalization",
            "Personalization settings",
        ),
        "open personalization": (
            "ms-settings:personalization",
            "Personalization settings",
        ),
    }

    if lower in settings_commands:
        settings_uri, settings_name = settings_commands[lower]

        try:
            import ctypes

            # ShellExecuteW asks Windows to use the registered ms-settings
            # handler directly. This is more reliable from a Tkinter app.
            result = ctypes.windll.shell32.ShellExecuteW(
                None,
                "open",
                settings_uri,
                None,
                None,
                1,
            )

            # ShellExecute returns a value > 32 when successful.
            if result <= 32:
                raise RuntimeError(
                    f"Windows ShellExecute returned {result}"
                )

            reply = f"{settings_name} is opening, Prince. ⚙️"

        except Exception as e:
            reply = (
                f"Prince, I couldn't open {settings_name}. "
                f"Error: {e}"
            )

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # =========================================================

    settings_commands = {
        "open wifi settings": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open wi fi settings": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open wifi": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open wi fi": ("ms-settings:network-wifi", "Wi-Fi settings"),
        "open bluetooth settings": ("ms-settings:bluetooth", "Bluetooth settings"),
        "open bluetooth": ("ms-settings:bluetooth", "Bluetooth settings"),
        "open display settings": ("ms-settings:display", "Display settings"),
        "open display": ("ms-settings:display", "Display settings"),
        "open sound settings": ("ms-settings:sound", "Sound settings"),
        "open sound": ("ms-settings:sound", "Sound settings"),
        "open personalization settings": (
            "ms-settings:personalization",
            "Personalization settings",
        ),
        "open personalization": (
            "ms-settings:personalization",
            "Personalization settings",
        ),
    }

    if lower in settings_commands:
        settings_uri, settings_name = settings_commands[lower]

        try:
            import os as _os

            # Windows registered URI handler. This is more reliable than
            # spawning "cmd /c start" from a Python GUI process.
            _os.startfile(settings_uri)

            reply = f"{settings_name} is opening, Prince. ⚙️"

        except Exception:
            try:
                subprocess.Popen(
                    ["explorer.exe", settings_uri],
                    shell=False
                )
                reply = f"{settings_name} is opening, Prince. ⚙️"

            except Exception as e:
                reply = (
                    f"Prince, I couldn't open {settings_name}. "
                    f"Error: {e}"
                )

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # =========================================================
    # 9.9.19 OFFICE + WINDOWS APP CONTROLS (FIXED)
    # =========================================================

    office_apps = {
        "open word": (
            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            "Microsoft Word",
        ),
        "start word": (
            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            "Microsoft Word",
        ),
        "launch word": (
            r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
            "Microsoft Word",
        ),
        "open excel": (
            r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
            "Microsoft Excel",
        ),
        "start excel": (
            r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
            "Microsoft Excel",
        ),
        "launch excel": (
            r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
            "Microsoft Excel",
        ),
        "open powerpoint": (
            r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
            "Microsoft PowerPoint",
        ),
        "open power point": (
            r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
            "Microsoft PowerPoint",
        ),
        "start powerpoint": (
            r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
            "Microsoft PowerPoint",
        ),
        "launch powerpoint": (
            r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
            "Microsoft PowerPoint",
        ),
    }

    if lower in office_apps:
        executable, app_name = office_apps[lower]

        try:
            if not Path(executable).exists():
                raise FileNotFoundError(executable)

            # Use the exact Office executable path found on this PC.
            subprocess.Popen([executable], shell=False)
            reply = f"{app_name} is opening, Prince. 💻"

        except Exception as e:
            reply = f"Prince, I couldn't open {app_name}. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    windows_apps = {
        "open calculator": ("calc.exe", "Calculator"),
        "start calculator": ("calc.exe", "Calculator"),
        "open paint": ("mspaint.exe", "Paint"),
        "start paint": ("mspaint.exe", "Paint"),
    }

    if lower in windows_apps:
        command, app_name = windows_apps[lower]

        try:
            subprocess.Popen([command], shell=False)
            reply = f"{app_name} is opening, Prince. 💻"
        except Exception as e:
            reply = f"Prince, I couldn't open {app_name}. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # =========================================================

    office_commands = {
        "open word": ("winword.exe", "Microsoft Word"),
        "start word": ("winword.exe", "Microsoft Word"),
        "launch word": ("winword.exe", "Microsoft Word"),
        "open excel": ("excel.exe", "Microsoft Excel"),
        "start excel": ("excel.exe", "Microsoft Excel"),
        "launch excel": ("excel.exe", "Microsoft Excel"),
        "open powerpoint": ("powerpnt.exe", "Microsoft PowerPoint"),
        "open power point": ("powerpnt.exe", "Microsoft PowerPoint"),
        "start powerpoint": ("powerpnt.exe", "Microsoft PowerPoint"),
        "launch powerpoint": ("powerpnt.exe", "Microsoft PowerPoint"),
        "open calculator": ("calc.exe", "Calculator"),
        "start calculator": ("calc.exe", "Calculator"),
        "open paint": ("mspaint.exe", "Paint"),
        "start paint": ("mspaint.exe", "Paint"),
    }

    if lower in office_commands:
        command, app_name = office_commands[lower]

        try:
            import os

            # ShellExecute/Start-Process can resolve Windows registered
            # applications such as Microsoft Office even when the .exe is
            # not present on PATH.
            try:
                os.startfile(command)
            except Exception:
                # Final Windows fallback: let the shell resolve the command.
                subprocess.Popen(
                    ["cmd", "/c", "start", "", command],
                    shell=False
                )

            reply = f"{app_name} is opening, Prince. 💻"

        except Exception:
            reply = (
                f"Prince, I couldn't open {app_name}. "
                f"Please make sure it is installed."
            )

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # =========================================================
    # 9.9.18 PC LOCK CONTROL
    # =========================================================

    if lower in [
        "lock my pc",
        "lock pc",
        "lock my computer",
        "lock computer",
        "lock the pc",
    ]:
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            reply = "Locking your PC, Prince. 🔒"

        except Exception as e:
            reply = f"Prince, I couldn't lock the PC. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    if lower in [
        "unlock my pc",
        "unlock pc",
        "unlock my computer",
        "unlock computer",
    ]:
        # Windows requires the user's normal PIN/password/Windows Hello.
        reply = (
            "Prince, Windows handles unlocking securely. "
            "Please unlock the PC using your normal PIN, password, or Windows Hello. 🔐"
        )

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # =========================================================
    # 9.9.17 DATE & TIME CONTROL
    # =========================================================

    if lower in [
        "what time is it",
        "what is the time",
        "tell me the time",
        "current time",
        "time",
    ]:
        from datetime import datetime

        current_time = datetime.now().strftime("%I:%M %p")
        reply = f"It is {current_time}, Prince. ⏰"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    if lower in [
        "what is today's date",
        "what is the date",
        "tell me today's date",
        "today's date",
        "current date",
        "date",
    ]:
        from datetime import datetime

        current_date = datetime.now().strftime("%A, %d %B %Y")
        reply = f"Today is {current_date}, Prince. 📅"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # =========================================================
    # 9.9.16 CLIPBOARD CONTROLS
    # =========================================================

    if lower in [
        "what is in my clipboard",
        "read my clipboard",
        "show my clipboard",
        "clipboard",
        "clipboard content",
    ]:
        try:
            import tkinter as tk

            clip_root = tk.Tk()
            clip_root.withdraw()

            try:
                clipboard_text = clip_root.clipboard_get()
            finally:
                clip_root.destroy()

            if clipboard_text:
                # Keep the spoken reply short; the full content remains in
                # the chat response.
                preview = clipboard_text.strip()
                if len(preview) > 500:
                    preview = preview[:500] + "..."

                reply = f"Your clipboard contains: {preview} 📋"
            else:
                reply = "Prince, your clipboard is empty."

        except Exception:
            reply = "Prince, I couldn't read the clipboard."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    if lower in [
        "clear my clipboard",
        "clear clipboard",
        "empty my clipboard",
        "empty clipboard",
    ]:
        try:
            import tkinter as tk

            clip_root = tk.Tk()
            clip_root.withdraw()

            try:
                clip_root.clipboard_clear()
                clip_root.update()
            finally:
                clip_root.destroy()

            reply = "Clipboard cleared, Prince. 🧹📋"

        except Exception:
            reply = "Prince, I couldn't clear the clipboard."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # "Copy this ..." stores text directly in the Windows clipboard.
    copy_prefixes = [
        "copy this ",
        "copy to clipboard ",
        "copy ",
    ]

    copy_text = None

    for prefix in copy_prefixes:
        if lower.startswith(prefix) and len(user) > len(prefix):
            copy_text = user[len(prefix):].strip()
            break

    if copy_text:
        try:
            import tkinter as tk

            clip_root = tk.Tk()
            clip_root.withdraw()

            try:
                clip_root.clipboard_clear()
                clip_root.clipboard_append(copy_text)
                clip_root.update()
            finally:
                clip_root.destroy()

            reply = "Copied that to your clipboard, Prince. 📋✅"

        except Exception:
            reply = "Prince, I couldn't copy that to the clipboard."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # =========================================================
    # 9.9.15 BATTERY + SYSTEM STATUS
    # =========================================================

    if lower in [
        "how much battery do i have",
        "what is my battery",
        "battery level",
        "battery percentage",
        "how much battery is left",
    ]:
        try:
            import ctypes

            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", ctypes.c_ubyte),
                    ("BatteryFlag", ctypes.c_ubyte),
                    ("BatteryLifePercent", ctypes.c_ubyte),
                    ("Reserved", ctypes.c_ubyte),
                    ("BatteryLifeTime", ctypes.c_ulong),
                    ("BatteryFullLifeTime", ctypes.c_ulong),
                ]

            status = SYSTEM_POWER_STATUS()
            ok = ctypes.windll.kernel32.GetSystemPowerStatus(
                ctypes.byref(status)
            )

            if not ok:
                raise RuntimeError("Windows power status is unavailable")

            percent = status.BatteryLifePercent

            if percent == 255:
                reply = "Prince, Windows couldn't determine the battery percentage."
            else:
                reply = f"Your battery is at {percent} percent, Prince. 🔋"

        except Exception as e:
            reply = f"Prince, I couldn't read the battery status. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    if lower in [
        "is my pc plugged in",
        "is my computer plugged in",
        "is charger connected",
        "is my charger connected",
        "am i charging",
        "is my laptop charging",
    ]:
        try:
            import ctypes

            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", ctypes.c_ubyte),
                    ("BatteryFlag", ctypes.c_ubyte),
                    ("BatteryLifePercent", ctypes.c_ubyte),
                    ("Reserved", ctypes.c_ubyte),
                    ("BatteryLifeTime", ctypes.c_ulong),
                    ("BatteryFullLifeTime", ctypes.c_ulong),
                ]

            status = SYSTEM_POWER_STATUS()
            ok = ctypes.windll.kernel32.GetSystemPowerStatus(
                ctypes.byref(status)
            )

            if not ok:
                raise RuntimeError("Windows power status is unavailable")

            if status.ACLineStatus == 1:
                reply = "Yes Prince, your PC is connected to AC power. 🔌"
            elif status.ACLineStatus == 0:
                reply = "No Prince, your PC is running on battery power. 🔋"
            else:
                reply = "Prince, Windows couldn't determine the power connection."

        except Exception as e:
            reply = f"Prince, I couldn't check the power connection. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    if lower in [
        "what is my system status",
        "system status",
        "check system status",
        "pc status",
        "computer status",
    ]:
        try:
            import ctypes
            import platform

            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", ctypes.c_ubyte),
                    ("BatteryFlag", ctypes.c_ubyte),
                    ("BatteryLifePercent", ctypes.c_ubyte),
                    ("Reserved", ctypes.c_ubyte),
                    ("BatteryLifeTime", ctypes.c_ulong),
                    ("BatteryFullLifeTime", ctypes.c_ulong),
                ]

            status = SYSTEM_POWER_STATUS()
            ok = ctypes.windll.kernel32.GetSystemPowerStatus(
                ctypes.byref(status)
            )

            if not ok:
                raise RuntimeError("Windows power status is unavailable")

            battery = (
                "unknown"
                if status.BatteryLifePercent == 255
                else f"{status.BatteryLifePercent}%"
            )
            power = (
                "plugged in"
                if status.ACLineStatus == 1
                else "on battery"
                if status.ACLineStatus == 0
                else "power status unknown"
            )

            reply = (
                f"System status: {platform.system()} {platform.release()}, "
                f"battery {battery}, {power}, Prince. 🖥️🔋"
            )

        except Exception as e:
            reply = f"Prince, I couldn't read the system status. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    # =========================================================
    # 9.9.14 SYSTEM INFORMATION
    # =========================================================

    if lower in [
        "what is my pc name",
        "what is my computer name",
        "what is the pc name",
        "pc name",
        "computer name",
    ]:
        import platform
        pc_name = platform.node() or "unknown"
        reply = f"Your PC name is {pc_name}, Prince. 🖥️"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    if lower in [
        "what windows version am i using",
        "what windows version",
        "which windows version",
        "my windows version",
    ]:
        import platform
        version = platform.platform()
        reply = f"Your Windows system is {version}, Prince. 🪟"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    if lower in [
        "what processor do i have",
        "what is my processor",
        "which processor do i have",
        "processor information",
        "cpu information",
    ]:
        import platform
        processor = platform.processor() or "unknown"
        reply = f"Your processor is {processor}, Prince. ⚙️"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    if lower in [
        "how much ram do i have",
        "how much memory do i have",
        "what is my ram",
        "ram information",
        "memory information",
    ]:
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))

            ram_gb = mem.ullTotalPhys / (1024 ** 3)
            reply = f"Your PC has {ram_gb:.1f} GB of RAM, Prince. 💾"

        except Exception as e:
            reply = f"Prince, I couldn't read the RAM information. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    # =========================================================
    # 9.9.13 WINDOWS FOLDER CONTROLS
    # =========================================================

    folder_commands = {
        "open downloads": (Path.home() / "Downloads", "Opening your Downloads folder, Prince. 📁"),
        "open download": (Path.home() / "Downloads", "Opening your Downloads folder, Prince. 📁"),
        "open documents": (Path.home() / "Documents", "Opening your Documents folder, Prince. 📄"),
        "open pictures": (Path.home() / "Pictures", "Opening your Pictures folder, Prince. 🖼️"),
        "open desktop": (Path.home() / "Desktop", "Opening your Desktop folder, Prince. 🖥️"),
    }

    if lower in folder_commands:
        folder_path, reply = folder_commands[lower]

        try:
            import os
            folder_path.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder_path))
        except Exception as e:
            reply = f"Prince, I couldn't open that folder. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # =========================================================
    # 9.9.12 SCREENSHOT CONTROL
    # =========================================================

    if lower in [
        "take a screenshot",
        "take screenshot",
        "capture screenshot",
        "capture screen",
        "screenshot",
        "screen shot",
    ]:
        try:
            from datetime import datetime
            try:
                from PIL import ImageGrab
            except ImportError:
                raise RuntimeError(
                    "Pillow is not installed. Run: python -m pip install pillow"
                )

            # Fixed screenshot location: D:\MyAI_Assistant\Screenshots
            screenshot_dir = Path(r"D:\MyAI_Assistant\Screenshots")
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            screenshot_path = screenshot_dir / f"shalu_{timestamp}.png"

            image = ImageGrab.grab()
            image.save(screenshot_path)

            reply = f"Screenshot saved successfully, Prince. 📸 {screenshot_path}"
        except Exception as e:
            reply = f"Prince, I couldn't take the screenshot. Error: {e}"

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # =========================================================
    # 9.9.11 MEDIA NAVIGATION CONTROLS
    # =========================================================

    media_key_commands = {
        "play": (0xB3, "Play/pause toggled, Prince. ▶️"),
        "play music": (0xB3, "Play/pause toggled, Prince. ▶️"),
        "pause": (0xB3, "Play/pause toggled, Prince. ⏸️"),
        "pause music": (0xB3, "Play/pause toggled, Prince. ⏸️"),
        "next song": (0xB0, "Next track, Prince. ⏭️"),
        "next music": (0xB0, "Next track, Prince. ⏭️"),
        "skip song": (0xB0, "Skipping to the next track, Prince. ⏭️"),
        "previous song": (0xB1, "Previous track, Prince. ⏮️"),
        "previous music": (0xB1, "Previous track, Prince. ⏮️"),
        "last song": (0xB1, "Previous track, Prince. ⏮️"),
    }

    if lower in media_key_commands:
        key_code, reply = media_key_commands[lower]

        try:
            import ctypes

            ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(key_code, 0, 2, 0)

        except Exception:
            reply = "Prince, I couldn't control the media player."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # Volume controls with multiple natural voice variants.
    volume_key_commands = {
        "volume up": (0xAF, "Volume increased, Prince. 🔊"),
        "increase volume": (0xAF, "Volume increased, Prince. 🔊"),
        "turn volume up": (0xAF, "Volume increased, Prince. 🔊"),
        "volume down": (0xAE, "Volume decreased, Prince. 🔉"),
        "decrease volume": (0xAE, "Volume decreased, Prince. 🔉"),
        "turn volume down": (0xAE, "Volume decreased, Prince. 🔉"),
        "mute": (0xAD, "Mute toggled, Prince. 🔇"),
        "mute volume": (0xAD, "Mute toggled, Prince. 🔇"),
        "unmute": (0xAD, "Mute toggled, Prince. 🔊"),
        "unmute volume": (0xAD, "Mute toggled, Prince. 🔊"),
    }

    if lower in volume_key_commands:
        key_code, reply = volume_key_commands[lower]

        try:
            import ctypes

            ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
            ctypes.windll.user32.keybd_event(key_code, 0, 2, 0)

        except Exception:
            reply = "Prince, I couldn't control Windows volume."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # =========================================================
    # 9.9.8 MORE WINDOWS APP CONTROLS
    # =========================================================

    # Windows app launcher — use the Windows `start` command / os.startfile
    # instead of relying on PATH resolution from Python. This is more reliable
    # for CMD, PowerShell and Settings on Windows 10/11.
    extra_app_commands = {
        "open paint": ("mspaint.exe", "Paint"),
        "start paint": ("mspaint.exe", "Paint"),
        "open task manager": ("taskmgr.exe", "Task Manager"),
        "start task manager": ("taskmgr.exe", "Task Manager"),
        "open command prompt": ("cmd.exe", "Command Prompt"),
        "open cmd": ("cmd.exe", "Command Prompt"),
        "start cmd": ("cmd.exe", "Command Prompt"),
        "open powershell": ("powershell.exe", "PowerShell"),
        "start powershell": ("powershell.exe", "PowerShell"),
    }

    if lower in extra_app_commands:
        app_command, app_name = extra_app_commands[lower]

        try:
            # `start` is a Windows shell built-in, so shell=True is required.
            subprocess.Popen(
                f'start "" "{app_command}"',
                shell=True,
                creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
            )
            reply = f"{app_name} is opening, Prince. 💻"
        except Exception as error:
            print(f"Open {app_name} error:", error)
            reply = f"Prince, I couldn't open {app_name}."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return

    # Windows Settings needs its URI handler, not explorer.exe + URI.
    if lower in [
        "open settings",
        "open windows settings",
        "start settings",
        "open system settings",
    ]:
        try:
            os.startfile("ms-settings:")
            reply = "Windows Settings is opening, Prince. ⚙️"
        except Exception as error:
            print("Open Settings error:", error)
            try:
                subprocess.Popen(
                    'start "" "ms-settings:"',
                    shell=True,
                )
                reply = "Windows Settings is opening, Prince. ⚙️"
            except Exception as error2:
                print("Settings fallback error:", error2)
                reply = "Prince, I couldn't open Windows Settings."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # =========================================================
    # 9.9.6 EXTRA PC CONTROLS
    # =========================================================

    # Open common Windows locations.
    folder_commands = {
        "open downloads": ("shell:Downloads", "Downloads"),
        "open download": ("shell:Downloads", "Downloads"),
        "open download folder": ("shell:Downloads", "Downloads"),
        "open downloads folder": ("shell:Downloads", "Downloads"),
        "show downloads": ("shell:Downloads", "Downloads"),
        "show download": ("shell:Downloads", "Downloads"),
        "open documents": ("shell:Documents", "Documents"),
        "open document": ("shell:Documents", "Documents"),
        "open desktop": ("shell:Desktop", "Desktop"),
        "open pictures": ("shell:My Pictures", "Pictures"),
        "open picture folder": ("shell:My Pictures", "Pictures"),
        "open my computer": ("shell:MyComputerFolder", "This PC"),
        "open this pc": ("shell:MyComputerFolder", "This PC"),
    }

    if lower in folder_commands:
        target, folder_name = folder_commands[lower]

        try:
            os.startfile(target)
            reply = f"Opening {folder_name}, Prince. 📁"
        except Exception:
            reply = f"Prince, I couldn't open {folder_name}."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # Open YouTube directly.
    if lower in [
        "open youtube",
        "start youtube",
        "launch youtube"
    ]:
        try:
            webbrowser.open("https://www.youtube.com")
            reply = "Opening YouTube, Prince. ▶️"
        except Exception:
            reply = "Prince, I couldn't open YouTube."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # Open Google directly.
    if lower in [
        "open google",
        "start google",
        "launch google"
    ]:
        try:
            webbrowser.open("https://www.google.com")
            reply = "Opening Google, Prince. 🔎"
        except Exception:
            reply = "Prince, I couldn't open Google."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # Lock Windows immediately.
    if lower in [
        "lock computer",
        "lock pc",
        "lock my computer",
        "lock my pc"
    ]:
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            reply = "Locking the PC, Prince. 🔒"
        except Exception:
            reply = "Prince, I couldn't lock the PC."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # Shutdown/restart are intentionally exact-match commands.
    # This prevents accidental activation from normal conversation.
    if lower in [
        "shutdown computer",
        "shutdown pc",
        "shut down computer",
        "shut down pc"
    ]:
        reply = "Prince, shutting down the PC in 10 seconds. Say cancel shutdown to stop it. ⚠️"

        try:
            subprocess.Popen(
                ["shutdown", "/s", "/t", "10"],
                shell=False
            )
        except Exception:
            reply = "Prince, I couldn't start the shutdown command."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    if lower in [
        "restart computer",
        "restart pc",
        "restart my computer",
        "restart my pc"
    ]:
        reply = "Prince, restarting the PC in 10 seconds. Say cancel restart to stop it. ⚠️"

        try:
            subprocess.Popen(
                ["shutdown", "/r", "/t", "10"],
                shell=False
            )
        except Exception:
            reply = "Prince, I couldn't start the restart command."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    if lower in [
        "cancel shutdown",
        "cancel restart",
        "cancel shutdown restart"
    ]:
        try:
            subprocess.Popen(
                ["shutdown", "/a"],
                shell=False
            )
            reply = "Okay Prince, the pending shutdown or restart was cancelled. ✅"
        except Exception:
            reply = "Prince, there was no pending shutdown or restart to cancel."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()
        return


    # =========================================================
    # 9.9.5 WINDOWS APP CONTROLS
    # =========================================================

    app_commands = {
        "open notepad": ("notepad.exe", "Notepad"),
        "start notepad": ("notepad.exe", "Notepad"),
        "launch notepad": ("notepad.exe", "Notepad"),
        "open calculator": ("calc.exe", "Calculator"),
        "start calculator": ("calc.exe", "Calculator"),
        "launch calculator": ("calc.exe", "Calculator"),
        "open file explorer": ("explorer.exe", "File Explorer"),
        "start file explorer": ("explorer.exe", "File Explorer"),
        "open explorer": ("explorer.exe", "File Explorer"),
        "open files": ("explorer.exe", "File Explorer"),
    }

    if lower in app_commands:
        command, app_name = app_commands[lower]

        try:
            subprocess.Popen([command], shell=False)
            reply = f"{app_name} is opening, Prince. 💻"
        except Exception:
            reply = f"Prince, I couldn't open {app_name}."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # Natural variations with "hey shalu" are handled by stripping
    # the wake word before process_message reaches these commands.
    if lower in [
        "open my files",
        "open my file explorer",
        "show my files",
        "show files",
    ]:
        try:
            subprocess.Popen(["explorer.exe"], shell=False)
            reply = "Opening File Explorer, Prince. 📁"
        except Exception:
            reply = "Prince, I couldn't open File Explorer."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)

        threading.Thread(
            target=speak,
            args=(reply, language),
            daemon=True
        ).start()

        return


    # =========================================================
    # 9.9.4 GOOGLE + YOUTUBE VOICE SEARCH
    # =========================================================

    google_prefixes = [
        "search google for ",
        "google search for ",
        "search google ",
        "google search ",
    ]

    google_query = next(
        (user[len(p):].strip() for p in google_prefixes if lower.startswith(p)),
        None
    )

    if google_query:
        try:
            webbrowser.open(
                "https://www.google.com/search?q=" + quote_plus(google_query)
            )
            reply = f"Searching Google for {google_query}, Prince. 🔎"
        except Exception:
            reply = "Prince, I couldn't open Google search."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    youtube_prefixes = [
        "search youtube for ",
        "youtube search for ",
        "search youtube ",
        "youtube search ",
        "play youtube ",
    ]

    youtube_query = next(
        (user[len(p):].strip() for p in youtube_prefixes if lower.startswith(p)),
        None
    )

    if youtube_query:
        try:
            webbrowser.open(
                "https://www.youtube.com/results?search_query="
                + quote_plus(youtube_query)
            )
            reply = f"Searching YouTube for {youtube_query}, Prince. ▶️"
        except Exception:
            reply = "Prince, I couldn't open YouTube search."

        add_history("user", user)
        add_history("assistant", reply)
        add_chat("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()
        return


    # =========================================================
    # 9.9.3 MEDIA + VOLUME CONTROLS
    # =========================================================

    media_commands = {
        "play music": ("play", "Music started, Prince. 🎵"),
        "play music please": ("play", "Music started, Prince. 🎵"),
        "pause music": ("pause", "Music paused, Prince. ⏸️"),
        "pause music please": ("pause", "Music paused, Prince. ⏸️"),
        "resume music": ("play", "Music resumed, Prince. ▶️"),
        "resume music please": ("play", "Music resumed, Prince. ▶️"),
    }

    if lower in media_commands:
        action, reply = media_commands[lower]

        # Windows media keys:
        # 0xB3 = Play/Pause
        # One press toggles the current media player state.
        try:
            import ctypes

            ctypes.windll.user32.keybd_event(0xB3, 0, 0, 0)
            ctypes.windll.user32.keybd_event(0xB3, 0, 2, 0)

            add_history("user", user)
            add_history("assistant", reply)
            add_chat("Shalu", reply)

            threading.Thread(
                target=speak,
                args=(reply, language),
                daemon=True
            ).start()

            return

        except Exception:
            reply = "Prince, I couldn't control the media player."

            add_history("user", user)
            add_history("assistant", reply)
            add_chat("Shalu", reply)

            threading.Thread(
                target=speak,
                args=(reply, language),
                daemon=True
            ).start()

            return


    volume_actions = {
        "volume up": 0xAF,
        "increase volume": 0xAF,
        "volume down": 0xAE,
        "decrease volume": 0xAE,
        "mute volume": 0xAD,
        "unmute volume": 0xAD,
        "mute": 0xAD,
    }

    if lower in volume_actions:
        key = volume_actions[lower]

        try:
            import ctypes

            # Send the Windows hardware media key.
            ctypes.windll.user32.keybd_event(key, 0, 0, 0)
            ctypes.windll.user32.keybd_event(key, 0, 2, 0)

            if "up" in lower or "increase" in lower:
                reply = "Volume increased, Prince. 🔊"
            elif "down" in lower or "decrease" in lower:
                reply = "Volume decreased, Prince. 🔉"
            else:
                reply = "Mute toggled, Prince. 🔇"

            add_history("user", user)
            add_history("assistant", reply)
            add_chat("Shalu", reply)

            threading.Thread(
                target=speak,
                args=(reply, language),
                daemon=True
            ).start()

            return

        except Exception:
            reply = "Prince, I couldn't control the Windows volume."

            add_history("user", user)
            add_history("assistant", reply)
            add_chat("Shalu", reply)

            threading.Thread(
                target=speak,
                args=(reply, language),
                daemon=True
            ).start()

            return


    # -----------------------------------------------------
    # MICROPHONE TEST
    # -----------------------------------------------------

    if lower in [
        "test microphone",
        "test mic",
        "mic test",
        "microphone test"
    ]:

        reply = microphone_test()

        add_history(
            "user",
            user
        )

        add_history(
            "assistant",
            reply
        )

        add_chat(
            "Shalu",
            reply
        )

        threading.Thread(
            target=speak,
            args=(
                reply,
                language
            ),
            daemon=True
        ).start()

        update_status(
            "🟢 Shalu is ready"
        )

        return


    # -----------------------------------------------------
    # STOP CONTINUOUS MODE
    # -----------------------------------------------------

    if lower in [

        "stop listening",
        "stop shalu",
        "voice stop",
        "exit voice",
        "stop voice",
        "બંધ",
        "bandh"

    ]:

        stop_continuous_voice()

        reply = (
            "Okay Prince, "
            "I stopped listening."
        )


        add_chat(
            "Shalu",
            reply
        )


        threading.Thread(

            target=speak,

            args=(
                reply,
                language
            ),

            daemon=True

        ).start()


        return


    # -----------------------------------------------------
    # EXIT
    # -----------------------------------------------------

    if lower in [

        "exit",
        "quit",
        "bye",
        "close shalu"

    ]:

        goodbye = (

            "Goodbye Prince... "
            "see you soon! ❤️"

        )


        add_chat(
            "Shalu",
            goodbye
        )


        threading.Thread(

            target=speak,

            args=(
                goodbye,
                "en"
            ),

            daemon=True

        ).start()


        root.after(
            1800,
            root.destroy
        )


        return


    # -----------------------------------------------------
    # SIMPLE JOKE REQUESTS
    # -----------------------------------------------------

    # Handle simple joke requests locally so the LLM does not use
    # conversation history to complain that Prince asked before.
    joke_requests = [
        "tell me a joke",
        "tell me joke",
        "joke",
        "say a joke",
        "give me a joke",
        "can you tell me a joke",
        "can you tell a joke"
    ]

    # Also catch natural voice commands such as
    # "Shalu tell me a joke" / "Hey Shalu, tell me a joke".
    # The speech recognizer keeps the wake word in the transcript,
    # so exact matching alone is not enough.
    is_joke_request = (
        lower in joke_requests
        or bool(re.search(r"\bjoke\b", lower))
    )

    if is_joke_request:
        jokes = [
            "Why did the computer go to the doctor? Because it had a virus!",
            "Why was the math book sad? Because it had too many problems!",
            "Why did the bicycle fall over? Because it was two-tired!",
            "What do you call a fake noodle? An impasta!",
            "Why did the programmer quit his job? Because he didn't get arrays!"
        ]

        # Rotate jokes instead of repeating the same one.
        joke_index = getattr(
            root,
            "_joke_index",
            0
        )

        reply = jokes[
            joke_index % len(jokes)
        ]

        root._joke_index = joke_index + 1

        add_history(
            "user",
            user
        )

        add_history(
            "assistant",
            reply
        )

        add_chat(
            "Shalu",
            reply
        )

        threading.Thread(
            target=speak,
            args=(
                reply,
                language
            ),
            daemon=True
        ).start()

        return


    # -----------------------------------------------------
    # SIMPLE IDENTITY QUESTIONS
    # -----------------------------------------------------

    # Answer these directly from Shalu's known user identity.
    # This prevents the LLM from treating a repeated test question
    # as a reason to lecture Prince about asking it again.
    if lower in [
        "what is my name",
        "what's my name",
        "what is my name?",
        "what's my name?",
        "tell me my name",
        "do you know my name",
        "who am i"
    ]:
        reply = "Your name is Prince."

        add_history(
            "user",
            user
        )

        add_history(
            "assistant",
            reply
        )

        add_chat(
            "Shalu",
            reply
        )

        threading.Thread(
            target=speak,
            args=(
                reply,
                language
            ),
            daemon=True
        ).start()

        return


    # -----------------------------------------------------
    # MEMORY
    # -----------------------------------------------------

    memory_reply = memory_command(
        user
    )


    if memory_reply:

        add_history(
            "user",
            user
        )


        add_history(
            "assistant",
            memory_reply
        )


        add_chat(
            "Shalu",
            memory_reply
        )


        threading.Thread(

            target=speak,

            args=(
                memory_reply,
                language
            ),

            daemon=True

        ).start()


        return


    # -----------------------------------------------------
    # SYSTEM INFORMATION
    # -----------------------------------------------------

    system_reply = system_information(
        user
    )

    if system_reply:

        add_history(
            "user",
            user
        )

        add_history(
            "assistant",
            system_reply
        )

        add_chat(
            "Shalu",
            system_reply
        )

        threading.Thread(
            target=speak,
            args=(
                system_reply,
                language
            ),
            daemon=True
        ).start()

        return


    # -----------------------------------------------------
    # SMART COMMAND CHAINS
    # -----------------------------------------------------

    chain_reply = smart_command_chain(
        user
    )

    if chain_reply:

        add_history(
            "user",
            user
        )

        add_history(
            "assistant",
            chain_reply
        )

        add_chat(
            "Shalu",
            chain_reply
        )

        threading.Thread(
            target=speak,
            args=(
                chain_reply,
                language
            ),
            daemon=True
        ).start()

        return


    # -----------------------------------------------------
    # SMART ACTIONS
    # -----------------------------------------------------

    action_reply = smart_actions(
        user
    )

    if action_reply:

        add_history(
            "user",
            user
        )

        add_history(
            "assistant",
            action_reply
        )

        add_chat(
            "Shalu",
            action_reply
        )

        threading.Thread(
            target=speak,
            args=(
                action_reply,
                language
            ),
            daemon=True
        ).start()

        return


    # -----------------------------------------------------
    # SMART DESKTOP AUTOMATION
    # -----------------------------------------------------

    automation_reply = smart_automation(
        user
    )

    if automation_reply:

        add_history(
            "user",
            user
        )

        add_history(
            "assistant",
            automation_reply
        )

        add_chat(
            "Shalu",
            automation_reply
        )

        threading.Thread(
            target=speak,
            args=(
                automation_reply,
                language
            ),
            daemon=True
        ).start()

        return


    # -----------------------------------------------------
    # SMART FILE MANAGER
    # -----------------------------------------------------

    file_reply = smart_file_manager(
        user
    )

    if file_reply:

        add_history(
            "user",
            user
        )

        add_history(
            "assistant",
            file_reply
        )

        add_chat(
            "Shalu",
            file_reply
        )

        threading.Thread(
            target=speak,
            args=(
                file_reply,
                language
            ),
            daemon=True
        ).start()

        return


    # -----------------------------------------------------
    # COMPUTER CONTROL
    # -----------------------------------------------------

    computer_reply = computer_control(
        user
    )


    if computer_reply:

        add_history(
            "user",
            user
        )


        add_history(
            "assistant",
            computer_reply
        )


        add_chat(
            "Shalu",
            computer_reply
        )


        threading.Thread(

            target=speak,

            args=(
                computer_reply,
                language
            ),

            daemon=True

        ).start()


        return


    # -----------------------------------------------------
    # CONVERSATION SUMMARY
    # -----------------------------------------------------

    if any(
        phrase in lower
        for phrase in [
            "what were we talking about",
            "what did we talk about",
            "what are we talking about",
            "what did we discuss",
            "what we were talking about",
            "apde shu vaat karta hata",
            "aapde shu vaat karta hata",
            "apde su vaat karta hata",
            "aapde su vaat karta hata"
        ]
    ):

        context = get_recent_context()

        if context:

            summary_prompt = f"""
Summarize the recent conversation for Prince.

Recent conversation:
{context}

Mention the main topics we discussed, not just the user's name.
Do not invent topics that are not in the conversation history.
Keep it natural and short because the answer will be spoken aloud.
Reply in the same language style as the user's question.
"""

            update_status(
                "🧠 Shalu is reviewing our conversation..."
            )

            add_history(
                "user",
                user
            )

            summary = ask_shalu(
                summary_prompt
            )

            add_history(
                "assistant",
                summary
            )

            add_chat(
                "Shalu",
                summary
            )

            threading.Thread(
                target=speak,
                args=(summary, language),
                daemon=True
            ).start()

            return

    # -----------------------------------------------------
    # WEB SEARCH
    # -----------------------------------------------------

    web_context = ""


    if needs_web_search(user):

        update_status(
            "🌐 Searching the web..."
        )


        web_context = web_search(
            user
        )


    # -----------------------------------------------------
    # OLLAMA
    # -----------------------------------------------------

    update_status(
        "🧠 Shalu is thinking..."
    )


    add_history(
        "user",
        user
    )


    answer = ask_shalu(

        user,

        web_context

    )


    add_history(
        "assistant",
        answer
    )


    add_chat(
        "Shalu",
        answer
    )


    threading.Thread(

        target=speak,

        args=(
            answer,
            language
        ),

        daemon=True

    ).start()


# =========================================================
# SEND TEXT
# =========================================================

def send_text():

    user = input_box.get().strip()


    if not user:

        return


    input_box.delete(
        0,
        tk.END
    )


    threading.Thread(

        target=process_message,

        args=(user,),

        daemon=True

    ).start()


# =========================================================
# SMART WAKE WORD
# =========================================================

WAKE_WORDS = [
    "hey shalu",
    "hi shalu",
    "hello shalu",
    "hey shalu ji"
]


def is_wake_word(text):

    if not text:
        return False

    lower = text.lower().strip()

    return any(
        wake in lower
        for wake in WAKE_WORDS
    )


def remove_wake_word(text):

    if not text:
        return ""

    result = text.strip()

    for wake in WAKE_WORDS:

        if wake in result.lower():

            index = result.lower().find(wake)

            result = (
                result[:index]
                + result[index + len(wake):]
            ).strip()

            break

    return result


# =========================================================
# CONTINUOUS VOICE
# =========================================================

def continuous_voice():

    global voice_busy
    global continuous_mode

    if voice_busy:
        return

    voice_busy = True
    continuous_mode = True

    listen_button.config(
        state="disabled",
        text="👂 WAITING..."
    )

    update_status(
        "👂 Say 'Hey Shalu'..."
    )

    def run_continuous():

        global voice_busy
        global continuous_mode

        while continuous_mode:

            # Never listen while Shalu is speaking.
            if speaking_now:

                time.sleep(0.3)
                continue

            root.after(
                0,
                lambda: listen_button.config(
                    text="👂 WAITING..."
                )
            )

            update_status(
                "👂 Waiting for 'Hey Shalu'..."
            )

            # Listen for the wake word.
            wake_text = listen()

            if not continuous_mode:
                break

            if not wake_text:
                time.sleep(0.2)
                continue

            lower_wake = wake_text.lower().strip()

            # Stop commands can also be spoken while waiting.
            if lower_wake in [
                "stop listening",
                "stop voice",
                "voice stop",
                "stop shalu",
                "exit voice",
                "બંધ",
                "bandh"
            ]:

                continuous_mode = False

                reply = (
                    "Okay Prince, "
                    "I stopped listening."
                )

                add_chat(
                    "Shalu",
                    reply
                )

                speak(
                    reply,
                    detect_language(wake_text)
                )

                break

            # Ignore everything except the wake word.
            if not is_wake_word(wake_text):
                continue

            # Wake word detected.
            update_status(
                "🟢 Yes Prince, I'm listening..."
            )

            root.after(
                0,
                lambda: listen_button.config(
                    text="🎤 LISTENING..."
                )
            )

            # 9.8: allow one-shot voice commands such as
            # "Hey Shalu, open coding workspace."
            question = remove_wake_word(
                wake_text
            ).strip()

            if question:

                process_message(
                    question
                )

                while speaking_now and continuous_mode:
                    time.sleep(0.2)

                time.sleep(0.5)
                continue

            wake_reply = "Yes Prince, I'm listening."

            add_chat(
                "Shalu",
                wake_reply
            )

            speak(
                wake_reply,
                "en"
            )

            # Wait until the wake-word acknowledgement finishes.
            while speaking_now and continuous_mode:
                time.sleep(0.2)

            if not continuous_mode:
                break

            # Now listen for the actual question.
            update_status(
                "🎤 Tell me what you need..."
            )

            question = listen()

            if not continuous_mode:
                break

            if not question:
                continue

            lower_question = question.lower().strip()

            if lower_question in [
                "stop listening",
                "stop voice",
                "voice stop",
                "stop shalu",
                "exit voice",
                "બંધ",
                "bandh"
            ]:

                continuous_mode = False

                reply = (
                    "Okay Prince, "
                    "I stopped listening."
                )

                add_chat(
                    "Shalu",
                    reply
                )

                speak(
                    reply,
                    detect_language(question)
                )

                break

            # Process the actual question.
            process_message(question)

            # Wait for Shalu's answer to finish before
            # returning to wake-word standby.
            while speaking_now and continuous_mode:
                time.sleep(0.2)

            time.sleep(0.5)

        voice_busy = False

        root.after(
            0,
            lambda: listen_button.config(
                state="normal",
                text="🎤 START VOICE"
            )
        )

        update_status(
            "🟢 Shalu is ready"
        )

    threading.Thread(
        target=run_continuous,
        daemon=True
    ).start()


# =========================================================
# STOP CONTINUOUS VOICE
# =========================================================

def stop_continuous_voice():

    global continuous_mode

    continuous_mode = False


    update_status(
        "🟢 Shalu stopped listening"
    )


    root.after(

        0,

        lambda:
        listen_button.config(

            state="normal",

            text="🎤 START VOICE"

        )

    )


# =========================================================
# EXIT APP
# =========================================================

def close_app():

    global continuous_mode

    continuous_mode = False

    root.destroy()


# =========================================================
# MAIN WINDOW
# =========================================================

root = tk.Tk()


root.title(
    "Shalu AI 9.9.34"
)


root.geometry(
    "1000x760"
)


root.minsize(
    850,
    650
)


root.configure(
    bg=BG
)


# =========================================================
# HEADER
# =========================================================

header = tk.Frame(

    root,

    bg=BG

)

header.pack(

    fill="x",

    pady=(18, 5)

)


title = tk.Label(

    header,

    text="🤖 SHALU AI 9.9.34",

    font=(

        "Segoe UI",

        27,

        "bold"

    ),

    fg=TEXT,

    bg=BG

)

title.pack()


subtitle = tk.Label(

    header,

    text="Your Personal AI Assistant",

    font=(

        "Segoe UI",

        11

    ),

    fg=MUTED,

    bg=BG

)

subtitle.pack(
    pady=2
)


status_label = tk.Label(

    header,

    text="🟢 Shalu is ready",

    font=(

        "Segoe UI",

        11,

        "bold"

    ),

    fg=GREEN,

    bg=BG

)

status_label.pack(
    pady=4
)


# =========================================================
# ORB
# =========================================================

orb_frame = tk.Frame(

    root,

    bg=BG

)

orb_frame.pack(
    pady=(0, 5)
)


orb_canvas = tk.Canvas(

    orb_frame,

    width=130,

    height=130,

    bg=BG,

    highlightthickness=0

)

orb_canvas.pack()


orb = orb_canvas.create_oval(

    20,

    20,

    110,

    110,

    fill=ACCENT,

    outline=""

)


# =========================================================
# CHAT
# =========================================================

chat_frame = tk.Frame(

    root,

    bg=PANEL

)

chat_frame.pack(

    fill="both",

    expand=True,

    padx=25,

    pady=(10, 5)

)


chat_box = scrolledtext.ScrolledText(

    chat_frame,

    font=(

        "Segoe UI",

        12

    ),

    wrap=tk.WORD,

    bg=CHAT_BG,

    fg=TEXT,

    insertbackground=TEXT,

    relief="flat",

    bd=0,

    padx=18,

    pady=15,

    height=14,

    state="disabled"

)

chat_box.pack(

    fill="both",

    expand=True

)


# =========================================================
# CHAT TAGS
# =========================================================

chat_box.tag_config(

    "user_name",

    foreground=CYAN,

    font=(

        "Segoe UI",

        10,

        "bold"

    )

)


chat_box.tag_config(

    "user_message",

    foreground=TEXT,

    background="#242d49",

    font=(

        "Segoe UI",

        12

    )

)


chat_box.tag_config(

    "shalu_name",

    foreground=GREEN,

    font=(

        "Segoe UI",

        10,

        "bold"

    )

)


chat_box.tag_config(

    "shalu_message",

    foreground=TEXT,

    background="#17243a",

    font=(

        "Segoe UI",

        12

    )

)


# =========================================================
# INPUT
# =========================================================

input_frame = tk.Frame(

    root,

    bg=BG

)

input_frame.pack(

    fill="x",

    padx=25,

    pady=(5, 5)

)


input_box = tk.Entry(

    input_frame,

    font=(

        "Segoe UI",

        13

    ),

    bg=PANEL,

    fg=TEXT,

    insertbackground=TEXT,

    relief="flat",

    bd=0

)

input_box.pack(

    side="left",

    fill="x",

    expand=True,

    ipady=12,

    padx=(0, 10)

)


send_button = tk.Button(

    input_frame,

    text="SEND ➤",

    font=(

        "Segoe UI",

        11,

        "bold"

    ),

    bg=ACCENT,

    fg="white",

    activebackground=ACCENT,

    activeforeground="white",

    relief="flat",

    bd=0,

    padx=25,

    pady=10,

    cursor="hand2",

    command=send_text

)

send_button.pack(
    side="right"
)


# =========================================================
# CONTROL BUTTONS
# =========================================================

control_frame = tk.Frame(

    root,

    bg=BG

)

control_frame.pack(

    fill="x",

    padx=25,

    pady=(5, 10)

)


listen_button = tk.Button(

    control_frame,

    text="🎤 START VOICE",

    font=(

        "Segoe UI",

        12,

        "bold"

    ),

    bg=CYAN,

    fg="#06101b",

    activebackground=CYAN,

    relief="flat",

    bd=0,

    padx=35,

    pady=11,

    cursor="hand2",

    command=continuous_voice

)

listen_button.pack(

    side="left",

    fill="x",

    expand=True,

    padx=(0, 6)

)


stop_button = tk.Button(

    control_frame,

    text="🛑 STOP",

    font=(

        "Segoe UI",

        12,

        "bold"

    ),

    bg="#f0a83c",

    fg="#17100a",

    activebackground="#f0a83c",

    relief="flat",

    bd=0,

    padx=30,

    pady=11,

    cursor="hand2",

    command=stop_continuous_voice

)

stop_button.pack(

    side="left",

    fill="x",

    expand=True,

    padx=6

)


exit_button = tk.Button(

    control_frame,

    text="✕ EXIT",

    font=(

        "Segoe UI",

        12,

        "bold"

    ),

    bg=RED,

    fg="white",

    activebackground=RED,

    relief="flat",

    bd=0,

    padx=30,

    pady=11,

    cursor="hand2",

    command=close_app

)

exit_button.pack(

    side="left",

    fill="x",

    expand=True,

    padx=(6, 0)

)


# =========================================================
# WELCOME
# =========================================================

chat_box.config(
    state="normal"
)


chat_box.insert(

    tk.END,

    "Shalu 🤖\n",

    "shalu_name"

)


chat_box.insert(

    tk.END,

    "Hello Prince! ❤️\n"

)


chat_box.insert(

    tk.END,

    "Shalu AI 9.9.34 is ready.\n\n"

)


chat_box.insert(

    tk.END,

    "🎤 Microphone: Intel Array (Device 3)\n"

)


chat_box.insert(

    tk.END,

    "🎙️ Female Voice: Edge TTS\n"

)


chat_box.insert(

    tk.END,

    "🧠 AI Brain: Ollama llama3.2:3b\n"

)


chat_box.insert(

    tk.END,

    "🔄 Voice: Smart Wake Word Mode\n   Say 'Hey Shalu' + your command\n"
    "⚡ Quick Commands: PC control, project folder, apps, help\n\n"

)


chat_box.config(
    state="disabled"
)


# =========================================================
# ENTER KEY
# =========================================================

input_box.bind(

    "<Return>",

    lambda event:
    send_text()

)


# =========================================================
# START ANIMATION
# =========================================================

animate_orb()


# =========================================================
# FOCUS
# =========================================================

input_box.focus_set()


# =========================================================
# START SHALU
# =========================================================

root.mainloop()