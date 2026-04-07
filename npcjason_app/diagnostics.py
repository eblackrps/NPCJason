from datetime import datetime
import os
from pathlib import Path
import subprocess
import threading

from .paths import APPDATA_DIR, LOG_PATH, ensure_app_dirs


class DiagnosticsLogger:
    def __init__(self, path=LOG_PATH):
        self.path = Path(path)
        self._lock = threading.Lock()
        ensure_app_dirs()

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}\n"
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)

    def open_log_file(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)
        open_path(self.path)

    def open_data_folder(self):
        open_path(APPDATA_DIR)


def open_path(path):
    target = str(Path(path))
    try:
        os.startfile(target)  # type: ignore[attr-defined]
    except AttributeError:
        subprocess.Popen(["explorer", target])
