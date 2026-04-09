import copy
import json
from pathlib import Path
import re

from .paths import BUNDLED_SKINS_DIR, RESOURCE_SKINS_DIR


PIXEL_SCALE = 4
GRID_W = 16
GRID_H = 20
CANVAS_W = GRID_W * PIXEL_SCALE
CANVAS_H = GRID_H * PIXEL_SCALE

BASE_PALETTE = {
    "K": "#1a1a2e",
    "S": "#e8c170",
    "H": "#4a3728",
    "E": "#16213e",
    "M": "#c84b31",
    "T": "#3a86c8",
    "P": "#2d4263",
    "O": "#e8c170",
    "W": "#ffffff",
    "B": "#0f3460",
    "R": "#c84b31",
    "G": "#aaaaaa",
    "Z": "#6f63ff",
    "L": "#ffd166",
    "N": "#d8dee9",
    "D": "#697886",
    "V": "#7dc7e8",
    "U": "#f4f8ff",
    "A": "#ff9f1c",
}

FRAME_LIBRARY = {
    "idle_open": [
        "................",
        "....KKKKKKKK....",
        "...KHHHHHHHHHK..",
        "..KHHHHHHHHHHK..",
        "..KHHHHHHHHHK...",
        "..KSSSSSSSSSK...",
        "..KSWEKSSWESK...",
        "..KSSSSSSSSK....",
        "..KSSSSMSSSK....",
        "..KKSSSSSSKK....",
        "....KTTTTTK.....",
        "...KTTTTTTTTK...",
        "..KTTTTTTTTTK...",
        "..KSKTTTTTKSK...",
        "...KKTTTTTKK....",
        "....KPPPPPK.....",
        "....KPKKPPK.....",
        "....KPKKPPK.....",
        "...KOKK.KOKK....",
        "...KKK..KKK.....",
    ],
    "idle_breathe_in": [
        "................",
        "....KKKKKKKK....",
        "...KHHHHHHHHHK..",
        "..KHHHHHHHHHHK..",
        "..KHHHHHHHHHK...",
        "..KSSSSSSSSSK...",
        "..KSWEKSSWESK...",
        "..KSSSSSSSSK....",
        "..KSSSSMSSSK....",
        "..KKSSSSSSKK....",
        "...KTTTTTTTK....",
        "..KTTTTTTTTTK...",
        "..KTTTTTTTTTK...",
        "..KSKTTTTTKSK...",
        "...KKTTTTTKK....",
        "....KPPPPPK.....",
        "...KPPKKPPPK....",
        "...KPKKPPKK.....",
        "..KOKK...KOK....",
        "..KKK.....KK....",
    ],
    "idle_breathe_out": [
        "................",
        "....KKKKKKKK....",
        "...KHHHHHHHHHK..",
        "..KHHHHHHHHHHK..",
        "..KHHHHHHHHHK...",
        "..KSSSSSSSSSK...",
        "..KSWEKSSWESK...",
        "..KSSSSSSSSK....",
        "..KSSSSMSSSK....",
        "..KKSSSSSSKK....",
        ".....KTTTK......",
        "...KTTTTTTTK....",
        "..KTTTTTTTTK....",
        "...KSKTTTTKSK...",
        "....KKTTTKK.....",
        "....KPPPPPK.....",
        "....KPKKPPK.....",
        "...KPP..PPK.....",
        "...KOK...KOK....",
        "...KKK...KKK....",
    ],
    "idle_blink": [
        "................",
        "....KKKKKKKK....",
        "...KHHHHHHHHHK..",
        "..KHHHHHHHHHHK..",
        "..KHHHHHHHHHK...",
        "..KSSSSSSSSSK...",
        "..KSKKKSSKKSK...",
        "..KSSSSSSSSK....",
        "..KSSSSMSSSK....",
        "..KKSSSSSSKK....",
        "....KTTTTTK.....",
        "...KTTTTTTTTK...",
        "..KTTTTTTTTTK...",
        "..KSKTTTTTKSK...",
        "...KKTTTTTKK....",
        "....KPPPPPK.....",
        "....KPKKPPK.....",
        "....KPKKPPK.....",
        "...KOKK.KOKK....",
        "...KKK..KKK.....",
    ],
    "dance1": [
        "................",
        "....KKKKKKKK....",
        "...KHHHHHHHHHK..",
        "..KHHHHHHHHHHK..",
        "..KHHHHHHHHHK...",
        "..KSSSSSSSSSK...",
        "..KSWEKSSWESK...",
        "..KSSSSSSSSK....",
        "..KSSSSMSSSK....",
        "..KKSSSSSSKK....",
        "..KSK.KTTTTTK...",
        ".KSK.KTTTTTTK...",
        "..KK.KTTTTTTTK..",
        ".....KTTTTTTK...",
        "......KTTTK.....",
        "....KPPPPPK.....",
        "...KPPK.KPPK....",
        "..KPPK...KPPK...",
        "..KOK.....KOK...",
        "..KKK.....KKK...",
    ],
    "dance2": [
        "................",
        "....KKKKKKKK....",
        "...KHHHHHHHHHK..",
        "..KHHHHHHHHHHK..",
        "..KHHHHHHHHHK...",
        "..KSSSSSSSSSK...",
        "..KSWEKSSWESK...",
        "..KSSSSSSSSK....",
        "..KSSSSMSSSK....",
        "..KKSSSSSSKK....",
        "..KTTTTTK.KSK...",
        "..KTTTTTTK.KSK..",
        "..KTTTTTTTK.KK..",
        "...KTTTTTTK.....",
        ".....KTTTK......",
        ".....KPPPPPK....",
        "....KPPK.KPPK...",
        "...KPPK...KPPK..",
        "...KOK.....KOK..",
        "...KKK.....KKK..",
    ],
    "dance3": [
        "................",
        "................",
        "....KKKKKKKK....",
        "...KHHHHHHHHHK..",
        "..KHHHHHHHHHHK..",
        "..KHHHHHHHHHK...",
        "..KSSSSSSSSSK...",
        "..KSWEKSSWESK...",
        "..KSSSSSSSSK....",
        "..KSSSSMSSSK....",
        "..KKSSSSSSKK....",
        "..KSKTTTTTKSK...",
        "..KSKTTTTTKSK...",
        "...KKTTTTTKK....",
        "....KPPPPPK.....",
        "...KPPKKKPPK....",
        "..KPPK...KPPK...",
        "..KOKK...KOKK...",
        "..KKKK...KKKK...",
        "..GGGG...GGGG...",
    ],
}

