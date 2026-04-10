from __future__ import annotations

import copy

from .companion_presence import sanitize_companion_presence_payload
from .data.defaults import (
    MOODS,
    SETTINGS_SCHEMA_VERSION,
    SHARED_STATE_SCHEMA_VERSION,
    default_settings,
    default_shared_state,
)


def _clone_defaults(factory):
    return copy.deepcopy(factory())


def _coerce_bool(value, default):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return bool(default)


def _coerce_int(value, default, minimum=None, maximum=None):
    try:
        coerced = int(value)
    except (TypeError, ValueError):
        coerced = int(default)
    if minimum is not None:
        coerced = max(int(minimum), coerced)
    if maximum is not None:
        coerced = min(int(maximum), coerced)
    return coerced


def _coerce_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _coerce_str(value, default=""):
    if value is None:
        return str(default)
    return str(value)


def _coerce_choice(value, default, allowed):
    normalized = _coerce_str(value, default).strip().lower()
    allowed = {str(item).strip().lower() for item in allowed if str(item).strip()}
    if normalized in allowed:
        return normalized
    return str(default).strip().lower()


def _coerce_dict(value, default=None):
    if isinstance(value, dict):
        return value
    return {} if default is None else dict(default)


def _coerce_str_list(value, limit=30):
    items = value if isinstance(value, list) else []
    normalized = []
    for entry in items[-int(limit):]:
        text = _coerce_str(entry).strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized[-int(limit):]


def _coerce_bool_map(value, defaults):
    incoming = _coerce_dict(value, defaults)
    normalized = {}
    for key, default_value in dict(defaults).items():
        normalized[str(key)] = _coerce_bool(incoming.get(key), default_value)
    return normalized


def _coerce_int_map(value, defaults):
    incoming = _coerce_dict(value, defaults)
    normalized = {}
    for key, default_value in dict(defaults).items():
        normalized[str(key)] = max(0, _coerce_int(incoming.get(key), default_value, 0))
    return normalized


def _normalize_schema_version(payload, key, expected_version, label, warnings):
    version = payload.get(key, expected_version)
    coerced = _coerce_int(version, expected_version, 1)
    if coerced < expected_version:
        warnings.append(f"{label} schema upgraded from {coerced} to {expected_version}")
    elif coerced > expected_version:
        warnings.append(
            f"{label} schema version {coerced} is newer than supported {expected_version}; using best-effort compatibility"
        )
    return expected_version


