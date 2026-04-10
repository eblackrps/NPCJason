from __future__ import annotations

from dataclasses import dataclass, field
import random
import time


@dataclass(frozen=True)
class ChainStep:
    action: str
    value: str = ""
    delay_ms: int = 0
    payload: dict = field(default_factory=dict)
    allow_skip: bool = True


@dataclass(frozen=True)
class ScenarioDefinition:
    key: str
    label: str
    description: str
    weight: int
    cooldown_ms: int
    tags: tuple[str, ...]
    preferred_skin_tags: tuple[str, ...] = ()
    preferred_states: tuple[str, ...] = ()
    preferred_quote_categories: tuple[str, ...] = ()
    preferred_quote_packs: tuple[str, ...] = ()
    seasonal_modes: tuple[str, ...] = ()
    required_unlock: str | None = None
    steps: tuple[ChainStep, ...] = ()


@dataclass
class ScenarioRuntime:
    definition: ScenarioDefinition
    step_index: int
    next_step_at_ms: int
    started_at_ms: int


@dataclass(frozen=True)
class ScenarioTickResult:
    command: ChainStep | None = None
    completed_scenario: str | None = None


SCENARIO_DEFINITIONS = {
    "busy-it-morning": ScenarioDefinition(
        key="busy-it-morning",
        label="Busy IT Morning",
        description="Ticket energy, hallway pacing, and a stress ball that knows too much.",
        weight=3,
        cooldown_ms=11 * 60 * 1000,
        tags=("office", "responsible", "busy"),
        preferred_skin_tags=("office", "responsible"),
        preferred_states=("busy", "annoyed"),
        preferred_quote_categories=("office", "responsible"),
        steps=(
            ChainStep("set_state", "busy", payload={"duration_ms": 7_000, "lock_ms": 2_600}),
            ChainStep("desk_item", "keyboard", delay_ms=250, payload={"show_saying": False, "categories": ["office", "helpdesk"]}),
            ChainStep("movement", "pace", delay_ms=400, payload={"duration_ms": 2_400}),
            ChainStep("toy", "stress-ball", delay_ms=500, payload={"show_saying": False}),
            ChainStep(
                "quote",
                delay_ms=1_000,
                payload={"contexts": ["scenario", "busy-it-morning"], "categories": ["office", "responsible"]},
            ),
            ChainStep("pause", delay_ms=750),
            ChainStep("set_state", "idle"),
        ),
    ),
    "homelab-troubleshooting": ScenarioDefinition(
        key="homelab-troubleshooting",
        label="Homelab Troubleshooting",
        description="Something in the rack is spiritually blinking at him again.",
        weight=3,
        cooldown_ms=13 * 60 * 1000,
        tags=("homelab", "debug", "what-do"),
        preferred_skin_tags=("homelab", "network"),
        preferred_states=("curious", "confused"),
        preferred_quote_categories=("homelab", "what-do"),
        preferred_quote_packs=("what-do",),
        seasonal_modes=("homelab-weekend",),
        steps=(
            ChainStep("set_state", "curious", payload={"duration_ms": 6_500, "lock_ms": 2_000}),
            ChainStep("desk_item", "tiny-network-rack", delay_ms=220, payload={"show_saying": False, "categories": ["network", "homelab"]}),
            ChainStep("movement", "inspect", delay_ms=400, payload={"duration_ms": 2_000, "focus": "right-edge"}),
            ChainStep("toy", "homelab-cart", delay_ms=450, payload={"show_saying": False}),
            ChainStep("set_state", "confused", delay_ms=300, payload={"duration_ms": 4_200}),
            ChainStep(
                "quote",
                delay_ms=1_000,
                payload={"contexts": ["scenario", "homelab-troubleshooting", "what-do"], "categories": ["homelab", "what-do"]},
            ),
            ChainStep("pause", delay_ms=900),
            ChainStep("set_state", "smug", payload={"duration_ms": 4_200}),
        ),
    ),
    "network-victory-lap": ScenarioDefinition(
        key="network-victory-lap",
        label="Network Victory Lap",
        description="Something routed correctly, which means the desktop deserves a parade.",
        weight=3,
        cooldown_ms=14 * 60 * 1000,
        tags=("network", "celebration", "playful"),
        preferred_skin_tags=("network",),
        preferred_states=("celebrating", "smug"),
        preferred_quote_categories=("network",),
        steps=(
            ChainStep("set_state", "celebrating", payload={"duration_ms": 6_000, "lock_ms": 2_200}),
            ChainStep("movement", "victory", delay_ms=350, payload={"duration_ms": 1_600}),
            ChainStep("toy", "tricycle", delay_ms=600, payload={"show_saying": False}),
            ChainStep(
                "quote",
                delay_ms=1_200,
                payload={"contexts": ["scenario", "network-victory-lap", "victory"], "categories": ["network"]},
            ),
            ChainStep("set_state", "smug", payload={"duration_ms": 5_200}),
        ),
    ),
    "responsible-adult-moment": ScenarioDefinition(
        key="responsible-adult-moment",
        label="Responsible Adult Moment",
        description="A brief and unsettling period of competence.",
        weight=2,
        cooldown_ms=12 * 60 * 1000,
        tags=("responsible", "office"),
        preferred_skin_tags=("responsible", "office"),
        preferred_states=("busy", "exhausted"),
        preferred_quote_categories=("responsible", "office"),
        steps=(
            ChainStep("set_state", "busy", payload={"duration_ms": 6_000, "lock_ms": 1_800}),
            ChainStep("desk_item", "coffee-mug", delay_ms=250, payload={"show_saying": False, "categories": ["office", "responsible"]}),
            ChainStep("toy", "stress-ball", delay_ms=400, payload={"show_saying": False}),
            ChainStep(
                "quote",
                delay_ms=900,
                payload={"contexts": ["scenario", "responsible-adult-moment"], "categories": ["responsible", "office"]},
            ),
            ChainStep("set_state", "exhausted", delay_ms=500, payload={"duration_ms": 7_200}),
            ChainStep("pause", delay_ms=950),
            ChainStep("set_state", "idle"),
        ),
    ),
    "office-chaos": ScenarioDefinition(
        key="office-chaos",
        label="Office Chaos",
        description="Pacing, muttering, one dramatic pause, and a general sense that the tickets are haunted.",
        weight=4,
        cooldown_ms=15 * 60 * 1000,
        tags=("office", "chaos", "playful"),
        preferred_skin_tags=("office", "responsible"),
        preferred_states=("annoyed", "busy", "sneaky"),
        preferred_quote_categories=("office", "what-do"),
        preferred_quote_packs=("what-do",),
        seasonal_modes=("april-fools", "monday-morning-survival", "patch-day-panic"),
        steps=(
            ChainStep("set_state", "annoyed", payload={"duration_ms": 5_000, "lock_ms": 2_000}),
            ChainStep("movement", "agitated", delay_ms=450, payload={"duration_ms": 2_000}),
            ChainStep(
                "quote",
                delay_ms=1_000,
                payload={"contexts": ["scenario", "office-chaos"], "categories": ["office"]},
            ),
            ChainStep("pause", delay_ms=1_250),
            ChainStep("set_state", "sneaky", payload={"duration_ms": 4_800}),
            ChainStep("movement", "sneak", delay_ms=320, payload={"duration_ms": 1_900, "focus": "left-edge"}),
            ChainStep("toy", "rubber-duck", delay_ms=500, payload={"show_saying": False}),
            ChainStep(
                "quote",
                delay_ms=900,
                payload={"contexts": ["scenario", "office-chaos", "what-do"], "categories": ["office", "what-do"]},
            ),
            ChainStep("set_state", "idle"),
        ),
    ),
    "orbital-desk-patrol": ScenarioDefinition(
        key="orbital-desk-patrol",
        label="Orbital Desk Patrol",
        description="A bonus zero-gravity-adjacent patrol unlocked after enough gremlin activity.",
        weight=2,
        cooldown_ms=16 * 60 * 1000,
        tags=("astronaut", "unlockable", "playful"),
        preferred_skin_tags=("astronaut", "network"),
        preferred_states=("curious", "celebrating"),
        preferred_quote_categories=("network", "homelab"),
        required_unlock="orbital-desk-patrol",
        steps=(
            ChainStep("set_state", "celebrating", payload={"duration_ms": 5_800, "lock_ms": 2_000}),
            ChainStep("movement", "inspect", delay_ms=350, payload={"duration_ms": 1_800, "focus": "top-right"}),
            ChainStep(
                "quote",
                delay_ms=950,
                payload={"contexts": ["scenario", "orbital-desk-patrol", "orbital"], "categories": ["network", "homelab"]},
            ),
            ChainStep("set_state", "sneaky", delay_ms=420, payload={"duration_ms": 4_800}),
            ChainStep("movement", "sneak", delay_ms=350, payload={"duration_ms": 1_500, "focus": "top-left"}),
            ChainStep("set_state", "smug", payload={"duration_ms": 4_400}),
        ),
    ),
}


