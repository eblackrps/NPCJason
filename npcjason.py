"""
NPCJason - Desktop Pet Companion
A pixel art NPC that lives on your desktop and system tray.
Click him to make him dance. He says random things throughout the day.

Requirements:
    pip install pystray Pillow
"""

import tkinter as tk
from tkinter import font as tkfont
import random
import time
import math
import threading
import sys
import os

try:
    import pystray
    from pystray import MenuItem as item
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False
    print("[WARN] pystray not installed. System tray icon disabled.")
    print("       Install with: pip install pystray Pillow")

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[WARN] Pillow not installed. System tray icon disabled.")
    print("       Install with: pip install Pillow")


# ─────────────────────────────────────────────
# QUOTES / SAYINGS
# ─────────────────────────────────────────────
SAYINGS = [
    # Funny / Sarcastic NPC Lines
    "I used to be an adventurer like you...\nthen I took a reboot to the BIOS.",
    "Have you tried turning it off\nand never turning it back on?",
    "I'm not lazy.\nI'm on energy-saving mode.",
    "Welcome, traveler!\nI have no quests.\nJust vibes.",
    "Do I look like I know\nwhat a JPEG is?",
    "Error 404:\nMotivation not found.",
    "I'd give you a quest,\nbut I'm on break.",
    "The real treasure was\nthe uptime we had along the way.",
    "Sure, I could help...\nbut have you checked Stack Overflow?",
    "NPC life is hard.\nSame dialogue. Every. Day.",
    "I guard this desktop\nwith my life.\nNo, literally. I can't leave.",
    "You look like someone\nwho closes terminals\nwithout saving.",
    "My therapist says I need\nto stop living in other\npeople's taskbars.",

    # Motivational
    "You're doing great.\nSeriously. Keep going.",
    "Every expert was once\na beginner who refused to quit.",
    "Ship it.\nYou can fix it in prod.\n(Don't actually do that.)",
    "Today's a good day\nto write clean code.",
    "Remember:\nDone is better than perfect.",
    "You've mass-deployed VMs\nbefore breakfast.\nYou can handle this.",
    "Believe in yourself.\nI believe in you.\nAnd I'm just pixels.",

    # Tech / Nerd Humor
    "There are 10 types of people:\nthose who understand binary\nand those who don't.",
    "A SQL query walks into a bar,\nsees two tables, and asks...\n'Can I JOIN you?'",
    "It works on my machine.\n...ships machine.",
    "Git commit -m\n'I have no idea what I changed\nbut it works now'",
    "'It's not a bug,\nit's a feature'\n- every dev ever",
    "Roses are red,\nviolets are blue,\nunexpected '{'\non line 32.",
    "To understand recursion,\nyou must first\nunderstand recursion.",
    "There's no place like\n127.0.0.1",
    "UDP joke?\nI'd tell you one\nbut you might not get it.",
    "!false\n...it's funny because it's true.",

    # Philosophical / Existential
    "Am I an NPC?\nOr are you the NPC\nin my story?",
    "If a desktop pet dances\nand no one is watching,\ndoes it still lag?",
    "I think, therefore I use RAM.",
    "We're all just processes\nwaiting to be scheduled.",
    "Do androids dream\nof electric uptime?",

    # Custom
    "It's been two weeks\nand no coffee videos.",
    "Where be my tokens?\nThey go'ed missin.",
    "All yo firewalls\nbelonging to NPCJason.",
    "F*CK Cisco Firepower.",
    "Is this on mang?",
    "Buller... Buller...",
    "Anyone? Anyone?",
    "ALL THE PATCHES?!",
    "Thinking about\nREBOOT'n Winderz...",
]


# ─────────────────────────────────────────────
# PIXEL ART FRAMES (drawn via tkinter Canvas)
# ─────────────────────────────────────────────
# Each frame is a grid of color values. None = transparent.
# Character is 16x20 pixels, rendered at 4x scale = 64x80 on screen.

