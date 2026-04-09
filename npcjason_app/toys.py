from __future__ import annotations

from dataclasses import dataclass, field
import math
import time


TOY_PIXEL_SCALE = 4


@dataclass(frozen=True)
class ToyDefinition:
    key: str
    label: str
    description: str
    behavior: str
    cooldown_ms: int
    sound_effect: str | None
    tags: tuple[str, ...]
    contexts: tuple[str, ...]
    palette: dict
    frames: dict
    animation_sequence: tuple[str, ...]
    anchor_offset: tuple[int, int] = (0, 0)
    behavior_config: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ToyTriggerResult:
    started: bool
    reason: str = ""
    toy_key: str | None = None
    sound_effect: str | None = None
    contexts: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    remaining_cooldown_ms: int = 0


@dataclass(frozen=True)
class ToyTickResult:
    active: bool
    next_delay_ms: int
    toy_key: str | None = None
    contexts: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    pet_position: tuple[int, int] | None = None
    finished_toy: str | None = None


TRICYCLE_FRAMES = {
    "roll_a": (
        "................",
        ".....R.....R....",
        "...RRR...RRR....",
        "..R...R.R...R...",
        "...RRR...RRR....",
        "....TTTTTT......",
        "...TTSSTTT......",
        "..TTTTTTTTT.....",
        "...K......K.....",
        "...K......K.....",
    ),
    "roll_b": (
        "................",
        ".....R.....R....",
        "...RRR...RRR....",
        "..R...R.R...R...",
        "...RRR...RRR....",
        "....TTTTTT......",
        "...TTSSSTT......",
        "..TTTTTTTTT.....",
        "..K........K....",
        "..K........K....",
    ),
}

DUCK_FRAMES = {
    "bob_a": (
        "............",
        "....YY......",
        "...YYYY.....",
        "..YYYYYO....",
        "..YYYKKYY...",
        "...YYYYYY...",
        ".....KK.....",
        "............",
    ),
    "bob_b": (
        "............",
        "....YY......",
        "...YYYY.....",
        "..YYYYYO....",
        "..YYYYKYY...",
        "...YYYYYY...",
        "....KKK.....",
        "............",
    ),
}

SERVER_CART_FRAMES = {
    "idle": (
        "..............",
        "..SSSSSSSS....",
        "..SGLGGLGS....",
        "..SLLLLLLS....",
        "..SLLLLLLS....",
        "..SGLGGLGS....",
        "..SSSSSSSS....",
        "...K....K.....",
        "...K....K.....",
        "..............",
    ),
    "blink": (
        "..............",
        "..SSSSSSSS....",
        "..SLGLGLLS....",
        "..SLLLLLLS....",
        "..SLLLLLLS....",
        "..SLGLGLLS....",
        "..SSSSSSSS....",
        "...K....K.....",
        "...K....K.....",
        "..............",
    ),
}

STRESS_BALL_FRAMES = {
    "round": (
        "........",
        "..BBBB..",
        ".BBBBBB.",
        ".BBBBBB.",
        ".BBBBBB.",
        "..BBBB..",
        "........",
        "........",
    ),
    "stretch": (
        "...BB...",
        "..BBBB..",
        ".BBBBBB.",
        ".BBBBBB.",
        "..BBBB..",
        "...BB...",
        "........",
        "........",
    ),
    "squash": (
        "........",
        "........",
        ".BBBBBB.",
        "BBBBBBBB",
        "BBBBBBBB",
        ".BBBBBB.",
        "........",
        "........",
    ),
}

