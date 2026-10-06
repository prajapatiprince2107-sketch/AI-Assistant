import tkinter as tk

from config import BG, TEXT, GREEN, ACCENT, CYAN, RED


class StatusBar:
    def __init__(self, parent):
        self.label = tk.Label(
            parent,
            text="Shalu is ready",
            font=("Segoe UI", 11, "bold"),
            fg=GREEN,
            bg=BG,
        )
        self.label.pack(pady=4)

        self.orb_frame = tk.Frame(parent, bg=BG)
        self.orb_frame.pack(pady=(0, 5))

        self.canvas = tk.Canvas(
            self.orb_frame,
            width=130,
            height=130,
            bg=BG,
            highlightthickness=0,
        )
        self.canvas.pack()

        self.orb_size = 90
        self.orb_growing = True
        self.orb = self.canvas.create_oval(20, 20, 110, 110, fill=ACCENT, outline="")

    def update_text(self, text):
        def _update():
            self.label.config(text=text)
            lower = text.lower()
            if "listening" in lower:
                self.canvas.itemconfig(self.orb, fill=CYAN)
            elif "thinking" in lower:
                self.canvas.itemconfig(self.orb, fill=ACCENT)
            elif "speaking" in lower:
                self.canvas.itemconfig(self.orb, fill=GREEN)
            elif "error" in lower:
                self.canvas.itemconfig(self.orb, fill=RED)
            else:
                self.canvas.itemconfig(self.orb, fill=ACCENT)
        self.label.after(0, _update)

    def animate(self):
        if self.orb_growing:
            self.orb_size += 1
            if self.orb_size >= 100:
                self.orb_growing = False
        else:
            self.orb_size -= 1
            if self.orb_size <= 90:
                self.orb_growing = True

        cx, cy = 65, 65
        self.canvas.coords(
            self.orb,
            cx - self.orb_size / 2,
            cy - self.orb_size / 2,
            cx + self.orb_size / 2,
            cy + self.orb_size / 2,
        )
        self.canvas.after(50, self.animate)