def sanitize_settings_payload(payload):
    defaults = _clone_defaults(default_settings)
    warnings = []
    if not isinstance(payload, dict):
        warnings.append("settings payload was not a JSON object; defaults restored")
        payload = {}

    sanitized = defaults
    sanitized["schema_version"] = _normalize_schema_version(
        payload,
        "schema_version",
        SETTINGS_SCHEMA_VERSION,
        "settings",
        warnings,
    )

    global_in = payload.get("global", {})
    if not isinstance(global_in, dict):
        warnings.append("settings.global was invalid; defaults restored")
        global_in = {}

    instance_in = payload.get("instances", {})
    if not isinstance(instance_in, dict):
        warnings.append("settings.instances was invalid; defaults restored")
        instance_in = {}

    global_out = sanitized["global"]
    global_out["sound_enabled"] = _coerce_bool(global_in.get("sound_enabled"), global_out["sound_enabled"])
    global_out["sound_volume"] = _coerce_int(global_in.get("sound_volume"), global_out["sound_volume"], 0, 100)
    global_out["sound_categories"] = _coerce_bool_map(
        global_in.get("sound_categories", {}),
        default_settings()["global"]["sound_categories"],
    )
    global_out["default_skin"] = _coerce_str(global_in.get("default_skin"), global_out["default_skin"]).strip() or global_out["default_skin"]
    global_out["auto_update_enabled"] = _coerce_bool(global_in.get("auto_update_enabled"), global_out["auto_update_enabled"])
    global_out["auto_start_enabled"] = _coerce_bool(global_in.get("auto_start_enabled"), global_out["auto_start_enabled"])
    global_out["event_reactions_enabled"] = _coerce_bool(global_in.get("event_reactions_enabled"), global_out["event_reactions_enabled"])
    global_out["quiet_hours_enabled"] = _coerce_bool(global_in.get("quiet_hours_enabled"), global_out["quiet_hours_enabled"])
    global_out["quiet_start_hour"] = _coerce_int(global_in.get("quiet_start_hour"), global_out["quiet_start_hour"], 0, 23)
    global_out["quiet_end_hour"] = _coerce_int(global_in.get("quiet_end_hour"), global_out["quiet_end_hour"], 0, 23)
    global_out["quiet_when_fullscreen"] = _coerce_bool(global_in.get("quiet_when_fullscreen"), global_out["quiet_when_fullscreen"])
    global_out["auto_antics_enabled"] = _coerce_bool(global_in.get("auto_antics_enabled"), global_out["auto_antics_enabled"])
    global_out["auto_antics_min_minutes"] = _coerce_int(global_in.get("auto_antics_min_minutes"), global_out["auto_antics_min_minutes"], 1, 60)
    global_out["auto_antics_max_minutes"] = _coerce_int(global_in.get("auto_antics_max_minutes"), global_out["auto_antics_max_minutes"], 1, 60)
    global_out["auto_antics_dance_chance"] = _coerce_int(global_in.get("auto_antics_dance_chance"), global_out["auto_antics_dance_chance"], 0, 100)
    global_out["rare_events_enabled"] = _coerce_bool(global_in.get("rare_events_enabled"), global_out["rare_events_enabled"])
    global_out["chaos_mode"] = _coerce_bool(global_in.get("chaos_mode"), global_out["chaos_mode"])
    global_out["movement_enabled"] = _coerce_bool(global_in.get("movement_enabled"), global_out["movement_enabled"])
    global_out["companion_enabled"] = _coerce_bool(global_in.get("companion_enabled"), global_out["companion_enabled"])
    global_out["selected_companion"] = _coerce_str(
        global_in.get("selected_companion", global_out["selected_companion"])
    ).strip() or global_out["selected_companion"]
    global_out["activity_level"] = _coerce_choice(
        global_in.get("activity_level", global_out["activity_level"]),
        global_out["activity_level"],
        {"low", "normal", "high"},
    )
    global_out["quote_frequency"] = _coerce_choice(
        global_in.get("quote_frequency", global_out["quote_frequency"]),
        global_out["quote_frequency"],
        {"quiet", "normal", "chatty"},
    )
    global_out["companion_frequency"] = _coerce_choice(
        global_in.get("companion_frequency", global_out["companion_frequency"]),
        global_out["companion_frequency"],
        {"low", "normal", "high"},
    )
    global_out["unlocks_enabled"] = _coerce_bool(global_in.get("unlocks_enabled"), global_out["unlocks_enabled"])
    seasonal_mode = _coerce_str(global_in.get("seasonal_mode_override", global_out["seasonal_mode_override"])).strip()
    global_out["seasonal_mode_override"] = seasonal_mode or global_out["seasonal_mode_override"]
    global_out["last_active_season"] = _coerce_str(
        global_in.get("last_active_season", global_out["last_active_season"])
    ).strip()

    reactions_in = global_in.get("reactions", {})
    if not isinstance(reactions_in, dict):
        warnings.append("settings.global.reactions was invalid; defaults restored")
        reactions_in = {}
    for key, default_value in default_settings()["global"]["reactions"].items():
        global_out["reactions"][key] = _coerce_bool(reactions_in.get(key), default_value)

    quote_pack_states = {}
    quote_pack_states_in = _coerce_dict(global_in.get("quote_pack_states", {}))
    for key, value in quote_pack_states_in.items():
        pack_key = _coerce_str(key).strip()
        if not pack_key:
            continue
        quote_pack_states[pack_key] = _coerce_bool(value, True)
    for entry in global_in.get("disabled_quote_packs", []):
        pack_key = _coerce_str(entry).strip()
        if pack_key and pack_key not in quote_pack_states:
            quote_pack_states[pack_key] = False
    global_out["quote_pack_states"] = quote_pack_states
    global_out["favorite_skins"] = _coerce_str_list(global_in.get("favorite_skins", []))
    global_out["favorite_toys"] = _coerce_str_list(global_in.get("favorite_toys", []))
    global_out["favorite_scenarios"] = _coerce_str_list(global_in.get("favorite_scenarios", []))
    global_out["favorite_quote_packs"] = _coerce_str_list(global_in.get("favorite_quote_packs", []))
    global_out["unlocked_skins"] = _coerce_str_list(global_in.get("unlocked_skins", []), limit=60)
    global_out["unlocked_toys"] = _coerce_str_list(global_in.get("unlocked_toys", []), limit=60)
    global_out["unlocked_scenarios"] = _coerce_str_list(global_in.get("unlocked_scenarios", []), limit=60)
    global_out["unlocked_quote_packs"] = _coerce_str_list(global_in.get("unlocked_quote_packs", []), limit=60)
    global_out["discovery_stats"] = _coerce_int_map(
        global_in.get("discovery_stats", {}),
        default_settings()["global"]["discovery_stats"],
    )
    global_out["recent_scenarios"] = _coerce_str_list(global_in.get("recent_scenarios", []), limit=12)

    global_out["favorite_sayings"] = _coerce_str_list(global_in.get("favorite_sayings", []))

    recent = []
    for entry in global_in.get("recent_sayings", []):
        if isinstance(entry, dict):
            template = _coerce_str(entry.get("template", entry.get("text", ""))).strip()
            text = _coerce_str(entry.get("text", template)).strip()
            if not text:
                continue
            recent.append(
                {
                    "template": template or text,
                    "text": text,
                    "source": _coerce_str(entry.get("source", "history")).strip() or "history",
                    "timestamp": _coerce_float(entry.get("timestamp", 0.0)),
                }
            )
            continue
        text = _coerce_str(entry).strip()
        if text:
            recent.append({"template": text, "text": text, "source": "history", "timestamp": 0.0})
    global_out["recent_sayings"] = recent[-30:]
    global_out["companion_presence"] = sanitize_companion_presence_payload(
        global_in.get("companion_presence", {})
    )

    instances_out = {}
    for pet_id, value in instance_in.items():
        if not isinstance(value, dict):
            warnings.append(f"settings.instances.{pet_id} was invalid; entry skipped")
            continue
        mood = _coerce_str(value.get("mood", "happy")).strip()
        if mood not in MOODS:
            mood = "happy"
        entry = {
            "x": value.get("x") if value.get("x") is None else _coerce_int(value.get("x"), 0),
            "y": value.get("y") if value.get("y") is None else _coerce_int(value.get("y"), 0),
            "skin": _coerce_str(value.get("skin", global_out["default_skin"])).strip() or global_out["default_skin"],
            "mood": mood,
            "name": _coerce_str(value.get("name", "Jason")).strip() or "Jason",
            "personality_state": _coerce_str(value.get("personality_state", "idle")).strip() or "idle",
            "last_scenario": _coerce_str(value.get("last_scenario", "")).strip(),
            "updated_at": _coerce_float(value.get("updated_at", 0.0)),
        }
        instances_out[_coerce_str(pet_id).strip() or "main"] = entry
    sanitized["instances"] = instances_out

    return sanitized, warnings


