from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DiscoveryDefinition:
    key: str
    item_type: str
    label: str
    description: str
    conditions: dict[str, int]
    default_unlocked: bool = False


DISCOVERY_DEFINITIONS = {
    "astronaut": DiscoveryDefinition(
        key="astronaut",
        item_type="skin",
        label="Astronaut Jason",
        description="Orbital-ready desktop duty.",
        conditions={},
        default_unlocked=True,
    ),
    "what-do": DiscoveryDefinition(
        key="what-do",
        item_type="quote_pack",
        label="What Do Pack",
        description="Confused little menace lines unlocked after enough baffled desktop staring.",
        conditions={"curious_beats": 2, "confused_beats": 1},
    ),
    "orbital-desk-patrol": DiscoveryDefinition(
        key="orbital-desk-patrol",
        item_type="scenario",
        label="Orbital Desk Patrol",
        description="A bonus scenario unlocked after enough toy-fueled nonsense.",
        conditions={"toy_uses": 4, "scenario_runs": 2},
    ),
}


PLURAL_ITEM_TYPES = {
    "skin": "skins",
    "toy": "toys",
    "scenario": "scenarios",
    "quote_pack": "quote_packs",
}


class UnlockManager:
    def __init__(self, logger=None):
        self.logger = logger
        self.enabled = True
        self._unlocked = {plural: set() for plural in PLURAL_ITEM_TYPES.values()}
        self._stats = {}
        self._pending = []

    def load(
        self,
        enabled=True,
        unlocked_skins=None,
        unlocked_toys=None,
        unlocked_scenarios=None,
        unlocked_quote_packs=None,
        discovery_stats=None,
    ):
        self.enabled = bool(enabled)
        self._unlocked = {
            "skins": {str(item).strip() for item in list(unlocked_skins or []) if str(item).strip()},
            "toys": {str(item).strip() for item in list(unlocked_toys or []) if str(item).strip()},
            "scenarios": {str(item).strip() for item in list(unlocked_scenarios or []) if str(item).strip()},
            "quote_packs": {
                str(item).strip()
                for item in list(unlocked_quote_packs or [])
                if str(item).strip()
            },
        }
        self._stats = {
            str(key).strip(): max(0, int(value))
            for key, value in dict(discovery_stats or {}).items()
            if str(key).strip()
        }
        self._pending = []
        for definition in DISCOVERY_DEFINITIONS.values():
            if definition.default_unlocked:
                self._unlocked[PLURAL_ITEM_TYPES[definition.item_type]].add(definition.key)
        self._refresh_unlocks(notify=False)

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)

    def is_unlocked(self, item_type, item_key):
        key = str(item_key or "").strip()
        if not key:
            return False
        if not self.enabled:
            return True
        item_type = str(item_type or "").strip()
        plural = PLURAL_ITEM_TYPES.get(item_type, item_type)
        if plural not in self._unlocked:
            return True
        if key in self._unlocked[plural]:
            return True
        definition = DISCOVERY_DEFINITIONS.get(key)
        if definition is None:
            return True
        if definition.item_type != item_type:
            return True
        return bool(definition.default_unlocked)

    def note_progress(self, counter_key, amount=1):
        counter_key = str(counter_key or "").strip()
        if not counter_key:
            return []
        self._stats[counter_key] = max(0, int(self._stats.get(counter_key, 0)) + int(amount))
        return self._refresh_unlocks(notify=self.enabled)

    def stats(self):
        return dict(self._stats)

    def pending_discoveries(self):
        pending = list(self._pending)
        self._pending.clear()
        return pending

    def restore_pending(self, discoveries):
        restored = [
            discovery
            for discovery in list(discoveries or [])
            if isinstance(discovery, DiscoveryDefinition)
        ]
        if not restored:
            return
        restored.extend(item for item in self._pending if item not in restored)
        self._pending = restored

    def unlocked_snapshot(self):
        return {
            "skins": sorted(self._unlocked["skins"]),
            "toys": sorted(self._unlocked["toys"]),
            "scenarios": sorted(self._unlocked["scenarios"]),
            "quote_packs": sorted(self._unlocked["quote_packs"]),
        }

    def discovery_catalog(self):
        items = []
        for definition in sorted(DISCOVERY_DEFINITIONS.values(), key=lambda value: value.label.lower()):
            items.append(
                {
                    "key": definition.key,
                    "label": definition.label,
                    "description": definition.description,
                    "item_type": definition.item_type,
                    "unlocked": self.is_unlocked(definition.item_type, definition.key),
                    "default_unlocked": bool(definition.default_unlocked),
                    "progress": self._progress(definition),
                    "progress_text": self._progress_text(definition),
                }
            )
        return items

    def _refresh_unlocks(self, notify):
        unlocked_now = []
        for definition in DISCOVERY_DEFINITIONS.values():
            plural = PLURAL_ITEM_TYPES[definition.item_type]
            if definition.key in self._unlocked[plural]:
                continue
            if definition.default_unlocked or self._conditions_met(definition.conditions):
                self._unlocked[plural].add(definition.key)
                unlocked_now.append(definition)
                self._stats["discoveries"] = max(0, int(self._stats.get("discoveries", 0)) + 1)
        if notify:
            self._pending.extend(unlocked_now)
        return unlocked_now

    def _conditions_met(self, conditions):
        for key, value in dict(conditions or {}).items():
            if int(self._stats.get(str(key).strip(), 0)) < int(value):
                return False
        return True

    def _progress(self, definition):
        progress = []
        for key, required in dict(definition.conditions or {}).items():
            counter_key = str(key).strip()
            progress.append(
                {
                    "key": counter_key,
                    "current": max(0, int(self._stats.get(counter_key, 0))),
                    "required": max(0, int(required)),
                }
            )
        return progress

    def _progress_text(self, definition):
        progress = self._progress(definition)
        if not progress:
            return "Ready"
        return ", ".join(
            f"{item['key']} {min(item['current'], item['required'])}/{item['required']}"
            for item in progress
        )
