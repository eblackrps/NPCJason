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


def _normalize_sequence(sequence, fallback):
    normalized = []
    for entry in list(sequence or []):
        if isinstance(entry, dict):
            frame_key = str(entry.get("frame", entry.get("frame_key", ""))).strip()
            if not frame_key:
                continue
            normalized.append(
                {
                    "frame": frame_key,
                    "offset_y": int(entry.get("offset_y", 0)),
                    "delay_ms": entry.get("delay_ms"),
                }
            )
            continue
        if isinstance(entry, str):
            normalized.append({"frame": entry.strip(), "offset_y": 0, "delay_ms": None})
            continue
        if isinstance(entry, (list, tuple)) and entry:
            normalized.append(
                {
                    "frame": str(entry[0]).strip(),
                    "offset_y": int(entry[1]) if len(entry) > 1 else 0,
                    "delay_ms": entry[2] if len(entry) > 2 else None,
                }
            )
    if normalized:
        return normalized
    return [dict(entry) for entry in fallback]


class AnimationController:
    def __init__(self):
        self.is_dancing = False
        self.dance_frame_idx = 0
        self.idle_frame_idx = 0
        self.idle_sequence = _normalize_sequence(
            [{"frame": frame_key, "offset_y": offset_y} for frame_key, offset_y in IDLE_SEQUENCE],
            [],
        )
        self.interaction_sequence = _normalize_sequence(
            [{"frame": frame_key, "offset_y": 0} for frame_key in DANCE_SEQUENCE],
            [],
        )

    def set_sequences(self, idle_sequence=None, interaction_sequence=None):
        self.idle_sequence = _normalize_sequence(
            idle_sequence,
            [{"frame": frame_key, "offset_y": offset_y} for frame_key, offset_y in IDLE_SEQUENCE],
        )
        self.interaction_sequence = _normalize_sequence(
            interaction_sequence,
            [{"frame": frame_key, "offset_y": 0} for frame_key in DANCE_SEQUENCE],
        )
        self.idle_frame_idx = 0
        if not self.is_dancing:
            self.dance_frame_idx = 0

    def start_dance(self):
        if not self.interaction_sequence:
            return False
        self.is_dancing = True
        self.dance_frame_idx = 0
        return True

    def reset_idle(self):
        self.is_dancing = False
        self.dance_frame_idx = 0
        self.idle_frame_idx = 0

    def on_skin_changed(self):
        self.idle_frame_idx = 0
        if not self.is_dancing:
            self.dance_frame_idx = 0

    def next_frame(self, mood_key, personality_profile=None):
        mood = MOODS.get(mood_key, MOODS["happy"])
        personality_profile = personality_profile if isinstance(personality_profile, dict) else {}
        delay_scale = max(0.5, float(personality_profile.get("delay_scale", 1.0)))
        extra_offset_y = int(personality_profile.get("offset_y", 0))
        bob_px = int(personality_profile.get("bob_px", 0))
        jitter_px = int(personality_profile.get("jitter_px", 0))
        state_wave = 0
        if bob_px:
            state_wave = bob_px if (self.idle_frame_idx + self.dance_frame_idx) % 2 == 0 else -bob_px
        if jitter_px:
            state_wave += jitter_px if (self.idle_frame_idx + self.dance_frame_idx) % 3 == 0 else 0
        if self.is_dancing and self.interaction_sequence:
            entry = self.interaction_sequence[self.dance_frame_idx % len(self.interaction_sequence)]
            self.dance_frame_idx += 1
            if self.dance_frame_idx >= len(self.interaction_sequence) * 3:
                self.reset_idle()
            return AnimationFrame(
                frame_key=entry["frame"],
                offset_y=int(entry.get("offset_y", 0)) + extra_offset_y + state_wave,
                delay_ms=max(
                    85,
                    int((entry.get("delay_ms") or DANCE_BASE_DELAY_MS) * mood["speed"] * delay_scale),
                ),
            )

        entry = self.idle_sequence[self.idle_frame_idx % len(self.idle_sequence)]
        self.idle_frame_idx += 1
        return AnimationFrame(
            frame_key=entry["frame"],
            offset_y=int(entry.get("offset_y", 0)) + extra_offset_y + state_wave,
            delay_ms=max(
                120,
                int((entry.get("delay_ms") or IDLE_BASE_DELAY_MS) * mood["speed"] * delay_scale),
            ),
        )
