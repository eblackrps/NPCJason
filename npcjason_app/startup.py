import os
from pathlib import Path
import sys

from .paths import STARTUP_DIR, runtime_entrypoint
from .version import APP_NAME


def startup_script_path():
    return STARTUP_DIR / f"{APP_NAME}.cmd"


def _quoted(path):
    return f'"{str(path)}"'


def build_startup_script():
    entrypoint = runtime_entrypoint()
    if getattr(sys, "frozen", False):
        launch_line = f"start \"\" {_quoted(entrypoint)}\r\n"
    else:
        launch_line = f"start \"\" {_quoted(Path(sys.executable).resolve())} {_quoted(entrypoint)}\r\n"
    return "@echo off\r\n" + launch_line


class StartupManager:
    def __init__(self, script_path=None):
        self.script_path = Path(script_path or startup_script_path())

    def is_enabled(self):
        return self.script_path.exists()

    def set_enabled(self, enabled):
        STARTUP_DIR.mkdir(parents=True, exist_ok=True)
        if enabled:
            self.script_path.write_text(build_startup_script(), encoding="utf-8")
        else:
            try:
                self.script_path.unlink()
            except FileNotFoundError:
                pass
