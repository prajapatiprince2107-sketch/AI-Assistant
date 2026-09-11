import ollama

from brain.memory import get_recent_context
from config import OLLAMA_MODEL

SYSTEM_BASE = "You are Shalu, a friendly female AI assistant. The user is Prince."


def ask(question, memory_dict, conversation_history, web_context=""):
    system_prompt = SYSTEM_BASE

    if memory_dict:
        memory_text = "\n".join(f"- {key}: {value}" for key, value in memory_dict.items())
        system_prompt += f"\n\nThings you remember about the user:\n{memory_text}"

    recent = get_recent_context(conversation_history)
    if recent:
        system_prompt += f"\n\nRecent conversation:\n{recent}"

    if web_context:
        system_prompt += f"\n\nWeb search results:\n{web_context}\nUse this information when relevant."

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history[-8:])
    messages.append({"role": "user", "content": question})

    response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
    return response["message"]["content"]