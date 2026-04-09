from __future__ import annotations

import tkinter as tk

from .skins import CANVAS_H, CANVAS_W, PIXEL_SCALE
from .ui import SpeechBubble
from .version import APP_NAME
from .windows_platform import (
    bubble_position,
    clamp_window_position,
    default_window_position,
    friend_spawn_position,
    primary_work_area,
    snap_window_position,
)


class PetWindow:
    def __init__(self, logger=None):
        self.logger = logger
        self.root = tk.Tk()
        self.position_x = 0
        self.position_y = 0
        self.current_bubble = None

        self.root.title(APP_NAME)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-transparentcolor", "#010101")
            self.bg_color = "#010101"
        except tk.TclError:
            self.bg_color = "#2d2d2d"
            self._log("warning", "Transparent window color not supported; falling back to solid background")
        self.root.configure(bg=self.bg_color)

        self.canvas = tk.Canvas(
            self.root,
            width=CANVAS_W,
            height=CANVAS_H,
            bg=self.bg_color,
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.pack()

    def bind_input_handlers(self, on_press, on_drag, on_release, on_right_click):
        self.canvas.bind("<Button-1>", on_press)
        self.canvas.bind("<B1-Motion>", on_drag)
        self.canvas.bind("<ButtonRelease-1>", on_release)
        self.canvas.bind("<Button-3>", on_right_click)

    def protocol(self, name, callback):
        self.root.protocol(name, callback)

    def mainloop(self):
        self.root.mainloop()

    def destroy(self):
        self.destroy_bubble()
        self.root.destroy()

    def screen_size(self):
        return self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def work_area(self):
        screen_w, screen_h = self.screen_size()
        return primary_work_area(screen_w, screen_h)

    def is_hidden(self):
        try:
            return self.root.state() == "withdrawn"
        except tk.TclError:
            return False

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.ensure_topmost()

    def hide(self):
        self.root.withdraw()

    def ensure_topmost(self):
        try:
            self.root.attributes("-topmost", True)
        except tk.TclError:
            self._log("exception", "Failed to re-assert topmost state")

    def default_position(self):
        return default_window_position(self.work_area(), CANVAS_W, CANVAS_H)

    def clamp_position(self, x, y):
        return clamp_window_position(x, y, CANVAS_W, CANVAS_H, self.work_area())

    def snap_position(self, margin):
        self.position_x, self.position_y = snap_window_position(
            self.position_x,
            self.position_y,
            CANVAS_W,
            CANVAS_H,
            self.work_area(),
            margin,
        )
        return self.position_x, self.position_y

    def friend_spawn_position(self, gap=40, y_offset=-10):
        return friend_spawn_position(
            self.position_x,
            self.position_y,
            CANVAS_W,
            CANVAS_H,
            self.work_area(),
            gap=gap,
            y_offset=y_offset,
        )

    def move_to(self, x, y, offset_y=0):
        self.position_x = int(x)
        self.position_y = int(y)
        self.root.geometry(f"+{self.position_x}+{self.position_y + int(offset_y)}")

    def draw_frame(self, frame_data, palette):
        self.canvas.delete("all")
        for row_idx, row in enumerate(frame_data):
            for col_idx, char in enumerate(row):
                if char == "." or char not in palette:
                    continue
                color = palette[char]
                x1 = col_idx * PIXEL_SCALE
                y1 = row_idx * PIXEL_SCALE
                x2 = x1 + PIXEL_SCALE
                y2 = y1 + PIXEL_SCALE
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)

    def render_frame(self, frame_data, palette, offset_y=0):
        self.draw_frame(frame_data, palette)
        self.move_to(self.position_x, self.position_y, offset_y=offset_y)

    def destroy_bubble(self):
        if not self.current_bubble:
            return
        bubble = self.current_bubble
        self.current_bubble = None
        if bubble.winfo_exists():
            bubble.destroy()

    def show_bubble(self, text, offset_x=0, offset_y=0):
        self.destroy_bubble()
        center_x = self.root.winfo_x() + CANVAS_W // 2 + int(offset_x)
        top_y = self.root.winfo_y() + int(offset_y)
        bubble = SpeechBubble(center_x, top_y, text, master=self.root)
        bubble.update_idletasks()
        x, y = bubble_position(
            center_x,
            top_y,
            bubble.winfo_reqwidth(),
            bubble.winfo_reqheight(),
            self.work_area(),
        )
        bubble.geometry(f"+{x}+{y}")
        bubble.bind("<Destroy>", lambda _event, target=bubble: self._clear_bubble(target))
        self.current_bubble = bubble
        return bubble

    def _clear_bubble(self, bubble):
        if self.current_bubble is bubble:
            self.current_bubble = None

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message)
