from __future__ import annotations

from dataclasses import dataclass, field
import math
import time


DESK_ITEM_PIXEL_SCALE = 4
DESK_ITEM_TICK_MS = 95


@dataclass(frozen=True)
class DeskItemDefinition:
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
class DeskItemTriggerResult:
    started: bool
    reason: str = ""
    item_key: str | None = None
    sound_effect: str | None = None
    contexts: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    remaining_cooldown_ms: int = 0


@dataclass(frozen=True)
class DeskItemTickResult:
    active: bool
    next_delay_ms: int
    item_key: str | None = None
    contexts: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    finished_item: str | None = None


COFFEE_MUG_FRAMES = {
    "steam_a": (
        "............",
        "...S..S.....",
        "...S..S.....",
        "....SS......",
        "...MMMM.....",
        "..MCCCCM....",
        "..MCCCCM....",
        "..MCCCCMMM..",
        "..MCCCCM....",
        "..MMMMMM....",
    ),
    "steam_b": (
        "............",
        "....S.......",
        "...S.S......",
        "....S..S....",
        "...MMMM.....",
        "..MCCCCM....",
        "..MCCCCM....",
        "..MCCCCMMM..",
        "..MCCCCM....",
        "..MMMMMM....",
    ),
    "sip": (
        "....S.......",
        "...S.S......",
        "....S.......",
        "..MMMM......",
        ".MCCCCM.....",
        ".MCCCCM.....",
        ".MCCCCMMM...",
        ".MCCCCM.....",
        ".MMMMMM.....",
        "............",
    ),
}

KEYBOARD_FRAMES = {
    "tap_a": (
        "................",
        ".KKKKKKKKKKKKKK.",
        ".KWWWWWWWWWWWWWK.",
        ".KWWKWWKWWKWWWWK.",
        ".KWWWWWWWWWWWWWK.",
        ".KKKKKKKKKKKKKK.",
    ),
    "tap_b": (
        "................",
        ".KKKKKKKKKKKKKK.",
        ".KWWWWWWWWWWWWWK.",
        ".KWWWWKWWWWKWWWK.",
        ".KWWWWWWWWWWWWWK.",
        ".KKKKKKKKKKKKKK.",
    ),
    "tap_c": (
        "................",
        ".KKKKKKKKKKKKKK.",
        ".KWWKWWWWKWWWWWK.",
        ".KWWWWWWWWWWWWWK.",
        ".KWWWKWWWWKWWWWK.",
        ".KKKKKKKKKKKKKK.",
    ),
}

NETWORK_RACK_FRAMES = {
    "blink_a": (
        "..............",
        "..RRRRRRRR....",
        "..RBBBBBBR....",
        "..RGLGLGLR....",
        "..RBBBBBBR....",
        "..RGLGLGLR....",
        "..RBBBBBBR....",
        "..RRRRRRRR....",
        "...K....K.....",
        "...K....K.....",
    ),
    "blink_b": (
        "..............",
        "..RRRRRRRR....",
        "..RBBBBBBR....",
        "..RLGGLGGR....",
        "..RBBBBBBR....",
        "..RGGLGGLR....",
        "..RBBBBBBR....",
        "..RRRRRRRR....",
        "...K....K.....",
        "...K....K.....",
    ),
}


DESK_ITEM_DEFINITIONS = {
    "coffee-mug": DeskItemDefinition(
        key="coffee-mug",
        label="Coffee Mug",
        description="A suspiciously restorative desk mug with visible steam and bad influence.",
        behavior="sip",
        cooldown_ms=78_000,
        sound_effect="coffee_mug",
        tags=("desk", "coffee", "office", "caffeinated"),
        contexts=("desk-item", "desk-coffee", "coffee-break"),
        palette={"M": "#6b4f3a", "C": "#f4efe8", "S": "#d8dee9"},
        frames=COFFEE_MUG_FRAMES,
        animation_sequence=("steam_a", "steam_b", "steam_a", "sip", "steam_b"),
        anchor_offset=(36, 28),
        behavior_config={"duration_ms": 2_600, "bob_px": 3, "drift_px": 6, "frame_ms": 190},
    ),
    "keyboard": DeskItemDefinition(
        key="keyboard",
        label="Desk Keyboard",
        description="A tiny keyboard Jason can aggressively pretend to use.",
        behavior="tap",
        cooldown_ms=64_000,
        sound_effect="keyboard_tap",
        tags=("desk", "keyboard", "office", "helpdesk"),
        contexts=("desk-item", "desk-keyboard", "keyboard"),
        palette={"K": "#39424e", "W": "#e5e7eb"},
        frames=KEYBOARD_FRAMES,
        animation_sequence=("tap_a", "tap_b", "tap_c", "tap_b"),
        anchor_offset=(6, 50),
        behavior_config={"duration_ms": 2_350, "shake_px": 4, "drift_px": 8, "frame_ms": 105},
    ),
    "tiny-network-rack": DeskItemDefinition(
        key="tiny-network-rack",
        label="Tiny Network Rack",
        description="A very serious little rack that blinks like it knows what broke.",
        behavior="roll",
        cooldown_ms=102_000,
        sound_effect="rack_blink",
        tags=("desk", "network", "homelab", "gear"),
        contexts=("desk-item", "desk-rack", "network-rack"),
        palette={"R": "#64748b", "B": "#0f172a", "G": "#22c55e", "L": "#60a5fa", "K": "#334155"},
        frames=NETWORK_RACK_FRAMES,
        animation_sequence=("blink_a", "blink_b"),
        anchor_offset=(-24, 28),
        behavior_config={"duration_ms": 2_900, "travel_px": 34, "pause_ratio": 0.34, "frame_ms": 165},
    ),
}


