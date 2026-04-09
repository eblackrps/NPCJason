import logging
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
        self._logger = logging.getLogger(f"NPCJason:{self.path}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        self._handler = None
        self._configure_handler()

    def _configure_handler(self):
        with self._lock:
            if self._handler:
                return
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(self.path, encoding="utf-8")
            handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s"))
            self._logger.addHandler(handler)
            self._handler = handler

    def _emit(self, level, message, *args, **kwargs):
        self._configure_handler()
        self._logger.log(level, str(message), *args, **kwargs)

    def log(self, message):
        self.info(message)

    def info(self, message):
        self._emit(logging.INFO, message)

    def warning(self, message):
        self._emit(logging.WARNING, message)

    def error(self, message):
        self._emit(logging.ERROR, message)

    def exception(self, message):
        self._configure_handler()
        self._logger.exception(str(message))

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