IDLE_SEQUENCE = [
    ("idle_open", 0),
    ("idle_breathe_in", -1),
    ("idle_open", 0),
    ("idle_breathe_out", 1),
    ("idle_open", 0),
    ("idle_blink", 0),
    ("idle_open", 0),
    ("idle_breathe_in", -1),
]

DANCE_SEQUENCE = ["dance1", "dance2", "dance3", "dance2", "dance1"]
EMPTY_OVERLAY = ["." * GRID_W for _ in range(GRID_H)]
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
AFFINITY_FIELDS = ("packs", "categories", "contexts", "toys", "skins", "tags", "moods")
ACCESSORY_OFFSET_KEYS = ("bubble", "toy_anchor", "carry")


def _sequence_entry(frame_key, offset_y=0, delay_ms=None):
    return {
        "frame": str(frame_key),
        "offset_y": int(offset_y),
        "delay_ms": None if delay_ms is None else int(delay_ms),
    }


def _default_idle_animation():
    return [_sequence_entry(frame_key, offset_y=offset_y) for frame_key, offset_y in IDLE_SEQUENCE]


def _default_interaction_animation():
    return [_sequence_entry(frame_key) for frame_key in DANCE_SEQUENCE]


def default_skin_definition():
    metadata = {
        "author": "NPCJason",
        "description": "The default blue-shirt desktop gremlin.",
        "version": "2.0",
    }
    definition = {
        "schema_version": 2,
        "key": "jason",
        "label": "Classic Jason",
        "author": metadata["author"],
        "description": metadata["description"],
        "version": metadata["version"],
        "metadata": metadata,
        "char_map": {},
        "overlay": EMPTY_OVERLAY,
        "frame_overlays": {},
        "custom_frames": {},
        "palette": {},
        "tray": {"hair": "#4a3728", "body": "#3a86c8", "legs": "#2d4263"},
        "tags": ["classic", "default", "desktop-gremlin"],
        "sound_set": None,
        "quote_affinity": {
            "packs": [],
            "categories": [],
            "contexts": [],
            "toys": [],
            "skins": [],
            "tags": [],
            "moods": [],
        },
        "accessory_offsets": {
            "bubble": {"x": 0, "y": 0},
            "toy_anchor": {"x": 2, "y": 46},
            "carry": {"x": 0, "y": 30},
        },
        "animations": {
            "idle": _default_idle_animation(),
            "interaction": _default_interaction_animation(),
        },
    }
    definition["capabilities"] = summarize_skin_capabilities(definition)
    return definition


