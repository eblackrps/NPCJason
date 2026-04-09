from __future__ import annotations

from dataclasses import dataclass

from .data.defaults import MOODS
from .skins import DANCE_SEQUENCE, IDLE_SEQUENCE


IDLE_BASE_DELAY_MS = 240
DANCE_BASE_DELAY_MS = 135


@dataclass
class AnimationFrame:
    frame_key: str
    offset_y: int
    delay_ms: int


class AnimationController:
    def __init__(self):
        self.is_dancing = False
        self.dance_frame_idx = 0
        self.idle_frame_idx = 0

    def start_dance(self):
        self.is_dancing = True
        self.dance_frame_idx = 0

    def reset_idle(self):
        self.is_dancing = False
        self.dance_frame_idx = 0
        self.idle_frame_idx = 0

    def on_skin_changed(self):
        self.idle_frame_idx = 0
        if not self.is_dancing:
            self.dance_frame_idx = 0

    def next_frame(self, mood_key):
        mood = MOODS.get(mood_key, MOODS["happy"])
        if self.is_dancing:
            frame_key = DANCE_SEQUENCE[self.dance_frame_idx % len(DANCE_SEQUENCE)]
            self.dance_frame_idx += 1
            if self.dance_frame_idx >= len(DANCE_SEQUENCE) * 3:
                self.reset_idle()
            return AnimationFrame(
                frame_key=frame_key,
                offset_y=0,
                delay_ms=max(85, int(DANCE_BASE_DELAY_MS * mood["speed"])),
            )

        frame_key, offset_y = IDLE_SEQUENCE[self.idle_frame_idx % len(IDLE_SEQUENCE)]
        self.idle_frame_idx += 1
        return AnimationFrame(
            frame_key=frame_key,
            offset_y=offset_y,
            delay_ms=max(120, int(IDLE_BASE_DELAY_MS * mood["speed"])),
        )