PALETTE = {
    "K": "#1a1a2e",   # outline / dark
    "S": "#e8c170",   # skin
    "H": "#4a3728",   # hair (brown)
    "E": "#16213e",   # eyes
    "M": "#c84b31",   # mouth / smile
    "T": "#3a86c8",   # t-shirt blue
    "P": "#2d4263",   # pants dark blue
    "O": "#e8c170",   # shoes (tan)
    "W": "#ffffff",   # eye whites
    "B": "#0f3460",   # shirt accent
    "R": "#c84b31",   # red accent
    "G": "#aaaaaa",   # ground shadow
}

# Idle frame
FRAME_IDLE = [
    "................",
    "....KKKKKKKK....",
    "...KHHHHHHHHHK..",
    "..KHHHHHHHHHHK..",
    "..KHHHHHHHHHK...",
    "..KSSSSSSSSSK...",
    "..KSWEKSSWESK...",
    "..KSSSSSSSSK....",
    "..KSSSSMSSSK....",
    "..KKSSSSSSKK....",
    "....KTTTTTK.....",
    "...KTTTTTTTTK...",
    "..KTTTTTTTTTK...",
    "..KSKTTTTTKSK...",
    "...KKTTTTTKK....",
    "....KPPPPPK.....",
    "....KPKKPPK.....",
    "....KPKKPPK.....",
    "...KOKK.KOKK....",
    "...KKK..KKK.....",
]

# Dance frame 1 - arms up, lean left
FRAME_DANCE1 = [
    "................",
    "....KKKKKKKK....",
    "...KHHHHHHHHHK..",
    "..KHHHHHHHHHHK..",
    "..KHHHHHHHHHK...",
    "..KSSSSSSSSSK...",
    "..KSWEKSSWESK...",
    "..KSSSSSSSSK....",
    "..KSSSSMSSSK....",
    "..KKSSSSSSKK....",
    "..KSK.KTTTTTK...",
    ".KSK.KTTTTTTK..",
    "..KK.KTTTTTTTK..",
    ".....KTTTTTTK...",
    "......KTTTK.....",
    "....KPPPPPK.....",
    "...KPPK.KPPK....",
    "..KPPK...KPPK...",
    "..KOK.....KOK...",
    "..KKK.....KKK...",
]

# Dance frame 2 - arms up, lean right
FRAME_DANCE2 = [
    "................",
    "....KKKKKKKK....",
    "...KHHHHHHHHHK..",
    "..KHHHHHHHHHHK..",
    "..KHHHHHHHHHK...",
    "..KSSSSSSSSSK...",
    "..KSWEKSSWESK...",
    "..KSSSSSSSSK....",
    "..KSSSSMSSSK....",
    "..KKSSSSSSKK....",
    "..KTTTTTK.KSK...",
    "..KTTTTTTK.KSK..",
    "..KTTTTTTTK.KK..",
    "...KTTTTTTK.....",
    ".....KTTTK......",
    ".....KPPPPPK....",
    "....KPPK.KPPK...",
    "...KPPK...KPPK..",
    "...KOK.....KOK..",
    "...KKK.....KKK..",
]

# Dance frame 3 - squat
FRAME_DANCE3 = [
    "................",
    "................",
    "....KKKKKKKK....",
    "...KHHHHHHHHHK..",
    "..KHHHHHHHHHHK..",
    "..KHHHHHHHHHK...",
    "..KSSSSSSSSSK...",
    "..KSWEKSSWESK...",
    "..KSSSSSSSSK....",
    "..KSSSSMSSSK....",
    "..KKSSSSSSKK....",
    "..KSKTTTTTKSK...",
    "..KSKTTTTTKSK...",
    "...KKTTTTTKK....",
    "....KPPPPPK.....",
    "...KPPKKKPPK....",
    "..KPPK...KPPK...",
    "..KOKK...KOKK...",
    "..KKKK...KKKK...",
    "..GGGG...GGGG...",
]

IDLE_FRAMES = [FRAME_IDLE]
DANCE_FRAMES = [FRAME_DANCE1, FRAME_DANCE2, FRAME_DANCE3, FRAME_DANCE2, FRAME_DANCE1]

PIXEL_SCALE = 4
GRID_W = 16
GRID_H = 20
CANVAS_W = GRID_W * PIXEL_SCALE  # 64
CANVAS_H = GRID_H * PIXEL_SCALE  # 80