def _apply_char_map(frame_data, char_map):
    if not char_map:
        return list(frame_data)
    return ["".join(char_map.get(char, char) for char in row) for row in frame_data]


def _apply_overlay(frame_data, overlay_rows):
    if not overlay_rows:
        return list(frame_data)
    rows = []
    for base_row, overlay_row in zip(frame_data, overlay_rows):
        merged = []
        for base_char, overlay_char in zip(base_row, overlay_row):
            merged.append(base_char if overlay_char == "." else overlay_char)
        rows.append("".join(merged))
    return rows


def _normalize_overlay(rows):
    normalized = []
    for row in list(rows or [])[:GRID_H]:
        row = str(row)
        normalized.append((row + "." * GRID_W)[:GRID_W])
    while len(normalized) < GRID_H:
        normalized.append("." * GRID_W)
    return normalized


def _valid_color(value):
    return isinstance(value, str) and bool(HEX_COLOR_PATTERN.match(value.strip()))


def _normalize_string_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]
    normalized = []
    seen = set()
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _normalize_affinity(value, source_name, field_name, errors):
    if value is None:
        return {field: [] for field in AFFINITY_FIELDS}
    if not isinstance(value, dict):
        errors.append(f"{source_name}: '{field_name}' must be an object")
        return {field: [] for field in AFFINITY_FIELDS}
    normalized = {}
    for field in AFFINITY_FIELDS:
        normalized[field] = _normalize_string_list(value.get(field, []))
    return normalized


def _normalize_offset_point(value, fallback, source_name, field_name, errors):
    if value is None:
        value = {}
    if not isinstance(value, dict):
        errors.append(f"{source_name}: '{field_name}' must be an object")
        return dict(fallback)
    try:
        x = int(value.get("x", fallback["x"]))
    except (TypeError, ValueError):
        errors.append(f"{source_name}: invalid x offset for '{field_name}'")
        x = int(fallback["x"])
    try:
        y = int(value.get("y", fallback["y"]))
    except (TypeError, ValueError):
        errors.append(f"{source_name}: invalid y offset for '{field_name}'")
        y = int(fallback["y"])
    return {"x": x, "y": y}


def _normalize_accessory_offsets(value, source_name, errors):
    default_offsets = default_skin_definition()["accessory_offsets"]
    if value is None:
        return copy.deepcopy(default_offsets)
    if not isinstance(value, dict):
        errors.append(f"{source_name}: 'accessory_offsets' must be an object")
        return copy.deepcopy(default_offsets)
    normalized = {}
    for key in ACCESSORY_OFFSET_KEYS:
        normalized[key] = _normalize_offset_point(
            value.get(key),
            default_offsets[key],
            source_name,
            f"accessory_offsets.{key}",
            errors,
        )
    return normalized


def _normalize_custom_frames(value, source_name, errors):
    if value is None:
        return {}
    if not isinstance(value, dict):
        errors.append(f"{source_name}: 'custom_frames' must be an object")
        return {}
    normalized = {}
    for frame_key, rows in value.items():
        key = str(frame_key).strip()
        if not key:
            errors.append(f"{source_name}: custom frame keys must be non-empty")
            continue
        normalized[key] = _normalize_overlay(rows)
    return normalized


def _normalize_frame_overlays(value, valid_frames, source_name, errors):
    if value is None:
        return {}
    if not isinstance(value, dict):
        errors.append(f"{source_name}: 'frame_overlays' must be an object")
        return {}
    normalized = {}
    for frame_key, rows in value.items():
        key = str(frame_key).strip()
        if not key:
            errors.append(f"{source_name}: frame_overlays keys must be non-empty")
            continue
        if key not in valid_frames:
            errors.append(f"{source_name}: frame overlay references unknown frame '{key}'")
            continue
        normalized[key] = _normalize_overlay(rows)
    return normalized


