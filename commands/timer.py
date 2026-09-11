import re
import threading
import datetime
from pathlib import Path

import config
from utils.platform import open_path, is_windows

DOCUMENTS = Path.home() / "Notes"
_joke_index = 0


def _timer_callback(message):
    try:
        from utils.platform import press_media_key, is_windows
        if is_windows():
            press_media_key(0x00, "Timer Alert")
        print(f"\n[TIMER] {message}")
    except Exception:
        print(f"\n[TIMER] {message}")


def handle(user_input):
    global _joke_index
    lower = user_input.lower().strip()

    if lower.startswith("set timer for "):
        parts = user_input[len("set timer for "):].strip()
        match = re.match(r"(\d+)\s*(second|seconds|sec|secs|minute|minutes|min|mins|hour|hours|hr|hrs)", parts, re.IGNORECASE)
        if not match:
            return "Use: set timer for X seconds/minutes/hours"
        value = int(match.group(1))
        unit = match.group(2).lower()
        if unit.startswith("sec"):
            seconds = value
        elif unit.startswith("min"):
            seconds = value * 60
        elif unit.startswith("hr") or unit.startswith("hour"):
            seconds = value * 3600
        else:
            seconds = value
        timer = threading.Timer(seconds, _timer_callback, args=[f"Timer of {parts} is done!"])
        timer.daemon = True
        timer.start()
        return f"Timer set for {parts}, Prince."

    if lower.startswith("calculate "):
        expression = user_input[len("calculate "):].strip()
        expression = expression.replace("x", "*").replace("X", "*").replace("times", "*").replace("plus", "+").replace("minus", "-").replace("divided by", "/").replace("mod", "%")
        if not re.fullmatch(r"[0-9\s\+\-\*\/\(\)\.\%\^]+", expression):
            return "Invalid expression. Use numbers and +, -, *, /, %, ^, ()"
        try:
            safe_expr = expression.replace("^", "**")
            result = eval(safe_expr, {"__builtins__": {}}, {})
            return f"Result: {result}"
        except ZeroDivisionError:
            return "Cannot divide by zero, Prince."
        except Exception:
            return "Could not calculate that expression."

    if lower.startswith("make a note ") or lower.startswith("take a note ") or lower.startswith("note "):
        if lower.startswith("make a note "):
            note_text = user_input[len("make a note "):].strip()
        elif lower.startswith("take a note "):
            note_text = user_input[len("take a note "):].strip()
        else:
            note_text = user_input[len("note "):].strip()
        DOCUMENTS.mkdir(parents=True, exist_ok=True)
        notes_file = DOCUMENTS / "Shalu_Notes.txt"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {note_text}\n"
        try:
            with open(notes_file, "a", encoding="utf-8") as f:
                f.write(entry)
            return f"Note saved: '{note_text[:50]}', Prince."
        except Exception as e:
            return f"Could not save note: {e}"

    if lower in ("open my notes", "open shalu notes", "show my notes", "show notes"):
        notes_file = DOCUMENTS / "Shalu_Notes.txt"
        if notes_file.exists():
            open_path(notes_file)
            return "Opening your notes, Prince."
        return "No notes file found yet. Make a note first!"

    if lower in ("tell me a joke", "joke", "say a joke", "tell a joke", "funny"):
        if not config.JOKES:
            return "No jokes available right now, Prince."
        joke = config.JOKES[_joke_index % len(config.JOKES)]
        _joke_index += 1
        return joke

    if lower in ("open recycle bin", "open trash", "recycle bin"):
        if is_windows():
            from utils.platform import open_path
            open_path("::{645FF040-5081-101B-9F08-00AA002F954E}")
            return "Opening Recycle Bin, Prince."
        return "Recycle Bin is a Windows feature."

    if lower in ("empty recycle bin", "clear recycle bin", "empty trash"):
        if is_windows():
            try:
                import subprocess
                subprocess.Popen(["cmd", "/c", "rd", "/s", "/q", "$Recycle.Bin"])
                return "Recycle Bin emptied, Prince."
            except Exception:
                return "Could not empty Recycle Bin."
        return "This feature is only available on Windows."

    return None