TOY_DEFINITIONS = {
    "tricycle": ToyDefinition(
        key="tricycle",
        label="Tricycle Ride",
        description="Jason pedals a little lap with a wobble and a victory pause.",
        behavior="ride",
        cooldown_ms=120000,
        sound_effect="tricycle",
        tags=("playful", "rare", "ride"),
        contexts=("toy-play", "rideby", "tricycle"),
        palette={"T": "#d1495b", "S": "#ffd166", "R": "#2d3142", "K": "#7f5539"},
        frames=TRICYCLE_FRAMES,
        animation_sequence=("roll_a", "roll_b"),
        anchor_offset=(-12, 42),
        behavior_config={"travel_px": 170, "duration_ms": 3200, "pause_ratio": 0.18, "frame_ms": 150, "wobble_px": 6},
    ),
    "rubber-duck": ToyDefinition(
        key="rubber-duck",
        label="Rubber Duck",
        description="A debugging duck bobs nearby for moral support.",
        behavior="bob",
        cooldown_ms=90000,
        sound_effect="duck",
        tags=("debug", "playful", "desk"),
        contexts=("toy-play", "duck", "debug"),
        palette={"Y": "#ffcc33", "O": "#f97316", "K": "#6b4f3a"},
        frames=DUCK_FRAMES,
        animation_sequence=("bob_a", "bob_b"),
        anchor_offset=(44, 28),
        behavior_config={"duration_ms": 2600, "bob_px": 6, "drift_px": 12, "frame_ms": 220},
    ),
    "homelab-cart": ToyDefinition(
        key="homelab-cart",
        label="Tiny Homelab Server Cart",
        description="A tiny rack cart rolls in, blinks proudly, and heads back out.",
        behavior="rollby",
        cooldown_ms=150000,
        sound_effect="server_cart",
        tags=("homelab", "gear", "rare"),
        contexts=("toy-play", "homelab", "server-cart"),
        palette={"S": "#7b8794", "L": "#cbd5e1", "G": "#22c55e", "K": "#334155"},
        frames=SERVER_CART_FRAMES,
        animation_sequence=("idle", "blink"),
        anchor_offset=(-18, 30),
        behavior_config={"travel_px": 120, "duration_ms": 2800, "pause_ratio": 0.24, "frame_ms": 180},
    ),
    "stress-ball": ToyDefinition(
        key="stress-ball",
        label="Stress Ball",
        description="A soft bounce loop for when Jason is being very responsible about things.",
        behavior="bounce",
        cooldown_ms=70000,
        sound_effect="stress_ball",
        tags=("office", "responsible", "desk"),
        contexts=("toy-play", "stress-ball", "reset"),
        palette={"B": "#ef476f"},
        frames=STRESS_BALL_FRAMES,
        animation_sequence=("round", "stretch", "squash", "stretch"),
        anchor_offset=(18, 18),
        behavior_config={"duration_ms": 2200, "height_px": 72, "bounces": 4, "frame_ms": 110, "drift_px": 24},
    ),
}


