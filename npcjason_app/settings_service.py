from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import random
import tempfile
import time
from typing import Dict, List, Optional

from .data.defaults import MOODS, default_settings
from .persistence import sanitize_settings_payload


def json_dumps_pretty(data):
    return json.dumps(data, indent=2, ensure_ascii=False)


def json_load_file(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


@dataclass
class InstanceSettings:
    x: Optional[int] = None
    y: Optional[int] = None
    skin: str = "jason"
    mood: str = "happy"
    name: str = "Jason"
    personality_state: str = "idle"
    last_scenario: str = ""


@dataclass
class GlobalSettings:
    sound_enabled: bool = True
    sound_volume: int = 70
    sound_categories: Dict[str, bool] = field(default_factory=dict)
    auto_update_enabled: bool = True
    event_reactions_enabled: bool = True
    quiet_hours_enabled: bool = False
    quiet_start_hour: int = 22
    quiet_end_hour: int = 8
    quiet_when_fullscreen: bool = True
    auto_antics_enabled: bool = True
    auto_antics_min_minutes: int = 4
    auto_antics_max_minutes: int = 9
    auto_antics_dance_chance: int = 55
    rare_events_enabled: bool = True
    chaos_mode: bool = False
    movement_enabled: bool = True
    companion_enabled: bool = True
    selected_companion: str = "mouse"
    activity_level: str = "normal"
    quote_frequency: str = "normal"
    companion_frequency: str = "normal"
    unlocks_enabled: bool = True
    seasonal_mode_override: str = "auto"
    last_active_season: str = ""
    reaction_toggles: Dict[str, bool] = field(default_factory=dict)
    quote_pack_states: Dict[str, bool] = field(default_factory=dict)
    favorite_skins: List[str] = field(default_factory=list)
    favorite_toys: List[str] = field(default_factory=list)
    favorite_scenarios: List[str] = field(default_factory=list)
    favorite_quote_packs: List[str] = field(default_factory=list)
    unlocked_skins: List[str] = field(default_factory=list)
    unlocked_toys: List[str] = field(default_factory=list)
    unlocked_scenarios: List[str] = field(default_factory=list)
    unlocked_quote_packs: List[str] = field(default_factory=list)
    discovery_stats: Dict[str, int] = field(default_factory=dict)
    recent_scenarios: List[str] = field(default_factory=list)
    favorite_templates: List[str] = field(default_factory=list)
    recent_sayings: List[dict] = field(default_factory=list)
    companion_presence: Dict[str, object] = field(default_factory=dict)


@dataclass
class SettingsSnapshot:
    global_settings: GlobalSettings
    instance_settings: InstanceSettings


def normalize_recent_sayings(items, now=None):
    timestamp = time.time() if now is None else float(now)
    normalized = []
    for item in list(items or [])[-30:]:
        if isinstance(item, dict):
            template = str(item.get("template", item.get("text", ""))).strip()
            text = str(item.get("text", template)).strip()
            if not text:
                continue
            normalized.append(
                {
                    "template": template or text,
                    "text": text,
                    "source": str(item.get("source", "history")),
                    "timestamp": float(item.get("timestamp", timestamp)),
                }
            )
            continue
        text = str(item).strip()
        if text:
            normalized.append(
                {
                    "template": text,
                    "text": text,
                    "source": "history",
                    "timestamp": timestamp,
                }
            )
    return normalized


def normalize_string_list(items, limit=30):
    normalized = []
    for item in list(items or [])[-int(limit):]:
        text = str(item).strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized[-int(limit):]


def normalize_bool_map(items, allowed_keys=None):
    items = items if isinstance(items, dict) else {}
    allowed = set(allowed_keys or items.keys())
    normalized = {}
    for key in allowed:
        if str(key).strip() in items:
            normalized[str(key).strip()] = bool(items[str(key).strip()])
    for key, value in items.items():
        text = str(key).strip()
        if text and text not in normalized and text in allowed:
            normalized[text] = bool(value)
    return normalized


def normalize_int_map(items, allowed_keys=None):
    items = items if isinstance(items, dict) else {}
    allowed = set(allowed_keys or items.keys())
    normalized = {}
    for key in allowed:
        text = str(key).strip()
        if not text:
            continue
        try:
            value = int(items.get(text, 0))
        except (TypeError, ValueError):
            value = 0
        normalized[text] = max(0, value)
    return normalized


class SettingsService:
    def __init__(self, store, startup_manager=None, logger=None):
        self.store = store
        self.startup_manager = startup_manager
        self.logger = logger

    def load(self, pet_id, requested_name=None):
        raw_settings = self.store.read()
        settings, warnings = sanitize_settings_payload(raw_settings)
        for warning in warnings:
            self._log("warning", warning)
        if raw_settings != settings:
            self.store.write(settings)
        instance_settings = settings.get("instances", {}).get(pet_id, {})
        global_settings = settings.get("global", {})
        reaction_defaults = default_settings()["global"]["reactions"]
        sound_category_defaults = default_settings()["global"]["sound_categories"]
        discovery_defaults = default_settings()["global"]["discovery_stats"]
        pet_name = str(
            instance_settings.get(
                "name",
                requested_name
                or ("Jason" if pet_id == "main" else f"Jason {pet_id.split('-')[-1].title()}"),
            )
        )
        mood = instance_settings.get("mood")
        if mood not in MOODS:
            mood = random.choice(list(MOODS.keys()))
        global_snapshot = GlobalSettings(
            sound_enabled=bool(global_settings.get("sound_enabled", True)),
            sound_volume=int(global_settings.get("sound_volume", 70)),
            sound_categories={
                **sound_category_defaults,
                **normalize_bool_map(global_settings.get("sound_categories", {}), sound_category_defaults.keys()),
            },
            auto_update_enabled=bool(global_settings.get("auto_update_enabled", True)),
            event_reactions_enabled=bool(global_settings.get("event_reactions_enabled", True)),
            quiet_hours_enabled=bool(global_settings.get("quiet_hours_enabled", False)),
            quiet_start_hour=int(global_settings.get("quiet_start_hour", 22)),
            quiet_end_hour=int(global_settings.get("quiet_end_hour", 8)),
            quiet_when_fullscreen=bool(global_settings.get("quiet_when_fullscreen", True)),
            auto_antics_enabled=bool(global_settings.get("auto_antics_enabled", True)),
            auto_antics_min_minutes=int(global_settings.get("auto_antics_min_minutes", 4)),
            auto_antics_max_minutes=int(global_settings.get("auto_antics_max_minutes", 9)),
            auto_antics_dance_chance=int(global_settings.get("auto_antics_dance_chance", 55)),
            rare_events_enabled=bool(global_settings.get("rare_events_enabled", True)),
            chaos_mode=bool(global_settings.get("chaos_mode", False)),
            movement_enabled=bool(global_settings.get("movement_enabled", True)),
            companion_enabled=bool(global_settings.get("companion_enabled", True)),
            selected_companion=str(global_settings.get("selected_companion", "mouse")).strip() or "mouse",
            activity_level=str(global_settings.get("activity_level", "normal")).strip() or "normal",
            quote_frequency=str(global_settings.get("quote_frequency", "normal")).strip() or "normal",
            companion_frequency=str(global_settings.get("companion_frequency", "normal")).strip() or "normal",
            unlocks_enabled=bool(global_settings.get("unlocks_enabled", True)),
            seasonal_mode_override=str(global_settings.get("seasonal_mode_override", "auto")).strip() or "auto",
            last_active_season=str(global_settings.get("last_active_season", "")).strip(),
            reaction_toggles={**reaction_defaults, **dict(global_settings.get("reactions", {}))},
            quote_pack_states={
                str(key).strip(): bool(value)
                for key, value in dict(global_settings.get("quote_pack_states", {})).items()
                if str(key).strip()
            },
            favorite_skins=normalize_string_list(global_settings.get("favorite_skins", [])),
            favorite_toys=normalize_string_list(global_settings.get("favorite_toys", [])),
            favorite_scenarios=normalize_string_list(global_settings.get("favorite_scenarios", [])),
            favorite_quote_packs=normalize_string_list(global_settings.get("favorite_quote_packs", [])),
            unlocked_skins=normalize_string_list(global_settings.get("unlocked_skins", []), limit=60),
            unlocked_toys=normalize_string_list(global_settings.get("unlocked_toys", []), limit=60),
            unlocked_scenarios=normalize_string_list(global_settings.get("unlocked_scenarios", []), limit=60),
            unlocked_quote_packs=normalize_string_list(global_settings.get("unlocked_quote_packs", []), limit=60),
            discovery_stats={
                **discovery_defaults,
                **normalize_int_map(global_settings.get("discovery_stats", {}), discovery_defaults.keys()),
            },
            recent_scenarios=normalize_string_list(global_settings.get("recent_scenarios", []), limit=12),
            favorite_templates=[
                str(item).strip()
                for item in global_settings.get("favorite_sayings", [])
                if str(item).strip()
            ][-30:],
            recent_sayings=normalize_recent_sayings(global_settings.get("recent_sayings", [])),
            companion_presence=dict(global_settings.get("companion_presence", {})),
        )
        instance_snapshot = InstanceSettings(
            x=instance_settings.get("x"),
            y=instance_settings.get("y"),
            skin=str(instance_settings.get("skin", global_settings.get("default_skin", "jason"))),
            mood=mood,
            name=pet_name,
            personality_state=str(instance_settings.get("personality_state", "idle")).strip() or "idle",
            last_scenario=str(instance_settings.get("last_scenario", "")).strip(),
        )
        return SettingsSnapshot(
            global_settings=global_snapshot,
            instance_settings=instance_snapshot,
        )

    def save(self, pet_id, global_settings, instance_settings):
        def mutate(data):
            sanitized, warnings = sanitize_settings_payload(data)
            data.clear()
            data.update(sanitized)
            for warning in warnings:
                self._log("warning", warning)
            data.setdefault("global", {})
            data.setdefault("instances", {})
            data["global"]["sound_enabled"] = bool(global_settings.sound_enabled)
            data["global"]["sound_volume"] = int(global_settings.sound_volume)
            data["global"]["sound_categories"] = dict(global_settings.sound_categories)
            data["global"]["default_skin"] = str(instance_settings.skin)
            data["global"]["auto_update_enabled"] = bool(global_settings.auto_update_enabled)
            data["global"]["auto_start_enabled"] = self._startup_enabled()
            data["global"]["event_reactions_enabled"] = bool(global_settings.event_reactions_enabled)
            data["global"]["quiet_hours_enabled"] = bool(global_settings.quiet_hours_enabled)
            data["global"]["quiet_start_hour"] = int(global_settings.quiet_start_hour)
            data["global"]["quiet_end_hour"] = int(global_settings.quiet_end_hour)
            data["global"]["quiet_when_fullscreen"] = bool(global_settings.quiet_when_fullscreen)
            data["global"]["auto_antics_enabled"] = bool(global_settings.auto_antics_enabled)
            data["global"]["auto_antics_min_minutes"] = int(global_settings.auto_antics_min_minutes)
            data["global"]["auto_antics_max_minutes"] = int(global_settings.auto_antics_max_minutes)
            data["global"]["auto_antics_dance_chance"] = int(global_settings.auto_antics_dance_chance)
            data["global"]["rare_events_enabled"] = bool(global_settings.rare_events_enabled)
            data["global"]["chaos_mode"] = bool(global_settings.chaos_mode)
            data["global"]["movement_enabled"] = bool(global_settings.movement_enabled)
            data["global"]["companion_enabled"] = bool(global_settings.companion_enabled)
            data["global"]["selected_companion"] = str(global_settings.selected_companion or "mouse")
            data["global"]["activity_level"] = str(global_settings.activity_level or "normal")
            data["global"]["quote_frequency"] = str(global_settings.quote_frequency or "normal")
            data["global"]["companion_frequency"] = str(global_settings.companion_frequency or "normal")
            data["global"]["unlocks_enabled"] = bool(global_settings.unlocks_enabled)
            data["global"]["seasonal_mode_override"] = str(global_settings.seasonal_mode_override or "auto")
            data["global"]["last_active_season"] = str(global_settings.last_active_season or "")
            data["global"]["reactions"] = dict(global_settings.reaction_toggles)
            data["global"]["quote_pack_states"] = dict(global_settings.quote_pack_states)
            data["global"]["favorite_skins"] = list(global_settings.favorite_skins[-30:])
            data["global"]["favorite_toys"] = list(global_settings.favorite_toys[-30:])
            data["global"]["favorite_scenarios"] = list(global_settings.favorite_scenarios[-30:])
            data["global"]["favorite_quote_packs"] = list(global_settings.favorite_quote_packs[-30:])
            data["global"]["unlocked_skins"] = list(global_settings.unlocked_skins[-60:])
            data["global"]["unlocked_toys"] = list(global_settings.unlocked_toys[-60:])
            data["global"]["unlocked_scenarios"] = list(global_settings.unlocked_scenarios[-60:])
            data["global"]["unlocked_quote_packs"] = list(global_settings.unlocked_quote_packs[-60:])
            data["global"]["discovery_stats"] = {
                str(key).strip(): max(0, int(value))
                for key, value in dict(global_settings.discovery_stats).items()
                if str(key).strip()
            }
            data["global"]["recent_scenarios"] = list(global_settings.recent_scenarios[-12:])
            data["global"]["favorite_sayings"] = list(global_settings.favorite_templates[-30:])
            data["global"]["recent_sayings"] = list(global_settings.recent_sayings[-30:])
            data["global"]["companion_presence"] = dict(global_settings.companion_presence)
            data["instances"][pet_id] = {
                "x": instance_settings.x,
                "y": instance_settings.y,
                "skin": instance_settings.skin,
                "mood": instance_settings.mood,
                "name": instance_settings.name,
                "personality_state": instance_settings.personality_state,
                "last_scenario": instance_settings.last_scenario,
                "updated_at": time.time(),
            }
            normalized, warnings = sanitize_settings_payload(data)
            data.clear()
            data.update(normalized)
            for warning in warnings:
                self._log("warning", warning)

        self.store.update(mutate)

    def export_to_file(self, path):
        exported, warnings = sanitize_settings_payload(self.store.read())
        for warning in warnings:
            self._log("warning", warning)
        self._write_json_atomically(path, exported)

    def import_from_file(self, path):
        imported = json_load_file(path)
        self._validate_import(imported)
        sanitized, warnings = sanitize_settings_payload(imported)
        for warning in warnings:
            self._log("warning", warning)
        self.store.write(sanitized)
        return sanitized

    def reset(self):
        fresh = default_settings()
        self.store.write(fresh)
        return fresh

    def as_dict(self, snapshot):
        return {
            "global": asdict(snapshot.global_settings),
            "instance": asdict(snapshot.instance_settings),
        }

    def _startup_enabled(self):
        if self.startup_manager is None:
            return False
        return bool(self.startup_manager.is_enabled())

    @staticmethod
    def _validate_import(imported):
        if not isinstance(imported, dict):
            raise ValueError("Settings file did not contain a JSON object.")
        if "global" in imported and not isinstance(imported["global"], dict):
            raise ValueError("Settings file field 'global' must be a JSON object.")
        if "instances" in imported and not isinstance(imported["instances"], dict):
            raise ValueError("Settings file field 'instances' must be a JSON object.")

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(f"settings: {message}")

    @staticmethod
    def _write_json_atomically(path, payload):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as handle:
            handle.write(json_dumps_pretty(payload))
            handle.flush()
            os.fsync(handle.fileno())
            temp_name = handle.name
        os.replace(temp_name, path)
