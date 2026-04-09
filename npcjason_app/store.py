import copy
import json
import os
from pathlib import Path
import tempfile
import time

from .paths import ensure_app_dirs

try:
    import msvcrt
except ImportError:
    msvcrt = None


def clamp(value, minimum, maximum):
    return max(minimum, min(value, maximum))


def _deepcopy_default(default_factory):
    return copy.deepcopy(default_factory())


def _lock_file(handle):
    if msvcrt is None:
        return
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)


def _unlock_file(handle):
    if msvcrt is None:
        return
    handle.seek(0)
    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


class JsonStore:
    def __init__(self, path, default_factory, logger=None, store_name="store"):
        self.path = Path(path)
        self.default_factory = default_factory
        self.logger = logger
        self.store_name = str(store_name)

    def _read_unlocked(self):
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, dict):
                    return data
                self._backup_invalid_file("top-level JSON value was not an object")
        except FileNotFoundError:
            pass
        except json.JSONDecodeError as exc:
            self._backup_invalid_file(f"JSON decode error: {exc}")
        except OSError as exc:
            self._log("warning", f"{self.store_name} read failed; using defaults ({exc})")
        return _deepcopy_default(self.default_factory)

    def _write_atomic(self, data):
        ensure_app_dirs()
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir=str(self.path.parent),
            encoding="utf-8",
        ) as temp_handle:
            json.dump(data, temp_handle, indent=2, ensure_ascii=False)
            temp_handle.flush()
            os.fsync(temp_handle.fileno())
            temp_name = temp_handle.name
        os.replace(temp_name, self.path)

    def _lock_path(self):
        return self.path.with_suffix(self.path.suffix + ".lock")

    def _with_lock(self, callback):
        lock_path = self._lock_path()
        with lock_path.open("a+b") as lock_handle:
            _lock_file(lock_handle)
            try:
                return callback()
            finally:
                _unlock_file(lock_handle)

    def read(self):
        ensure_app_dirs()
        return self._read_unlocked()

    def write(self, data):
        ensure_app_dirs()
        self._with_lock(lambda: self._write_atomic(data))

    def update(self, mutator):
        ensure_app_dirs()
        def callback():
                data = self._read_unlocked()
                result = mutator(data)
                self._write_atomic(data)
                return result

        return self._with_lock(callback)

    def _backup_invalid_file(self, reason):
        if not self.path.exists():
            return
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        backup_path = self.path.with_name(f"{self.path.stem}.corrupt-{timestamp}{self.path.suffix}")
        try:
            os.replace(self.path, backup_path)
            self._log("warning", f"{self.store_name} was invalid and was backed up to {backup_path.name} ({reason})")
        except OSError as exc:
            self._log("warning", f"{self.store_name} was invalid and could not be backed up ({reason}; {exc})")

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message)
