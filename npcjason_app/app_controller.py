from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import tkinter as tk
import uuid
import webbrowser

from .animation import AnimationController
from .coordination import PresenceRecord, PetCoordinator
from .data.defaults import MOODS, default_settings, default_shared_state
from .diagnostics import DiagnosticsLogger
from .dialogue import DialogueLibrary, PET_CONVERSATIONS, render_template
from .paths import RESOURCE_DIR, SETTINGS_PATH, SHARED_STATE_PATH
from .pet_window import PetWindow
from .runtime_state import RuntimeStateController, is_screenshot_window_title, quiet_hours_active
from .scheduler import ManagedTkScheduler
from .settings_service import GlobalSettings, InstanceSettings, SettingsService
from .settings_window import SettingsWindow
from .skins import (
    BASE_PALETTE,
    build_skin_assets,
    load_skin_bundle,
)
from .sound import SoundManager
from .speech_history import SpeechHistory
from .startup import StartupManager
from .store import JsonStore, clamp
from .tray_controller import TrayActions, TrayController, TrayPetOption, TraySkinOption, TrayState
from .updates import UpdateChecker, UpdateCoordinator
from .version import APP_NAME, APP_VERSION
from .windows_events import (
    WindowsEventBridge,
    get_battery_snapshot,
    get_foreground_window_title,
    get_removable_drives,
    is_foreground_fullscreen,
)


RANDOM_SAYING_RANGE_MS = (3 * 60 * 1000, 8 * 60 * 1000)
MOOD_SHIFT_RANGE_MS = (4 * 60 * 1000, 7 * 60 * 1000)
PRESENCE_POLL_MS = 8000
CONVERSATION_POLL_MS = 2500
CONVERSATION_ATTEMPT_RANGE_MS = (45000, 90000)
COMMAND_POLL_MS = 1500
HOT_RELOAD_MS = 3000
UPDATE_CHECK_DELAY_MS = 10000
EDGE_SNAP_MARGIN = 28
SUPPRESSION_POLL_MS = 1200