class SpeechBubble(tk.Toplevel):
    """A floating speech bubble window."""

    def __init__(self, parent_x, parent_y, text, master=None):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#1a1a2e")

        # Transparent / clickthrough on Windows
        try:
            self.attributes("-transparentcolor", "")
        except Exception:
            pass

        frame = tk.Frame(self, bg="#fef9e7", bd=0, highlightthickness=2,
                         highlightbackground="#1a1a2e")
        frame.pack(padx=2, pady=2)

        lbl = tk.Label(frame, text=text, bg="#fef9e7", fg="#1a1a2e",
                       font=("Consolas", 10, "bold"), justify="left",
                       padx=10, pady=6, wraplength=260)
        lbl.pack()

        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()

        # Position above the character
        bx = parent_x - w // 2
        by = parent_y - h - 10
        self.geometry(f"+{bx}+{by}")

        # Auto-destroy after a few seconds
        self.after(4000 + len(text) * 40, self._fade_out)

    def _fade_out(self):
        try:
            self.destroy()
        except Exception:
            pass


class NPCJason:
    """Main desktop pet application."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NPCJason")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#01010100")

        # Make window background transparent on Windows
        try:
            self.root.attributes("-transparentcolor", "#010101")
            self.bg_color = "#010101"
        except Exception:
            self.bg_color = "#2d2d2d"

        self.canvas = tk.Canvas(
            self.root, width=CANVAS_W, height=CANVAS_H,
            bg=self.bg_color, highlightthickness=0, cursor="hand2"
        )
        self.canvas.pack()

        # State
        self.is_dancing = False
        self.dance_frame_idx = 0
        self.dance_cycles = 0
        self.idle_bob = 0
        self.current_bubble = None
        self.dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

        # Position: bottom-right of screen
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        start_x = sw - CANVAS_W - 120
        start_y = sh - CANVAS_H - 80
        self.root.geometry(f"+{start_x}+{start_y}")

        # Bindings
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_right_click)

        # Draw initial frame
        self._draw_frame(FRAME_IDLE)

        # Start animation loop
        self._animation_loop()

        # Start random sayings timer
        self._schedule_random_saying()

        # System tray
        self.tray_icon = None
        if HAS_TRAY and HAS_PIL:
            tray_thread = threading.Thread(target=self._setup_tray, daemon=True)
            tray_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self._quit)

    def _draw_frame(self, frame_data):
        """Render a pixel art frame to the canvas."""
        self.canvas.delete("all")
        for row_idx, row in enumerate(frame_data):
            for col_idx, char in enumerate(row):
                if char == "." or char not in PALETTE:
                    continue
                color = PALETTE[char]
                x1 = col_idx * PIXEL_SCALE
                y1 = row_idx * PIXEL_SCALE
                x2 = x1 + PIXEL_SCALE
                y2 = y1 + PIXEL_SCALE
                self.canvas.create_rectangle(x1, y1, x2, y2,
                                             fill=color, outline=color)

    def _animation_loop(self):
        """Main animation tick."""
        if self.is_dancing:
            frame = DANCE_FRAMES[self.dance_frame_idx % len(DANCE_FRAMES)]
            self._draw_frame(frame)
            self.dance_frame_idx += 1

            if self.dance_frame_idx >= len(DANCE_FRAMES) * 3:
                self.is_dancing = False
                self.dance_frame_idx = 0
                self._draw_frame(FRAME_IDLE)

            self.root.after(150, self._animation_loop)
        else:
            # Subtle idle bob (move window up/down 1-2 px)
            self.idle_bob += 1
            if self.idle_bob % 40 == 0:
                x = self.root.winfo_x()
                y = self.root.winfo_y()
                offset = 2 if (self.idle_bob // 40) % 2 == 0 else -2
                self.root.geometry(f"+{x}+{y + offset}")

            self.root.after(50, self._animation_loop)

    def _on_click(self, event):
        """Handle left click - start dancing!"""
        self.drag_offset_x = event.x
        self.drag_offset_y = event.y
        self.dragging = False

        if not self.is_dancing:
            self.is_dancing = True
            self.dance_frame_idx = 0
            self.dance_cycles = 0
            self._show_saying()

    def _on_drag(self, event):
        """Allow dragging the pet around."""
        self.dragging = True
        x = self.root.winfo_x() + event.x - self.drag_offset_x
        y = self.root.winfo_y() + event.y - self.drag_offset_y
        self.root.geometry(f"+{x}+{y}")

    def _on_release(self, event):
        self.dragging = False

    def _on_right_click(self, event):
        """Right-click context menu."""
        menu = tk.Menu(self.root, tearoff=0, bg="#1a1a2e", fg="#fef9e7",
                       activebackground="#3a86c8", activeforeground="#ffffff",
                       font=("Consolas", 10))
        menu.add_command(label="Dance!", command=self._trigger_dance)
        menu.add_command(label="Say Something", command=self._show_saying)
        menu.add_separator()
        menu.add_command(label="Quit NPCJason", command=self._quit)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _trigger_dance(self):
        if not self.is_dancing:
            self.is_dancing = True
            self.dance_frame_idx = 0

    def _show_saying(self):
        """Show a random speech bubble."""
        if self.current_bubble:
            try:
                self.current_bubble.destroy()
            except Exception:
                pass

        text = random.choice(SAYINGS)
        cx = self.root.winfo_x() + CANVAS_W // 2
        cy = self.root.winfo_y()
        self.current_bubble = SpeechBubble(cx, cy, text, master=self.root)

    def _schedule_random_saying(self):
        """Pop up a random saying every 3-8 minutes."""
        delay_ms = random.randint(3 * 60 * 1000, 8 * 60 * 1000)
        self.root.after(delay_ms, self._random_saying_tick)

    def _random_saying_tick(self):
        self._show_saying()
        self._schedule_random_saying()

    def _setup_tray(self):
        """Create system tray icon."""
        icon_img = self._make_tray_icon()
        self.tray_icon = pystray.Icon(
            "NPCJason",
            icon_img,
            "NPCJason",
            menu=pystray.Menu(
                item("Show/Hide", self._toggle_visibility, default=True),
                item("Dance!", self._tray_dance),
                item("Say Something", self._tray_say),
                pystray.Menu.SEPARATOR,
                item("Quit", self._quit),
            )
        )
        self.tray_icon.run()

    def _make_tray_icon(self):
        """Generate a 64x64 icon for the system tray."""
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Simple pixel face for tray icon
        # Head
        draw.rectangle([16, 8, 48, 40], fill="#e8c170", outline="#1a1a2e", width=2)
        # Hair
        draw.rectangle([14, 4, 50, 16], fill="#4a3728", outline="#1a1a2e", width=1)
        # Eyes
        draw.rectangle([22, 20, 28, 26], fill="#16213e")
        draw.rectangle([36, 20, 42, 26], fill="#16213e")
        # Mouth
        draw.rectangle([28, 30, 36, 34], fill="#c84b31")
        # Body
        draw.rectangle([20, 40, 44, 56], fill="#3a86c8", outline="#1a1a2e", width=1)
        # Legs
        draw.rectangle([22, 56, 30, 64], fill="#2d4263")
        draw.rectangle([34, 56, 42, 64], fill="#2d4263")

        return img

    def _toggle_visibility(self, icon=None, item=None):
        """Toggle the desktop pet window."""
        self.root.after(0, self._do_toggle)

    def _do_toggle(self):
        if self.root.state() == "withdrawn":
            self.root.deiconify()
        else:
            self.root.withdraw()

    def _tray_dance(self, icon=None, item=None):
        self.root.after(0, self._trigger_dance)

    def _tray_say(self, icon=None, item=None):
        self.root.after(0, self._show_saying)

    def _quit(self, icon=None, item=None):
        """Clean exit."""
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass
        sys.exit(0)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    print("=" * 40)
    print("  NPCJason Desktop Pet")
    print("  Left-click  = Dance + Say Something")
    print("  Right-click = Menu")
    print("  Drag to move around!")
    print("=" * 40)
    app = NPCJason()
    app.run()
