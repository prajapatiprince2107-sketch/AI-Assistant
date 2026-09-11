import tkinter as tk
from tkinter import scrolledtext

from config import BG, PANEL, CHAT_BG, TEXT, MUTED, CYAN, GREEN


class ChatDisplay:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=PANEL)
        self.frame.pack(fill="both", expand=True, padx=25, pady=(10, 5))

        self.box = scrolledtext.ScrolledText(
            self.frame,
            font=("Segoe UI", 12),
            wrap=tk.WORD,
            bg=CHAT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            padx=18,
            pady=15,
            height=14,
            state="disabled",
        )
        self.box.pack(fill="both", expand=True)

        self.box.tag_config("user_name", foreground=CYAN, font=("Segoe UI", 10, "bold"))
        self.box.tag_config("user_message", foreground=TEXT, background="#242d49", font=("Segoe UI", 12))
        self.box.tag_config("shalu_name", foreground=GREEN, font=("Segoe UI", 10, "bold"))
        self.box.tag_config("shalu_message", foreground=TEXT, background="#17243a", font=("Segoe UI", 12))

    def add(self, sender, message):
        def _update():
            self.box.config(state="normal")
            if sender == "Prince":
                self.box.insert(tk.END, "\nPrince\n", "user_name")
                self.box.insert(tk.END, message + "\n", "user_message")
            else:
                self.box.insert(tk.END, "\nShalu\n", "shalu_name")
                self.box.insert(tk.END, message + "\n", "shalu_message")
            self.box.see(tk.END)
            self.box.config(state="disabled")
        self.box.after(0, _update)

    def welcome(self):
        self.box.config(state="normal")
        self.box.insert(tk.END, "Shalu\n", "shalu_name")
        self.box.insert(tk.END, "Hello Prince!\n")
        self.box.insert(tk.END, "Shalu AI is ready.\n\n")
        self.box.insert(tk.END, "Voice: Edge TTS (Female)\n")
        self.box.insert(tk.END, "AI Brain: Ollama llama3.2:3b\n")
        self.box.insert(tk.END, "Say 'Hey Shalu' + your command\n\n")
        self.box.config(state="disabled")
