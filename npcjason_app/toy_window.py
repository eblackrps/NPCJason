from __future__ import annotations

import tkinter as tk


class ToyWindow:
    def __init__(self, root, width, height, logger=None):
        self.logger = logger
        self.root = tk.Toplevel(root)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-transparentcolor", "#010101")
            self.bg_color = "#010101"
        except tk.TclError:
            self.bg_color = "#2d2d2d"
            self._log("warning", "Transparent toy window color not supported; falling back to solid background")
        self.root.configure(bg=self.bg_color)
        self.canvas = tk.Canvas(
            self.root,
            width=int(width),
            height=int(height),
            bg=self.bg_color,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()

    def move_to(self, x, y):
        self.root.geometry(f"+{int(x)}+{int(y)}")

    def render_frame(self, frame_rows, palette, pixel_scale):
        self.canvas.delete("all")
        scale = max(1, int(pixel_scale))
        for row_idx, row in enumerate(frame_rows):
            for col_idx, char in enumerate(row):
                if char == "." or char not in palette:
                    continue
                color = palette[char]
                x1 = col_idx * scale
                y1 = row_idx * scale
                x2 = x1 + scale
                y2 = y1 + scale
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)

    def hide(self):
        self.root.withdraw()

    def show(self):
        self.root.deiconify()
        self.root.lift()
        try:
            self.root.attributes("-topmost", True)
        except tk.TclError:
            self._log("exception", "Failed to re-assert topmost state for toy window")

    def destroy(self):
        if self.exists():
            self.root.destroy()

    def exists(self):
        try:
            return bool(self.root.winfo_exists())
        except tk.TclError:
            return False

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message)
