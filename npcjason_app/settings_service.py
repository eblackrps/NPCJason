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


@dataclass
class GlobalSettings:
    sound_enabled: bool = True
    sound_volume: int = 70
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
    reaction_toggles: Dict[str, bool] = field(default_factory=dict)
    quote_pack_states: Dict[str, bool] = field(default_factory=dict)
    favorite_templates: List[str] = field(default_factory=list)
    recent_sayings: List[dict] = field(default_factory=list)


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
            reaction_toggles={**reaction_defaults, **dict(global_settings.get("reactions", {}))},
            quote_pack_states={
                str(key).strip(): bool(value)
                for key, value in dict(global_settings.get("quote_pack_states", {})).items()
                if str(key).strip()
            },
            favorite_templates=[
                str(item).strip()
                for item in global_settings.get("favorite_sayings", [])
                if str(item).strip()
            ][-30:],
            recent_sayings=normalize_recent_sayings(global_settings.get("recent_sayings", [])),
        )
        instance_snapshot = InstanceSettings(
            x=instance_settings.get("x"),
            y=instance_settings.get("y"),
            skin=str(instance_settings.get("skin", global_settings.get("default_skin", "jason"))),
            mood=mood,
            name=pet_name,
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
            data["global"]["reactions"] = dict(global_settings.reaction_toggles)
            data["global"]["quote_pack_states"] = dict(global_settings.quote_pack_states)
            data["global"]["favorite_sayings"] = list(global_settings.favorite_templates[-30:])
            data["global"]["recent_sayings"] = list(global_settings.recent_sayings[-30:])
            data["instances"][pet_id] = {
                "x": instance_settings.x,
                "y": instance_settings.y,
                "skin": instance_settings.skin,
                "mood": instance_settings.mood,
                "name": instance_settings.name,
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