class BaseToyBehavior:
    def __init__(self, definition, root, pet_x, pet_y, work_area, skin_offsets=None, logger=None):
        self.definition = definition
        self.root = root
        self.logger = logger
        self.work_area = work_area
        self.skin_offsets = skin_offsets or {}
        self.base_pet_x = int(pet_x)
        self.base_pet_y = int(pet_y)
        self.started_at_ms = None
        self.width = max(len(row) for row in next(iter(definition.frames.values())))
        self.height = len(next(iter(definition.frames.values())))
        try:
            from .toy_window import ToyWindow
        except Exception as exc:
            raise RuntimeError("toy-window-unavailable") from exc
        self.window = ToyWindow(
            root,
            self.width * TOY_PIXEL_SCALE,
            self.height * TOY_PIXEL_SCALE,
            logger=logger,
        )

    def destroy(self):
        self.window.destroy()

    def tick(self, now_ms, hidden=False):
        if hidden:
            self.destroy()
            return None
        if self.started_at_ms is None:
            self.started_at_ms = int(now_ms)
        elapsed_ms = max(0, int(now_ms) - self.started_at_ms)
        pose = self._pose(elapsed_ms)
        if pose is None:
            self.destroy()
            return None
        self.window.show()
        self.window.render_frame(
            self.definition.frames[pose["frame"]],
            self.definition.palette,
            TOY_PIXEL_SCALE,
        )
        self.window.move_to(pose["x"], pose["y"])
        return pose

    def _anchor_origin(self):
        toy_anchor = self.skin_offsets.get("toy_anchor", {"x": 0, "y": 0})
        return (
            self.base_pet_x + int(toy_anchor.get("x", 0)),
            self.base_pet_y + int(toy_anchor.get("y", 0)),
        )

    def _frame_key(self, elapsed_ms):
        sequence = tuple(self.definition.animation_sequence or tuple(self.definition.frames.keys()))
        if not sequence:
            return next(iter(self.definition.frames))
        frame_ms = max(50, int(self.definition.behavior_config.get("frame_ms", 180)))
        return sequence[(elapsed_ms // frame_ms) % len(sequence)]

    def _pose(self, elapsed_ms):
        raise NotImplementedError


class RideToyBehavior(BaseToyBehavior):
    def __init__(self, definition, root, pet_x, pet_y, work_area, skin_offsets=None, logger=None):
        super().__init__(definition, root, pet_x, pet_y, work_area, skin_offsets=skin_offsets, logger=logger)
        travel_px = int(self.definition.behavior_config.get("travel_px", 160))
        midpoint = (int(work_area.left) + int(work_area.right)) // 2
        if self.base_pet_x < midpoint and self.base_pet_x + travel_px < int(work_area.right) - 90:
            self.direction = 1
        elif self.base_pet_x - travel_px > int(work_area.left) + 20:
            self.direction = -1
        else:
            self.direction = 1 if self.base_pet_x < midpoint else -1

    def _ride_distance_ratio(self, progress):
        if progress < 0.45:
            return progress / 0.45
        if progress < 0.62:
            return 1.0
        return max(0.0, 1.0 - ((progress - 0.62) / 0.38))

    def _pose(self, elapsed_ms):
        duration_ms = max(600, int(self.definition.behavior_config.get("duration_ms", 3000)))
        if elapsed_ms >= duration_ms:
            return None
        progress = elapsed_ms / duration_ms
        wobble_px = int(self.definition.behavior_config.get("wobble_px", 6))
        travel_px = int(self.definition.behavior_config.get("travel_px", 160))
        ride_ratio = self._ride_distance_ratio(progress)
        x_offset = int(self.direction * travel_px * ride_ratio)
        y_offset = int(math.sin(progress * math.pi * 8) * wobble_px)
        pet_position = (self.base_pet_x + x_offset, self.base_pet_y + y_offset)
        anchor_x, anchor_y = self._anchor_origin()
        anchor_offset_x, anchor_offset_y = self.definition.anchor_offset
        return {
            "frame": self._frame_key(elapsed_ms),
            "x": anchor_x + x_offset + anchor_offset_x,
            "y": anchor_y + y_offset + anchor_offset_y,
            "pet_position": pet_position,
        }


class BobToyBehavior(BaseToyBehavior):
    def __init__(self, definition, root, pet_x, pet_y, work_area, skin_offsets=None, logger=None):
        super().__init__(definition, root, pet_x, pet_y, work_area, skin_offsets=skin_offsets, logger=logger)
        anchor_x, _anchor_y = self._anchor_origin()
        right_space = int(work_area.right) - anchor_x
        self.direction = 1 if right_space > 160 else -1

    def _pose(self, elapsed_ms):
        duration_ms = max(800, int(self.definition.behavior_config.get("duration_ms", 2600)))
        if elapsed_ms >= duration_ms:
            return None
        progress = elapsed_ms / duration_ms
        bob_px = int(self.definition.behavior_config.get("bob_px", 6))
        drift_px = int(self.definition.behavior_config.get("drift_px", 12))
        anchor_x, anchor_y = self._anchor_origin()
        anchor_offset_x, anchor_offset_y = self.definition.anchor_offset
        return {
            "frame": self._frame_key(elapsed_ms),
            "x": anchor_x + anchor_offset_x + self.direction * int(drift_px * math.sin(progress * math.pi * 2)),
            "y": anchor_y + anchor_offset_y + int(math.sin(progress * math.pi * 4) * bob_px),
        }


class RollByToyBehavior(BaseToyBehavior):
    def __init__(self, definition, root, pet_x, pet_y, work_area, skin_offsets=None, logger=None):
        super().__init__(definition, root, pet_x, pet_y, work_area, skin_offsets=skin_offsets, logger=logger)
        midpoint = (int(work_area.left) + int(work_area.right)) // 2
        self.direction = 1 if self.base_pet_x < midpoint else -1

    def _offset_ratio(self, progress):
        if progress < 0.35:
            return -1.0 + (progress / 0.35)
        if progress < 0.65:
            return 0.0
        return (progress - 0.65) / 0.35

    def _pose(self, elapsed_ms):
        duration_ms = max(800, int(self.definition.behavior_config.get("duration_ms", 2800)))
        if elapsed_ms >= duration_ms:
            return None
        progress = elapsed_ms / duration_ms
        travel_px = int(self.definition.behavior_config.get("travel_px", 120))
        anchor_x, anchor_y = self._anchor_origin()
        anchor_offset_x, anchor_offset_y = self.definition.anchor_offset
        offset_x = int(self.direction * travel_px * self._offset_ratio(progress))
        return {
            "frame": self._frame_key(elapsed_ms),
            "x": anchor_x + anchor_offset_x + offset_x,
            "y": anchor_y + anchor_offset_y,
        }


class BounceToyBehavior(BaseToyBehavior):
    def _pose(self, elapsed_ms):
        duration_ms = max(800, int(self.definition.behavior_config.get("duration_ms", 2200)))
        if elapsed_ms >= duration_ms:
            return None
        progress = elapsed_ms / duration_ms
        bounces = max(1, int(self.definition.behavior_config.get("bounces", 4)))
        drift_px = int(self.definition.behavior_config.get("drift_px", 24))
        height_px = int(self.definition.behavior_config.get("height_px", 72))
        bounce_progress = progress * bounces
        local = bounce_progress - math.floor(bounce_progress)
        amplitude = max(8, int(height_px * (1.0 - (progress * 0.65))))
        height_offset = -abs(math.sin(local * math.pi)) * amplitude
        anchor_x, anchor_y = self._anchor_origin()
        anchor_offset_x, anchor_offset_y = self.definition.anchor_offset
        if local > 0.82:
            frame_key = "squash"
        elif local > 0.58:
            frame_key = "stretch"
        else:
            frame_key = "round"
        return {
            "frame": frame_key if frame_key in self.definition.frames else self._frame_key(elapsed_ms),
            "x": anchor_x + anchor_offset_x + int(math.sin(progress * math.pi * 2) * drift_px),
            "y": anchor_y + anchor_offset_y + int(height_offset),
        }


BEHAVIOR_TYPES = {
    "ride": RideToyBehavior,
    "bob": BobToyBehavior,
    "rollby": RollByToyBehavior,
    "bounce": BounceToyBehavior,
}


class ToyManager:
    def __init__(self, root, logger=None, clock=None):
        self.root = root
        self.logger = logger
        self.clock = clock or time.monotonic
        self.definitions = dict(TOY_DEFINITIONS)
        self._cooldowns = {}
        self._active = None

    def available_toys(self):
        now_ms = self._now_ms()
        items = []
        for definition in sorted(self.definitions.values(), key=lambda value: value.label.lower()):
            remaining = max(0, int(self._cooldowns.get(definition.key, 0) - now_ms))
            items.append(
                {
                    "key": definition.key,
                    "label": definition.label,
                    "description": definition.description,
                    "active": bool(self._active and self._active.definition.key == definition.key),
                    "cooldown_ms": remaining,
                    "tags": list(definition.tags),
                    "contexts": list(definition.contexts),
                }
            )
        return items

    def active_toy_key(self):
        if not self._active:
            return None
        return self._active.definition.key

    def active_contexts(self):
        if not self._active:
            return ()
        return tuple(self._active.definition.contexts)

    def active_tags(self):
        if not self._active:
            return ()
        return tuple(self._active.definition.tags)

    def can_trigger(self, toy_key):
        return self.remaining_cooldown_ms(toy_key) <= 0 and self._active is None

    def remaining_cooldown_ms(self, toy_key):
        return max(0, int(self._cooldowns.get(toy_key, 0) - self._now_ms()))

    def trigger(self, toy_key, pet_x, pet_y, work_area, skin_offsets=None):
        definition = self.definitions.get(toy_key)
        if not definition:
            return ToyTriggerResult(started=False, reason="unknown-toy")
        if self._active is not None:
            return ToyTriggerResult(started=False, reason="busy")
        remaining = self.remaining_cooldown_ms(toy_key)
        if remaining > 0:
            return ToyTriggerResult(
                started=False,
                reason="cooldown",
                toy_key=toy_key,
                remaining_cooldown_ms=remaining,
            )
        behavior_type = BEHAVIOR_TYPES.get(definition.behavior)
        if behavior_type is None:
            return ToyTriggerResult(started=False, reason="unsupported-behavior", toy_key=toy_key)
        try:
            self._active = behavior_type(
                definition,
                self.root,
                pet_x,
                pet_y,
                work_area,
                skin_offsets=skin_offsets,
                logger=self.logger,
            )
        except RuntimeError as exc:
            self._log("warning", f"toy: could not start {toy_key} ({exc})")
            return ToyTriggerResult(started=False, reason="ui-unavailable", toy_key=toy_key)
        return ToyTriggerResult(
            started=True,
            toy_key=definition.key,
            sound_effect=definition.sound_effect,
            contexts=definition.contexts,
            tags=definition.tags,
        )

    def tick(self, hidden=False):
        if self._active is None:
            return ToyTickResult(active=False, next_delay_ms=150)
        pose = self._active.tick(self._now_ms(), hidden=hidden)
        if pose is None:
            definition = self._active.definition
            self._cooldowns[definition.key] = self._now_ms() + int(definition.cooldown_ms)
            self._active = None
            return ToyTickResult(active=False, next_delay_ms=150, finished_toy=definition.key)
        definition = self._active.definition
        return ToyTickResult(
            active=True,
            next_delay_ms=55,
            toy_key=definition.key,
            contexts=definition.contexts,
            tags=definition.tags,
            pet_position=pose.get("pet_position"),
        )

    def shutdown(self):
        if self._active is not None:
            self._active.destroy()
            self._active = None

    def _now_ms(self):
        return int(self.clock() * 1000)

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message)
