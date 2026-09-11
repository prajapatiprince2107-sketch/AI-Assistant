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
from datetime import datetime
from urllib.parse import quote_plus

import ollama
import edge_tts
import speech_recognition as sr
import sounddevice as sd
from scipy.io.wavfile import write


# =========================================================
# SHALU AI FINAL
# =========================================================

MODEL = "llama3.2:3b"

MEMORY_FILE = "memory.json"
INPUT_FILE = "voice_input.wav"

MAX_HISTORY = 20

# 🎤 LAPTOP MICROPHONE
MIC_DEVICE = 3

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

conversation_history = []


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


    for attempt in range(3):

        filename = (

            f"shalu_voice_"
            f"{int(time.time() * 1000)}_"
            f"{attempt}.mp3"

        )


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

                and

                os.path.getsize(filename) > 1000

            ):

                print(
                    "🔊 Voice created:",
                    filename
                )


                os.startfile(

                    os.path.abspath(
                        filename
                    )

                )


                # Give Windows media player
                # a moment to start.
                time.sleep(0.7)


                speaking_now = False


                update_status(
                    "🟢 Shalu is ready"
                )


                return


        except Exception as error:

            print(

                f"TTS attempt "
                f"{attempt + 1}/3 failed:",
                error

            )


            if attempt < 2:

                time.sleep(1)


    speaking_now = False


    print(
        "TTS failed after 3 attempts."
    )


    update_status(
        "🟢 Shalu is ready"
    )


# =========================================================
# MICROPHONE
# =========================================================

def listen():

    update_status(
        "🎤 Shalu is listening..."
    )


    duration = 5

    sample_rate = 16000


    try:

        print(
            f"🎤 Microphone Device: "
            f"{MIC_DEVICE}"
        )


        recording = sd.rec(

            int(
                duration *
                sample_rate
            ),

            samplerate=sample_rate,

            channels=1,

            dtype="int16",

            device=MIC_DEVICE

        )


        sd.wait()


        write(

            INPUT_FILE,

            sample_rate,

            recording

        )


        print(
            "🎧 Recording complete."
        )


    except Exception as error:

        print(
            "Microphone error:",
            error
        )


        update_status(
            "❌ Microphone error"
        )


        return ""


    recognizer = sr.Recognizer()


    recognizer.energy_threshold = 250

    recognizer.dynamic_energy_threshold = True

    recognizer.pause_threshold = 0.8

    recognizer.phrase_threshold = 0.3

    recognizer.non_speaking_duration = 0.5


    try:

        with sr.AudioFile(
            INPUT_FILE
        ) as source:

            audio = recognizer.record(
                source
            )


        print(
            "🧠 Converting speech to text..."
        )


        text = recognizer.recognize_google(

            audio,

            language="en-IN"

        )


        print(
            "Prince:",
            text
        )


        return text


    except sr.UnknownValueError:

        print(
            "Shalu: Sorry Prince, "
            "mane samjhayu nahi."
        )


        return ""


    except sr.RequestError:

        print(
            "Shalu: Speech recognition "
            "mate internet joiye."
        )


        return ""


    except Exception as error:

        print(
            "Speech recognition error:",
            error
        )


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


    if "open d drive" in lower:

        os.startfile(
            "D:\\"
        )


        return (
            "D drive is opening, Prince."
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

    if tavily is None:

        return ""


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


        context = ""


        for index, result in enumerate(

            results,

            start=1

        ):

            context += (

                f"\nRESULT {index}\n"

                f"TITLE: "
                f"{result.get('title', '')}\n"

                f"CONTENT: "
                f"{result.get('content', '')}\n"

            )


        return context


    except Exception as error:

        print(
            "Web search error:",
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


Use web information when useful.

Do not invent facts.

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

Be warm, natural and conversational.

Understand:

English
Gujarati
Hindi
Roman Gujarati
Roman Hindi

Reply in the same language style
the user is using.

If the user uses Roman Gujarati,
reply in natural Roman Gujarati.

If the user uses Gujarati script,
reply in Gujarati script.

If the user uses Hindi,
reply in Hindi.

If the user uses English,
reply in English.

Keep spoken answers reasonably short.

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

        text="🟢 CONTINUOUS"

    )


    update_status(
        "🎤 Continuous voice mode"
    )


    def run_continuous():

        global voice_busy
        global continuous_mode


        while continuous_mode:

            # Don't listen while Shalu is speaking.
            if speaking_now:

                time.sleep(0.5)

                continue


            # 🎤 Listen
            user = listen()


            if not continuous_mode:

                break


            if not user:

                # Try again
                time.sleep(0.3)

                continue


            lower = user.lower().strip()


            # Stop command
            if lower in [

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
                    detect_language(user)
                )


                break


            # Process user's request
            process_message(
                user
            )


            # Wait for Shalu to finish speaking
            while (

                speaking_now

                and

                continuous_mode

            ):

                time.sleep(0.2)


            # Small pause
            time.sleep(0.5)


        voice_busy = False


        root.after(

            0,

            lambda:
            listen_button.config(

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
    "Shalu AI 8.1"
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

    text="🤖 SHALU AI 8.1",

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

    pady=10

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

    pady=(5, 18)

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

    padx=8

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

    padx=8

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

    padx=8

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

    "Shalu AI Final is ready.\n\n"

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

    "🔄 Voice: Continuous Mode\n\n"

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