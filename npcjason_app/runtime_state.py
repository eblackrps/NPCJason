from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Dict, Optional, Set, Tuple


SCREENSHOT_TITLE_TOKENS = (
    "snipping tool",
    "snip & sketch",
    "screen snipping",
    "screenshot",
    "capture",
)


def quiet_hours_active(enabled, start_hour, end_hour, now=None):
    if not enabled:
        return False
    current_hour = time.localtime().tm_hour if now is None else int(getattr(now, "hour", now)) % 24
    if start_hour == end_hour:
        return True
    if start_hour < end_hour:
        return start_hour <= current_hour < end_hour
    return current_hour >= start_hour or current_hour < end_hour


def normalize_window_title(title):
    return " ".join(str(title or "").lower().split())


def is_screenshot_window_title(title):
    normalized = normalize_window_title(title)
    return any(token in normalized for token in SCREENSHOT_TITLE_TOKENS)


@dataclass
class SuppressionEntry:
    reason: str
    details: str = ""
    expires_at: Optional[float] = None

    def active(self, now):
        return self.expires_at is None or self.expires_at > now


@dataclass
class RuntimeSnapshot:
    initialized: bool
    startup_complete: bool
    running: bool
    paused: bool
    hidden: bool
    shutting_down: bool
    hidden_reason: str = ""
    manually_hidden: bool = False
    pause_reasons: Tuple[str, ...] = field(default_factory=tuple)
    active_suppressions: Tuple[str, ...] = field(default_factory=tuple)
    suppressed: bool = False
    screenshot_suppressed: bool = False
    fullscreen_suppressed: bool = False
    quiet_hours_suppressed: bool = False
    should_animate: bool = False
    should_move: bool = False
    should_speak: bool = False
    automatic_actions_allowed: bool = False


class RuntimeStateController:
    def __init__(self, logger=None, clock=None, screenshot_ttl_seconds=3.0):
        self.logger = logger
        self.clock = clock or time.monotonic
        self.screenshot_ttl_seconds = max(0.5, float(screenshot_ttl_seconds))
        self.initialized = False
        self.startup_complete = False
        self.running = False
        self.hidden = False
        self.hidden_reason = ""
        self.shutting_down = False
        self._pause_reasons: Set[str] = set()
        self._suppressions: Dict[str, SuppressionEntry] = {}

    def mark_initialized(self):
        self.initialized = True

    def mark_running(self):
        self.running = True
        self._pause_reasons.clear()
        self.startup_complete = True

    def begin_shutdown(self):
        self.shutting_down = True
        self.running = False

    def set_hidden(self, hidden):
        self.set_visibility(hidden, reason="manual" if hidden else "")

    def set_visibility(self, hidden, reason="manual"):
        self.hidden = bool(hidden)
        self.hidden_reason = str(reason or "") if self.hidden else ""

    def set_paused(self, paused):
        self.set_pause("manual", paused)

    def set_pause(self, reason, paused=True):
        reason = str(reason or "manual")
        if paused:
            if reason not in self._pause_reasons:
                self._pause_reasons.add(reason)
                self._log("info", f"Pause active: {reason}")
            return
        if reason in self._pause_reasons:
            self._pause_reasons.remove(reason)
            self._log("info", f"Pause cleared: {reason}")

    def clear_all_pauses(self):
        if not self._pause_reasons:
            return
        self._pause_reasons.clear()
        self._log("info", "All pause reasons cleared")

    def activate(self, reason, details="", ttl_seconds=None):
        expires_at = None
        if ttl_seconds is not None:
            expires_at = self.clock() + max(0.1, float(ttl_seconds))
        current = self._suppressions.get(reason)
        self._suppressions[reason] = SuppressionEntry(
            reason=reason,
            details=str(details or ""),
            expires_at=expires_at,
        )
        if current is None or current.details != details or current.expires_at != expires_at:
            self._log("info", f"Suppression active: {reason}" + (f" ({details})" if details else ""))

    def clear(self, reason):
        if self._suppressions.pop(reason, None) is not None:
            self._log("info", f"Suppression cleared: {reason}")

    def prune_expired(self):
        now = self.clock()
        expired = [reason for reason, entry in self._suppressions.items() if not entry.active(now)]
        for reason in expired:
            self._suppressions.pop(reason, None)
            self._log("info", f"Suppression expired: {reason}")
        return expired

    def update_quiet_hours(self, active):
        if active:
            self.activate("quiet_hours")
        else:
            self.clear("quiet_hours")

    def update_fullscreen(self, active):
        if active:
            self.activate("fullscreen")
        else:
            self.clear("fullscreen")

    def note_foreground_window(self, title):
        if is_screenshot_window_title(title):
            self.activate("screenshot", details=title, ttl_seconds=self.screenshot_ttl_seconds)
        else:
            self.clear("screenshot")

    def snapshot(self):
        self.prune_expired()
        suppressions = tuple(sorted(self._suppressions))
        suppressed = bool(suppressions)
        running = self.running and not self.shutting_down
        pause_reasons = tuple(sorted(self._pause_reasons))
        paused = bool(pause_reasons)
        should_animate = running and not self.hidden
        should_move = should_animate and not paused
        should_speak = should_move
        return RuntimeSnapshot(
            initialized=self.initialized,
            startup_complete=self.startup_complete,
            running=running,
            paused=paused,
            hidden=self.hidden,
            hidden_reason=self.hidden_reason,
            manually_hidden=self.hidden and self.hidden_reason in {"manual", "tray"},
            shutting_down=self.shutting_down,
            pause_reasons=pause_reasons,
            active_suppressions=suppressions,
            suppressed=suppressed,
            screenshot_suppressed="screenshot" in suppressions,
            fullscreen_suppressed="fullscreen" in suppressions,
            quiet_hours_suppressed="quiet_hours" in suppressions,
            should_animate=should_animate,
            should_move=should_move,
            should_speak=should_speak,
            automatic_actions_allowed=should_move and not suppressed,
        )

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message)
