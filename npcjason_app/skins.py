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


def load_skin_files():
    definitions = {}
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
                continue
            skin_key = data.get("key")
            if not skin_key:
                continue
            data.setdefault("label", skin_key.title())
            data.setdefault("char_map", {})
            data.setdefault("palette", {})
            data.setdefault("tray", default_skin_definition()["tray"])
            data["overlay"] = _normalize_overlay(data.get("overlay", EMPTY_OVERLAY))
            definitions[skin_key] = data

    if "jason" not in definitions:
        definitions["jason"] = default_skin_definition()
    return definitions


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
