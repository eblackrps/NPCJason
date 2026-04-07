import copy
import json
import os
from pathlib import Path
import tempfile

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
    def __init__(self, path, default_factory):
        self.path = Path(path)
        self.default_factory = default_factory

    def _read_unlocked(self):
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, dict):
                    return data
        except (FileNotFoundError, json.JSONDecodeError):
            pass
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
            temp_name = temp_handle.name
        os.replace(temp_name, self.path)

    def read(self):
        ensure_app_dirs()
        return self._read_unlocked()

    def update(self, mutator):
        ensure_app_dirs()
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        with lock_path.open("a+b") as lock_handle:
            _lock_file(lock_handle)
            try:
                data = self._read_unlocked()
                result = mutator(data)
                self._write_atomic(data)
                return result
            finally:
                _unlock_file(lock_handle)