class BaseDeskItemBehavior:
    def __init__(self, definition, root, owner_x, owner_y, work_area, skin_offsets=None, logger=None):
        self.definition = definition
        self.root = root
        self.logger = logger
        self.work_area = work_area
        self.skin_offsets = skin_offsets or {}
        self.owner_x = int(owner_x)
        self.owner_y = int(owner_y)
        self.started_at_ms = None
        self.width = max(len(row) for row in next(iter(definition.frames.values())))
        self.height = len(next(iter(definition.frames.values())))
        try:
            from .toy_window import ToyWindow
        except Exception as exc:
            raise RuntimeError("desk-item-window-unavailable") from exc
        self.window = ToyWindow(
            root,
            self.width * DESK_ITEM_PIXEL_SCALE,
            self.height * DESK_ITEM_PIXEL_SCALE,
            logger=logger,
        )

    def update_owner_position(self, owner_x, owner_y):
        self.owner_x = int(owner_x)
        self.owner_y = int(owner_y)

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
            DESK_ITEM_PIXEL_SCALE,
        )
        self.window.move_to(pose["x"], pose["y"])
        return pose

    def _anchor_origin(self):
        anchor = self.skin_offsets.get("toy_anchor", {"x": 0, "y": 0})
        return (
            self.owner_x + int(anchor.get("x", 0)),
            self.owner_y + int(anchor.get("y", 0)),
        )

    def _frame_key(self, elapsed_ms):
        sequence = tuple(self.definition.animation_sequence or tuple(self.definition.frames.keys()))
        if not sequence:
            return next(iter(self.definition.frames))
        frame_ms = max(60, int(self.definition.behavior_config.get("frame_ms", 180)))
        return sequence[(elapsed_ms // frame_ms) % len(sequence)]

    def _pose(self, elapsed_ms):
        raise NotImplementedError


class BobDeskItemBehavior(BaseDeskItemBehavior):
    def _pose(self, elapsed_ms):
        duration_ms = max(700, int(self.definition.behavior_config.get("duration_ms", 2400)))
        if elapsed_ms >= duration_ms:
            return None
        progress = elapsed_ms / duration_ms
        bob_px = int(self.definition.behavior_config.get("bob_px", 3))
        drift_px = int(self.definition.behavior_config.get("drift_px", 6))
        anchor_x, anchor_y = self._anchor_origin()
        offset_x, offset_y = self.definition.anchor_offset
        return {
            "frame": self._frame_key(elapsed_ms),
            "x": anchor_x + offset_x + int(math.sin(progress * math.pi * 2.0) * drift_px),
            "y": anchor_y + offset_y + int(math.sin(progress * math.pi * 4.0) * bob_px),
        }


class TapDeskItemBehavior(BaseDeskItemBehavior):
    def _pose(self, elapsed_ms):
        duration_ms = max(700, int(self.definition.behavior_config.get("duration_ms", 2200)))
        if elapsed_ms >= duration_ms:
            return None
        progress = elapsed_ms / duration_ms
        shake_px = int(self.definition.behavior_config.get("shake_px", 3))
        drift_px = int(self.definition.behavior_config.get("drift_px", 6))
        anchor_x, anchor_y = self._anchor_origin()
        offset_x, offset_y = self.definition.anchor_offset
        local_shake = math.sin(progress * math.pi * 16.0) * shake_px
        return {
            "frame": self._frame_key(elapsed_ms),
            "x": anchor_x + offset_x + int(local_shake),
            "y": anchor_y + offset_y + int(abs(math.sin(progress * math.pi * 8.0)) * (drift_px / 2.0)),
        }


class RollDeskItemBehavior(BaseDeskItemBehavior):
    def __init__(self, definition, root, owner_x, owner_y, work_area, skin_offsets=None, logger=None):
        super().__init__(definition, root, owner_x, owner_y, work_area, skin_offsets=skin_offsets, logger=logger)
        midpoint = (int(work_area.left) + int(work_area.right)) // 2
        self.direction = -1 if self.owner_x > midpoint else 1

    def _offset_ratio(self, progress):
        pause_ratio = max(0.1, min(0.6, float(self.definition.behavior_config.get("pause_ratio", 0.3))))
        travel_ratio = (1.0 - pause_ratio) / 2.0
        if progress < travel_ratio:
            return -1.0 + (progress / travel_ratio)
        if progress < travel_ratio + pause_ratio:
            return 0.0
        return (progress - travel_ratio - pause_ratio) / travel_ratio

    def _pose(self, elapsed_ms):
        duration_ms = max(900, int(self.definition.behavior_config.get("duration_ms", 2800)))
        if elapsed_ms >= duration_ms:
            return None
        progress = elapsed_ms / duration_ms
        travel_px = int(self.definition.behavior_config.get("travel_px", 28))
        anchor_x, anchor_y = self._anchor_origin()
        offset_x, offset_y = self.definition.anchor_offset
        travel = int(self.direction * travel_px * self._offset_ratio(progress))
        return {
            "frame": self._frame_key(elapsed_ms),
            "x": anchor_x + offset_x + travel,
            "y": anchor_y + offset_y,
        }


BEHAVIOR_TYPES = {
    "sip": BobDeskItemBehavior,
    "tap": TapDeskItemBehavior,
    "roll": RollDeskItemBehavior,
}


class DeskItemManager:
    def __init__(self, root, logger=None, clock=None):
        self.root = root
        self.logger = logger
        self.clock = clock or time.monotonic
        self.definitions = dict(DESK_ITEM_DEFINITIONS)
        self._cooldowns = {}
        self._active = None

    def available_items(self):
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

    def active_item_key(self):
        if not self._active:
            return ""
        return self._active.definition.key

    def active_contexts(self):
        if not self._active:
            return ()
        return tuple(self._active.definition.contexts)

    def active_tags(self):
        if not self._active:
            return ()
        return tuple(self._active.definition.tags)

    def remaining_cooldown_ms(self, item_key):
        return max(0, int(self._cooldowns.get(item_key, 0) - self._now_ms()))

    def trigger(self, item_key, owner_x, owner_y, work_area, skin_offsets=None):
        definition = self.definitions.get(item_key)
        if not definition:
            return DeskItemTriggerResult(started=False, reason="unknown-desk-item")
        if self._active is not None:
            return DeskItemTriggerResult(started=False, reason="busy", item_key=item_key)
        remaining = self.remaining_cooldown_ms(item_key)
        if remaining > 0:
            return DeskItemTriggerResult(
                started=False,
                reason="cooldown",
                item_key=item_key,
                remaining_cooldown_ms=remaining,
            )
        behavior_type = BEHAVIOR_TYPES.get(definition.behavior)
        if behavior_type is None:
            return DeskItemTriggerResult(started=False, reason="unsupported-behavior", item_key=item_key)
        try:
            self._active = behavior_type(
                definition,
                self.root,
                owner_x,
                owner_y,
                work_area,
                skin_offsets=skin_offsets,
                logger=self.logger,
            )
        except RuntimeError as exc:
            self._log("warning", f"desk-item: could not start {item_key} ({exc})")
            return DeskItemTriggerResult(started=False, reason="ui-unavailable", item_key=item_key)
        return DeskItemTriggerResult(
            started=True,
            item_key=definition.key,
            sound_effect=definition.sound_effect,
            contexts=definition.contexts,
            tags=definition.tags,
        )

    def tick(self, hidden=False, owner_x=None, owner_y=None):
        if self._active is None:
            return DeskItemTickResult(active=False, next_delay_ms=DESK_ITEM_TICK_MS)
        if owner_x is not None and owner_y is not None:
            self._active.update_owner_position(owner_x, owner_y)
        pose = self._active.tick(self._now_ms(), hidden=hidden)
        if pose is None:
            definition = self._active.definition
            self._cooldowns[definition.key] = self._now_ms() + int(definition.cooldown_ms)
            self._active = None
            return DeskItemTickResult(active=False, next_delay_ms=DESK_ITEM_TICK_MS, finished_item=definition.key)
        definition = self._active.definition
        return DeskItemTickResult(
            active=True,
            next_delay_ms=DESK_ITEM_TICK_MS,
            item_key=definition.key,
            contexts=definition.contexts,
            tags=definition.tags,
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
