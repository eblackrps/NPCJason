from __future__ import annotations

from dataclasses import dataclass
import random
import time


@dataclass(frozen=True)
class PersonalityDefinition:
    key: str
    label: str
    description: str
    movement_style: str
    quote_contexts: tuple[str, ...]
    preferred_categories: tuple[str, ...]
    animation_profile: dict
    sound_effect: str | None
    min_duration_ms: int
    max_duration_ms: int
    transition_weights: dict[str, int]


PERSONALITY_STATES = {
    "idle": PersonalityDefinition(
        key="idle",
        label="Idle",
        description="Loitering on the desktop and acting like that is a real job.",
        movement_style="linger",
        quote_contexts=("personality-idle", "settled"),
        preferred_categories=("ambient",),
        animation_profile={"delay_scale": 1.0, "offset_y": 0, "bob_px": 0, "jitter_px": 0},
        sound_effect=None,
        min_duration_ms=18_000,
        max_duration_ms=38_000,
        transition_weights={
            "idle": 2,
            "curious": 4,
            "busy": 3,
            "sneaky": 2,
            "confused": 2,
            "exhausted": 1,
        },
    ),
    "curious": PersonalityDefinition(
        key="curious",
        label="Curious",
        description="Has decided some desktop thing needs inspecting immediately.",
        movement_style="inspect",
        quote_contexts=("personality-curious", "curious", "what-do"),
        preferred_categories=("curious", "what-do"),
        animation_profile={"delay_scale": 0.94, "offset_y": -1, "bob_px": 1, "jitter_px": 0},
        sound_effect="state_curious",
        min_duration_ms=8_000,
        max_duration_ms=18_000,
        transition_weights={
            "idle": 4,
            "curious": 1,
            "confused": 3,
            "smug": 2,
            "sneaky": 2,
        },
    ),
    "smug": PersonalityDefinition(
        key="smug",
        label="Smug",
        description="Looks deeply pleased with whatever nonsense just happened.",
        movement_style="strut",
        quote_contexts=("personality-smug", "smug"),
        preferred_categories=("network", "smug"),
        animation_profile={"delay_scale": 0.9, "offset_y": -1, "bob_px": 1, "jitter_px": 0},
        sound_effect="state_smug",
        min_duration_ms=7_000,
        max_duration_ms=16_000,
        transition_weights={
            "idle": 5,
            "curious": 1,
            "smug": 1,
            "sneaky": 2,
            "celebrating": 1,
        },
    ),
    "busy": PersonalityDefinition(
        key="busy",
        label="Busy",
        description="Moving like there are tickets to close and at least one of them is cursed.",
        movement_style="pace",
        quote_contexts=("personality-busy", "busy"),
        preferred_categories=("office", "responsible"),
        animation_profile={"delay_scale": 0.82, "offset_y": 0, "bob_px": 1, "jitter_px": 0},
        sound_effect="state_busy",
        min_duration_ms=10_000,
        max_duration_ms=22_000,
        transition_weights={
            "idle": 3,
            "busy": 2,
            "annoyed": 3,
            "exhausted": 2,
            "celebrating": 1,
        },
    ),
    "annoyed": PersonalityDefinition(
        key="annoyed",
        label="Annoyed",
        description="One authentication prompt away from a tiny desktop incident.",
        movement_style="agitated",
        quote_contexts=("personality-annoyed", "annoyed"),
        preferred_categories=("office", "responsible", "what-do"),
        animation_profile={"delay_scale": 0.8, "offset_y": 1, "bob_px": 1, "jitter_px": 1},
        sound_effect="state_annoyed",
        min_duration_ms=7_000,
        max_duration_ms=14_000,
        transition_weights={
            "idle": 3,
            "busy": 3,
            "annoyed": 1,
            "confused": 1,
            "exhausted": 2,
        },
    ),
    "celebrating": PersonalityDefinition(
        key="celebrating",
        label="Celebrating",
        description="Operating on the firm belief that every tiny win deserves a whole desktop bit.",
        movement_style="victory",
        quote_contexts=("personality-celebrating", "celebrating", "victory"),
        preferred_categories=("network", "celebrating"),
        animation_profile={"delay_scale": 0.72, "offset_y": -1, "bob_px": 3, "jitter_px": 0},
        sound_effect="state_celebrating",
        min_duration_ms=6_000,
        max_duration_ms=12_000,
        transition_weights={
            "idle": 3,
            "smug": 4,
            "celebrating": 1,
            "busy": 1,
        },
    ),
    "confused": PersonalityDefinition(
        key="confused",
        label="Confused",
        description="There is clearly some kind of thing happening here and it is not appreciated.",
        movement_style="hesitate",
        quote_contexts=("personality-confused", "confused", "what-do"),
        preferred_categories=("what-do", "office"),
        animation_profile={"delay_scale": 1.08, "offset_y": 1, "bob_px": 0, "jitter_px": 1},
        sound_effect="state_confused",
        min_duration_ms=7_000,
        max_duration_ms=15_000,
        transition_weights={
            "idle": 4,
            "curious": 3,
            "annoyed": 2,
            "confused": 1,
            "busy": 1,
        },
    ),
    "sneaky": PersonalityDefinition(
        key="sneaky",
        label="Sneaky",
        description="Acting like the desktop edges are made of shadows and plausible deniability.",
        movement_style="sneak",
        quote_contexts=("personality-sneaky", "sneaky"),
        preferred_categories=("office", "playful"),
        animation_profile={"delay_scale": 0.98, "offset_y": 2, "bob_px": 0, "jitter_px": 0},
        sound_effect="state_sneaky",
        min_duration_ms=8_000,
        max_duration_ms=18_000,
        transition_weights={
            "idle": 4,
            "curious": 2,
            "smug": 2,
            "sneaky": 1,
            "celebrating": 1,
        },
    ),
    "exhausted": PersonalityDefinition(
        key="exhausted",
        label="Exhausted",
        description="Still on duty, but spiritually in a rolling office chair somewhere.",
        movement_style="slump",
        quote_contexts=("personality-exhausted", "exhausted"),
        preferred_categories=("responsible",),
        animation_profile={"delay_scale": 1.28, "offset_y": 3, "bob_px": 0, "jitter_px": 0},
        sound_effect="state_exhausted",
        min_duration_ms=12_000,
        max_duration_ms=26_000,
        transition_weights={
            "idle": 4,
            "busy": 2,
            "curious": 1,
            "exhausted": 2,
        },
    ),
}


