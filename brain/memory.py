import json

from config import CONVERSATION_FILE, MAX_HISTORY, MEMORY_FILE


def load_memory():
    if not MEMORY_FILE.exists():
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


def handle_memory_command(command, memory):
    cmd = command.strip().lower()

    if cmd.startswith("remember that ") or cmd.startswith("remember "):
        phrase = cmd.replace("remember that ", "", 1).replace("remember ", "", 1)
        if not phrase:
            return ("What should I remember?", memory)
        memory["remembered"] = memory.get("remembered", [])
        if phrase not in memory["remembered"]:
            memory["remembered"].append(phrase)
        return (f"Okay, I will remember that: {phrase}", memory)

    if cmd.startswith("my name is "):
        name = cmd.replace("my name is ", "", 1).strip()
        if not name:
            return ("What name should I use for you?", memory)
        memory["name"] = name
        return (f"Nice to meet you, {name}. I will remember this.", memory)

    if "what do you remember" in cmd or "show my memory" in cmd or "show memory" in cmd:
        if not memory:
            return ("I do not remember anything yet.", memory)
        lines = [f"{key}: {value}" for key, value in memory.items()]
        return ("\n".join(lines), memory)

    return (None, memory)


def load_conversation():
    if not CONVERSATION_FILE.exists():
        return []
    try:
        with open(CONVERSATION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_conversation(history):
    with open(CONVERSATION_FILE, "w", encoding="utf-8") as f:
        json.dump(history[-MAX_HISTORY:], f, indent=2, ensure_ascii=False)


def add_to_history(history, role, content):
    history.append({"role": role, "content": content})
    return history[-MAX_HISTORY:]


def get_recent_context(history):
    return "\n".join(f"{m['role']}: {m['content']}" for m in history[-10:])