class NPCJasonApp:
    def __init__(self, args):
        self.args = args
        self.pet_id = args.pet_id or "main"
        self.friend_of = args.friend_of

        self.logger = DiagnosticsLogger()
        self.logger.info(f"Starting {APP_NAME} v{APP_VERSION} on pet_id={self.pet_id}")

        self.window = PetWindow(logger=self.logger)
        self.root = self.window.root
        self.scheduler = ManagedTkScheduler(self.root, logger=self.logger)
        self.runtime_state = RuntimeStateController(logger=self.logger)
        self.animation = AnimationController()

        self.settings_store = JsonStore(SETTINGS_PATH, default_settings, logger=self.logger, store_name="settings")
        self.shared_state_store = JsonStore(
            SHARED_STATE_PATH,
            default_shared_state,
            logger=self.logger,
            store_name="shared-state",
        )
        self.startup_manager = StartupManager()
        self.settings_service = SettingsService(self.settings_store, self.startup_manager, logger=self.logger)
        self.coordinator = PetCoordinator(self.shared_state_store, self.pet_id, logger=self.logger)
        self.dialogue = DialogueLibrary()
        self.update_checker = UpdateChecker()
        self.update_coordinator = UpdateCoordinator(self.update_checker, logger=self.logger)
        self.sound_manager = SoundManager(True, 70, logger=self.logger)
        self.speech_history = SpeechHistory(logger=self.logger)

        self.settings_window = None
        self.event_bridge = None
        self.skin_load_errors = []
        self._last_logged_skin_warnings = ()
        self._last_logged_dialogue_warnings = ()
        self.last_active_window_title = get_foreground_window_title()
        self.last_battery_snapshot = get_battery_snapshot()
        self.removable_drives = get_removable_drives()
        self.was_battery_low = bool(
            self.last_battery_snapshot
            and self.last_battery_snapshot["percent"] <= 20
            and not self.last_battery_snapshot["charging"]
        )

        self.dragging = False
        self.drag_start_root = (0, 0)
        self.drag_pointer_offset = (0, 0)
        self.last_speech_at = 0.0
        self.last_conversation_started_at = 0.0
        self.seen_conversation_ids = []
        self.tray_controller = None

        self.canvas = self.window.canvas
        self._load_settings()
        self.window.bind_input_handlers(self._on_press, self._on_drag, self._on_release, self._on_right_click)
        self._apply_initial_position()

        self.scheduler.start()
        self._setup_native_events()
        self._setup_tray()

        self.window.draw_frame(self.active_frames["idle_open"], self.active_palette)
        self.runtime_state.mark_initialized()
        self.runtime_state.mark_running()
        self._publish_presence()
        self._start_runtime_loops()

        if self.friend_of:
            self.scheduler.schedule(
                "friend_greeting",
                1800,
                lambda: self._show_text("Co-op mode engaged.\nDesktop duty accepted."),
                owner="speech",
            )

        self.window.protocol("WM_DELETE_WINDOW", self._quit)

    def _load_settings(self):
        snapshot = self.settings_service.load(self.pet_id, requested_name=self.args.name)
        global_settings = snapshot.global_settings
        instance_settings = snapshot.instance_settings

        self.saved_window_x = instance_settings.x
        self.saved_window_y = instance_settings.y
        self.sound_enabled = bool(global_settings.sound_enabled)
        self.sound_volume = int(global_settings.sound_volume)
        self.auto_update_enabled = bool(global_settings.auto_update_enabled)
        self.event_reactions_enabled = bool(global_settings.event_reactions_enabled)
        self.quiet_hours_enabled = bool(global_settings.quiet_hours_enabled)
        self.quiet_start_hour = int(global_settings.quiet_start_hour)
        self.quiet_end_hour = int(global_settings.quiet_end_hour)
        self.quiet_when_fullscreen = bool(global_settings.quiet_when_fullscreen)
        self.auto_antics_enabled = bool(global_settings.auto_antics_enabled)
        self.auto_antics_min_minutes = int(global_settings.auto_antics_min_minutes)
        self.auto_antics_max_minutes = int(global_settings.auto_antics_max_minutes)
        self.auto_antics_dance_chance = int(global_settings.auto_antics_dance_chance)
        self.reaction_toggles = dict(global_settings.reaction_toggles)
        self.speech_history.load(
            recent=global_settings.recent_sayings,
            favorites=global_settings.favorite_templates,
        )
        self.pet_name = str(instance_settings.name)

        self.sound_manager.set_enabled(self.sound_enabled)
        self.sound_manager.set_volume(self.sound_volume)

        skin_bundle = load_skin_bundle()
        self.skins = skin_bundle["definitions"]
        self.skin_load_errors = skin_bundle["errors"]
        self._log_asset_warnings_if_changed()

        self.skin_key = instance_settings.skin
        if self.skin_key not in self.skins:
            self.skin_key = "jason"

        self.mood = instance_settings.mood
        if self.mood not in MOODS:
            self.mood = random.choice(list(MOODS.keys()))

        self._apply_skin_assets()
        self.animation.on_skin_changed()
        self._refresh_suppression_state()

    def _apply_skin_assets(self):
        assets = build_skin_assets(self.skins[self.skin_key])
        self.active_frames = assets["frames"]
        self.active_palette = dict(BASE_PALETTE)
        self.active_palette.update(assets["palette"])
        self.tray_colors = assets["tray"]

    def _apply_initial_position(self):
        default_x, default_y = self._default_window_position()
        start_x = self.args.x if self.args.x is not None else self.saved_window_x
        start_y = self.args.y if self.args.y is not None else self.saved_window_y
        if start_x is None:
            start_x = default_x
        if start_y is None:
            start_y = default_y
        self.window_x, self.window_y = self._clamp_window_position(start_x, start_y)
        self._apply_window_position(0)

    def _start_runtime_loops(self):
        self.scheduler.schedule_loop(
            "animation",
            self._animation_tick,
            initial_delay_ms=0,
            default_delay_ms=200,
            owner="animation",
        )
        self.scheduler.schedule_loop(
            "suppression_state",
            self._suppression_tick,
            initial_delay_ms=0,
            default_delay_ms=SUPPRESSION_POLL_MS,
            owner="runtime",
        )
        self.scheduler.schedule_loop(
            "presence",
            self._presence_heartbeat,
            initial_delay_ms=PRESENCE_POLL_MS,
            default_delay_ms=PRESENCE_POLL_MS,
            owner="coordination",
        )
        self.scheduler.schedule_loop(
            "conversation_poll",
            self._poll_conversations,
            initial_delay_ms=CONVERSATION_POLL_MS,
            default_delay_ms=CONVERSATION_POLL_MS,
            owner="coordination",
        )
        self.scheduler.schedule_loop(
            "command_poll",
            self._poll_commands,
            initial_delay_ms=COMMAND_POLL_MS,
            default_delay_ms=COMMAND_POLL_MS,
            owner="coordination",
        )
        self.scheduler.schedule_loop(
            "asset_reload",
            self._reload_assets_tick,
            initial_delay_ms=HOT_RELOAD_MS,
            default_delay_ms=HOT_RELOAD_MS,
            owner="assets",
        )
        self.scheduler.schedule_loop(
            "random_saying",
            self._random_saying_tick,
            initial_delay_ms=self._random_delay(RANDOM_SAYING_RANGE_MS),
            default_delay_ms=RANDOM_SAYING_RANGE_MS[0],
            owner="speech",
        )
        self.scheduler.schedule_loop(
            "mood_shift",
            self._rotate_mood,
            initial_delay_ms=self._random_delay(MOOD_SHIFT_RANGE_MS),
            default_delay_ms=MOOD_SHIFT_RANGE_MS[0],
            owner="behavior",
        )
        self.scheduler.schedule_loop(
            "conversation_attempt",
            self._maybe_start_conversation,
            initial_delay_ms=self._random_delay(CONVERSATION_ATTEMPT_RANGE_MS),
            default_delay_ms=CONVERSATION_ATTEMPT_RANGE_MS[0],
            owner="coordination",
        )
        self._schedule_auto_antics()
        if self.auto_update_enabled:
            self.scheduler.schedule(
                "auto_update_check",
                UPDATE_CHECK_DELAY_MS,
                self._auto_check_for_updates,
                owner="updates",
            )
        self.logger.info(f"Scheduled runtime jobs: {self.scheduler.describe_jobs()}")

    def _setup_native_events(self):
        self.event_bridge = WindowsEventBridge(
            self.root,
            on_usb_change=self._handle_usb_change_event,
            on_power_change=self._handle_power_change_event,
            on_foreground_change=self._handle_foreground_change_event,
            dispatch=self.scheduler.dispatch,
        )
        try:
            installed = self.event_bridge.install()
            if installed:
                self.logger.info("Installed Windows event bridge")
        except OSError:
            self.logger.exception("Failed to install Windows event bridge")
            self.event_bridge = None

    def _setup_tray(self):
        self.tray_controller = TrayController(
            APP_NAME,
            APP_VERSION,
            dispatch=self.scheduler.dispatch,
            state_provider=self._tray_state,
            actions=TrayActions(
                toggle_visibility=self._do_toggle_visibility,
                select_skin=self._set_skin,
                dance=lambda: self._trigger_dance(False),
                say=lambda: self._show_saying(True),
                repeat_last=self.repeat_last_saying,
                favorite_last=self.favorite_last_saying,
                random_favorite=self.say_random_favorite,
                summon_friend=self._summon_friend,
                dismiss_pet=self.dismiss_pet,
                open_settings=self._open_settings_window,
                toggle_auto_start=self._toggle_auto_start,
                toggle_sound=self._toggle_sound_enabled,
                bring_back=self.bring_back_on_screen,
                check_updates=self.check_for_updates_manual,
                open_releases=self._open_releases_page,
                open_data=self.open_data_folder,
                open_log=self.open_log_file,
                quit=self._do_quit,
            ),
            logger=self.logger,
        )
        self.tray_controller.start()

    def _suppression_tick(self):
        self._refresh_suppression_state()
        return SUPPRESSION_POLL_MS

    def _refresh_suppression_state(self):
        self.runtime_state.update_quiet_hours(self._is_quiet_hours_active())
        self.runtime_state.update_fullscreen(self._is_fullscreen_quiet())
        hidden = self._root_is_hidden()
        self.runtime_state.set_visibility(
            hidden,
            reason="tray" if hidden else "",
        )
        self.runtime_state.snapshot()

    def _root_is_hidden(self):
        return self.window.is_hidden()

    def skin_metadata(self, skin_key=None):
        key = skin_key or self.skin_key
        return dict(self.skins.get(key, {}))

    def _sayings_context(self, overrides=None):
        now = datetime.now()
        battery = self.last_battery_snapshot or get_battery_snapshot() or {}
        context = {
            "pet_name": self.pet_name,
            "mood": MOODS[self.mood]["label"],
            "mood_key": self.mood,
            "time": now.strftime("%I:%M %p").lstrip("0"),
            "date": now.strftime("%Y-%m-%d"),
            "active_window": self.last_active_window_title or "desktop",
            "battery_percent": battery.get("percent", "?"),
            "skin": self.skin_metadata().get("label", self.skin_key),
        }
        if overrides:
            context.update(overrides)
        return context

    def _is_quiet_hours_active(self):
        return quiet_hours_active(
            self.quiet_hours_enabled,
            self.quiet_start_hour,
            self.quiet_end_hour,
        )

    def _is_fullscreen_quiet(self):
        if not self.quiet_when_fullscreen:
            return False
        try:
            screen_w, screen_h = self.window.screen_size()
            return is_foreground_fullscreen(
                screen_w,
                screen_h,
            )
        except OSError:
            self.logger.exception("Fullscreen detection failed")
            return False

    def _automatic_actions_allowed(self):
        self._refresh_suppression_state()
        return self.runtime_state.snapshot().automatic_actions_allowed

    def _record_saying(self, template_text, rendered_text, source):
        self.speech_history.record(template_text, rendered_text, source)
        self._schedule_settings_save()

    def recent_saying_texts(self):
        return self.speech_history.recent_texts()

    def favorite_saying_texts(self):
        return self.speech_history.favorites()

    def favorite_last_saying(self):
        if self.speech_history.favorite_last():
            self._schedule_settings_save()

    def remove_favorite_saying(self, template_text):
        if self.speech_history.remove_favorite(template_text):
            self._schedule_settings_save()

    def repeat_last_saying(self):
        if not self.speech_history.last_record:
            return
        template = self.speech_history.last_record.template
        self._show_text(
            render_template(template, self._sayings_context()),
            source="repeat",
            template_text=template,
        )

    def say_random_favorite(self):
        template = self.speech_history.pick_random_favorite()
        if not template:
            self._show_text("No favorites yet.\nStar a line first.")
            return
        self._show_text(
            render_template(template, self._sayings_context()),
            source="favorite",
            template_text=template,
        )

    def _snap_position(self):
        self.window.snap_position(EDGE_SNAP_MARGIN)

    def _default_window_position(self):
        return self.window.default_position()

    def _clamp_window_position(self, x, y):
        return self.window.clamp_position(x, y)

    def _bring_back_on_screen(self):
        self.window_x, self.window_y = self._clamp_window_position(self.window_x, self.window_y)
        self._snap_position()
        self._apply_window_position(0)
        self._schedule_settings_save()
        self.window.ensure_topmost()

    def bring_back_on_screen(self):
        self._bring_back_on_screen()

    def _apply_window_position(self, offset_y):
        self.window.move_to(self.window_x, self.window_y, offset_y=offset_y)

    def _draw_frame(self, frame_data):
        self.window.draw_frame(frame_data, self.active_palette)

    def _render_pose(self, frame_key, offset_y=0):
        self.window.render_frame(self.active_frames[frame_key], self.active_palette, offset_y=offset_y)

    def _animation_tick(self):
        if self.is_quitting:
            return None
        snapshot = self.runtime_state.snapshot()
        if not snapshot.should_animate:
            return 220
        frame = self.animation.next_frame(self.mood)
        self._render_pose(frame.frame_key, frame.offset_y)
        return frame.delay_ms

    def _can_speak(self, min_gap_seconds=8):
        return (time.time() - self.last_speech_at) >= min_gap_seconds

    def _destroy_current_bubble(self):
        self.window.destroy_bubble()

    def _show_text(self, text, reveal_if_hidden=False, source="speech", template_text=None):
        if self.is_quitting:
            return False
        if self._root_is_hidden():
            if reveal_if_hidden:
                self.window.show()
                self.runtime_state.set_visibility(False)
            else:
                return False

        try:
            self.window.show_bubble(text)
        except tk.TclError:
            self.logger.exception("Failed to create speech bubble")
            return False

        self.last_speech_at = time.time()
        self.sound_manager.play("speech")
        self._record_saying(template_text or text, text, source)
        return True

    def _show_saying(self, reveal_if_hidden=False):
        template = random.choice(self.dialogue.ambient_pool(self.mood))
        rendered = render_template(template, self._sayings_context())
        return self._show_text(rendered, reveal_if_hidden, source="ambient", template_text=template)

    def _random_saying_tick(self):
        if (
            self._can_speak(20)
            and self.reaction_toggles.get("random_sayings", True)
            and self._automatic_actions_allowed()
        ):
            self._show_saying()
        return self._random_delay(RANDOM_SAYING_RANGE_MS)

    def _rotate_mood(self):
        if self.is_quitting:
            return None
        choices = [mood for mood in MOODS if mood != self.mood]
        self.mood = random.choice(choices)
        self._schedule_settings_save()
        self._refresh_tray()
        return self._random_delay(MOOD_SHIFT_RANGE_MS)

    def available_skin_keys(self):
        return sorted(self.skins.keys())

    def available_skin_labels(self):
        return {key: self.skins[key].get("label", key) for key in self.available_skin_keys()}

    def _set_skin(self, skin_key):
        if skin_key not in self.skins or skin_key == self.skin_key:
            return
        self.skin_key = skin_key
        self._apply_skin_assets()
        self.animation.on_skin_changed()
        if not self.animation.is_dancing:
            self._render_pose("idle_open", 0)
        self._schedule_settings_save()
        self._refresh_tray()

    def _toggle_sound_enabled(self):
        self.sound_enabled = not self.sound_enabled
        self.sound_manager.set_enabled(self.sound_enabled)
        self.logger.info(f"Sound enabled set to {self.sound_enabled}")
        self._schedule_settings_save()
        self._refresh_tray()

    def apply_settings(
        self,
        skin_key,
        sound_enabled,
        sound_volume,
        auto_start_enabled,
        auto_update_enabled,
        event_reactions_enabled,
        quiet_hours_enabled,
        quiet_start_hour,
        quiet_end_hour,
        quiet_when_fullscreen,
        auto_antics_enabled,
        auto_antics_min_minutes,
        auto_antics_max_minutes,
        auto_antics_dance_chance,
        pet_name,
        reaction_toggles,
    ):
        self.sound_enabled = bool(sound_enabled)
        self.sound_volume = clamp(int(sound_volume), 0, 100)
        self.auto_update_enabled = bool(auto_update_enabled)
        self.event_reactions_enabled = bool(event_reactions_enabled)
        self.quiet_hours_enabled = bool(quiet_hours_enabled)
        self.quiet_start_hour = clamp(int(quiet_start_hour), 0, 23)
        self.quiet_end_hour = clamp(int(quiet_end_hour), 0, 23)
        self.quiet_when_fullscreen = bool(quiet_when_fullscreen)
        self.auto_antics_enabled = bool(auto_antics_enabled)
        self.auto_antics_min_minutes = max(1, int(auto_antics_min_minutes))
        self.auto_antics_max_minutes = max(1, int(auto_antics_max_minutes))
        self.auto_antics_dance_chance = clamp(int(auto_antics_dance_chance), 0, 100)
        self.pet_name = str(pet_name or self.pet_name)
        self.reaction_toggles = dict(default_settings()["global"]["reactions"])
        self.reaction_toggles.update(reaction_toggles)
        self.sound_manager.set_enabled(self.sound_enabled)
        self.sound_manager.set_volume(self.sound_volume)
        try:
            self.startup_manager.set_enabled(auto_start_enabled)
        except OSError:
            self.logger.exception("Failed to update startup entry")
            self._show_text("Startup setting failed.\nSee log for details.")
        self._set_skin(skin_key)
        self._schedule_auto_antics()
        self._refresh_suppression_state()
        if self.auto_update_enabled:
            self.scheduler.schedule(
                "auto_update_check",
                UPDATE_CHECK_DELAY_MS,
                self._auto_check_for_updates,
                owner="updates",
            )
        else:
            self.scheduler.cancel("auto_update_check")
        self._publish_presence()
        self._refresh_tray()
        self.logger.info("Applied settings")
        self._schedule_settings_save()

    def preview_sound(self, volume, enabled):
        SoundManager.preview_effect("speech", enabled=enabled, volume=volume, logger=self.logger)

    def _random_auto_antics_delay(self):
        minimum = max(1, min(self.auto_antics_min_minutes, self.auto_antics_max_minutes))
        maximum = max(minimum, max(self.auto_antics_min_minutes, self.auto_antics_max_minutes))
        return random.randint(minimum * 60 * 1000, maximum * 60 * 1000)

    def _schedule_auto_antics(self):
        self.scheduler.cancel("auto_antics")
        if not self.auto_antics_enabled or self.is_quitting:
            return
        self.scheduler.schedule_loop(
            "auto_antics",
            self._auto_antics_tick,
            initial_delay_ms=self._random_auto_antics_delay(),
            default_delay_ms=self._random_auto_antics_delay(),
            owner="behavior",
        )

    def _auto_antics_tick(self):
        if self.is_quitting:
            return None
        if self.auto_antics_enabled and self._automatic_actions_allowed() and self._can_speak(14):
            if random.randint(1, 100) <= self.auto_antics_dance_chance:
                self._trigger_dance(show_saying=False)
            else:
                self._show_saying()
        return self._random_auto_antics_delay()

    def reload_dialogue(self):
        self.dialogue.reload_if_needed(force=True)
        self._log_asset_warnings_if_changed()
        self.logger.info("Reloaded dialogue packs")

    def export_settings(self, path):
        self._save_settings()
        self.settings_service.export_to_file(path)
        self.logger.info(f"Exported settings to {path}")

    def import_settings(self, path):
        self.settings_service.import_from_file(path)
        self._load_settings()
        default_x, default_y = self._default_window_position()
        self.window_x, self.window_y = self._clamp_window_position(
            self.saved_window_x if self.saved_window_x is not None else default_x,
            self.saved_window_y if self.saved_window_y is not None else default_y,
        )
        self._bring_back_on_screen()
        self._schedule_auto_antics()
        if not self.animation.is_dancing:
            self._render_pose("idle_open", 0)
        self._refresh_tray()
        self._publish_presence()
        self.logger.info(f"Imported settings from {path}")

    def reset_settings(self):
        self.settings_service.reset()
        self._load_settings()
        default_x, default_y = self._default_window_position()
        self.window_x, self.window_y = self._clamp_window_position(default_x, default_y)
        self._bring_back_on_screen()
        self._schedule_auto_antics()
        if not self.animation.is_dancing:
            self._render_pose("idle_open", 0)
        self._refresh_tray()
        self._publish_presence()
        self.logger.info("Reset settings to defaults")

    def open_data_folder(self):
        self.logger.open_data_folder()

    def open_log_file(self):
        self.logger.open_log_file()

    def _open_settings_window(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return
        self.settings_window = SettingsWindow(self)

    def _reload_assets_tick(self):
        if self.is_quitting:
            return None

        self.dialogue.reload_if_needed()
        skin_bundle = load_skin_bundle()
        reloaded_skins = skin_bundle["definitions"]
        reloaded_errors = skin_bundle["errors"]
        if reloaded_skins != self.skins or reloaded_errors != self.skin_load_errors:
            self.skins = reloaded_skins
            self.skin_load_errors = reloaded_errors
            if self.skin_key not in self.skins:
                self.skin_key = "jason"
            self._apply_skin_assets()
            if not self.animation.is_dancing:
                self._render_pose("idle_open", 0)
            self._refresh_tray()
        self._log_asset_warnings_if_changed()

        return HOT_RELOAD_MS

    def _log_asset_warnings_if_changed(self):
        current_skin_warnings = tuple(self.skin_load_errors)
        if current_skin_warnings and current_skin_warnings != self._last_logged_skin_warnings:
            self.logger.warning("Skin load warnings: " + "; ".join(current_skin_warnings))
        self._last_logged_skin_warnings = current_skin_warnings

        current_dialogue_warnings = tuple(self.dialogue.warnings)
        if current_dialogue_warnings and current_dialogue_warnings != self._last_logged_dialogue_warnings:
            self.logger.warning("Dialogue warnings: " + "; ".join(current_dialogue_warnings))
        self._last_logged_dialogue_warnings = current_dialogue_warnings

    def _on_press(self, event):
        self.dragging = False
        self.drag_start_root = (event.x_root, event.y_root)
        self.drag_pointer_offset = (
            event.x_root - self.root.winfo_x(),
            event.y_root - self.root.winfo_y(),
        )
        self.runtime_state.set_pause("drag", False)

    def _on_drag(self, event):
        delta_x = abs(event.x_root - self.drag_start_root[0])
        delta_y = abs(event.y_root - self.drag_start_root[1])
        if not self.dragging and max(delta_x, delta_y) < 3:
            return
        self.dragging = True
        self.runtime_state.set_pause("drag", True)
        actual_x = event.x_root - self.drag_pointer_offset[0]
        actual_y = event.y_root - self.drag_pointer_offset[1]
        self.window_x, self.window_y = self._clamp_window_position(actual_x, actual_y)
        self._apply_window_position(0)

    def _on_release(self, _event):
        self.runtime_state.set_pause("drag", False)
        if self.dragging:
            self.dragging = False
            self._snap_position()
            self._bring_back_on_screen()
            self._schedule_settings_save()
            self._publish_presence()
            return
        self._trigger_dance(show_saying=True)

    def _trigger_dance(self, show_saying=False):
        self.animation.start_dance()
        self.sound_manager.play("dance")
        if show_saying:
            self._show_saying()

    def _active_other_instances(self):
        return self.coordinator.active_other_instances()

    def list_active_pets(self):
        entries = []
        for pet_id, info in self._active_other_instances():
            description = (
                f"{info.get('name', pet_id)} | "
                f"{self.skins.get(info.get('skin', 'jason'), {}).get('label', info.get('skin', 'jason'))} | "
                f"{info.get('mood', 'happy')}"
            )
            entries.append((pet_id, description))
        return entries

    def _friend_spawn_position(self):
        return self.window.friend_spawn_position()

    def _summon_friend(self):
        friend_id = f"friend-{uuid.uuid4().hex[:6]}"
        friend_x, friend_y = self._friend_spawn_position()
        friend_name = f"{self.pet_name} Friend"
        if getattr(sys, "frozen", False):
            command = [
                sys.executable,
                "--pet-id",
                friend_id,
                "--x",
                str(friend_x),
                "--y",
                str(friend_y),
                "--friend-of",
                self.pet_id,
                "--name",
                friend_name,
            ]
        else:
            command = [
                sys.executable,
                str(Path(RESOURCE_DIR / "npcjason.py").resolve()),
                "--pet-id",
                friend_id,
                "--x",
                str(friend_x),
                "--y",
                str(friend_y),
                "--friend-of",
                self.pet_id,
                "--name",
                friend_name,
            ]

        try:
            subprocess.Popen(
                command,
                cwd=str(RESOURCE_DIR),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self.logger.info(f"Spawned friend pet_id={friend_id}")
        except OSError:
            self.logger.exception("Failed to spawn friend pet")
            self._show_text("Summon spell fizzled.\nCould not launch a friend.")

    def summon_friend_from_settings(self):
        self._summon_friend()

    def dismiss_pet(self, pet_id):
        if pet_id and pet_id != self.pet_id:
            self.coordinator.enqueue_command(pet_id, "quit")
            self.logger.info(f"Queued dismiss for pet_id={pet_id}")

    def dismiss_all_friends(self):
        for pet_id, _info in self._active_other_instances():
            self.coordinator.enqueue_command(pet_id, "quit")

    def _publish_presence(self):
        self.coordinator.publish_presence(
            PresenceRecord(
                pet_id=self.pet_id,
                name=self.pet_name,
                skin=self.skin_key,
                mood=self.mood,
                x=self.window_x,
                y=self.window_y,
                friend_of=self.friend_of,
                pid=os.getpid(),
            )
        )

    def _presence_heartbeat(self):
        if self.is_quitting:
            return None
        self._publish_presence()
        self._refresh_tray()
        return PRESENCE_POLL_MS

    def _maybe_start_conversation(self):
        if self.is_quitting:
            return None
        active_partners = self._active_other_instances()
        now = time.time()
        if (
            active_partners
            and self._can_speak(15)
            and self.reaction_toggles.get("pet_chat", True)
            and self._automatic_actions_allowed()
            and (now - self.last_conversation_started_at) >= 35
            and random.random() < 0.55
        ):
            partner_id, partner_info = random.choice(active_partners)
            line_self, line_partner = random.choice(PET_CONVERSATIONS)
            self_context = self._sayings_context(
                {
                    "other_pet_name": partner_info.get("name", partner_id),
                }
            )
            partner_context = {
                "pet_name": partner_info.get("name", partner_id),
                "other_pet_name": self.pet_name,
            }
            conversation_id = uuid.uuid4().hex
            conversation = {
                "id": conversation_id,
                "created_at": now,
                "participants": [self.pet_id, partner_id],
                "lines": {
                    self.pet_id: render_template(line_self, self_context),
                    partner_id: render_template(line_partner, partner_context),
                },
            }
            self.coordinator.add_conversation(conversation)
            self.seen_conversation_ids.append(conversation_id)
            self.last_conversation_started_at = now
            self._show_text(
                conversation["lines"][self.pet_id],
                source="pet-chat",
                template_text=line_self,
            )

        return self._random_delay(CONVERSATION_ATTEMPT_RANGE_MS)

    def _poll_conversations(self):
        if self.is_quitting:
            return None

        for conversation in self.coordinator.pending_conversations(self.seen_conversation_ids):
            conversation_id = conversation.get("id")
            line = conversation.get("lines", {}).get(self.pet_id)
            if not line:
                continue
            self.seen_conversation_ids.append(conversation_id)
            self.seen_conversation_ids = self.seen_conversation_ids[-64:]
            if self._can_speak(4):
                self._show_text(line, source="pet-chat", template_text=line)

        return CONVERSATION_POLL_MS

    def _poll_commands(self):
        if self.is_quitting:
            return None

        actions = self.coordinator.consume_commands()
        if "quit" in actions:
            self._do_quit()
            return None
        return COMMAND_POLL_MS

    def _handle_usb_change_event(self):
        current_drives = get_removable_drives()
        if (
            not self.event_reactions_enabled
            or not self.reaction_toggles.get("usb", True)
            or not self._can_speak(10)
            or not self._automatic_actions_allowed()
        ):
            self.removable_drives = current_drives
            return
        new_drives = sorted(current_drives - self.removable_drives)
        if new_drives:
            drive_label = new_drives[0].rstrip("\\")
            self._show_text(
                self.dialogue.format_event_text("usb", label=drive_label, **self._sayings_context()),
                source="usb",
            )
        self.removable_drives = current_drives

    def _handle_power_change_event(self):
        if not self.event_reactions_enabled or not self.reaction_toggles.get("battery", True):
            return
        battery = get_battery_snapshot()
        self.last_battery_snapshot = battery
        if not battery:
            return
        is_low = battery["percent"] <= 20 and not battery["charging"]
        if is_low and not self.was_battery_low and self._can_speak(12) and self._automatic_actions_allowed():
            self._show_text(
                self.dialogue.format_event_text(
                    "battery_low",
                    percent=battery["percent"],
                    **self._sayings_context({"battery_percent": battery["percent"]}),
                ),
                source="battery",
            )
        self.was_battery_low = is_low

    def _trim_window_title(self, title):
        compact = " ".join(title.split())
        if len(compact) > 36:
            return compact[:33].rstrip() + "..."
        return compact

    def _handle_foreground_change_event(self, title):
        self.last_active_window_title = title
        self.runtime_state.note_foreground_window(title)
        self._refresh_suppression_state()
        if is_screenshot_window_title(title):
            self.logger.info(f"Foreground screenshot/capture window detected: {title}")
            return
        if not self.event_reactions_enabled:
            return
        if title in {"", APP_NAME, "Program Manager"} or not self.reaction_toggles.get("focus", True):
            return
        if self._can_speak(16) and random.random() < 0.4 and self._automatic_actions_allowed():
            trimmed = self._trim_window_title(title)
            self._show_text(
                self.dialogue.format_event_text(
                    "window_focus",
                    title=trimmed,
                    **self._sayings_context({"active_window": trimmed}),
                ),
                source="focus",
            )

    def _auto_check_for_updates(self):
        if self.is_quitting or not self.auto_update_enabled:
            return
        self.update_coordinator.request_check(
            self._on_update_check_complete,
            dispatcher=self.scheduler.dispatch,
            manual=False,
        )

    def check_for_updates_manual(self):
        started = self.update_coordinator.request_check(
            self._on_update_check_complete,
            dispatcher=self.scheduler.dispatch,
            manual=True,
        )
        if not started and not self.is_quitting:
            self._show_text("Update check already running.\nHang tight.")

    def _on_update_check_complete(self, result, error, manual=False):
        if self.is_quitting:
            return
        prompt = self.update_coordinator.build_prompt(
            result,
            error,
            manual=manual,
            updates_enabled=self.reaction_toggles.get("updates", True),
            automatic_actions_allowed=self._automatic_actions_allowed(),
        )
        if prompt.kind == "error":
            self.logger.error(f"Update check failed: {error}")
            self._show_text("Update check failed.\nTry again in a bit.")
            return
        if prompt.kind == "none":
            return
        if prompt.kind == "available":
            self._show_text(
                self.dialogue.format_event_text("update", version=prompt.version, **self._sayings_context()),
                source="update",
            )
        elif prompt.kind == "up_to_date":
            self._show_text(f"Already on the latest build.\nVersion {APP_VERSION}")

    def _open_releases_page(self):
        webbrowser.open(self.update_checker.latest_release_url())

    def _on_right_click(self, event):
        menu = tk.Menu(
            self.root,
            tearoff=0,
            bg="#1a1a2e",
            fg="#fef9e7",
            activebackground="#3a86c8",
            activeforeground="#ffffff",
            font=("Consolas", 10),
        )
        menu.add_command(label=f"Mood: {MOODS[self.mood]['label']}", state="disabled")
        menu.add_command(label=f"Name: {self.pet_name}", state="disabled")
        menu.add_command(label="Dance!", command=lambda: self._trigger_dance(True))
        menu.add_command(label="Say Something", command=self._show_saying)
        menu.add_command(label="Repeat Last Saying", command=self.repeat_last_saying)
        menu.add_command(label="Favorite Last Saying", command=self.favorite_last_saying)
        menu.add_command(label="Random Favorite", command=self.say_random_favorite)
        menu.add_command(label="Summon a Friend", command=self._summon_friend)
        menu.add_command(label="Bring Back On Screen", command=self.bring_back_on_screen)
        menu.add_command(label="Settings", command=self._open_settings_window)

        skins_menu = tk.Menu(menu, tearoff=0, bg="#1a1a2e", fg="#fef9e7")
        selected_skin = tk.StringVar(value=self.skin_key)
        for skin_key, skin_data in sorted(self.skins.items()):
            skins_menu.add_radiobutton(
                label=skin_data.get("label", skin_key),
                value=skin_key,
                variable=selected_skin,
                command=lambda chosen=skin_key: self._set_skin(chosen),
            )
        menu.add_cascade(label="Choose Skin", menu=skins_menu)
        menu.add_checkbutton(
            label="Sound Effects",
            onvalue=True,
            offvalue=False,
            variable=tk.BooleanVar(value=self.sound_enabled),
            command=self._toggle_sound_enabled,
        )
        menu.add_command(label="Dismiss All Friends", command=self.dismiss_all_friends)
        menu.add_command(label="Check for Updates", command=self.check_for_updates_manual)
        menu.add_command(label="Open Data Folder", command=self.open_data_folder)
        menu.add_command(label="Open Log File", command=self.open_log_file)
        menu.add_separator()
        menu.add_command(label="Quit NPCJason", command=self._quit)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _tray_state(self):
        return TrayState(
            pet_name=self.pet_name,
            mood_label=MOODS[self.mood]["label"],
            skin_key=self.skin_key,
            sound_enabled=self.sound_enabled,
            auto_start_enabled=self.startup_manager.is_enabled(),
            skin_options=[
                TraySkinOption(key=skin_key, label=skin_data.get("label", skin_key))
                for skin_key, skin_data in sorted(self.skins.items())
            ],
            pets=[
                TrayPetOption(pet_id=pet_id, label=description)
                for pet_id, description in self.list_active_pets()
            ],
            tray_colors=dict(self.tray_colors),
        )

    def _refresh_tray(self):
        if not self.tray_controller:
            return
        self.tray_controller.refresh()

    def _do_toggle_visibility(self):
        if self._root_is_hidden():
            self.window.show()
            self.runtime_state.set_visibility(False)
        else:
            self._destroy_current_bubble()
            self.window.hide()
            self.runtime_state.set_visibility(True, reason="tray")
        self._refresh_suppression_state()

    def _toggle_auto_start(self):
        try:
            self.startup_manager.set_enabled(not self.startup_manager.is_enabled())
        except OSError:
            self.logger.exception("Failed to toggle startup setting")
            self._show_text("Could not update startup.\nSee log for details.")
            return
        self._schedule_settings_save()
        self._refresh_tray()

    def _schedule_settings_save(self, delay_ms=350):
        if self.is_quitting:
            return
        self.scheduler.schedule("settings_save", delay_ms, self._save_settings, owner="settings")

    def _current_global_settings(self):
        return GlobalSettings(
            sound_enabled=self.sound_enabled,
            sound_volume=self.sound_volume,
            auto_update_enabled=self.auto_update_enabled,
            event_reactions_enabled=self.event_reactions_enabled,
            quiet_hours_enabled=self.quiet_hours_enabled,
            quiet_start_hour=self.quiet_start_hour,
            quiet_end_hour=self.quiet_end_hour,
            quiet_when_fullscreen=self.quiet_when_fullscreen,
            auto_antics_enabled=self.auto_antics_enabled,
            auto_antics_min_minutes=self.auto_antics_min_minutes,
            auto_antics_max_minutes=self.auto_antics_max_minutes,
            auto_antics_dance_chance=self.auto_antics_dance_chance,
            reaction_toggles=dict(self.reaction_toggles),
            favorite_templates=list(self.speech_history.favorites()),
            recent_sayings=list(self.speech_history.recent()),
        )

    def _current_instance_settings(self):
        return InstanceSettings(
            x=self.window_x,
            y=self.window_y,
            skin=self.skin_key,
            mood=self.mood,
            name=self.pet_name,
        )

    def _save_settings(self):
        try:
            self.settings_service.save(
                self.pet_id,
                self._current_global_settings(),
                self._current_instance_settings(),
            )
        except OSError:
            self.logger.exception("Failed to save settings")

    def _quit(self, icon=None, menu_item=None):
        if self.scheduler.on_ui_thread():
            self._do_quit()
            return
        self.scheduler.dispatch(self._do_quit)

    def _do_quit(self):
        if self.is_quitting:
            return
        self.runtime_state.begin_shutdown()
        self.scheduler.shutdown()
        self._destroy_current_bubble()

        self._save_settings()
        try:
            self.coordinator.unregister_presence()
        except OSError:
            self.logger.exception("Failed to unregister pet presence")

        if self.event_bridge:
            try:
                self.event_bridge.uninstall()
            except OSError:
                self.logger.exception("Failed to uninstall Windows event bridge")

        if self.tray_controller:
            self.tray_controller.stop()
        self.sound_manager.shutdown()

        self.logger.info(f"Stopping {APP_NAME} pet_id={self.pet_id}")
        try:
            self.window.destroy()
        except tk.TclError:
            self.logger.exception("Failed to destroy Tk root window cleanly")

    @property
    def is_quitting(self):
        return self.runtime_state.shutting_down

    @property
    def window_x(self):
        return self.window.position_x

    @window_x.setter
    def window_x(self, value):
        self.window.position_x = int(value)

    @property
    def window_y(self):
        return self.window.position_y

    @window_y.setter
    def window_y(self, value):
        self.window.position_y = int(value)

    def run(self):
        self.root.mainloop()

    @property
    def last_render_record(self):
        if not self.speech_history.last_record:
            return None
        return self.speech_history.last_record.as_dict()

    @staticmethod
    def _random_delay(delay_range):
        return random.randint(*delay_range)


def parse_args(argv):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--pet-id", default="main")
    parser.add_argument("--x", type=int)
    parser.add_argument("--y", type=int)
    parser.add_argument("--friend-of")
    parser.add_argument("--name")
    args, _unknown = parser.parse_known_args(argv)
    return args
