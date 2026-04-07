import os
from pathlib import Path
import sys

from .version import APP_NAME


RESOURCE_DIR = Path(
    sys.executable if getattr(sys, "frozen", False) else __file__
).resolve().parent.parent
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", RESOURCE_DIR))
APPDATA_DIR = Path(
    os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming"))
) / APP_NAME
SETTINGS_PATH = APPDATA_DIR / "settings.json"
SHARED_STATE_PATH = APPDATA_DIR / "shared_state.json"
SOUNDS_CACHE_DIR = APPDATA_DIR / "sounds"
LOGS_DIR = APPDATA_DIR / "logs"
LOG_PATH = LOGS_DIR / "npcjason.log"
RESOURCE_SAYINGS_PATH = RESOURCE_DIR / "sayings.txt"
RESOURCE_DIALOGUE_PACKS_DIR = RESOURCE_DIR / "dialogue-packs"
RESOURCE_SKINS_DIR = RESOURCE_DIR / "skins"
BUNDLED_SKINS_DIR = BUNDLE_DIR / "skins"
STARTUP_DIR = (
    Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs"
    / "Startup"
)


def ensure_app_dirs():
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    SOUNDS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def runtime_entrypoint():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve()
    return Path(RESOURCE_DIR / "npcjason.py").resolve()
