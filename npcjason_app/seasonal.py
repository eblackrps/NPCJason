from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SeasonalMode:
    key: str
    label: str
    description: str
    activation_rule: str
    contexts: tuple[str, ...]
    preferred_scenarios: tuple[str, ...] = ()
    preferred_quote_packs: tuple[str, ...] = ()
    preferred_states: tuple[str, ...] = ()
    preferred_skin_tags: tuple[str, ...] = ()


SEASONAL_MODES = {
    "april-fools": SeasonalMode(
        key="april-fools",
        label="April Fools Mode",
        description="More smugness, more chaos, and at least one desktop bit too many.",
        activation_rule="april-fools",
        contexts=("april-fools", "chaos", "desktop-menace"),
        preferred_scenarios=("office-chaos",),
        preferred_quote_packs=("what-do",),
        preferred_states=("sneaky", "smug", "celebrating"),
        preferred_skin_tags=("office", "playful"),
    ),
    "halloween": SeasonalMode(
        key="halloween",
        label="Halloween Mode",
        description="Slightly haunted office energy.",
        activation_rule="halloween-window",
        contexts=("halloween", "spooky", "desktop-haunting"),
        preferred_scenarios=("office-chaos",),
        preferred_states=("sneaky", "confused"),
        preferred_skin_tags=("wizard", "knight"),
    ),
    "winter-holiday": SeasonalMode(
        key="winter-holiday",
        label="Winter Holiday Mode",
        description="A festive but still mildly unhinged desktop shift.",
        activation_rule="winter-window",
        contexts=("winter", "holiday", "cozy"),
        preferred_scenarios=("responsible-adult-moment",),
        preferred_states=("idle", "smug"),
        preferred_skin_tags=("responsible", "astronaut"),
    ),
    "patch-day-panic": SeasonalMode(
        key="patch-day-panic",
        label="Patch Day Panic",
        description="The specific posture of pretending patching is going fine.",
        activation_rule="patch-day",
        contexts=("patch-day", "panic", "busy"),
        preferred_scenarios=("busy-it-morning", "office-chaos"),
        preferred_quote_packs=("jason-quotes",),
        preferred_states=("busy", "annoyed", "confused"),
        preferred_skin_tags=("office", "responsible"),
    ),
    "homelab-weekend": SeasonalMode(
        key="homelab-weekend",
        label="Homelab Weekend",
        description="Weekend behavior where one tiny change becomes a whole project.",
        activation_rule="weekend",
        contexts=("homelab-weekend", "weekend", "lab-hours"),
        preferred_scenarios=("homelab-troubleshooting",),
        preferred_quote_packs=("jason-quotes", "what-do"),
        preferred_states=("curious", "busy"),
        preferred_skin_tags=("homelab", "network"),
    ),
    "monday-morning-survival": SeasonalMode(
        key="monday-morning-survival",
        label="Monday Morning Survival",
        description="Boot sequence incomplete but technically online.",
        activation_rule="monday-morning",
        contexts=("monday-morning", "survival", "office"),
        preferred_scenarios=("busy-it-morning", "office-chaos"),
        preferred_quote_packs=("jason-quotes",),
        preferred_states=("busy", "annoyed", "exhausted"),
        preferred_skin_tags=("office", "responsible"),
    ),
}


class SeasonalModeManager:
    def __init__(self, override="auto", logger=None):
        self.logger = logger
        self.override = str(override or "auto").strip() or "auto"
        self.definitions = dict(SEASONAL_MODES)

    def set_override(self, override):
        value = str(override or "auto").strip() or "auto"
        if value in {"auto", "off"} or value in self.definitions:
            self.override = value
            return True
        return False

    def available_modes(self):
        items = [
            {"key": "auto", "label": "Auto", "description": "Use date-based special modes."},
            {"key": "off", "label": "Off", "description": "Disable seasonal and special-event content."},
        ]
        items.extend(
            {
                "key": definition.key,
                "label": definition.label,
                "description": definition.description,
            }
            for definition in sorted(self.definitions.values(), key=lambda value: value.label.lower())
        )
        return items

    def active_modes(self, now=None):
        now = now or datetime.now()
        if self.override == "off":
            return []
        if self.override != "auto" and self.override in self.definitions:
            return [self.definitions[self.override]]
        return [
            definition
            for definition in self.definitions.values()
            if self._is_active(definition.activation_rule, now)
        ]

    def primary_mode(self, now=None):
        active = self.active_modes(now=now)
        if not active:
            return None
        return active[0]

    def context(self, now=None):
        active = self.active_modes(now=now)
        contexts = []
        preferred_scenarios = []
        preferred_quote_packs = []
        preferred_states = []
        preferred_skin_tags = []
        for definition in active:
            contexts.extend(item for item in definition.contexts if item not in contexts)
            preferred_scenarios.extend(item for item in definition.preferred_scenarios if item not in preferred_scenarios)
            preferred_quote_packs.extend(
                item for item in definition.preferred_quote_packs if item not in preferred_quote_packs
            )
            preferred_states.extend(item for item in definition.preferred_states if item not in preferred_states)
            preferred_skin_tags.extend(item for item in definition.preferred_skin_tags if item not in preferred_skin_tags)
        return {
            "override": self.override,
            "active_keys": [definition.key for definition in active],
            "contexts": contexts,
            "preferred_scenarios": preferred_scenarios,
            "preferred_quote_packs": preferred_quote_packs,
            "preferred_states": preferred_states,
            "preferred_skin_tags": preferred_skin_tags,
        }

    @staticmethod
    def _is_active(rule, now):
        month = int(now.month)
        day = int(now.day)
        weekday = int(now.weekday())
        hour = int(now.hour)
        if rule == "april-fools":
            return month == 4 and day == 1
        if rule == "halloween-window":
            return (month == 10 and day >= 24) or (month == 11 and day <= 2)
        if rule == "winter-window":
            return month == 12 or (month == 1 and day <= 5)
        if rule == "weekend":
            return weekday >= 5
        if rule == "monday-morning":
            return weekday == 0 and hour < 12
        if rule == "patch-day":
            return weekday == 1 and 8 <= day <= 14
        return False
