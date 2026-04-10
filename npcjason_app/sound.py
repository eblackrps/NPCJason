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
    "tricycle": [(0.04, 659), (0.03, 784), (0.03, 988)],
    "duck": [(0.05, 740), (0.04, 622)],
    "server_cart": [(0.04, 392), (0.04, 440), (0.04, 523)],
    "stress_ball": [(0.03, 392), (0.03, 330), (0.02, 294)],
    "coffee_mug": [(0.03, 523), (0.05, 659)],
    "keyboard_tap": [(0.01, 1175), (0.01, 1047), (0.01, 1319), (0.01, 988)],
    "rack_blink": [(0.03, 392), (0.02, 523), (0.02, 659)],
    "office_interaction": [(0.03, 784), (0.03, 988), (0.03, 1175)],
    "homelab_interaction": [(0.04, 349), (0.04, 440), (0.04, 523)],
    "network_interaction": [(0.03, 1047), (0.03, 1319), (0.03, 1568)],
    "responsible_interaction": [(0.04, 523), (0.04, 659), (0.05, 698)],
    "astronaut_interaction": [(0.03, 784), (0.05, 988), (0.04, 1175)],
    "state_curious": [(0.03, 698), (0.03, 784)],
    "state_smug": [(0.03, 523), (0.04, 659)],
    "state_busy": [(0.02, 988), (0.02, 784), (0.03, 1047)],
    "state_annoyed": [(0.02, 440), (0.02, 415), (0.03, 392)],
    "state_celebrating": [(0.03, 880), (0.03, 988), (0.04, 1319)],
    "state_confused": [(0.03, 622), (0.03, 554)],
    "state_sneaky": [(0.03, 523), (0.03, 587)],
    "state_exhausted": [(0.05, 349), (0.05, 294)],
    "scenario_busy_it_morning": [(0.02, 784), (0.02, 988), (0.03, 784)],
    "scenario_homelab_troubleshooting": [(0.04, 330), (0.04, 392), (0.04, 330)],
    "scenario_network_victory_lap": [(0.03, 784), (0.03, 1047), (0.04, 1319)],
    "scenario_responsible_adult_moment": [(0.03, 523), (0.03, 659), (0.03, 523)],
    "scenario_office_chaos": [(0.02, 466), (0.02, 415), (0.02, 466), (0.03, 523)],
    "scenario_orbital_desk_patrol": [(0.03, 784), (0.05, 932), (0.05, 1175)],
}
_STOP_SENTINEL = object()
DEFAULT_SOUND_CATEGORIES = {
    "speech": True,
    "toy": True,
    "state": True,
    "scenario": True,
}


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
        self.category_states = dict(DEFAULT_SOUND_CATEGORIES)
        self._asset_lock = threading.Lock()
        self._play_queue = queue.Queue(maxsize=8)
        self._worker = None
        self._stopped = False
        self._last_played_at_ms = {}
        ensure_app_dirs()

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)

    def set_volume(self, volume):
        self.volume = max(0, min(100, int(volume)))

    def set_categories(self, category_states):
        states = category_states if isinstance(category_states, dict) else {}
        self.category_states = {
            key: bool(states.get(key, default))
            for key, default in DEFAULT_SOUND_CATEGORIES.items()
        }

    def _ensure_asset(self, effect_name):
        effect_path = _effect_filename(effect_name, self.volume)
        if effect_path.exists():
            return effect_path
        with self._asset_lock:
            if not effect_path.exists():
                _build_wave_file(effect_path, SOUND_PATTERNS[effect_name], self.volume)
        return effect_path

    def play(self, effect_name, category="toy", throttle_ms=0, throttle_key=None):
        if self._stopped or not self.enabled or not HAS_WINSOUND or effect_name not in SOUND_PATTERNS:
            return
        category = str(category or "toy").strip() or "toy"
        if category in self.category_states and not self.category_states.get(category, True):
            return
        throttle_key = str(throttle_key or effect_name).strip() or str(effect_name)
        if int(throttle_ms or 0) > 0:
            now_ms = int(time.monotonic() * 1000)
            if now_ms - int(self._last_played_at_ms.get(throttle_key, 0)) < int(throttle_ms):
                return
            self._last_played_at_ms[throttle_key] = now_ms
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
    def has_effect(cls, effect_name):
        return str(effect_name) in SOUND_PATTERNS

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