class ScenarioManager:
    def __init__(self, logger=None, clock=None):
        self.logger = logger
        self.clock = clock or time.monotonic
        self.definitions = dict(SCENARIO_DEFINITIONS)
        self._cooldowns = {}
        self._recent_history = []
        self._active = None

    def load_recent(self, recent_scenarios=None):
        self._recent_history = [
            str(item).strip()
            for item in list(recent_scenarios or [])[-12:]
            if str(item).strip()
        ]

    def recent_history(self):
        return list(self._recent_history)

    def available_scenarios(self, unlock_manager=None, favorites=None):
        favorites = set(str(item).strip() for item in list(favorites or []) if str(item).strip())
        items = []
        for definition in sorted(self.definitions.values(), key=lambda value: value.label.lower()):
            items.append(
                {
                    "key": definition.key,
                    "label": definition.label,
                    "description": definition.description,
                    "cooldown_ms": self.remaining_cooldown_ms(definition.key),
                    "active": bool(self._active and self._active.definition.key == definition.key),
                    "favorite": definition.key in favorites,
                    "unlocked": self._unlocked(definition, unlock_manager),
                    "tags": list(definition.tags),
                }
            )
        return items

    def active_scenario_key(self):
        if not self._active:
            return ""
        return self._active.definition.key

    def definition(self, scenario_key):
        return self.definitions.get(str(scenario_key or "").strip())

    def can_start(self, scenario_key, unlock_manager=None):
        definition = self.definitions.get(str(scenario_key or "").strip())
        if definition is None or self._active is not None:
            return False
        if self.remaining_cooldown_ms(definition.key) > 0:
            return False
        return self._unlocked(definition, unlock_manager)

    def start(self, scenario_key, unlock_manager=None):
        definition = self.definitions.get(str(scenario_key or "").strip())
        if definition is None:
            return False
        if not self.can_start(definition.key, unlock_manager=unlock_manager):
            return False
        now_ms = self._now_ms()
        self._active = ScenarioRuntime(
            definition=definition,
            step_index=0,
            next_step_at_ms=now_ms,
            started_at_ms=now_ms,
        )
        self._log("info", f"scenario: started {definition.key}")
        return True

    def tick(self):
        if self._active is None:
            return ScenarioTickResult()
        now_ms = self._now_ms()
        if now_ms < self._active.next_step_at_ms:
            return ScenarioTickResult()

        definition = self._active.definition
        while self._active and self._active.step_index < len(definition.steps):
            step = definition.steps[self._active.step_index]
            self._active.step_index += 1
            self._active.next_step_at_ms = now_ms + max(0, int(step.delay_ms))
            if step.action == "pause":
                continue
            return ScenarioTickResult(command=step)

        completed = definition.key
        self._cooldowns[definition.key] = now_ms + int(definition.cooldown_ms)
        self._recent_history.append(definition.key)
        self._recent_history = self._recent_history[-12:]
        self._active = None
        self._log("info", f"scenario: completed {completed}")
        return ScenarioTickResult(completed_scenario=completed)

    def remaining_cooldown_ms(self, scenario_key):
        return max(0, int(self._cooldowns.get(str(scenario_key or ""), 0) - self._now_ms()))

    def pick_scenario(self, context=None, unlock_manager=None, rng=None):
        context = context or {}
        rng = rng or random
        favorites = {str(item).strip() for item in context.get("favorite_scenarios", []) if str(item).strip()}
        skin_tags = {str(item).strip() for item in context.get("skin_tags", []) if str(item).strip()}
        seasonal_modes = {str(item).strip() for item in context.get("seasonal_modes", []) if str(item).strip()}
        preferred_categories = {
            str(item).strip() for item in context.get("preferred_categories", []) if str(item).strip()
        }
        personality_state = str(context.get("personality_state", "")).strip()
        chaos_mode = bool(context.get("chaos_mode"))

        weighted = []
        for definition in self.definitions.values():
            if not self._unlocked(definition, unlock_manager):
                continue
            if self.remaining_cooldown_ms(definition.key) > 0:
                continue
            if definition.key in self._recent_history[-2:]:
                continue
            weight = max(1, int(definition.weight))
            if definition.key in favorites:
                weight += 4
            if skin_tags & set(definition.preferred_skin_tags):
                weight += 3
            if personality_state and personality_state in definition.preferred_states:
                weight += 2
            if preferred_categories & set(definition.preferred_quote_categories):
                weight += 2
            if seasonal_modes & set(definition.seasonal_modes):
                weight += 4
            if chaos_mode and {"chaos", "playful"} & set(definition.tags):
                weight += 2
            weighted.append((definition, weight))

        if not weighted:
            return None
        total = sum(weight for _definition, weight in weighted)
        pick = rng.uniform(0, total)
        current = 0.0
        for definition, weight in weighted:
            current += weight
            if pick <= current:
                return definition
        return weighted[-1][0]

    @staticmethod
    def _unlocked(definition, unlock_manager):
        if unlock_manager is None:
            return True
        return unlock_manager.is_unlocked("scenario", definition.required_unlock or definition.key)

    def _now_ms(self):
        return int(self.clock() * 1000)

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message)