DEFAULT_STATE = "idle"


class PersonalityController:
    def __init__(self, logger=None, clock=None):
        self.logger = logger
        self.clock = clock or time.monotonic
        self.current = DEFAULT_STATE
        self.state_until_ms = 0
        self.locked_until_ms = 0
        self._last_reason = "startup"
        self._last_transition_ms = self._now_ms()
        self._seed_state_duration(self.definition())

    def available_states(self):
        return list(PERSONALITY_STATES.values())

    def load(self, state_key=None):
        sanitized = self._sanitize_state(state_key)
        self.current = sanitized
        self._last_reason = "load"
        self._last_transition_ms = self._now_ms()
        self._seed_state_duration(self.definition())

    def definition(self, state_key=None):
        return PERSONALITY_STATES[self._sanitize_state(state_key or self.current)]

    def current_state(self):
        return self.current

    def snapshot(self):
        definition = self.definition()
        return {
            "key": definition.key,
            "label": definition.label,
            "description": definition.description,
            "movement_style": definition.movement_style,
            "quote_contexts": list(definition.quote_contexts),
            "preferred_categories": list(definition.preferred_categories),
            "locked": self._now_ms() < self.locked_until_ms,
            "time_remaining_ms": max(0, int(self.state_until_ms - self._now_ms())),
        }

    def animation_profile(self):
        return dict(self.definition().animation_profile)

    def movement_style(self):
        return str(self.definition().movement_style)

    def quote_contexts(self):
        return list(self.definition().quote_contexts)

    def preferred_categories(self):
        return list(self.definition().preferred_categories)

    def transition_to(self, state_key, reason="manual", duration_ms=None, lock_ms=0):
        target = self._sanitize_state(state_key)
        if target == self.current and duration_ms is None and int(lock_ms or 0) <= 0:
            return False
        previous = self.current
        self.current = target
        self._last_reason = str(reason or "manual")
        self._last_transition_ms = self._now_ms()
        definition = self.definition(target)
        if duration_ms is None:
            self._seed_state_duration(definition)
        else:
            self.state_until_ms = self._now_ms() + max(1, int(duration_ms))
        if int(lock_ms or 0) > 0:
            self.locked_until_ms = self._now_ms() + int(lock_ms)
        self._log("info", f"personality: {previous} -> {target} ({self._last_reason})")
        return True

    def tick(self, context=None, rng=None):
        rng = rng or random
        now_ms = self._now_ms()
        if now_ms < self.locked_until_ms or now_ms < self.state_until_ms:
            return None
        next_state = self._pick_next_state(context or {}, rng)
        if next_state == self.current:
            self._seed_state_duration(self.definition())
            return None
        self.transition_to(next_state, reason="natural")
        return self.current

    def _pick_next_state(self, context, rng):
        current = self.definition()
        weighted = []
        active_toy = str(context.get("active_toy", "")).strip()
        current_mood = str(context.get("mood", "happy")).strip()
        seasonal_contexts = {str(item).strip() for item in context.get("seasonal_contexts", []) if str(item).strip()}
        recent_scenarios = list(context.get("recent_scenarios", []))
        chaos_mode = bool(context.get("chaos_mode"))
        active_scenario = str(context.get("active_scenario", "")).strip()

        for state_key, weight in current.transition_weights.items():
            adjusted = max(1, int(weight))
            if chaos_mode and state_key in {"sneaky", "celebrating", "confused"}:
                adjusted += 2
            if active_toy and state_key in {"busy", "curious", "smug"}:
                adjusted += 1
            if current_mood == "tired" and state_key == "exhausted":
                adjusted += 3
            if current_mood == "caffeinated" and state_key in {"busy", "celebrating", "annoyed"}:
                adjusted += 2
            if "monday-morning" in seasonal_contexts and state_key in {"busy", "annoyed", "exhausted"}:
                adjusted += 2
            if "patch-day" in seasonal_contexts and state_key in {"busy", "confused", "annoyed"}:
                adjusted += 2
            if recent_scenarios and state_key == "busy" and any("office" in item for item in recent_scenarios[-2:]):
                adjusted += 1
            if active_scenario and state_key == "celebrating" and "victory" in active_scenario:
                adjusted += 2
            weighted.append((state_key, adjusted))

        total = sum(weight for _state_key, weight in weighted)
        if total <= 0:
            return DEFAULT_STATE
        pick = rng.uniform(0, total)
        current_total = 0.0
        for state_key, weight in weighted:
            current_total += weight
            if pick <= current_total:
                return state_key
        return weighted[-1][0]

    def _seed_state_duration(self, definition):
        self.state_until_ms = self._now_ms() + random.randint(
            int(definition.min_duration_ms),
            int(definition.max_duration_ms),
        )

    @staticmethod
    def _sanitize_state(state_key):
        candidate = str(state_key or DEFAULT_STATE).strip().lower()
        if candidate in PERSONALITY_STATES:
            return candidate
        return DEFAULT_STATE

    def _now_ms(self):
        return int(self.clock() * 1000)

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message)
