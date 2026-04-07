import json
from pathlib import Path

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


def default_skin_definition():
    return {
        "key": "jason",
        "label": "Classic Jason",
        "author": "NPCJason",
        "description": "The default blue-shirt desktop gremlin.",
        "version": "1.0",
        "char_map": {},
        "overlay": EMPTY_OVERLAY,
        "palette": {},
        "tray": {"hair": "#4a3728", "body": "#3a86c8", "legs": "#2d4263"},
    }


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


def validate_skin_definition(data, source_name="<memory>"):
    errors = []
    normalized = dict(data or {})

    skin_key = normalized.get("key")
    if not isinstance(skin_key, str) or not skin_key.strip():
        errors.append(f"{source_name}: missing or invalid 'key'")
        return None, errors
    normalized["key"] = skin_key.strip()

    label = normalized.get("label", skin_key.title())
    normalized["label"] = str(label)
    normalized["author"] = str(normalized.get("author", "Unknown"))
    normalized["description"] = str(normalized.get("description", "No description provided."))
    normalized["version"] = str(normalized.get("version", "1.0"))

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
        normalized["palette"] = {
            str(key)[:1]: str(value)
            for key, value in normalized.get("palette", {}).items()
        }

    tray = normalized.get("tray", {})
    if not isinstance(tray, dict):
        errors.append(f"{source_name}: 'tray' must be an object")
        tray = {}
    default_tray = default_skin_definition()["tray"]
    normalized["tray"] = {
        "hair": str(tray.get("hair", default_tray["hair"])),
        "body": str(tray.get("body", default_tray["body"])),
        "legs": str(tray.get("legs", default_tray["legs"])),
    }
    normalized["overlay"] = _normalize_overlay(normalized.get("overlay", EMPTY_OVERLAY))
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
            except (OSError, json.JSONDecodeError):
                errors.append(f"{path.name}: could not parse JSON")
                continue
            normalized, skin_errors = validate_skin_definition(data, path.name)
            errors.extend(skin_errors)
            if normalized is None:
                continue
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
    for frame_key, frame_data in FRAME_LIBRARY.items():
        mapped = _apply_char_map(frame_data, skin_definition.get("char_map", {}))
        frames[frame_key] = _apply_overlay(mapped, skin_definition.get("overlay", EMPTY_OVERLAY))

    return {
        "frames": frames,
        "palette": palette,
        "tray": skin_definition.get("tray", default_skin_definition()["tray"]),
        "label": skin_definition.get("label", skin_definition.get("key", "Skin")),
    }
