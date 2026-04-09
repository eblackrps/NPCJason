import math
from pathlib import Path
import queue
import struct
import threading
import time
import wave

from .paths import SOUNDS_CACHE_DIR, ensure_app_dirs

try:
    import winsound

    HAS_WINSOUND = True
except ImportError:
    winsound = None
    HAS_WINSOUND = False


SOUND_PATTERNS = {
    "speech": [(0.04, 880), (0.03, 660)],
    "dance": [(0.05, 523), (0.05, 659), (0.07, 784)],
}
_STOP_SENTINEL = object()


def _effect_filename(effect_name, volume):
    return SOUNDS_CACHE_DIR / f"{effect_name}-v{int(volume):03d}.wav"


def _build_wave_file(path, pattern, volume):
    sample_rate = 22050
    amplitude = int(32767 * max(0.0, min(1.0, volume / 100.0)) * 0.75)
    frames = []

    for duration, frequency in pattern:
        total_samples = max(1, int(sample_rate * duration))
        for index in range(total_samples):
            envelope = 1.0 - (index / total_samples) * 0.35
            sample = int(
                amplitude
                * envelope
                * math.sin(2.0 * math.pi * frequency * index / sample_rate)
            )
            frames.append(struct.pack("<h", sample))
        silence_samples = int(sample_rate * 0.012)
        frames.extend(struct.pack("<h", 0) for _ in range(silence_samples))

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"".join(frames))


class SoundManager:
    def __init__(self, enabled=True, volume=70, logger=None):
        self.enabled = bool(enabled)
        self.volume = int(volume)
        self.logger = logger
        self._asset_lock = threading.Lock()
        self._play_queue = queue.Queue(maxsize=8)
        self._worker = None
        self._stopped = False
        ensure_app_dirs()

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)

    def set_volume(self, volume):
        self.volume = max(0, min(100, int(volume)))

    def _ensure_asset(self, effect_name):
        effect_path = _effect_filename(effect_name, self.volume)
        if effect_path.exists():
            return effect_path
        with self._asset_lock:
            if not effect_path.exists():
                _build_wave_file(effect_path, SOUND_PATTERNS[effect_name], self.volume)
        return effect_path

    def play(self, effect_name):
        if self._stopped or not self.enabled or not HAS_WINSOUND or effect_name not in SOUND_PATTERNS:
            return
        self._ensure_worker_started()
        if self._play_queue.full():
            try:
                self._play_queue.get_nowait()
            except queue.Empty:
                pass
        try:
            self._play_queue.put_nowait(effect_name)
        except queue.Full:
            self._log("warning", "sound queue full; dropping effect")

    def _ensure_worker_started(self):
        if self._worker and self._worker.is_alive():
            return
        self._stopped = False
        self._worker = threading.Thread(target=self._play_worker_loop, daemon=True)
        self._worker.start()

    def _play_worker_loop(self):
        while True:
            effect_name = self._play_queue.get()
            if effect_name is _STOP_SENTINEL:
                return
            try:
                effect_path = self._ensure_asset(effect_name)
                winsound.PlaySound(
                    str(effect_path),
                    winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
                )
            except (RuntimeError, OSError):
                self._log("exception", "sound playback failed")
            time.sleep(0.01)

    def shutdown(self):
        self._stopped = True
        if not self._worker or not self._worker.is_alive():
            return
        try:
            self._play_queue.put_nowait(_STOP_SENTINEL)
        except queue.Full:
            try:
                self._play_queue.get_nowait()
            except queue.Empty:
                pass
            self._play_queue.put_nowait(_STOP_SENTINEL)

    @classmethod
    def preview_effect(cls, effect_name, enabled=True, volume=70, logger=None):
        if not enabled or not HAS_WINSOUND or effect_name not in SOUND_PATTERNS:
            return False
        manager = cls(enabled=enabled, volume=volume, logger=logger)
        try:
            effect_path = manager._ensure_asset(effect_name)
            winsound.PlaySound(
                str(effect_path),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
            return True
        except (RuntimeError, OSError):
            manager._log("exception", "sound preview failed")
            return False

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message)
