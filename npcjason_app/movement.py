from __future__ import annotations

from dataclasses import dataclass
import random
import time


EDGE_MARGIN = 18
CORNER_MARGIN = 48


@dataclass(frozen=True)
class MovementProfile:
    key: str
    step_px: int
    roam_radius_px: int
    hold_min_ms: int
    hold_max_ms: int
    inspect_ms: int
    haste: float = 1.0


@dataclass
class MovementIntent:
    style: str
    target_x: int
    target_y: int
    hold_until_ms: int
    expires_at_ms: int
    focus: str = ""
    direction_x: int = 0
    direction_y: int = 0
    inspected: bool = False


@dataclass(frozen=True)
class MovementResult:
    x: int
    y: int
    moved: bool
    style: str
    facing: str
    next_delay_ms: int
    debug_note: str = ""


PROFILES = {
    "linger": MovementProfile("linger", step_px=3, roam_radius_px=36, hold_min_ms=600, hold_max_ms=2400, inspect_ms=900),
    "inspect": MovementProfile("inspect", step_px=4, roam_radius_px=96, hold_min_ms=300, hold_max_ms=900, inspect_ms=1200),
    "strut": MovementProfile("strut", step_px=5, roam_radius_px=86, hold_min_ms=260, hold_max_ms=700, inspect_ms=700, haste=1.15),
    "pace": MovementProfile("pace", step_px=6, roam_radius_px=120, hold_min_ms=220, hold_max_ms=540, inspect_ms=600, haste=1.25),
    "agitated": MovementProfile("agitated", step_px=5, roam_radius_px=92, hold_min_ms=180, hold_max_ms=420, inspect_ms=380, haste=1.2),
    "victory": MovementProfile("victory", step_px=7, roam_radius_px=144, hold_min_ms=160, hold_max_ms=360, inspect_ms=520, haste=1.35),
    "hesitate": MovementProfile("hesitate", step_px=3, roam_radius_px=64, hold_min_ms=700, hold_max_ms=1900, inspect_ms=1100),
    "sneak": MovementProfile("sneak", step_px=4, roam_radius_px=88, hold_min_ms=500, hold_max_ms=1300, inspect_ms=980),
    "slump": MovementProfile("slump", step_px=2, roam_radius_px=28, hold_min_ms=1200, hold_max_ms=2800, inspect_ms=1200),
}