def _normalize_animation_sequence(value, default_sequence, valid_frames, source_name, field_name, errors):
    if value is None:
        return [dict(entry) for entry in default_sequence]
    if not isinstance(value, list):
        errors.append(f"{source_name}: '{field_name}' must be a list")
        return [dict(entry) for entry in default_sequence]

    normalized = []
    for index, entry in enumerate(value):
        frame_key = ""
        offset_y = 0
        delay_ms = None
        if isinstance(entry, str):
            frame_key = entry.strip()
        elif isinstance(entry, dict):
            frame_key = str(entry.get("frame", entry.get("frame_key", ""))).strip()
            try:
                offset_y = int(entry.get("offset_y", 0))
            except (TypeError, ValueError):
                errors.append(f"{source_name}: invalid offset_y in '{field_name}' entry {index}")
                offset_y = 0
            raw_delay = entry.get("delay_ms")
            if raw_delay is not None:
                try:
                    delay_ms = max(1, int(raw_delay))
                except (TypeError, ValueError):
                    errors.append(f"{source_name}: invalid delay_ms in '{field_name}' entry {index}")
                    delay_ms = None
        elif isinstance(entry, (list, tuple)) and entry:
            frame_key = str(entry[0]).strip()
            if len(entry) > 1:
                try:
                    offset_y = int(entry[1])
                except (TypeError, ValueError):
                    errors.append(f"{source_name}: invalid offset_y in '{field_name}' entry {index}")
            if len(entry) > 2 and entry[2] is not None:
                try:
                    delay_ms = max(1, int(entry[2]))
                except (TypeError, ValueError):
                    errors.append(f"{source_name}: invalid delay_ms in '{field_name}' entry {index}")
        else:
            errors.append(f"{source_name}: invalid '{field_name}' entry {index}")
            continue

        if not frame_key:
            errors.append(f"{source_name}: missing frame in '{field_name}' entry {index}")
            continue
        if frame_key not in valid_frames:
            errors.append(f"{source_name}: '{field_name}' references unknown frame '{frame_key}'")
            continue
        normalized.append(_sequence_entry(frame_key, offset_y=offset_y, delay_ms=delay_ms))

    if not normalized:
        return [dict(entry) for entry in default_sequence]
    return normalized


def summarize_skin_capabilities(definition):
    idle_animation = list(definition.get("animations", {}).get("idle", []))
    interaction_animation = list(definition.get("animations", {}).get("interaction", []))
    accessory_offsets = definition.get("accessory_offsets", {})
    quote_affinity = definition.get("quote_affinity", {})
    return {
        "idle_animation": "custom" if idle_animation != _default_idle_animation() else "default",
        "interaction_animation": (
            "none"
            if not interaction_animation
            else "custom" if interaction_animation != _default_interaction_animation() else "default"
        ),
        "sound_set": bool(definition.get("sound_set")),
        "quote_affinity": any(bool(values) for values in quote_affinity.values()),
        "accessory_offsets": any(
            accessory_offsets.get(key, {}).get(axis, 0)
            for key in ACCESSORY_OFFSET_KEYS
            for axis in ("x", "y")
        ),
        "metadata_tags": bool(definition.get("tags")),
        "custom_frames": bool(definition.get("custom_frames")),
    }


