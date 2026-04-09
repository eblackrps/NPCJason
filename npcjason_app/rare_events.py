from __future__ import annotations

from dataclasses import dataclass
import random
import time


@dataclass(frozen=True)
class RareEventDefinition:
    key: str
    label: str
    description: str
    weight: int
    cooldown_ms: int
    toy_key: str | None
    contexts: tuple[str, ...]
    preferred_skin_tags: tuple[str, ...] = ()
    preferred_categories: tuple[str, ...] = ()


RARE_EVENT_DEFINITIONS = {
    "tricycle-lap": RareEventDefinition(
        key="tricycle-lap",
        label="Tricycle Lap",
        description="Jason does a tiny tricycle lap with a wobble and a pause.",
        weight=2,
        cooldown_ms=12 * 60 * 1000,
        toy_key="tricycle",
        contexts=("rare-event", "rideby", "playful"),
        preferred_skin_tags=("office", "network", "playful"),
        preferred_categories=("office", "network"),
    ),
    "duck-debug": RareEventDefinition(
        key="duck-debug",
        label="Duck Debug Visit",
        description="A rubber duck appears for a suspiciously helpful debugging check-in.",
        weight=2,
        cooldown_ms=10 * 60 * 1000,
        toy_key="rubber-duck",
        contexts=("rare-event", "duck", "debug"),
        preferred_skin_tags=("office", "responsible", "network"),
        preferred_categories=("office", "responsible"),
    ),
    "homelab-delivery": RareEventDefinition(
        key="homelab-delivery",
        label="Homelab Delivery",
        description="The tiny server cart rolls in like something probably needs racking.",
        weight=3,
        cooldown_ms=14 * 60 * 1000,
        toy_key="homelab-cart",
        contexts=("rare-event", "homelab", "gear"),
        preferred_skin_tags=("homelab", "network"),
        preferred_categories=("homelab", "network"),
    ),
    "stress-reset": RareEventDefinition(
        key="stress-reset",
        label="Stress Reset",
        description="A little bounce break when Responsible Jason energy starts to creep in.",
        weight=2,
        cooldown_ms=8 * 60 * 1000,
        toy_key="stress-ball",
        contexts=("rare-event", "reset", "responsible"),
        preferred_skin_tags=("responsible", "office"),
        preferred_categories=("responsible", "office"),
    ),
}


class RareEventManager:
    def __init__(self, logger=None, clock=None):
        self.logger = logger
        self.clock = clock or time.monotonic
        self.definitions = dict(RARE_EVENT_DEFINITIONS)
        self._cooldowns = {}

    def available_events(self):
        now_ms = self._now_ms()
        events = []
        for event in sorted(self.definitions.values(), key=lambda value: value.label.lower()):
            events.append(
                {
                    "key": event.key,
                    "label": event.label,
                    "description": event.description,
                    "cooldown_ms": max(0, int(self._cooldowns.get(event.key, 0) - now_ms)),
                    "toy_key": event.toy_key,
                    "contexts": list(event.contexts),
                }
            )
        return events

    def remaining_cooldown_ms(self, event_key):
        return max(0, int(self._cooldowns.get(event_key, 0) - self._now_ms()))

    def pick_event(self, context=None, rng=None):
        context = context or {}
        rng = rng or random
        weighted = []
        skin_tags = set(str(tag).strip() for tag in context.get("skin_tags", []) if str(tag).strip())
        preferred_categories = set(
            str(category).strip() for category in context.get("preferred_categories", []) if str(category).strip()
        )
        chaos_mode = bool(context.get("chaos_mode"))

        for event in self.definitions.values():
            if self.remaining_cooldown_ms(event.key) > 0:
                continue
            weight = max(1, int(event.weight))
            if skin_tags & set(event.preferred_skin_tags):
                weight += 3
            if preferred_categories & set(event.preferred_categories):
                weight += 2
            if chaos_mode and "playful" in event.contexts:
                weight += 2
            weighted.append((event, weight))

        if not weighted:
            return None

        total = sum(weight for _event, weight in weighted)
        pick = rng.uniform(0, total)
        current = 0.0
        for event, weight in weighted:
            current += weight
            if pick <= current:
                return event
        return weighted[-1][0]

    def mark_triggered(self, event_key):
        event = self.definitions.get(event_key)
        if event is None:
            return False
        self._cooldowns[event_key] = self._now_ms() + int(event.cooldown_ms)
        return True

    def _now_ms(self):
        return int(self.clock() * 1000)