class MovementController:
    def __init__(self, logger=None, clock=None):
        self.logger = logger
        self.clock = clock or time.monotonic
        self.facing = "right"
        self._intent = None
        self._scripted = None
        self._last_position = None
        self._stuck_count = 0

    def clear(self):
        self._intent = None
        self._scripted = None
        self._stuck_count = 0

    def set_scripted(self, style, duration_ms=2000, focus=""):
        self._scripted = {
            "style": str(style or "linger").strip() or "linger",
            "focus": str(focus or "").strip(),
            "expires_at_ms": self._now_ms() + max(200, int(duration_ms)),
        }
        self._intent = None

    def active_style(self, fallback_style="linger"):
        if self._scripted and self._scripted["expires_at_ms"] > self._now_ms():
            return self._scripted["style"]
        return str(fallback_style or "linger")

    def tick(self, x, y, bounds, style="linger", rng=None):
        rng = rng or random
        style = self.active_style(style)
        if style not in PROFILES:
            style = "linger"
        if self._scripted and self._scripted["expires_at_ms"] <= self._now_ms():
            self._scripted = None
            self._intent = None

        if self._intent is None or self._intent.style != style or self._intent.expires_at_ms <= self._now_ms():
            self._intent = self._build_intent(x, y, bounds, style, rng)

        if self._intent.hold_until_ms > self._now_ms():
            return MovementResult(int(x), int(y), False, style, self.facing, 140, debug_note="hold")

        delta_x = int(self._intent.target_x) - int(x)
        delta_y = int(self._intent.target_y) - int(y)
        if abs(delta_x) <= 3 and abs(delta_y) <= 3:
            if self._intent.focus and not self._intent.inspected:
                self._intent.inspected = True
                self._intent.hold_until_ms = self._now_ms() + int(PROFILES[style].inspect_ms)
                retreat_x, retreat_y = self._retreat_target(x, y, bounds, self._intent.focus)
                self._intent.target_x = retreat_x
                self._intent.target_y = retreat_y
                return MovementResult(int(x), int(y), False, style, self.facing, 180, debug_note="inspect")
            self._intent = self._build_intent(x, y, bounds, style, rng)
            return MovementResult(int(x), int(y), False, style, self.facing, 130, debug_note="retarget")

        profile = PROFILES[style]
        step_px = max(1, int(profile.step_px))
        move_x = self._step_towards(delta_x, step_px)
        move_y = self._step_towards(delta_y, max(1, step_px - 1))
        if style in {"pace", "strut", "victory", "agitated"} and abs(delta_x) > abs(delta_y):
            move_y = self._step_towards(delta_y, 1)
        if style in {"hesitate", "sneak", "slump"} and rng.random() < 0.12:
            self._intent.hold_until_ms = self._now_ms() + rng.randint(profile.hold_min_ms, profile.hold_max_ms)
            return MovementResult(int(x), int(y), False, style, self.facing, 160, debug_note="hesitate")

        proposed_x = int(x) + move_x
        proposed_y = int(y) + move_y
        clamped_x = max(int(bounds.left), min(int(bounds.right), proposed_x))
        clamped_y = max(int(bounds.top), min(int(bounds.bottom), proposed_y))
        if clamped_x == int(x) and clamped_y == int(y):
            self._stuck_count += 1
            self._intent = self._recover_intent(x, y, bounds, style, rng)
            return MovementResult(int(x), int(y), False, style, self.facing, 160, debug_note="recover")

        if clamped_x != proposed_x or clamped_y != proposed_y:
            self._intent = self._recover_intent(clamped_x, clamped_y, bounds, style, rng)

        if clamped_x > int(x):
            self.facing = "right"
        elif clamped_x < int(x):
            self.facing = "left"

        moved = clamped_x != int(x) or clamped_y != int(y)
        if self._last_position == (clamped_x, clamped_y):
            self._stuck_count += 1
        else:
            self._stuck_count = 0
        self._last_position = (clamped_x, clamped_y)
        return MovementResult(int(clamped_x), int(clamped_y), moved, style, self.facing, 120)

    def _build_intent(self, x, y, bounds, style, rng):
        profile = PROFILES[style]
        focus = ""
        scripted_focus = ""
        if self._scripted:
            scripted_focus = str(self._scripted.get("focus", "")).strip()
        if style in {"inspect", "sneak"}:
            focus = scripted_focus or self._pick_focus(x, y, bounds, rng)
            target_x, target_y = self._focus_target(bounds, focus)
        elif style == "hesitate" and scripted_focus:
            focus = scripted_focus
            target_x, target_y = self._focus_target(bounds, focus)
        elif style == "pace":
            direction = -1 if self.facing == "right" else 1
            target_x = int(x) + (direction * profile.roam_radius_px)
            target_y = int(y) + rng.randint(-10, 10)
        elif style == "victory":
            direction = 1 if rng.random() < 0.5 else -1
            target_x = int(x) + (direction * profile.roam_radius_px)
            target_y = int(y) + rng.randint(-18, 10)
        elif style == "agitated":
            target_x = int(x) + rng.choice((-1, 1)) * rng.randint(28, profile.roam_radius_px)
            target_y = int(y) + rng.randint(-14, 14)
        elif style == "strut":
            target_x = int(x) + rng.choice((-1, 1)) * rng.randint(24, profile.roam_radius_px)
            target_y = int(y) + rng.randint(-8, 8)
        elif style == "slump":
            target_x = int(x) + rng.randint(-profile.roam_radius_px, profile.roam_radius_px)
            target_y = int(y) + rng.randint(-4, 4)
        elif style == "hesitate":
            if rng.random() < 0.5:
                focus = self._pick_focus(x, y, bounds, rng)
                target_x, target_y = self._focus_target(bounds, focus)
            else:
                target_x = int(x) + rng.randint(-profile.roam_radius_px, profile.roam_radius_px)
                target_y = int(y) + rng.randint(-16, 16)
        else:
            target_x = int(x) + rng.randint(-profile.roam_radius_px, profile.roam_radius_px)
            target_y = int(y) + rng.randint(-18, 18)

        target_x = self._clamp_target(target_x, int(bounds.left), int(bounds.right))
        target_y = self._clamp_target(target_y, int(bounds.top), int(bounds.bottom))
        return MovementIntent(
            style=style,
            target_x=target_x,
            target_y=target_y,
            hold_until_ms=self._now_ms() + rng.randint(profile.hold_min_ms, profile.hold_max_ms),
            expires_at_ms=self._now_ms() + rng.randint(1400, 4200),
            focus=focus,
        )

    def _recover_intent(self, x, y, bounds, style, rng):
        inward_x = int(x)
        inward_y = int(y)
        if self._near_left_edge(x, bounds):
            inward_x = int(x) + 48
        elif self._near_right_edge(x, bounds):
            inward_x = int(x) - 48
        else:
            inward_x = int(x) + rng.choice((-1, 1)) * 32
        if self._near_top_edge(y, bounds):
            inward_y = int(y) + 36
        elif self._near_bottom_edge(y, bounds):
            inward_y = int(y) - 36
        else:
            inward_y = int(y) + rng.randint(-18, 18)
        return MovementIntent(
            style=style,
            target_x=self._clamp_target(inward_x, int(bounds.left), int(bounds.right)),
            target_y=self._clamp_target(inward_y, int(bounds.top), int(bounds.bottom)),
            hold_until_ms=self._now_ms() + 180,
            expires_at_ms=self._now_ms() + 1800,
        )

    @staticmethod
    def _step_towards(delta, step_px):
        if delta == 0:
            return 0
        if abs(delta) <= step_px:
            return int(delta)
        return step_px if delta > 0 else -step_px

    @staticmethod
    def _clamp_target(value, minimum, maximum):
        low = int(minimum) + EDGE_MARGIN
        high = max(low, int(maximum) - EDGE_MARGIN)
        return max(low, min(int(value), high))

    def _pick_focus(self, x, y, bounds, rng):
        options = []
        if self._near_left_edge(x, bounds):
            options.extend(["left-edge", "top-left", "bottom-left"])
        if self._near_right_edge(x, bounds):
            options.extend(["right-edge", "top-right", "bottom-right"])
        if self._near_top_edge(y, bounds):
            options.extend(["top-edge", "top-left", "top-right"])
        if self._near_bottom_edge(y, bounds):
            options.extend(["bottom-edge", "bottom-left", "bottom-right"])
        if not options:
            options = [
                "left-edge",
                "right-edge",
                "top-edge",
                "bottom-edge",
                "top-left",
                "top-right",
                "bottom-left",
                "bottom-right",
            ]
        return rng.choice(options)

    @staticmethod
    def _focus_target(bounds, focus):
        targets = {
            "left-edge": (int(bounds.left) + EDGE_MARGIN, (int(bounds.top) + int(bounds.bottom)) // 2),
            "right-edge": (int(bounds.right) - EDGE_MARGIN, (int(bounds.top) + int(bounds.bottom)) // 2),
            "top-edge": ((int(bounds.left) + int(bounds.right)) // 2, int(bounds.top) + EDGE_MARGIN),
            "bottom-edge": ((int(bounds.left) + int(bounds.right)) // 2, int(bounds.bottom) - EDGE_MARGIN),
            "top-left": (int(bounds.left) + EDGE_MARGIN, int(bounds.top) + EDGE_MARGIN),
            "top-right": (int(bounds.right) - EDGE_MARGIN, int(bounds.top) + EDGE_MARGIN),
            "bottom-left": (int(bounds.left) + EDGE_MARGIN, int(bounds.bottom) - EDGE_MARGIN),
            "bottom-right": (int(bounds.right) - EDGE_MARGIN, int(bounds.bottom) - EDGE_MARGIN),
        }
        return targets.get(str(focus or ""), targets["right-edge"])

    @staticmethod
    def _retreat_target(x, y, bounds, focus):
        target_x = int(x)
        target_y = int(y)
        if "left" in focus:
            target_x += 44
        if "right" in focus:
            target_x -= 44
        if "top" in focus:
            target_y += 28
        if "bottom" in focus:
            target_y -= 28
        if focus.endswith("edge"):
            if focus.startswith("left"):
                target_x += 44
            elif focus.startswith("right"):
                target_x -= 44
            elif focus.startswith("top"):
                target_y += 28
            elif focus.startswith("bottom"):
                target_y -= 28
        target_x = max(int(bounds.left) + EDGE_MARGIN, min(int(bounds.right) - EDGE_MARGIN, target_x))
        target_y = max(int(bounds.top) + EDGE_MARGIN, min(int(bounds.bottom) - EDGE_MARGIN, target_y))
        return int(target_x), int(target_y)

    @staticmethod
    def _near_left_edge(x, bounds):
        return int(x) <= int(bounds.left) + CORNER_MARGIN

    @staticmethod
    def _near_right_edge(x, bounds):
        return int(x) >= int(bounds.right) - CORNER_MARGIN

    @staticmethod
    def _near_top_edge(y, bounds):
        return int(y) <= int(bounds.top) + CORNER_MARGIN

    @staticmethod
    def _near_bottom_edge(y, bounds):
        return int(y) >= int(bounds.bottom) - CORNER_MARGIN

    def _now_ms(self):
        return int(self.clock() * 1000)