def validate_skin_definition(data, source_name="<memory>"):
    errors = []
    defaults = default_skin_definition()
    normalized = dict(data or {})

    skin_key = normalized.get("key")
    if not isinstance(skin_key, str) or not skin_key.strip():
        errors.append(f"{source_name}: missing or invalid 'key'")
        return None, errors
    normalized["key"] = skin_key.strip()

    label = normalized.get("label", skin_key.title())
    normalized["label"] = str(label)
    normalized["schema_version"] = 2
    normalized["author"] = str(normalized.get("author", defaults["author"]))
    normalized["description"] = str(normalized.get("description", defaults["description"]))
    normalized["version"] = str(normalized.get("version", defaults["version"]))
    normalized["metadata"] = {
        "author": normalized["author"],
        "description": normalized["description"],
        "version": normalized["version"],
    }

    if not isinstance(normalized.get("char_map", {}), dict):
        errors.append(f"{source_name}: 'char_map' must be an object")
        normalized["char_map"] = {}
    else:
        normalized["char_map"] = {
            str(key)[:1]: str(value)[:1]
            for key, value in normalized.get("char_map", {}).items()
        }

    if not isinstance(normalized.get("palette", {}), dict):
        errors.append(f"{source_name}: 'palette' must be an object")
        normalized["palette"] = {}
    else:
        palette = {}
        for key, value in normalized.get("palette", {}).items():
            color = str(value).strip()
            if not _valid_color(color):
                errors.append(f"{source_name}: invalid palette color for '{str(key)[:1]}'")
                continue
            palette[str(key)[:1]] = color
        normalized["palette"] = palette

    tray = normalized.get("tray", {})
    if not isinstance(tray, dict):
        errors.append(f"{source_name}: 'tray' must be an object")
        tray = {}
    default_tray = defaults["tray"]
    normalized["tray"] = {
        "hair": str(tray.get("hair", default_tray["hair"])),
        "body": str(tray.get("body", default_tray["body"])),
        "legs": str(tray.get("legs", default_tray["legs"])),
    }
    for part, default_color in default_tray.items():
        if not _valid_color(normalized["tray"][part]):
            errors.append(f"{source_name}: invalid tray color for '{part}'")
            normalized["tray"][part] = default_color
    normalized["overlay"] = _normalize_overlay(normalized.get("overlay", defaults["overlay"]))
    normalized["custom_frames"] = _normalize_custom_frames(normalized.get("custom_frames"), source_name, errors)
    valid_frames = set(FRAME_LIBRARY)
    valid_frames.update(normalized["custom_frames"].keys())
    normalized["frame_overlays"] = _normalize_frame_overlays(
        normalized.get("frame_overlays"),
        valid_frames,
        source_name,
        errors,
    )
    normalized["tags"] = _normalize_string_list(normalized.get("tags", defaults["tags"]))
    normalized["sound_set"] = (
        str(normalized.get("sound_set")).strip() if normalized.get("sound_set") is not None else None
    ) or None
    normalized["quote_affinity"] = _normalize_affinity(
        normalized.get("quote_affinity"),
        source_name,
        "quote_affinity",
        errors,
    )
    normalized["accessory_offsets"] = _normalize_accessory_offsets(
        normalized.get("accessory_offsets"),
        source_name,
        errors,
    )

    animations = normalized.get("animations", {})
    if animations is None:
        animations = {}
    if not isinstance(animations, dict):
        errors.append(f"{source_name}: 'animations' must be an object")
        animations = {}
    normalized["animations"] = {
        "idle": _normalize_animation_sequence(
            animations.get("idle"),
            defaults["animations"]["idle"],
            valid_frames,
            source_name,
            "animations.idle",
            errors,
        ),
        "interaction": _normalize_animation_sequence(
            animations.get("interaction"),
            defaults["animations"]["interaction"],
            valid_frames,
            source_name,
            "animations.interaction",
            errors,
        ),
    }
    normalized["capabilities"] = summarize_skin_capabilities(normalized)
    return normalized, errors


def load_skin_bundle():
    definitions = {}
    errors = []
    seen_directories = []
    for directory in [BUNDLED_SKINS_DIR, RESOURCE_SKINS_DIR]:
        directory = Path(directory)
        if directory in seen_directories:
            continue
        seen_directories.append(directory)
        if not Path(directory).exists():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                errors.append(f"{path.name}: could not parse JSON")
                continue
            normalized, skin_errors = validate_skin_definition(data, path.name)
            errors.extend(skin_errors)
            if normalized is None:
                continue
            if normalized["key"] in definitions:
                errors.append(f"{path.name}: overriding existing skin key '{normalized['key']}'")
            definitions[normalized["key"]] = normalized

    if "jason" not in definitions:
        definitions["jason"] = default_skin_definition()
    return {"definitions": definitions, "errors": errors}


def load_skin_files():
    return load_skin_bundle()["definitions"]


def build_skin_assets(skin_definition):
    palette = dict(BASE_PALETTE)
    palette.update(skin_definition.get("palette", {}))

    frames = {}
    frame_library = dict(FRAME_LIBRARY)
    frame_library.update(skin_definition.get("custom_frames", {}))
    frame_overlays = skin_definition.get("frame_overlays", {})
    for frame_key, frame_data in frame_library.items():
        mapped = _apply_char_map(frame_data, skin_definition.get("char_map", {}))
        mapped = _apply_overlay(mapped, skin_definition.get("overlay", EMPTY_OVERLAY))
        frames[frame_key] = _apply_overlay(mapped, frame_overlays.get(frame_key, EMPTY_OVERLAY))

    return {
        "frames": frames,
        "palette": palette,
        "tray": skin_definition.get("tray", default_skin_definition()["tray"]),
        "label": skin_definition.get("label", skin_definition.get("key", "Skin")),
        "metadata": dict(skin_definition.get("metadata", {})),
        "tags": list(skin_definition.get("tags", [])),
        "sound_set": skin_definition.get("sound_set"),
        "quote_affinity": copy.deepcopy(skin_definition.get("quote_affinity", {})),
        "accessory_offsets": copy.deepcopy(skin_definition.get("accessory_offsets", {})),
        "capabilities": dict(skin_definition.get("capabilities", {})),
        "idle_sequence": [dict(entry) for entry in skin_definition.get("animations", {}).get("idle", _default_idle_animation())],
        "interaction_sequence": [
            dict(entry)
            for entry in skin_definition.get("animations", {}).get("interaction", _default_interaction_animation())
        ],
    }