def sanitize_shared_state_payload(payload):
    defaults = _clone_defaults(default_shared_state)
    warnings = []
    if not isinstance(payload, dict):
        warnings.append("shared-state payload was not a JSON object; defaults restored")
        payload = {}

    sanitized = defaults
    sanitized["schema_version"] = _normalize_schema_version(
        payload,
        "schema_version",
        SHARED_STATE_SCHEMA_VERSION,
        "shared-state",
        warnings,
    )

    instances_in = payload.get("instances", {})
    if not isinstance(instances_in, dict):
        warnings.append("shared-state instances payload was invalid; defaults restored")
        instances_in = {}
    for pet_id, value in instances_in.items():
        if not isinstance(value, dict):
            warnings.append(f"shared-state instance {pet_id} was invalid; entry skipped")
            continue
        sanitized["instances"][_coerce_str(pet_id).strip() or "main"] = {
            "updated_at": _coerce_float(value.get("updated_at", 0.0)),
            "x": _coerce_int(value.get("x", 0), 0),
            "y": _coerce_int(value.get("y", 0), 0),
            "mood": (
                _coerce_str(value.get("mood", "happy")).strip()
                if _coerce_str(value.get("mood", "happy")).strip() in MOODS
                else "happy"
            ),
            "skin": _coerce_str(value.get("skin", "jason")).strip() or "jason",
            "name": _coerce_str(value.get("name", "Jason")).strip() or "Jason",
            "friend_of": _coerce_str(value.get("friend_of", "")).strip() or None,
            "pid": _coerce_int(value.get("pid", 0), 0),
        }

    conversations_in = payload.get("conversations", [])
    if not isinstance(conversations_in, list):
        warnings.append("shared-state conversations payload was invalid; defaults restored")
        conversations_in = []
    for entry in conversations_in:
        if not isinstance(entry, dict):
            continue
        conversation_id = _coerce_str(entry.get("id")).strip()
        participants = [
            _coerce_str(value).strip()
            for value in entry.get("participants", [])
            if _coerce_str(value).strip()
        ]
        lines_in = entry.get("lines", {})
        if not conversation_id or not isinstance(lines_in, dict):
            continue
        lines = {}
        for key, value in lines_in.items():
            pet_key = _coerce_str(key).strip()
            text = _coerce_str(value).strip()
            if pet_key and text:
                lines[pet_key] = text
        if participants and lines:
            sanitized["conversations"].append(
                {
                    "id": conversation_id,
                    "created_at": _coerce_float(entry.get("created_at", 0.0)),
                    "participants": participants,
                    "lines": lines,
                }
            )

    commands_in = payload.get("commands", [])
    if not isinstance(commands_in, list):
        warnings.append("shared-state commands payload was invalid; defaults restored")
        commands_in = []
    for entry in commands_in:
        if not isinstance(entry, dict):
            continue
        command_id = _coerce_str(entry.get("id")).strip()
        target = _coerce_str(entry.get("target")).strip()
        action = _coerce_str(entry.get("action")).strip()
        if command_id and target and action:
            sanitized["commands"].append(
                {
                    "id": command_id,
                    "created_at": _coerce_float(entry.get("created_at", 0.0)),
                    "target": target,
                    "action": action,
                }
            )

    return sanitized, warnings
