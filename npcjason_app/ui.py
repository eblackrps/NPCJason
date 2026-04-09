import tkinter as tk


class SpeechBubble(tk.Toplevel):
    def __init__(self, parent_x, parent_y, text, master=None):
        super().__init__(master)
        self._fade_after_id = None
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#1a1a2e")

        frame = tk.Frame(
            self,
            bg="#fef9e7",
            bd=0,
            highlightthickness=2,
            highlightbackground="#1a1a2e",
        )
        frame.pack(padx=2, pady=2)

        label = tk.Label(
            frame,
            text=text,
            bg="#fef9e7",
            fg="#1a1a2e",
            font=("Consolas", 10, "bold"),
            justify="left",
            padx=10,
            pady=6,
            wraplength=260,
        )
        label.pack()

        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        bubble_x = parent_x - width // 2
        bubble_y = parent_y - height - 10
        self.geometry(f"+{bubble_x}+{bubble_y}")
        self._fade_after_id = self.after(4000 + len(text) * 40, self._fade_out)

    def _fade_out(self):
        self._fade_after_id = None
        if self.winfo_exists():
            self.destroy()

    def destroy(self):
        if self._fade_after_id is not None:
            try:
                self.after_cancel(self._fade_after_id)
            except tk.TclError:
                pass
            self._fade_after_id = None
        super().destroy()
