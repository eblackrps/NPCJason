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


@dataclass(frozen=True)
class DanceRoutineDefinition:
    key: str
    label: str
    description: str
    contexts: tuple[str, ...]
    preferred_categories: tuple[str, ...]


DANCE_ROUTINE_DEFINITIONS = (
    DanceRoutineDefinition(
        key="classic-bounce",
        label="Classic Bounce",
        description="The original little desktop victory loop.",
        contexts=("dance", "dance-classic-bounce"),
        preferred_categories=("dance", "playful"),
    ),
    DanceRoutineDefinition(
        key="desk-shuffle",
        label="Desk Shuffle",
        description="A side-to-side office goblin shuffle with extra shoulder attitude.",
        contexts=("dance", "dance-desk-shuffle", "office-shuffle"),
        preferred_categories=("dance", "office", "playful"),
    ),
    DanceRoutineDefinition(
        key="victory-stomp",
        label="Victory Stomp",
        description="A louder, stompier success routine for suspiciously confident moments.",
        contexts=("dance", "dance-victory-stomp", "victory"),
        preferred_categories=("dance", "network", "celebrating"),
    ),
)

_DANCE_ROUTINE_MAP = {definition.key: definition for definition in DANCE_ROUTINE_DEFINITIONS}


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


def _copy_entry(entry, offset_delta=0, delay_scale=1.0):
    delay = entry.get("delay_ms")
    scaled_delay = None
    if delay is not None:
        scaled_delay = max(70, int(int(delay) * float(delay_scale)))
    return {
        "frame": str(entry["frame"]),
        "offset_y": int(entry.get("offset_y", 0)) + int(offset_delta),
        "delay_ms": scaled_delay,
    }


def _auto_dance_routines(base_sequence):
    base = _normalize_sequence(
        base_sequence,
        [{"frame": frame_key, "offset_y": 0, "delay_ms": None} for frame_key in DANCE_SEQUENCE],
    )
    if not base:
        base = [{"frame": frame_key, "offset_y": 0, "delay_ms": None} for frame_key in DANCE_SEQUENCE]

    def entry(index):
        return dict(base[index % len(base)])

    return {
        "classic-bounce": [dict(item) for item in base],
        "desk-shuffle": [
            _copy_entry(entry(0), offset_delta=0, delay_scale=0.95),
            _copy_entry(entry(1), offset_delta=-1, delay_scale=0.84),
            _copy_entry(entry(0), offset_delta=1, delay_scale=0.80),
            _copy_entry(entry(1), offset_delta=-1, delay_scale=0.82),
            _copy_entry(entry(len(base) // 2), offset_delta=0, delay_scale=0.74),
            _copy_entry(entry(-2), offset_delta=1, delay_scale=0.86),
            _copy_entry(entry(-1), offset_delta=0, delay_scale=0.92),
        ],
        "victory-stomp": [
            _copy_entry(entry(len(base) // 2), offset_delta=1, delay_scale=0.82),
            _copy_entry(entry(-1), offset_delta=2, delay_scale=0.72),
            _copy_entry(entry(len(base) // 2), offset_delta=0, delay_scale=0.74),
            _copy_entry(entry(0), offset_delta=-1, delay_scale=0.88),
            _copy_entry(entry(len(base) // 2), offset_delta=1, delay_scale=0.72),
            _copy_entry(entry(-1), offset_delta=2, delay_scale=0.68),
            _copy_entry(entry(0), offset_delta=0, delay_scale=0.96),
        ],
    }


def _normalize_dance_routines(dance_sequences, fallback_sequence):
    if not isinstance(dance_sequences, dict):
        return _auto_dance_routines(fallback_sequence)
    normalized = {}
    for key, sequence in dance_sequences.items():
        routine_key = str(key).strip()
        if not routine_key:
            continue
        routine_sequence = _normalize_sequence(sequence, [])
        if routine_sequence:
            normalized[routine_key] = routine_sequence
    if normalized:
        return normalized
    return _auto_dance_routines(fallback_sequence)


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
        self.dance_routines = _auto_dance_routines(self.interaction_sequence)
        self.active_dance_key = next(iter(self.dance_routines.keys()), "classic-bounce")
        self.interaction_sequence = [dict(entry) for entry in self.dance_routines.get(self.active_dance_key, [])]

    def set_sequences(self, idle_sequence=None, interaction_sequence=None, dance_sequences=None):
        self.idle_sequence = _normalize_sequence(
            idle_sequence,
            [{"frame": frame_key, "offset_y": offset_y} for frame_key, offset_y in IDLE_SEQUENCE],
        )
        self.interaction_sequence = _normalize_sequence(
            interaction_sequence,
            [{"frame": frame_key, "offset_y": 0} for frame_key in DANCE_SEQUENCE],
        )
        self.dance_routines = _normalize_dance_routines(dance_sequences, self.interaction_sequence)
        self.active_dance_key = next(iter(self.dance_routines.keys()), "classic-bounce")
        self.interaction_sequence = [dict(entry) for entry in self.dance_routines.get(self.active_dance_key, [])]
        self.idle_frame_idx = 0
        if not self.is_dancing:
            self.dance_frame_idx = 0

    def available_dance_routines(self):
        routines = []
        for routine_key in self.dance_routines:
            definition = _DANCE_ROUTINE_MAP.get(
                routine_key,
                DanceRoutineDefinition(
                    key=routine_key,
                    label=routine_key.replace("-", " ").title(),
                    description="Custom dance routine.",
                    contexts=("dance", routine_key),
                    preferred_categories=("dance",),
                ),
            )
            routines.append(definition)
        return routines

    def current_dance_key(self):
        return str(self.active_dance_key or "")

    def start_dance(self, routine_key=None):
        target_key = str(routine_key or self.active_dance_key or "").strip()
        if not target_key or target_key not in self.dance_routines:
            target_key = next(iter(self.dance_routines.keys()), "")
        if not target_key:
            return False
        self.active_dance_key = target_key
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

        active_sequence = self.dance_routines.get(self.active_dance_key, self.interaction_sequence)
        if self.is_dancing and active_sequence:
            entry = active_sequence[self.dance_frame_idx % len(active_sequence)]
            self.dance_frame_idx += 1
            if self.dance_frame_idx >= len(active_sequence) * 3:
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
