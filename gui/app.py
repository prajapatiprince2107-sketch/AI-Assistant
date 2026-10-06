import tkinter as tk
import threading
import time
import re

from config import (
    BG, TEXT, MUTED, CYAN, GREEN, RED, ACCENT,
    WAKE_WORDS, JOKES, MEMORY_FILE, CONVERSATION_FILE,
)
from brain.language import detect_language
from brain.memory import (
    load_memory, save_memory, handle_memory_command,
    load_conversation, save_conversation, add_to_history, get_recent_context,
)
from brain.llm import ask as llm_ask
from voice.tts import speak
from voice.stt import listen, microphone_test
from commands import route, needs_web_search
from utils.web_search import web_search
from gui.chat import ChatDisplay
from gui.status import StatusBar


class ShaluApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Shalu AI")
        self.root.geometry("1000x760")
        self.root.minsize(850, 650)
        self.root.configure(bg=BG)

        self.memory = load_memory()
        self.conversation = load_conversation()
        self.voice_busy = False
        self.continuous_mode = False
        self.speaking_now = False
        self.joke_index = 0

        self._build_header()
        self.status = StatusBar(self.root)
        self.chat = ChatDisplay(self.root)
        self._build_input()
        self._build_controls()

        self.chat.welcome()
        self.status.animate()

        self.input_box.bind("<Return>", lambda e: self.send_text())
        self.input_box.focus_set()

        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    def _build_header(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", pady=(18, 5))

        tk.Label(
            header, text="SHALU AI",
            font=("Segoe UI", 27, "bold"),
            fg=TEXT, bg=BG,
        ).pack()

        tk.Label(
            header, text="Your Personal AI Assistant",
            font=("Segoe UI", 11),
            fg=MUTED, bg=BG,
        ).pack(pady=2)

    def _build_input(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="x", padx=25, pady=(5, 5))

        self.input_box = tk.Entry(
            frame,
            font=("Segoe UI", 13),
            bg="#11182b", fg=TEXT,
            insertbackground=TEXT,
            relief="flat", bd=0,
        )
        self.input_box.pack(side="left", fill="x", expand=True, ipady=12, padx=(0, 10))

        tk.Button(
            frame, text="SEND",
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT, fg="white",
            activebackground=ACCENT, activeforeground="white",
            relief="flat", bd=0, padx=25, pady=10,
            cursor="hand2", command=self.send_text,
        ).pack(side="right")

    def _build_controls(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="x", padx=25, pady=(5, 10))

        self.listen_button = tk.Button(
            frame, text="START VOICE",
            font=("Segoe UI", 12, "bold"),
            bg=CYAN, fg="#06101b",
            activebackground=CYAN,
            relief="flat", bd=0, padx=35, pady=11,
            cursor="hand2", command=self.start_voice,
        )
        self.listen_button.pack(side="left", fill="x", expand=True, padx=(0, 6))

        tk.Button(
            frame, text="STOP",
            font=("Segoe UI", 12, "bold"),
            bg="#f0a83c", fg="#17100a",
            activebackground="#f0a83c",
            relief="flat", bd=0, padx=30, pady=11,
            cursor="hand2", command=self.stop_voice,
        ).pack(side="left", fill="x", expand=True, padx=6)

        tk.Button(
            frame, text="EXIT",
            font=("Segoe UI", 12, "bold"),
            bg=RED, fg="white",
            activebackground=RED,
            relief="flat", bd=0, padx=30, pady=11,
            cursor="hand2", command=self.close_app,
        ).pack(side="left", fill="x", expand=True, padx=(6, 0))

    def send_text(self):
        user = self.input_box.get().strip()
        if not user:
            return
        self.input_box.delete(0, tk.END)
        threading.Thread(target=self.process_message, args=(user,), daemon=True).start()

    def process_message(self, user):
        if not user:
            return

        language = detect_language(user)
        self.chat.add("Prince", user)

        lower = user.lower().strip()

        if lower in ["stop listening", "stop shalu", "voice stop", "exit voice", "stop voice", "bandh"]:
            self.stop_voice()
            reply = "Okay Prince, I stopped listening."
            self._respond(reply, language)
            return

        if lower in ["exit", "quit", "bye", "close shalu"]:
            goodbye = "Goodbye Prince... see you soon!"
            self.chat.add("Shalu", goodbye)
            threading.Thread(target=speak, args=(goodbye, "en"), daemon=True).start()
            self.root.after(1800, self.root.destroy)
            return

        mem_reply, self.memory = handle_memory_command(user, self.memory)
        if mem_reply:
            save_memory(self.memory)
            self._respond(mem_reply, language)
            return

        if "what were we talking about" in lower or "what did we talk about" in lower:
            context = get_recent_context(self.conversation)
            if context:
                self.status.update_text("Reviewing conversation...")
                summary = llm_ask(
                    f"Summarize the recent conversation briefly:\n{context}",
                    self.memory, self.conversation,
                )
                self._respond(summary, language)
                return

        cmd_reply, need_search = route(user)
        if cmd_reply:
            self._respond(cmd_reply, language)
            return

        web_context = ""
        if need_search:
            self.status.update_text("Searching the web...")
            web_context = web_search(user)

        self.status.update_text("Thinking...")
        add_to_history(self.conversation, "user", user)
        answer = llm_ask(user, self.memory, self.conversation, web_context)
        add_to_history(self.conversation, "assistant", answer)
        save_conversation(self.conversation)
        self._respond(answer, language)

    def _respond(self, reply, language):
        add_to_history(self.conversation, "assistant", reply)
        save_conversation(self.conversation)
        self.chat.add("Shalu", reply)
        threading.Thread(target=speak, args=(reply, language), daemon=True).start()

    def start_voice(self):
        if self.voice_busy:
            return
        self.voice_busy = True
        self.continuous_mode = True
        self.listen_button.config(state="disabled", text="WAITING...")
        threading.Thread(target=self._voice_loop, daemon=True).start()

    def _voice_loop(self):
        while self.continuous_mode:
            if self.speaking_now:
                time.sleep(0.3)
                continue

            self.root.after(0, lambda: self.listen_button.config(text="WAITING..."))
            self.status.update_text("Waiting for 'Hey Shalu'...")

            wake_text = listen()
            if not self.continuous_mode:
                break
            if not wake_text:
                time.sleep(0.2)
                continue

            lower_wake = wake_text.lower().strip()

            if lower_wake in ["stop listening", "stop voice", "voice stop", "stop shalu", "exit voice", "bandh"]:
                self.continuous_mode = False
                self._respond("Okay Prince, I stopped listening.", detect_language(wake_text))
                break

            if not any(w in lower_wake for w in WAKE_WORDS):
                continue

            self.status.update_text("Listening...")
            self.root.after(0, lambda: self.listen_button.config(text="LISTENING..."))

            question = self._remove_wake(wake_text).strip()
            if question:
                self.process_message(question)
                while self.speaking_now and self.continuous_mode:
                    time.sleep(0.2)
                time.sleep(0.5)
                continue

            self._respond("Yes Prince, I'm listening.", "en")
            while self.speaking_now and self.continuous_mode:
                time.sleep(0.2)

            self.status.update_text("Tell me what you need...")
            question = listen()
            if not self.continuous_mode:
                break
            if not question:
                continue

            lower_q = question.lower().strip()
            if lower_q in ["stop listening", "stop voice", "voice stop", "stop shalu", "exit voice", "bandh"]:
                self.continuous_mode = False
                self._respond("Okay Prince, I stopped listening.", detect_language(question))
                break

            self.process_message(question)
            while self.speaking_now and self.continuous_mode:
                time.sleep(0.2)
            time.sleep(0.5)

        self.voice_busy = False
        self.root.after(0, lambda: self.listen_button.config(state="normal", text="START VOICE"))
        self.status.update_text("Shalu is ready")

    def _remove_wake(self, text):
        result = text.strip()
        for wake in WAKE_WORDS:
            if wake in result.lower():
                idx = result.lower().find(wake)
                result = (result[:idx] + result[idx + len(wake):]).strip()
                break
        return result

    def stop_voice(self):
        self.continuous_mode = False
        self.status.update_text("Shalu stopped listening")
        self.root.after(0, lambda: self.listen_button.config(state="normal", text="START VOICE"))

    def close_app(self):
        self.continuous_mode = False
        self.root.destroy()

    def run(self):
        self.root.mainloop()
