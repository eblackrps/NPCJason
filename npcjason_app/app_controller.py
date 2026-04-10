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
from .companions import CompanionManager
from .coordination import PresenceRecord, PetCoordinator
from .data.defaults import MOODS, default_settings, default_shared_state
from .desk_items import DeskItemManager
from .diagnostics import DiagnosticsLogger
from .dialogue import DialogueLibrary, PET_CONVERSATIONS, FollowUpQuote, render_template
from .movement import MovementController
from .notifications import pick_notification_reaction
from .paths import RESOURCE_DIR, SETTINGS_PATH, SHARED_STATE_PATH
from .pet_window import PetWindow
from .personality import PersonalityController
from .rare_events import RareEventManager
from .runtime_state import RuntimeStateController, is_screenshot_window_title, quiet_hours_active
from .scenarios import ScenarioManager
from .scheduler import ManagedTkScheduler
from .seasonal import SeasonalModeManager
from .settings_service import GlobalSettings, InstanceSettings, SettingsService
from .settings_window import SettingsWindow
from .skins import (
    BASE_PALETTE,
    CANVAS_H,
    CANVAS_W,
    build_skin_assets,
    load_skin_bundle,
)
from .sound import SoundManager
from .speech_history import SpeechHistory
from .startup import StartupManager
from .store import JsonStore, clamp
from .toys import ToyManager
from .tray_controller import (
    TrayCompanionInteractionOption,
    TrayCompanionOption,
    TrayDeskItemOption,
    TrayActions,
    TrayController,
    TrayPetOption,
    TrayQuotePackOption,
    TrayScenarioOption,
    TraySeasonOption,
    TraySkinOption,
    TrayState,
    TrayToyOption,
)
from .unlocks import UnlockManager
from .updates import UpdateChecker, UpdateCoordinator
from .version import APP_NAME, APP_VERSION
from .title_humor import classify_window_title
from .windows_events import (
    WindowsEventBridge,
    get_battery_snapshot,
    get_foreground_window_title,
    get_removable_drives,
    is_foreground_fullscreen,
)
from .windows_platform import DesktopBounds


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
RARE_EVENT_RANGE_MS = (9 * 60 * 1000, 16 * 60 * 1000)
PERSONALITY_TICK_RANGE_MS = (3500, 6500)
MOVEMENT_TICK_MS = 140
SCENARIO_TICK_MS = 150
CONTINUITY_TICK_MS = 60 * 1000
IDLE_MICRO_ACTION_RANGE_MS = (14 * 1000, 28 * 1000)


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
        self.movement = MovementController(logger=self.logger)
        self.personality = PersonalityController(logger=self.logger)
        self.companion_manager = CompanionManager(self.root, logger=self.logger)
        self.toy_manager = ToyManager(self.root, logger=self.logger)
        self.desk_item_manager = DeskItemManager(self.root, logger=self.logger)
        self.rare_event_manager = RareEventManager(logger=self.logger)
        self.scenario_manager = ScenarioManager(logger=self.logger)
        self.unlock_manager = UnlockManager(logger=self.logger)
        self.seasonal_manager = SeasonalModeManager()

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
        self.skin_tags = []
        self.skin_sound_set = None
        self.skin_quote_affinity = {}
        self.skin_accessory_offsets = {}
        self.skin_capabilities = {}
        self.quote_pack_states = {}
        self.rare_events_enabled = True
        self.chaos_mode = False
        self.sound_categories = {}
        self.movement_enabled = True
        self.companion_enabled = True
        self.selected_companion_key = "mouse"
        self.activity_level = "normal"
        self.quote_frequency = "normal"
        self.companion_frequency = "normal"
        self.unlocks_enabled = True
        self.seasonal_mode_override = "auto"
        self.last_active_season = ""
        self.favorite_skin_keys = []
        self.favorite_toy_keys = []
        self.favorite_scenario_keys = []
        self.favorite_quote_pack_keys = []
        self.last_scenario_key = ""
        self.recent_scenario_keys = []
        self.last_dance_routine_key = ""
        self._comedy_bias = {"contexts": [], "categories": [], "packs": [], "render": {}, "until_ms": 0, "label": ""}
        self._last_title_joke_at = 0.0
        self._last_title_reaction_key = ""
        self._ride_origin_position = None
        self._last_notification_reaction_at = 0.0
        self._last_notification_reaction_key = ""
        self._last_idle_micro_action_key = ""
        self._last_idle_micro_action_at = 0.0
        self._speech_serial = 0

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
        self._record_discovery_progress("launches", 1, schedule_save=False)
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
        self.sound_categories = dict(global_settings.sound_categories)
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
        self.rare_events_enabled = bool(global_settings.rare_events_enabled)
        self.chaos_mode = bool(global_settings.chaos_mode)
        self.movement_enabled = bool(global_settings.movement_enabled)
        self.companion_enabled = bool(global_settings.companion_enabled)
        self.selected_companion_key = str(global_settings.selected_companion or "mouse")
        self.activity_level = str(global_settings.activity_level or "normal")
        self.quote_frequency = str(global_settings.quote_frequency or "normal")
        self.companion_frequency = str(global_settings.companion_frequency or "normal")
        self.unlocks_enabled = bool(global_settings.unlocks_enabled)
        self.seasonal_mode_override = str(global_settings.seasonal_mode_override or "auto")
        self.last_active_season = str(global_settings.last_active_season or "")
        self.reaction_toggles = dict(global_settings.reaction_toggles)
        self.quote_pack_states = dict(global_settings.quote_pack_states)
        self.favorite_skin_keys = list(global_settings.favorite_skins)
        self.favorite_toy_keys = list(global_settings.favorite_toys)
        self.favorite_scenario_keys = list(global_settings.favorite_scenarios)
        self.favorite_quote_pack_keys = list(global_settings.favorite_quote_packs)
        self.recent_scenario_keys = list(global_settings.recent_scenarios)
        self.speech_history.load(
            recent=global_settings.recent_sayings,
            favorites=global_settings.favorite_templates,
        )
        self.pet_name = str(instance_settings.name)
        self.last_scenario_key = str(instance_settings.last_scenario or "")
        self.personality.load(instance_settings.personality_state)
        self.unlock_manager.load(
            enabled=self.unlocks_enabled,
            unlocked_skins=global_settings.unlocked_skins,
            unlocked_toys=global_settings.unlocked_toys,
            unlocked_scenarios=global_settings.unlocked_scenarios,
            unlocked_quote_packs=global_settings.unlocked_quote_packs,
            discovery_stats=global_settings.discovery_stats,
        )
        self.scenario_manager.load_recent(self.recent_scenario_keys)
        self.seasonal_manager.set_override(self.seasonal_mode_override)
        self.seasonal_mode_override = self.seasonal_manager.override

        self.sound_manager.set_enabled(self.sound_enabled)
        self.sound_manager.set_volume(self.sound_volume)
        self.sound_manager.set_categories(self.sound_categories)
        self.companion_manager.configure(
            enabled=self.companion_enabled,
            selected_key=self.selected_companion_key,
        )
        selected_definition = self.companion_manager.selected_definition()
        if selected_definition is not None:
            self.selected_companion_key = selected_definition.key

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

        if not self.unlock_manager.is_unlocked("skin", self.skin_key):
            self.skin_key = "jason"

        self._apply_skin_assets()
        self.animation.on_skin_changed()
        self._apply_dialogue_pack_states()
        self._refresh_suppression_state()

    def _apply_skin_assets(self):
        assets = build_skin_assets(self.skins[self.skin_key])
        self.active_frames = assets["frames"]
        self.active_palette = dict(BASE_PALETTE)
        self.active_palette.update(assets["palette"])
        self.tray_colors = assets["tray"]
        self.skin_tags = list(assets.get("tags", []))
        self.skin_sound_set = assets.get("sound_set")
        self.skin_quote_affinity = dict(assets.get("quote_affinity", {}))
        self.skin_accessory_offsets = dict(assets.get("accessory_offsets", {}))
        self.skin_capabilities = dict(assets.get("capabilities", {}))
        self.animation.set_sequences(
            assets.get("idle_sequence"),
            assets.get("interaction_sequence"),
        )

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
            "toy_tick",
            self._toy_tick,
            initial_delay_ms=0,
            default_delay_ms=150,
            owner="behavior",
        )
        self.scheduler.schedule_loop(
            "desk_item_tick",
            self._desk_item_tick,
            initial_delay_ms=0,
            default_delay_ms=120,
            owner="behavior",
        )
        self.scheduler.schedule_loop(
            "companion_tick",
            self._companion_tick,
            initial_delay_ms=600,
            default_delay_ms=150,
            owner="behavior",
        )
        self.scheduler.schedule_loop(
            "movement_tick",
            self._movement_tick,
            initial_delay_ms=1200,
            default_delay_ms=MOVEMENT_TICK_MS,
            owner="behavior",
        )
        self.scheduler.schedule_loop(
            "random_saying",
            self._random_saying_tick,
            initial_delay_ms=self._random_delay(RANDOM_SAYING_RANGE_MS),
            default_delay_ms=RANDOM_SAYING_RANGE_MS[0],
            owner="speech",
        )
        self.scheduler.schedule_loop(
            "personality_tick",
            self._personality_tick,
            initial_delay_ms=self._random_delay(PERSONALITY_TICK_RANGE_MS),
            default_delay_ms=PERSONALITY_TICK_RANGE_MS[0],
            owner="behavior",
        )
        self.scheduler.schedule_loop(
            "mood_shift",
            self._rotate_mood,
            initial_delay_ms=self._random_delay(MOOD_SHIFT_RANGE_MS),
            default_delay_ms=MOOD_SHIFT_RANGE_MS[0],
            owner="behavior",
        )
        self.scheduler.schedule_loop(
            "scenario_tick",
            self._scenario_tick,
            initial_delay_ms=SCENARIO_TICK_MS,
            default_delay_ms=SCENARIO_TICK_MS,
            owner="behavior",
        )
        self.scheduler.schedule_loop(
            "continuity_tick",
            self._continuity_tick,
            initial_delay_ms=CONTINUITY_TICK_MS,
            default_delay_ms=CONTINUITY_TICK_MS,
            owner="behavior",
        )
        self.scheduler.schedule_loop(
            "idle_micro_action",
            self._idle_micro_action_tick,
            initial_delay_ms=self._random_idle_micro_action_delay(),
            default_delay_ms=IDLE_MICRO_ACTION_RANGE_MS[0],
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
        self._schedule_rare_events()
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
                toggle_rare_events=self._toggle_rare_events_enabled,
                toggle_chaos_mode=self._toggle_chaos_mode,
                toggle_movement=self._toggle_movement_enabled,
                toggle_companion=self._toggle_companion_enabled,
                select_companion=self._set_companion,
                trigger_companion_interaction=self._trigger_companion_interaction_from_menu,
                toggle_unlocks=self._toggle_unlocks_enabled,
                trigger_toy=self._trigger_toy_from_menu,
                trigger_desk_item=self._trigger_desk_item_from_menu,
                trigger_quote=lambda: self._show_saying(True),
                toggle_quote_pack=self._toggle_quote_pack,
                trigger_scenario=self._trigger_scenario_from_menu,
                set_seasonal_mode=self._set_seasonal_mode,
                set_activity_level=self._set_activity_level,
                set_quote_frequency=self._set_quote_frequency,
                set_companion_frequency=self._set_companion_frequency,
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

    @staticmethod
    def _dedupe(values):
        ordered = []
        seen = set()
        for value in list(values or []):
            text = str(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            ordered.append(text)
        return ordered

    def _active_comedy_bias(self):
        if int(self._comedy_bias.get("until_ms", 0)) <= int(time.monotonic() * 1000):
            return {"contexts": [], "categories": [], "packs": [], "render": {}, "label": ""}
        return {
            "contexts": list(self._comedy_bias.get("contexts", [])),
            "categories": list(self._comedy_bias.get("categories", [])),
            "packs": list(self._comedy_bias.get("packs", [])),
            "render": dict(self._comedy_bias.get("render", {})),
            "label": str(self._comedy_bias.get("label", "")).strip(),
        }

    def _set_comedy_bias(self, contexts=None, categories=None, packs=None, render_overrides=None, duration_ms=12_000, label=""):
        self._comedy_bias = {
            "contexts": self._dedupe(contexts),
            "categories": self._dedupe(categories),
            "packs": self._dedupe(packs),
            "render": dict(render_overrides or {}),
            "until_ms": int(time.monotonic() * 1000) + max(250, int(duration_ms)),
            "label": str(label or "").strip(),
        }
        if self._comedy_bias["label"]:
            self.logger.info(f"comedy-bias: {self._comedy_bias['label']} -> {self._comedy_bias}")

    def _is_unlocked(self, item_type, item_key):
        return self.unlock_manager.is_unlocked(item_type, item_key)

    def _effective_quote_pack_states(self):
        states = dict(self.quote_pack_states)
        if not self.unlocks_enabled:
            return states
        for pack in self.dialogue.available_packs():
            if not self._is_unlocked("quote_pack", pack["key"]):
                states[pack["key"]] = False
        return states

    def _apply_dialogue_pack_states(self):
        self.dialogue.set_pack_states(self._effective_quote_pack_states())

    def _seasonal_context(self):
        context = self.seasonal_manager.context()
        if context.get("active_keys"):
            self.last_active_season = context["active_keys"][0]
        elif self.seasonal_mode_override == "off":
            self.last_active_season = ""
        return context

    def _active_scenario_label(self):
        active_key = self.scenario_manager.active_scenario_key()
        if not active_key:
            return ""
        for item in self.available_scenarios():
            if item["key"] == active_key:
                return item["label"]
        return active_key

    def _personality_label(self):
        return self.personality.snapshot()["label"]

    def _favorite_list_for(self, item_type):
        mapping = {
            "skin": self.favorite_skin_keys,
            "toy": self.favorite_toy_keys,
            "scenario": self.favorite_scenario_keys,
            "quote_pack": self.favorite_quote_pack_keys,
        }
        return mapping.get(str(item_type or "").strip(), [])

    def _is_favorite(self, item_type, item_key):
        key = str(item_key or "").strip()
        return bool(key and key in self._favorite_list_for(item_type))

    def _set_favorite(self, item_type, item_key, enabled):
        key = str(item_key or "").strip()
        if not key:
            return False
        values = list(self._favorite_list_for(item_type))
        changed = False
        if enabled and key not in values:
            values.append(key)
            changed = True
        elif not enabled and key in values:
            values = [item for item in values if item != key]
            changed = True
        if not changed:
            return False
        normalized = self._dedupe(values)
        if item_type == "skin":
            self.favorite_skin_keys = normalized
        elif item_type == "toy":
            self.favorite_toy_keys = normalized
        elif item_type == "scenario":
            self.favorite_scenario_keys = normalized
        elif item_type == "quote_pack":
            self.favorite_quote_pack_keys = normalized
        else:
            return False
        self._schedule_settings_save()
        self._refresh_tray()
        return True

    @staticmethod
    def _weighted_choice(weighted):
        if not weighted:
            return None
        total = sum(max(1, int(weight)) for _value, weight in weighted)
        if total <= 0:
            return weighted[-1][0]
        pick = random.uniform(0, total)
        current = 0.0
        for value, weight in weighted:
            current += max(1, int(weight))
            if pick <= current:
                return value
        return weighted[-1][0]

    def _skin_weight(self, skin_key, preferred_tags=None):
        metadata = self.skin_metadata(skin_key)
        tags = set(metadata.get("tags", []))
        preferred = set(self._dedupe(preferred_tags))
        seasonal_tags = set(self._seasonal_context().get("preferred_skin_tags", []))
        current_tags = set(self.skin_tags)
        weight = 1
        if skin_key == self.skin_key:
            weight += 2
        if skin_key in self.favorite_skin_keys:
            weight += 4
        if preferred and preferred & tags:
            weight += 4
        if seasonal_tags and seasonal_tags & tags:
            weight += 2
        if skin_key != self.skin_key and current_tags and current_tags & tags:
            weight += 1
        return weight

    def _preferred_skin_key(self, preferred_tags=None, include_current=True):
        weighted = []
        for skin_key in self.available_skin_keys():
            if not include_current and skin_key == self.skin_key:
                continue
            weighted.append((skin_key, self._skin_weight(skin_key, preferred_tags=preferred_tags)))
        return self._weighted_choice(weighted)

    def _maybe_shift_skin_for_context(self, preferred_tags=None, reason="context", force=False):
        if not preferred_tags:
            return False
        current_score = self._skin_weight(self.skin_key, preferred_tags=preferred_tags)
        candidate = self._preferred_skin_key(preferred_tags=preferred_tags, include_current=False)
        if not candidate:
            return False
        candidate_score = self._skin_weight(candidate, preferred_tags=preferred_tags)
        if candidate_score <= current_score:
            return False
        if self.skin_key in self.favorite_skin_keys and current_score >= candidate_score - 1 and not force:
            return False
        if not force and candidate_score < current_score + 2:
            return False
        if not force and random.randint(1, 100) > 38:
            return False
        previous = self.skin_key
        self._set_skin(candidate)
        changed = previous != self.skin_key
        if changed:
            self.logger.info(f"skin: shifted {previous} -> {self.skin_key} ({reason})")
        return changed

    def _record_discovery_progress(self, counter_key, amount=1, schedule_save=True):
        discoveries = self.unlock_manager.note_progress(counter_key, amount=amount)
        if discoveries:
            self._apply_dialogue_pack_states()
            self._refresh_tray()
        if discoveries or schedule_save:
            self._schedule_settings_save()
        return discoveries

    def _flush_discovery_notifications(self, reveal_if_hidden=False):
        pending = self.unlock_manager.pending_discoveries()
        if not pending:
            return False
        if not self._can_speak(1):
            self.unlock_manager.restore_pending(pending)
            return False
        for discovery in pending:
            if discovery.item_type == "quote_pack":
                self.quote_pack_states.pop(discovery.key, None)
        self._apply_dialogue_pack_states()
        first = pending[0]
        label = first.label
        text = f"Discovery unlocked:\n{label}"
        if len(pending) > 1:
            text += f"\n+{len(pending) - 1} more weird little thing(s)."
        return self._show_text(text, reveal_if_hidden=reveal_if_hidden, source="discovery")

    def _set_personality_state(self, state_key, reason="manual", duration_ms=None, lock_ms=0, play_sound=False):
        changed = self.personality.transition_to(
            state_key,
            reason=reason,
            duration_ms=duration_ms,
            lock_ms=lock_ms,
        )
        if not changed:
            return False
        current_state = self.personality.current_state()
        self._record_discovery_progress("state_changes", 1)
        if current_state == "curious":
            self._record_discovery_progress("curious_beats", 1, schedule_save=False)
        if current_state == "confused":
            self._record_discovery_progress("confused_beats", 1, schedule_save=False)
        if play_sound:
            self._play_state_sound(current_state)
        self._flush_discovery_notifications(reveal_if_hidden=False)
        self._refresh_tray()
        return True

    def _active_toy_label(self, toy_key=None):
        active_key = toy_key or self.toy_manager.active_toy_key()
        if not active_key:
            return ""
        for item in self.toy_manager.available_toys():
            if item["key"] == active_key:
                return item["label"]
        return active_key

    def _active_desk_item_label(self, item_key=None):
        active_key = item_key or self.desk_item_manager.active_item_key()
        if not active_key:
            return ""
        for item in self.available_desk_items():
            if item["key"] == active_key:
                return item["label"]
        return active_key

    def _activity_multiplier(self):
        return {
            "low": 1.35,
            "normal": 1.0,
            "high": 0.72,
        }.get(str(self.activity_level or "normal"), 1.0)

    def _quote_delay_multiplier(self):
        return {
            "quiet": 1.45,
            "normal": 1.0,
            "chatty": 0.74,
        }.get(str(self.quote_frequency or "normal"), 1.0)

    def _companion_frequency_multiplier(self):
        return {
            "low": 0.7,
            "normal": 1.0,
            "high": 1.35,
        }.get(str(self.companion_frequency or "normal"), 1.0)

    def _skin_specialty_context(self):
        contexts = []
        categories = []
        desk_item_bonus = {}
        companion_bonus = {}
        if "astronaut" in self.skin_tags:
            contexts.extend(["skin-specialty", "astronaut-specialty"])
            categories.extend(["playful", "homelab"])
            desk_item_bonus["tiny-network-rack"] = 4
            companion_bonus["desk-patrol"] = 2
        if "network" in self.skin_tags:
            contexts.extend(["skin-specialty", "network-specialty"])
            categories.extend(["network", "cisco"])
            desk_item_bonus["tiny-network-rack"] = desk_item_bonus.get("tiny-network-rack", 0) + 6
            companion_bonus["cable-audit"] = companion_bonus.get("cable-audit", 0) + 4
        if "office" in self.skin_tags or "responsible" in self.skin_tags:
            contexts.extend(["skin-specialty", "office-specialty"])
            categories.extend(["office", "responsible"])
            desk_item_bonus["keyboard"] = desk_item_bonus.get("keyboard", 0) + 4
            desk_item_bonus["coffee-mug"] = desk_item_bonus.get("coffee-mug", 0) + 2
        if "squarl" in self.skin_tags or "suit" in self.skin_tags:
            contexts.extend(["skin-specialty", "squarl-specialty"])
            categories.extend(["playful", "smug"])
            desk_item_bonus["coffee-mug"] = desk_item_bonus.get("coffee-mug", 0) + 3
            companion_bonus["victory-scamper"] = companion_bonus.get("victory-scamper", 0) + 2
        return {
            "contexts": self._dedupe(contexts),
            "categories": self._dedupe(categories),
            "desk_item_bonus": desk_item_bonus,
            "companion_bonus": companion_bonus,
        }

    def _sayings_context(self, overrides=None):
        now = datetime.now()
        battery = self.last_battery_snapshot or get_battery_snapshot() or {}
        active_companion = self.companion_manager.current_companion_label()
        context = {
            "pet_name": self.pet_name,
            "mood": MOODS[self.mood]["label"],
            "mood_key": self.mood,
            "personality": self._personality_label(),
            "personality_key": self.personality.current_state(),
            "time": now.strftime("%I:%M %p").lstrip("0"),
            "date": now.strftime("%Y-%m-%d"),
            "active_window": self.last_active_window_title or "desktop",
            "battery_percent": battery.get("percent", "?"),
            "skin": self.skin_metadata().get("label", self.skin_key),
            "skin_key": self.skin_key,
            "toy": self._active_toy_label(),
            "desk_item": self._active_desk_item_label(),
            "companion": active_companion,
            "dance_routine": self.last_dance_routine_key or "classic-bounce",
        }
        if overrides:
            context.update(overrides)
        return context

    def _quote_selection_context(self, extra_contexts=None, extra_categories=None, extra_packs=None, toy_key=None):
        seasonal = self._seasonal_context()
        bias = self._active_comedy_bias()
        specialty = self._skin_specialty_context()
        contexts = self._dedupe(self.skin_quote_affinity.get("contexts", []))
        contexts.extend(context for context in self.personality.quote_contexts() if context not in contexts)
        contexts.extend(context for context in self._dedupe(extra_contexts) if context not in contexts)
        contexts.extend(context for context in self.toy_manager.active_contexts() if context not in contexts)
        contexts.extend(context for context in self.desk_item_manager.active_contexts() if context not in contexts)
        contexts.extend(context for context in self.companion_manager.active_contexts() if context not in contexts)
        contexts.extend(context for context in seasonal.get("contexts", []) if context not in contexts)
        contexts.extend(context for context in specialty.get("contexts", []) if context not in contexts)
        contexts.extend(context for context in bias.get("contexts", []) if context not in contexts)

        preferred_categories = self._dedupe(self.skin_quote_affinity.get("categories", []))
        preferred_categories.extend(
            category for category in self.personality.preferred_categories() if category not in preferred_categories
        )
        preferred_categories.extend(
            category for category in self._dedupe(extra_categories) if category not in preferred_categories
        )
        preferred_categories.extend(
            tag for tag in self.toy_manager.active_tags() if tag not in preferred_categories
        )
        preferred_categories.extend(
            tag for tag in self.desk_item_manager.active_tags() if tag not in preferred_categories
        )
        preferred_categories.extend(
            tag for tag in self.companion_manager.active_tags() if tag not in preferred_categories
        )
        preferred_categories.extend(
            category for category in seasonal.get("preferred_skin_tags", []) if category not in preferred_categories
        )
        preferred_categories.extend(
            category for category in specialty.get("categories", []) if category not in preferred_categories
        )
        preferred_categories.extend(
            category for category in bias.get("categories", []) if category not in preferred_categories
        )

        preferred_packs = self._dedupe(self.skin_quote_affinity.get("packs", []))
        preferred_packs.extend(pack for pack in self._dedupe(extra_packs) if pack not in preferred_packs)
        preferred_packs.extend(
            pack for pack in self.favorite_quote_pack_keys if pack not in preferred_packs and self._is_unlocked("quote_pack", pack)
        )
        preferred_packs.extend(
            pack for pack in seasonal.get("preferred_quote_packs", []) if pack not in preferred_packs
        )
        preferred_packs.extend(
            pack for pack in bias.get("packs", []) if pack not in preferred_packs
        )

        return {
            "skin_key": self.skin_key,
            "skin_tags": list(self.skin_tags),
            "mood_key": self.mood,
            "personality_key": self.personality.current_state(),
            "contexts": contexts,
            "preferred_categories": preferred_categories,
            "preferred_packs": preferred_packs,
            "toy": toy_key or self.toy_manager.active_toy_key() or "",
            "desk_item": self.desk_item_manager.active_item_key() or "",
        }

    def _recent_templates(self):
        return [entry.get("template", entry.get("text", "")) for entry in self.speech_history.recent()]

    def _play_effect(self, effect_name, category="toy", throttle_ms=0, throttle_key=None):
        if not effect_name:
            return
        self.sound_manager.play(
            effect_name,
            category=category,
            throttle_ms=throttle_ms,
            throttle_key=throttle_key,
        )

    def _play_interaction_sound(self):
        custom_effect = None
        if self.skin_sound_set:
            candidate = str(self.skin_sound_set).replace("-", "_") + "_interaction"
            if self.sound_manager.has_effect(candidate):
                custom_effect = candidate
        self._play_effect(custom_effect or "dance", category="state", throttle_ms=1800, throttle_key="interaction")

    def _play_state_sound(self, state_key):
        definition = self.personality.definition(state_key)
        if definition.sound_effect and self.sound_manager.has_effect(definition.sound_effect):
            self._play_effect(
                definition.sound_effect,
                category="state",
                throttle_ms=5500,
                throttle_key=f"state:{definition.key}",
            )

    def _play_scenario_sound(self, scenario_key):
        effect_name = "scenario_" + str(scenario_key).replace("-", "_")
        if self.sound_manager.has_effect(effect_name):
            self._play_effect(
                effect_name,
                category="scenario",
                throttle_ms=9000,
                throttle_key=f"scenario:{scenario_key}",
            )

    def _pick_dance_routine(self):
        routines = self.animation.available_dance_routines()
        if not routines:
            return ""
        active_scenario = self.scenario_manager.active_scenario_key()
        bias = self._active_comedy_bias()
        weighted = []
        for routine in routines:
            weight = 2
            if routine.key == "victory-stomp" and (
                "network" in self.skin_tags
                or self.personality.current_state() in {"celebrating", "smug"}
                or "title-cisco" in bias.get("contexts", [])
                or "network" in bias.get("categories", [])
                or "victory" in active_scenario
            ):
                weight += 5
            if routine.key == "desk-shuffle" and (
                "office" in self.skin_tags
                or self.personality.current_state() in {"busy", "annoyed"}
                or "title-ticket" in bias.get("contexts", [])
                or "office" in bias.get("categories", [])
            ):
                weight += 4
            if routine.key == "classic-bounce" and self.companion_manager.active_interaction_key():
                weight += 3
            if routine.key == self.last_dance_routine_key:
                weight = max(1, weight - 2)
            weighted.append((routine.key, weight))
        total = sum(weight for _key, weight in weighted)
        pick = random.uniform(0, total)
        current = 0.0
        for routine_key, weight in weighted:
            current += weight
            if pick <= current:
                return routine_key
        return weighted[-1][0]

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
        self._record_discovery_progress("quotes_spoken", 1, schedule_save=False)
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
        frame = self.animation.next_frame(
            self.mood,
            personality_profile=self.personality.animation_profile(),
        )
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
            bubble_offset = self.skin_accessory_offsets.get("bubble", {})
            self.window.show_bubble(
                text,
                offset_x=bubble_offset.get("x", 0),
                offset_y=bubble_offset.get("y", 0),
            )
        except tk.TclError:
            self.logger.exception("Failed to create speech bubble")
            return False

        self._speech_serial += 1
        self.last_speech_at = time.time()
        self._play_effect("speech", category="speech", throttle_ms=350, throttle_key="speech")
        self._record_saying(template_text or text, text, source)
        return True

    def _follow_up_allowed(self, follow_up, render_context):
        if not isinstance(follow_up, FollowUpQuote):
            return False
        active_contexts = set(self._quote_selection_context().get("contexts", []))
        if follow_up.require_contexts and not set(follow_up.require_contexts).issubset(active_contexts):
            return False
        if follow_up.exclude_contexts and active_contexts & set(follow_up.exclude_contexts):
            return False
        if float(follow_up.chance) < 1.0 and random.random() > float(follow_up.chance):
            return False
        rendered = render_template(follow_up.text, render_context)
        if rendered in self.recent_saying_texts():
            return False
        return True

    def _queue_follow_ups(self, follow_ups, render_context, source, speech_serial):
        for index, follow_up in enumerate(tuple(follow_ups or ())):
            if not self._follow_up_allowed(follow_up, render_context):
                continue

            def deliver(target=follow_up, serial=speech_serial, follow_up_index=index):
                if self.is_quitting:
                    return
                if serial != self._speech_serial:
                    return
                if self.scenario_manager.active_scenario_key() or self.animation.is_dancing:
                    return
                if not self._automatic_actions_allowed():
                    return
                rendered_text = render_template(target.text, render_context)
                if rendered_text in self.recent_saying_texts():
                    return
                self._show_text(
                    rendered_text,
                    source=f"{source}:follow-up",
                    template_text=target.text,
                )
                self.logger.info(f"speech follow-up delivered: {follow_up_index} from {source}")

            self.scheduler.schedule(
                f"speech_follow_up_{speech_serial}_{index}",
                max(250, int(follow_up.delay_ms)),
                deliver,
                owner="speech",
            )

    def _show_saying(
        self,
        reveal_if_hidden=False,
        source="ambient",
        extra_contexts=None,
        extra_categories=None,
        extra_packs=None,
        toy_key=None,
        render_overrides=None,
    ):
        choice = self.dialogue.pick_ambient(
            self.mood,
            context=self._quote_selection_context(
                extra_contexts=extra_contexts,
                extra_categories=extra_categories,
                extra_packs=extra_packs,
                toy_key=toy_key,
            ),
            recent_templates=self._recent_templates(),
        )
        render_context = self._sayings_context(
            {
                "toy": self._active_toy_label(toy_key),
                **self._active_comedy_bias().get("render", {}),
                **dict(render_overrides or {}),
            }
        )
        rendered = render_template(
            choice.template,
            render_context,
        )
        shown = self._show_text(
            rendered,
            reveal_if_hidden,
            source=f"{source}:{choice.pack_key}",
            template_text=choice.template,
        )
        if shown and choice.follow_ups:
            self._queue_follow_ups(
                choice.follow_ups,
                render_context,
                source=f"{source}:{choice.pack_key}",
                speech_serial=self._speech_serial,
            )
        return shown

    def _random_saying_tick(self):
        min_gap = {
            "quiet": 30,
            "normal": 20,
            "chatty": 14,
        }.get(str(self.quote_frequency or "normal"), 20)
        if (
            self._can_speak(min_gap)
            and self.reaction_toggles.get("random_sayings", True)
            and self._automatic_actions_allowed()
            and not self.companion_manager.blocks_owner_movement()
        ):
            self._show_saying()
        minimum, maximum = RANDOM_SAYING_RANGE_MS
        scale = self._quote_delay_multiplier()
        return int(self._random_delay((minimum, maximum)) * scale)

    def _rotate_mood(self):
        if self.is_quitting:
            return None
        choices = [mood for mood in MOODS if mood != self.mood]
        self.mood = random.choice(choices)
        self._schedule_settings_save()
        self._refresh_tray()
        return self._random_delay(MOOD_SHIFT_RANGE_MS)

    def available_skin_keys(self):
        return sorted(
            skin_key
            for skin_key in self.skins.keys()
            if self._is_unlocked("skin", skin_key)
        )

    def available_skin_labels(self):
        return {key: self.skins[key].get("label", key) for key in self.available_skin_keys()}

    def available_quote_packs(self):
        packs = []
        for pack in self.dialogue.available_packs():
            if not self._is_unlocked("quote_pack", pack["key"]):
                continue
            item = dict(pack)
            item["favorite"] = self._is_favorite("quote_pack", pack["key"])
            packs.append(item)
        return packs

    def available_toys(self):
        toys = []
        for toy in self.toy_manager.available_toys():
            if not self._is_unlocked("toy", toy["key"]):
                continue
            item = dict(toy)
            item["favorite"] = self._is_favorite("toy", toy["key"])
            toys.append(item)
        return toys

    def available_desk_items(self):
        items = []
        for desk_item in self.desk_item_manager.available_items():
            item = dict(desk_item)
            item["favorite"] = False
            items.append(item)
        return items

    def available_companions(self):
        return self.companion_manager.available_companions()

    def available_companion_interactions(self):
        return self.companion_manager.available_interactions()

    def available_scenarios(self, include_locked=False):
        scenarios = self.scenario_manager.available_scenarios(
            unlock_manager=self.unlock_manager,
            favorites=self.favorite_scenario_keys,
        )
        if include_locked:
            return scenarios
        return [scenario for scenario in scenarios if scenario.get("unlocked", True)]

    def _movement_bounds(self):
        bounds = self.window.work_area()
        right = max(int(bounds.left), int(bounds.right) - int(CANVAS_W) - 4)
        bottom = max(int(bounds.top), int(bounds.bottom) - int(CANVAS_H) - 8)
        return DesktopBounds(
            left=int(bounds.left),
            top=int(bounds.top),
            right=right,
            bottom=bottom,
        )

    def available_seasonal_modes(self):
        active = set(self._seasonal_context().get("active_keys", []))
        if not active:
            active = {self.seasonal_mode_override}
        options = []
        for option in self.seasonal_manager.available_modes():
            item = dict(option)
            item["active"] = option["key"] in active
            if option["key"] == "auto" and self.seasonal_mode_override == "auto":
                item["active"] = True
            if option["key"] == "off" and self.seasonal_mode_override == "off":
                item["active"] = True
            options.append(item)
        return options

    def available_discoveries(self):
        return self.unlock_manager.discovery_catalog()

    def quote_pack_enabled(self, pack_key):
        if not self._is_unlocked("quote_pack", pack_key):
            return False
        return self.dialogue.pack_enabled(pack_key)

    def _set_skin(self, skin_key):
        if skin_key not in self.skins or skin_key == self.skin_key or not self._is_unlocked("skin", skin_key):
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

    def _toggle_movement_enabled(self):
        self.movement_enabled = not self.movement_enabled
        if not self.movement_enabled:
            self.movement.clear()
        self._schedule_settings_save()
        self._refresh_tray()

    def _toggle_companion_enabled(self):
        self.companion_enabled = not self.companion_enabled
        self.companion_manager.configure(enabled=self.companion_enabled, selected_key=self.selected_companion_key)
        selected_definition = self.companion_manager.selected_definition()
        if selected_definition is not None:
            self.selected_companion_key = selected_definition.key
        self._schedule_settings_save()
        self._refresh_tray()

    def _set_companion(self, companion_key):
        if not companion_key:
            return False
        self.selected_companion_key = str(companion_key).strip()
        self.companion_enabled = True
        self.companion_manager.configure(enabled=True, selected_key=self.selected_companion_key)
        selected_definition = self.companion_manager.selected_definition()
        if selected_definition is not None:
            self.selected_companion_key = selected_definition.key
        self._schedule_settings_save()
        self._refresh_tray()
        return True

    def _set_activity_level(self, level):
        normalized = str(level or "normal").strip().lower()
        if normalized not in {"low", "normal", "high"}:
            return False
        self.activity_level = normalized
        self._schedule_auto_antics()
        self._schedule_settings_save()
        self._refresh_tray()
        return True

    def _set_quote_frequency(self, level):
        normalized = str(level or "normal").strip().lower()
        if normalized not in {"quiet", "normal", "chatty"}:
            return False
        self.quote_frequency = normalized
        self._schedule_settings_save()
        self._refresh_tray()
        return True

    def _set_companion_frequency(self, level):
        normalized = str(level or "normal").strip().lower()
        if normalized not in {"low", "normal", "high"}:
            return False
        self.companion_frequency = normalized
        self._schedule_settings_save()
        self._refresh_tray()
        return True

    def _toggle_rare_events_enabled(self):
        self.rare_events_enabled = not self.rare_events_enabled
        self._schedule_rare_events()
        self._schedule_settings_save()
        self._refresh_tray()

    def _toggle_chaos_mode(self):
        self.chaos_mode = not self.chaos_mode
        self._schedule_rare_events()
        self._schedule_settings_save()
        self._refresh_tray()

    def _toggle_unlocks_enabled(self):
        self.unlocks_enabled = not self.unlocks_enabled
        self.unlock_manager.set_enabled(self.unlocks_enabled)
        self._apply_dialogue_pack_states()
        self._schedule_settings_save()
        self._refresh_tray()

    def _set_seasonal_mode(self, mode_key):
        if not self.seasonal_manager.set_override(mode_key):
            return False
        self.seasonal_mode_override = self.seasonal_manager.override
        seasonal = self._seasonal_context()
        if self.seasonal_mode_override not in {"auto", "off"}:
            self._maybe_shift_skin_for_context(
                preferred_tags=seasonal.get("preferred_skin_tags", []),
                reason=f"season:{self.seasonal_mode_override}",
                force=False,
            )
        self._schedule_settings_save()
        self._refresh_tray()
        return True

    def _toggle_quote_pack(self, pack_key):
        if not pack_key:
            return
        self.set_quote_pack_enabled(pack_key, not self.dialogue.pack_enabled(pack_key))

    def set_quote_pack_enabled(self, pack_key, enabled):
        if not pack_key or not self._is_unlocked("quote_pack", pack_key):
            return False
        if not self.dialogue.set_pack_enabled(pack_key, enabled):
            return False
        self.quote_pack_states = self.dialogue.pack_state_overrides()
        self._schedule_settings_save()
        self._refresh_tray()
        return True

    def _trigger_toy_from_menu(self, toy_key):
        self._trigger_toy(toy_key, reveal_if_hidden=True, show_saying=True, source="toy-manual")

    def _trigger_companion_interaction_from_menu(self, interaction_key):
        self._trigger_companion_interaction(interaction_key, reveal_if_hidden=True, source="companion-manual")

    def _trigger_scenario_from_menu(self, scenario_key):
        self._start_scenario(scenario_key, reveal_if_hidden=True, source="scenario-manual")

    def apply_settings(
        self,
        skin_key,
        sound_enabled,
        sound_volume,
        sound_categories,
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
        rare_events_enabled,
        chaos_mode,
        movement_enabled,
        activity_level,
        quote_frequency,
        companion_frequency,
        unlocks_enabled,
        seasonal_mode_override,
        pet_name,
        reaction_toggles,
        favorite_skins,
        favorite_toys,
        favorite_scenarios,
        favorite_quote_packs,
    ):
        self.sound_enabled = bool(sound_enabled)
        self.sound_volume = clamp(int(sound_volume), 0, 100)
        self.sound_categories = dict(sound_categories or self.sound_categories)
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
        self.rare_events_enabled = bool(rare_events_enabled)
        self.chaos_mode = bool(chaos_mode)
        self.movement_enabled = bool(movement_enabled)
        self.activity_level = str(activity_level or "normal").strip().lower() or "normal"
        if self.activity_level not in {"low", "normal", "high"}:
            self.activity_level = "normal"
        self.quote_frequency = str(quote_frequency or "normal").strip().lower() or "normal"
        if self.quote_frequency not in {"quiet", "normal", "chatty"}:
            self.quote_frequency = "normal"
        self.companion_frequency = str(companion_frequency or "normal").strip().lower() or "normal"
        if self.companion_frequency not in {"low", "normal", "high"}:
            self.companion_frequency = "normal"
        self.unlocks_enabled = bool(unlocks_enabled)
        self.seasonal_mode_override = str(seasonal_mode_override or "auto").strip() or "auto"
        self.pet_name = str(pet_name or self.pet_name)
        self.reaction_toggles = dict(default_settings()["global"]["reactions"])
        self.reaction_toggles.update(reaction_toggles)
        self.favorite_skin_keys = self._dedupe(favorite_skins)
        self.favorite_toy_keys = self._dedupe(favorite_toys)
        self.favorite_scenario_keys = self._dedupe(favorite_scenarios)
        self.favorite_quote_pack_keys = self._dedupe(favorite_quote_packs)
        self.sound_manager.set_enabled(self.sound_enabled)
        self.sound_manager.set_volume(self.sound_volume)
        self.sound_manager.set_categories(self.sound_categories)
        self.unlock_manager.set_enabled(self.unlocks_enabled)
        self.seasonal_manager.set_override(self.seasonal_mode_override)
        self.seasonal_mode_override = self.seasonal_manager.override
        if not self.movement_enabled:
            self.movement.clear()
        try:
            self.startup_manager.set_enabled(auto_start_enabled)
        except OSError:
            self.logger.exception("Failed to update startup entry")
            self._show_text("Startup setting failed.\nSee log for details.")
        self._set_skin(skin_key)
        self._schedule_auto_antics()
        self._schedule_rare_events()
        self._apply_dialogue_pack_states()
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

    def _scenario_pick_context(self):
        seasonal = self._seasonal_context()
        preferred_categories = self._dedupe(self.skin_quote_affinity.get("categories", []))
        preferred_categories.extend(
            category
            for category in self.personality.preferred_categories()
            if category not in preferred_categories
        )
        return {
            "skin_tags": list(self.skin_tags) + list(seasonal.get("preferred_skin_tags", [])),
            "preferred_categories": preferred_categories,
            "favorite_scenarios": list(self.favorite_scenario_keys),
            "seasonal_modes": list(seasonal.get("active_keys", [])),
            "personality_state": self.personality.current_state(),
            "chaos_mode": self.chaos_mode,
        }

    def _trigger_random_scenario(self, source="scenario-auto", reveal_if_hidden=False):
        definition = self.scenario_manager.pick_scenario(
            context=self._scenario_pick_context(),
            unlock_manager=self.unlock_manager,
        )
        if definition is None:
            return False
        return self._start_scenario(definition.key, reveal_if_hidden=reveal_if_hidden, source=source)

    def _random_auto_antics_delay(self):
        minimum = max(1, min(self.auto_antics_min_minutes, self.auto_antics_max_minutes))
        maximum = max(minimum, max(self.auto_antics_min_minutes, self.auto_antics_max_minutes))
        multiplier = self._activity_multiplier()
        return int(random.randint(minimum * 60 * 1000, maximum * 60 * 1000) * multiplier)

    def _random_rare_event_delay(self):
        delay_range = (5 * 60 * 1000, 11 * 60 * 1000) if self.chaos_mode else RARE_EVENT_RANGE_MS
        return self._random_delay(delay_range)

    def _random_idle_micro_action_delay(self):
        minimum, maximum = IDLE_MICRO_ACTION_RANGE_MS
        multiplier = self._activity_multiplier()
        return int(random.randint(minimum, maximum) * multiplier)

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

    def _schedule_rare_events(self):
        self.scheduler.cancel("rare_event")
        if not self.rare_events_enabled or self.is_quitting:
            return
        self.scheduler.schedule_loop(
            "rare_event",
            self._rare_event_tick,
            initial_delay_ms=self._random_rare_event_delay(),
            default_delay_ms=self._random_rare_event_delay(),
            owner="behavior",
        )

    def _auto_antics_tick(self):
        if self.is_quitting:
            return None
        if self.auto_antics_enabled and self._automatic_actions_allowed() and self._can_speak(14) and not self.companion_manager.blocks_owner_movement() and not self.desk_item_manager.active_item_key():
            if not self.scenario_manager.active_scenario_key() and random.randint(1, 100) <= (28 if self.chaos_mode else 18):
                if self._trigger_random_scenario(source="auto-antics"):
                    return self._random_auto_antics_delay()
            if self.chaos_mode and random.randint(1, 100) <= 22:
                if not self._trigger_random_toy(source="auto-antics"):
                    self._show_saying(source="auto-antics")
            elif random.randint(1, 100) <= self.auto_antics_dance_chance:
                self._trigger_dance(show_saying=False)
            else:
                self._show_saying(source="auto-antics")
        return self._random_auto_antics_delay()

    def _rare_event_tick(self):
        if self.is_quitting:
            return None
        if (
            not self.rare_events_enabled
            or not self._automatic_actions_allowed()
            or not self._can_speak(18)
            or self.companion_manager.blocks_owner_movement()
            or self.desk_item_manager.active_item_key()
        ):
            return self._random_rare_event_delay()
        if not self.scenario_manager.active_scenario_key() and random.randint(1, 100) <= (62 if self.chaos_mode else 42):
            if self._trigger_random_scenario(source="rare-scenario"):
                return self._random_rare_event_delay()
        event = self.rare_event_manager.pick_event(
            {
                "skin_tags": self.skin_tags,
                "preferred_categories": self.skin_quote_affinity.get("categories", []) + self.personality.preferred_categories(),
                "chaos_mode": self.chaos_mode,
            }
        )
        if event and self._trigger_toy(
            event.toy_key,
            reveal_if_hidden=False,
            show_saying=True,
            source=f"rare:{event.key}",
            extra_contexts=list(event.contexts),
            extra_categories=list(event.preferred_categories),
        ):
            self.rare_event_manager.mark_triggered(event.key)
        return self._random_rare_event_delay()

    def _preferred_toy_key(self):
        weighted = []
        preferred_categories = set(self.skin_quote_affinity.get("categories", []))
        skin_tags = set(self.skin_tags)
        personality_categories = set(self.personality.preferred_categories())
        seasonal_tags = set(self._seasonal_context().get("preferred_skin_tags", []))
        for toy in self.available_toys():
            if toy["cooldown_ms"] > 0 or toy["active"]:
                continue
            weight = 1
            if skin_tags & set(toy["tags"]):
                weight += 3
            if preferred_categories & set(toy["tags"]):
                weight += 2
            if personality_categories & set(toy["tags"]):
                weight += 2
            if seasonal_tags & set(toy["tags"]):
                weight += 1
            if toy.get("favorite"):
                weight += 4
            weighted.append((toy["key"], weight))
        if not weighted:
            return None
        total = sum(weight for _key, weight in weighted)
        pick = random.uniform(0, total)
        current = 0.0
        for toy_key, weight in weighted:
            current += weight
            if pick <= current:
                return toy_key
        return weighted[-1][0]

    def _preferred_desk_item_key(self):
        weighted = []
        preferred_categories = set(self.skin_quote_affinity.get("categories", [])) | set(self.personality.preferred_categories())
        specialty = self._skin_specialty_context()
        active_bias = self._active_comedy_bias()
        active_contexts = set(active_bias.get("contexts", []))
        active_categories = set(active_bias.get("categories", []))
        for item in self.available_desk_items():
            if item["cooldown_ms"] > 0 or item["active"]:
                continue
            weight = 1
            item_tags = set(item.get("tags", []))
            item_contexts = set(item.get("contexts", []))
            if preferred_categories & item_tags:
                weight += 3
            if active_categories & item_tags:
                weight += 2
            if active_contexts & item_contexts:
                weight += 3
            weight += int(specialty.get("desk_item_bonus", {}).get(item["key"], 0))
            if self.personality.current_state() in {"busy", "annoyed"} and item["key"] == "keyboard":
                weight += 4
            if self.personality.current_state() in {"curious", "confused"} and item["key"] == "tiny-network-rack":
                weight += 4
            if self.mood == "tired" and item["key"] == "coffee-mug":
                weight += 3
            weighted.append((item["key"], weight))
        if not weighted:
            return None
        total = sum(weight for _key, weight in weighted)
        pick = random.uniform(0, total)
        current = 0.0
        for item_key, weight in weighted:
            current += weight
            if pick <= current:
                return item_key
        return weighted[-1][0]

    def _preferred_companion_interaction_key(self, automatic=False):
        if not self.companion_enabled:
            return None
        weighted = []
        specialty = self._skin_specialty_context()
        personality_state = self.personality.current_state()
        active_bias = self._active_comedy_bias()
        contexts = set(active_bias.get("contexts", []))
        categories = set(active_bias.get("categories", []))
        for interaction in self.available_companion_interactions():
            key = interaction["key"]
            if interaction["cooldown_ms"] > 0 or interaction["active"]:
                continue
            if automatic and key == "feed-cheese":
                continue
            weight = 1
            interaction_tags = set(interaction.get("tags", []))
            interaction_contexts = set(interaction.get("contexts", []))
            if contexts & interaction_contexts:
                weight += 3
            if categories & interaction_tags:
                weight += 2
            weight += int(specialty.get("companion_bonus", {}).get(key, 0))
            if personality_state in {"curious", "confused"} and key in {"desk-patrol", "cable-audit"}:
                weight += 3
            if personality_state in {"celebrating", "smug"} and key == "victory-scamper":
                weight += 4
            if personality_state in {"busy", "annoyed"} and key == "desk-patrol":
                weight += 2
            weighted.append((key, max(1, int(weight))))
        if not weighted:
            return None
        total = sum(weight for _key, weight in weighted)
        pick = random.uniform(0, total)
        current = 0.0
        for interaction_key, weight in weighted:
            current += weight
            if pick <= current:
                return interaction_key
        return weighted[-1][0]

    def _trigger_random_toy(self, source="toy-auto", reveal_if_hidden=False):
        toy_key = self._preferred_toy_key()
        if not toy_key:
            return False
        return self._trigger_toy(toy_key, reveal_if_hidden=reveal_if_hidden, show_saying=True, source=source)

    def _trigger_desk_item_from_menu(self, item_key):
        self._trigger_desk_item(item_key, reveal_if_hidden=True, show_saying=True, source="desk-item-manual")

    def _trigger_companion_interaction(self, interaction_key, reveal_if_hidden=False, source="companion"):
        if self.is_quitting or not interaction_key:
            return False
        if not self.companion_enabled:
            self.companion_enabled = True
            self.companion_manager.configure(enabled=True, selected_key=self.selected_companion_key)
        if self._root_is_hidden():
            if reveal_if_hidden:
                self.window.show()
                self.runtime_state.set_visibility(False)
            else:
                return False
        result = self.companion_manager.trigger_interaction(interaction_key)
        if not result.started:
            if reveal_if_hidden and result.reason == "cooldown":
                seconds = max(1, int(result.remaining_cooldown_ms / 1000))
                interaction_label = next(
                    (item["label"] for item in self.available_companion_interactions() if item["key"] == interaction_key),
                    "That mouse bit",
                )
                self._show_text(f"{interaction_label} is cooling down.\nTry again in {seconds}s.")
            elif reveal_if_hidden and result.reason == "busy":
                self._show_text("The mouse is already doing a whole bit.\nGive it a second.")
            return False
        self._set_personality_state("curious", reason=f"companion:{interaction_key}", duration_ms=3_600)
        self._set_comedy_bias(
            contexts=list(result.contexts),
            categories=list(result.tags),
            duration_ms=15_000,
            label=f"{source}:{interaction_key}",
        )
        self._schedule_settings_save()
        self._refresh_tray()
        return True

    def _trigger_desk_item(
        self,
        item_key,
        reveal_if_hidden=False,
        show_saying=False,
        source="desk-item",
        extra_contexts=None,
        extra_categories=None,
        extra_packs=None,
    ):
        if self.is_quitting or not item_key:
            return False
        if self._root_is_hidden():
            if reveal_if_hidden:
                self.window.show()
                self.runtime_state.set_visibility(False)
            else:
                return False
        result = self.desk_item_manager.trigger(
            item_key,
            self.window_x,
            self.window_y,
            self.window.work_area(),
            skin_offsets=self.skin_accessory_offsets,
        )
        if not result.started:
            if reveal_if_hidden and result.reason == "cooldown":
                seconds = max(1, int(result.remaining_cooldown_ms / 1000))
                self._show_text(f"{self._active_desk_item_label(item_key)} is cooling down.\nTry again in {seconds}s.")
            elif reveal_if_hidden and result.reason == "busy":
                self._show_text("That desk prop is already doing a whole thing.\nGive it a second.")
            return False
        state_map = {
            "coffee-mug": "busy",
            "keyboard": "busy",
            "tiny-network-rack": "curious",
        }
        if item_key in state_map:
            self._set_personality_state(state_map[item_key], reason=f"desk-item:{item_key}", duration_ms=3_800)
        self._set_comedy_bias(
            contexts=list(result.contexts),
            categories=list(result.tags),
            packs=list(extra_packs or []),
            duration_ms=12_000,
            label=f"{source}:{item_key}",
        )
        self._play_effect(result.sound_effect, category="toy", throttle_ms=2400, throttle_key=f"desk-item:{item_key}")
        self._refresh_tray()
        if show_saying and self._can_speak(4):
            self._show_saying(
                reveal_if_hidden=reveal_if_hidden,
                source=source,
                extra_contexts=list(extra_contexts or []) + list(result.contexts),
                extra_categories=list(extra_categories or []) + list(result.tags),
                extra_packs=list(extra_packs or []),
            )
        return True

    def _trigger_toy(
        self,
        toy_key,
        reveal_if_hidden=False,
        show_saying=False,
        source="toy",
        extra_contexts=None,
        extra_categories=None,
    ):
        if self.is_quitting or not toy_key:
            return False
        if self._root_is_hidden():
            if reveal_if_hidden:
                self.window.show()
                self.runtime_state.set_visibility(False)
            else:
                return False
        result = self.toy_manager.trigger(
            toy_key,
            self.window_x,
            self.window_y,
            self.window.work_area(),
            skin_offsets=self.skin_accessory_offsets,
        )
        if not result.started:
            if reveal_if_hidden and result.reason == "cooldown":
                seconds = max(1, int(result.remaining_cooldown_ms / 1000))
                self._show_text(f"{self._active_toy_label(toy_key)} is cooling down.\nTry again in {seconds}s.")
            elif reveal_if_hidden and result.reason == "busy":
                self._show_text("Jason is already busy with a toy.\nGive him a second.")
            return False
        if toy_key == "tricycle":
            self._ride_origin_position = (self.window_x, self.window_y)
        self._record_discovery_progress("toy_uses", 1, schedule_save=False)
        toy_state_map = {
            "tricycle": "celebrating",
            "rubber-duck": "curious",
            "homelab-cart": "busy",
            "stress-ball": "annoyed",
        }
        if toy_key in toy_state_map:
            self._set_personality_state(toy_state_map[toy_key], reason=f"toy:{toy_key}", duration_ms=5200)
        self._play_effect(result.sound_effect, category="toy", throttle_ms=2600, throttle_key=f"toy:{toy_key}")
        self._refresh_tray()
        if show_saying and self._can_speak(2):
            self._show_saying(
                reveal_if_hidden=reveal_if_hidden,
                source=source,
                extra_contexts=list(extra_contexts or []) + list(result.contexts),
                extra_categories=list(extra_categories or []) + list(result.tags),
                toy_key=result.toy_key,
            )
        return True

    def _toy_tick(self):
        if self.is_quitting:
            return None
        result = self.toy_manager.tick(hidden=self._root_is_hidden())
        if result.pet_position and not self.dragging:
            self.window_x, self.window_y = self._clamp_window_position(*result.pet_position)
            self._apply_window_position(0)
        if result.finished_toy == "tricycle" and self._ride_origin_position:
            self.window_x, self.window_y = self._ride_origin_position
            self._apply_window_position(0)
            self._ride_origin_position = None
        if result.finished_toy:
            if result.finished_toy == "tricycle":
                self._set_personality_state("smug", reason="toy-finished:tricycle", duration_ms=5000)
            self._refresh_tray()
        return result.next_delay_ms

    def _desk_item_tick(self):
        if self.is_quitting:
            return None
        result = self.desk_item_manager.tick(
            hidden=self._root_is_hidden(),
            owner_x=self.window_x,
            owner_y=self.window_y,
        )
        if result.finished_item:
            self._refresh_tray()
        return result.next_delay_ms

    def _companion_runtime_context(self):
        return {
            "personality_state": self.personality.current_state(),
            "active_toy": self.toy_manager.active_toy_key() or "",
            "active_desk_item": self.desk_item_manager.active_item_key() or "",
            "active_scenario": self.scenario_manager.active_scenario_key(),
            "mood": self.mood,
        }

    def _companion_tick(self):
        if self.is_quitting:
            return None
        result = self.companion_manager.tick(
            self.window_x,
            self.window_y,
            self.window.work_area(),
            hidden=self._root_is_hidden(),
            owner_context=self._companion_runtime_context(),
        )
        if result.state_changed:
            self._refresh_tray()
        if result.sound_effect:
            self._play_effect(result.sound_effect, category="toy", throttle_ms=2200, throttle_key=f"companion:{result.sound_effect}")
        if result.speech_line:
            self._set_comedy_bias(
                contexts=list(result.contexts),
                categories=list(result.tags),
                duration_ms=14_000,
                label=f"companion:{result.companion_key}:{result.active_interaction or result.state_key}",
            )
            self._show_text(
                result.speech_line,
                source=f"companion:{result.companion_key}",
                template_text=result.speech_line,
            )
        return result.next_delay_ms

    def _personality_runtime_context(self):
        seasonal = self._seasonal_context()
        return {
            "mood": self.mood,
            "chaos_mode": self.chaos_mode,
            "active_toy": self.toy_manager.active_toy_key() or "",
            "active_desk_item": self.desk_item_manager.active_item_key() or "",
            "recent_scenarios": list(self.scenario_manager.recent_history()),
            "seasonal_contexts": seasonal.get("contexts", []),
            "active_scenario": self.scenario_manager.active_scenario_key(),
        }

    def _personality_tick(self):
        if self.is_quitting:
            return None
        if self.scenario_manager.active_scenario_key():
            return self._random_delay(PERSONALITY_TICK_RANGE_MS)
        changed = self.personality.tick(context=self._personality_runtime_context())
        if changed:
            self._record_discovery_progress("state_changes", 1, schedule_save=False)
            if changed == "curious":
                self._record_discovery_progress("curious_beats", 1, schedule_save=False)
            if changed == "confused":
                self._record_discovery_progress("confused_beats", 1, schedule_save=False)
            self._play_state_sound(changed)
            self._schedule_settings_save()
            self._refresh_tray()
        self._flush_discovery_notifications(reveal_if_hidden=False)
        return self._random_delay(PERSONALITY_TICK_RANGE_MS)

    def _idle_micro_action_definitions(self):
        return [
            {
                "key": "suspicious-check",
                "state": "curious",
                "weight": 3,
                "movement_style": "inspect",
                "focus": random.choice(["left-edge", "right-edge", "top-right", "bottom-left"]),
                "contexts": ["micro-action", "suspicious-check", "curious"],
                "categories": ["what-do", "playful"],
                "quote_chance": 0.22,
            },
            {
                "key": "stretch-routine",
                "state": "exhausted",
                "weight": 2,
                "movement_style": "slump",
                "contexts": ["micro-action", "stretch-routine"],
                "categories": ["responsible"],
                "quote_chance": 0.0,
            },
            {
                "key": "keyboard-tap",
                "state": "busy",
                "weight": 4,
                "desk_item": "keyboard",
                "contexts": ["micro-action", "keyboard-tap"],
                "categories": ["office", "helpdesk"],
                "packs": ["networking-meltdown-helpdesk-chaos"],
                "quote_chance": 0.34,
            },
            {
                "key": "coffee-sip",
                "state": "busy",
                "weight": 3,
                "desk_item": "coffee-mug",
                "contexts": ["micro-action", "coffee-break"],
                "categories": ["office", "playful"],
                "quote_chance": 0.26,
            },
            {
                "key": "rack-check",
                "state": "curious",
                "weight": 3,
                "desk_item": "tiny-network-rack",
                "contexts": ["micro-action", "rack-check", "network"],
                "categories": ["network", "homelab"],
                "packs": ["networking-meltdown-helpdesk-chaos", "cisco-jokes"],
                "quote_chance": 0.4,
            },
            {
                "key": "inspect-mouse",
                "state": "curious",
                "weight": 2,
                "companion_interaction": "desk-patrol",
                "contexts": ["micro-action", "mouse-sidekick"],
                "categories": ["playful"],
                "quote_chance": 0.18,
            },
            {
                "key": "cable-audit",
                "state": "curious",
                "weight": 2,
                "companion_interaction": "cable-audit",
                "contexts": ["micro-action", "network", "mouse-sidekick"],
                "categories": ["network", "cisco"],
                "packs": ["cisco-jokes", "networking-meltdown-helpdesk-chaos"],
                "quote_chance": 0.24,
            },
            {
                "key": "proud-of-nothing",
                "state": "smug",
                "weight": 2,
                "contexts": ["micro-action", "smug"],
                "categories": ["playful", "smug"],
                "quote_chance": 0.5,
            },
            {
                "key": "victory-scamper",
                "state": "celebrating",
                "weight": 1,
                "companion_interaction": "victory-scamper",
                "contexts": ["micro-action", "victory", "mouse-sidekick"],
                "categories": ["celebrating", "playful"],
                "quote_chance": 0.16,
            },
        ]

    def _automatic_idle_micro_actions_allowed(self):
        return (
            self.auto_antics_enabled
            and self._automatic_actions_allowed()
            and not self._root_is_hidden()
            and not self.dragging
            and (time.time() - self.last_speech_at) >= 6
            and not self.animation.is_dancing
            and not self.scenario_manager.active_scenario_key()
            and not self.toy_manager.active_toy_key()
            and not self.desk_item_manager.active_item_key()
            and not self.companion_manager.active_interaction_key()
            and not self.companion_manager.blocks_owner_movement()
        )

    def _pick_idle_micro_action(self):
        specialty = self._skin_specialty_context()
        current_state = self.personality.current_state()
        available_companion_keys = {item["key"] for item in self.available_companion_interactions() if item["cooldown_ms"] <= 0 and not item["active"]}
        available_desk_item_keys = {item["key"] for item in self.available_desk_items() if item["cooldown_ms"] <= 0 and not item["active"]}
        weighted = []
        for action in self._idle_micro_action_definitions():
            if action.get("desk_item") and action["desk_item"] not in available_desk_item_keys:
                continue
            if action.get("companion_interaction"):
                if not self.companion_enabled or action["companion_interaction"] not in available_companion_keys:
                    continue
            weight = int(action.get("weight", 1))
            if action["key"] == self._last_idle_micro_action_key:
                weight = max(1, weight - 2)
            if current_state == action.get("state"):
                weight += 2
            if self.mood == "tired" and action["key"] == "coffee-sip":
                weight += 3
            if "network" in self.skin_tags and action["key"] in {"rack-check", "cable-audit"}:
                weight += 4
            if "astronaut" in self.skin_tags and action["key"] in {"suspicious-check", "rack-check"}:
                weight += 2
            if ("squarl" in self.skin_tags or "suit" in self.skin_tags) and action["key"] == "proud-of-nothing":
                weight += 5
            if action.get("desk_item"):
                weight += int(specialty.get("desk_item_bonus", {}).get(action["desk_item"], 0))
            if action.get("companion_interaction"):
                weight += int(specialty.get("companion_bonus", {}).get(action["companion_interaction"], 0))
                weight = int(weight * self._companion_frequency_multiplier())
            weighted.append((action, max(1, weight)))
        if not weighted:
            return None
        total = sum(weight for _action, weight in weighted)
        pick = random.uniform(0, total)
        current = 0.0
        for action, weight in weighted:
            current += weight
            if pick <= current:
                return action
        return weighted[-1][0]

    def _run_idle_micro_action(self, action):
        if not action:
            return False
        anything_started = False
        if action.get("state"):
            anything_started = self._set_personality_state(
                action["state"],
                reason=f"micro:{action['key']}",
                duration_ms=3_800,
            ) or anything_started
        if self.movement_enabled and action.get("movement_style"):
            self.movement.set_scripted(
                action["movement_style"],
                duration_ms=1_600,
                focus=action.get("focus", ""),
            )
            anything_started = True
        if action.get("desk_item"):
            anything_started = self._trigger_desk_item(
                action["desk_item"],
                show_saying=False,
                source=f"micro:{action['key']}",
                extra_contexts=list(action.get("contexts", [])),
                extra_categories=list(action.get("categories", [])),
                extra_packs=list(action.get("packs", [])),
            ) or anything_started
        if action.get("companion_interaction"):
            anything_started = self._trigger_companion_interaction(
                action["companion_interaction"],
                source=f"micro:{action['key']}",
            ) or anything_started
        if (
            anything_started
            and float(action.get("quote_chance", 0.0)) > 0.0
            and self._can_speak(9 if self.quote_frequency == "chatty" else 12)
            and random.random() <= float(action.get("quote_chance", 0.0))
        ):
            self._show_saying(
                source=f"micro:{action['key']}",
                extra_contexts=list(action.get("contexts", [])),
                extra_categories=list(action.get("categories", [])),
                extra_packs=list(action.get("packs", [])),
            )
        return anything_started

    def _idle_micro_action_tick(self):
        if self.is_quitting:
            return None
        if not self._automatic_idle_micro_actions_allowed():
            return self._random_idle_micro_action_delay()
        action = self._pick_idle_micro_action()
        if action and self._run_idle_micro_action(action):
            self._last_idle_micro_action_key = str(action.get("key", ""))
            self._last_idle_micro_action_at = time.time()
            self.logger.info(f"idle micro-action: {self._last_idle_micro_action_key}")
        return self._random_idle_micro_action_delay()

    def _movement_tick(self):
        if self.is_quitting:
            return None
        snapshot = self.runtime_state.snapshot()
        if (
            not self.movement_enabled
            or not snapshot.automatic_actions_allowed
            or self.dragging
            or self.toy_manager.active_toy_key()
            or self.desk_item_manager.active_item_key()
            or self.companion_manager.blocks_owner_movement()
        ):
            return MOVEMENT_TICK_MS
        result = self.movement.tick(
            self.window_x,
            self.window_y,
            self._movement_bounds(),
            style=self.personality.movement_style(),
        )
        if result.moved:
            self.window_x, self.window_y = self._clamp_window_position(result.x, result.y)
            self._apply_window_position(0)
        return result.next_delay_ms

    def _start_scenario(self, scenario_key, reveal_if_hidden=False, source="scenario"):
        if self.is_quitting or not scenario_key:
            return False
        if self._root_is_hidden():
            if reveal_if_hidden:
                self.window.show()
                self.runtime_state.set_visibility(False)
            else:
                return False
        if not self.scenario_manager.start(scenario_key, unlock_manager=self.unlock_manager):
            if reveal_if_hidden:
                for option in self.available_scenarios():
                    if option["key"] == scenario_key and option["cooldown_ms"] > 0:
                        seconds = max(1, int(option["cooldown_ms"] / 1000))
                        self._show_text(f"{option['label']} is cooling down.\nTry again in {seconds}s.")
                        break
            return False
        definition = self.scenario_manager.definition(scenario_key)
        if definition and source != "scenario-manual":
            self._maybe_shift_skin_for_context(
                preferred_tags=definition.preferred_skin_tags,
                reason=f"scenario:{scenario_key}",
                force=False,
            )
        self.last_scenario_key = scenario_key
        self._record_discovery_progress("scenario_runs", 1, schedule_save=False)
        self._play_scenario_sound(scenario_key)
        self._schedule_settings_save()
        self._refresh_tray()
        self._scenario_tick()
        return True

    def _execute_scenario_step(self, step, scenario_key):
        action = str(step.action or "").strip()
        payload = dict(step.payload or {})
        if action == "set_state":
            return self._set_personality_state(
                step.value,
                reason=f"scenario:{scenario_key}",
                duration_ms=payload.get("duration_ms"),
                lock_ms=payload.get("lock_ms", 0),
                play_sound=bool(payload.get("play_sound", True)),
            )
        if action == "movement":
            if not self.movement_enabled:
                return False
            self.movement.set_scripted(
                step.value or self.personality.movement_style(),
                duration_ms=int(payload.get("duration_ms", 1800)),
                focus=payload.get("focus", ""),
            )
            return True
        if action == "toy":
            return self._trigger_toy(
                step.value,
                reveal_if_hidden=False,
                show_saying=bool(payload.get("show_saying", False)),
                source=f"scenario:{scenario_key}",
                extra_contexts=list(payload.get("contexts", [])) + ["scenario", scenario_key],
                extra_categories=list(payload.get("categories", [])),
            )
        if action == "desk_item":
            return self._trigger_desk_item(
                step.value,
                reveal_if_hidden=False,
                show_saying=bool(payload.get("show_saying", False)),
                source=f"scenario:{scenario_key}",
                extra_contexts=list(payload.get("contexts", [])) + ["scenario", scenario_key],
                extra_categories=list(payload.get("categories", [])),
                extra_packs=list(payload.get("packs", [])),
            )
        if action == "companion":
            return self._trigger_companion_interaction(
                step.value,
                reveal_if_hidden=False,
                source=f"scenario:{scenario_key}",
            )
        if action == "quote":
            return self._show_saying(
                reveal_if_hidden=False,
                source=f"scenario:{scenario_key}",
                extra_contexts=list(payload.get("contexts", [])) + ["scenario", scenario_key],
                extra_categories=list(payload.get("categories", [])),
                extra_packs=list(payload.get("packs", [])),
            )
        if action == "sound":
            self._play_effect(
                step.value,
                category=payload.get("category", "scenario"),
                throttle_ms=int(payload.get("throttle_ms", 7000)),
                throttle_key=payload.get("throttle_key", f"scenario-step:{scenario_key}:{step.value}"),
            )
            return True
        if action == "dance":
            return self._trigger_dance(
                show_saying=bool(payload.get("show_saying", False)),
                routine_key=payload.get("routine"),
            )
        return False

    def _scenario_tick(self):
        if self.is_quitting:
            return None
        result = self.scenario_manager.tick()
        if result.command:
            active_key = self.scenario_manager.active_scenario_key() or self.last_scenario_key
            self._execute_scenario_step(result.command, active_key)
        if result.completed_scenario:
            self.last_scenario_key = result.completed_scenario
            self.recent_scenario_keys = self.scenario_manager.recent_history()
            self._schedule_settings_save()
            self._refresh_tray()
        return SCENARIO_TICK_MS

    def _continuity_tick(self):
        if self.is_quitting:
            return None
        self._record_discovery_progress("runtime_minutes", 1, schedule_save=False)
        self.recent_scenario_keys = self.scenario_manager.recent_history()
        self._flush_discovery_notifications(reveal_if_hidden=False)
        self._schedule_settings_save()
        return CONTINUITY_TICK_MS

    def reload_dialogue(self):
        self._apply_dialogue_pack_states()
        self.dialogue.reload_if_needed(force=True)
        self._log_asset_warnings_if_changed()
        self._refresh_tray()
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
        self._schedule_rare_events()
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
        self._schedule_rare_events()
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
        self._apply_dialogue_pack_states()
        skin_bundle = load_skin_bundle()
        reloaded_skins = skin_bundle["definitions"]
        reloaded_errors = skin_bundle["errors"]
        if reloaded_skins != self.skins or reloaded_errors != self.skin_load_errors:
            self.skins = reloaded_skins
            self.skin_load_errors = reloaded_errors
            if self.skin_key not in self.skins or not self._is_unlocked("skin", self.skin_key):
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

    def _trigger_dance(self, show_saying=False, routine_key=None):
        chosen_routine = str(routine_key or self._pick_dance_routine() or "").strip()
        started = self.animation.start_dance(chosen_routine)
        if not started:
            return False
        active_routine = self.animation.current_dance_key()
        routine_definition = next(
            (routine for routine in self.animation.available_dance_routines() if routine.key == active_routine),
            None,
        )
        self.last_dance_routine_key = active_routine
        self._set_personality_state("celebrating", reason="dance", duration_ms=4800)
        self._play_interaction_sound()
        if routine_definition is not None:
            self._set_comedy_bias(
                contexts=list(routine_definition.contexts),
                categories=list(routine_definition.preferred_categories),
                duration_ms=14_000,
                label=f"dance:{routine_definition.key}",
            )
        if show_saying:
            self._show_saying(
                source="interaction",
                extra_contexts=list(routine_definition.contexts) if routine_definition else ["dance"],
                extra_categories=list(routine_definition.preferred_categories) if routine_definition else ["dance"],
            )
        return True

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
        compact = " ".join(str(title or "").split())
        if len(compact) > 36:
            return compact[:33].rstrip() + "..."
        return compact

    def _notification_runtime_context(self):
        return {
            "personality_state": self.personality.current_state(),
            "active_desk_item": self.desk_item_manager.active_item_key(),
            "active_companion_interaction": self.companion_manager.active_interaction_key(),
        }

    def _maybe_trigger_notification_reaction(self, observation):
        if not observation.get("interesting"):
            return False
        if (
            not self.event_reactions_enabled
            or not self.reaction_toggles.get("focus", True)
            or not self._automatic_actions_allowed()
            or self.animation.is_dancing
            or self.scenario_manager.active_scenario_key()
            or self.toy_manager.active_toy_key()
            or self.desk_item_manager.active_item_key()
            or self.companion_manager.active_interaction_key()
            or (time.time() - self._last_idle_micro_action_at) < 8
        ):
            return False
        definition = pick_notification_reaction(observation, runtime_context=self._notification_runtime_context())
        if definition is None:
            return False
        reaction_key = f"{definition.key}:{observation.get('reaction_key', '')}"
        now_ms = int(time.monotonic() * 1000)
        if (
            reaction_key == self._last_notification_reaction_key
            and (now_ms - int(self._last_notification_reaction_at * 1000)) < int(definition.cooldown_ms)
        ):
            return False
        chance = float(definition.chance) * min(1.35, 0.82 + ((1.35 - self._activity_multiplier()) * 0.45))
        if random.random() > max(0.0, min(1.0, chance)):
            return False
        anything_started = False
        anything_started = self._set_personality_state(
            definition.state_key,
            reason=f"notification:{definition.key}",
            duration_ms=4_400,
        ) or anything_started
        if definition.desk_item_key:
            anything_started = self._trigger_desk_item(
                definition.desk_item_key,
                show_saying=False,
                source=f"notification:{definition.key}",
                extra_contexts=list(definition.quote_contexts),
                extra_categories=list(definition.preferred_categories),
                extra_packs=list(definition.preferred_packs),
            ) or anything_started
        if definition.companion_interaction and random.random() <= min(1.0, 0.36 * self._companion_frequency_multiplier()):
            anything_started = self._trigger_companion_interaction(
                definition.companion_interaction,
                source=f"notification:{definition.key}",
            ) or anything_started
        if self._can_speak(12):
            anything_started = self._show_saying(
                source=f"notification:{definition.key}",
                extra_contexts=list(definition.quote_contexts) + list(observation.get("contexts", [])),
                extra_categories=list(definition.preferred_categories) + list(observation.get("categories", [])),
                extra_packs=list(definition.preferred_packs) + list(observation.get("preferred_packs", [])),
                render_overrides={
                    **dict(observation.get("render_overrides", {})),
                    **dict(definition.render_overrides or {}),
                },
            ) or anything_started
        if anything_started:
            self._last_notification_reaction_key = reaction_key
            self._last_notification_reaction_at = time.time()
            self.logger.info(f"notification reaction: {reaction_key}")
        return anything_started

    def _handle_foreground_change_event(self, title):
        title = str(title or "").strip()
        self.last_active_window_title = title
        self.runtime_state.note_foreground_window(title)
        self._refresh_suppression_state()
        if is_screenshot_window_title(title):
            self.logger.info(f"Foreground screenshot/capture window detected: {title}")
            return
        trimmed = self._trim_window_title(title)
        observation = classify_window_title(trimmed)
        if observation.get("interesting"):
            self._set_comedy_bias(
                contexts=observation.get("contexts", []),
                categories=observation.get("categories", []),
                packs=observation.get("preferred_packs", []),
                render_overrides=observation.get("render_overrides", {}),
                duration_ms=18_000,
                label=f"title:{observation.get('reaction_key', '')[:32]}",
            )
        if not self.event_reactions_enabled:
            return
        if title in {"", APP_NAME, "Program Manager"} or not self.reaction_toggles.get("focus", True):
            return
        if self.animation.is_dancing or self.scenario_manager.active_scenario_key():
            return
        if not self._automatic_actions_allowed() or self.companion_manager.blocks_owner_movement():
            return
        now = time.time()
        if (
            observation.get("interesting")
            and self._can_speak(24)
            and observation.get("reaction_key") != self._last_title_reaction_key
            and now - self._last_title_joke_at >= 24
            and random.random() < float(observation.get("chance", 0.0))
        ):
            if self._show_saying(
                source="focus-title",
                extra_contexts=observation.get("contexts", []),
                extra_categories=observation.get("categories", []),
                extra_packs=observation.get("preferred_packs", []),
                render_overrides=observation.get("render_overrides", {}),
            ):
                self._last_title_joke_at = now
                self._last_title_reaction_key = observation.get("reaction_key", "")
                return
        if self._maybe_trigger_notification_reaction(observation):
            return
        if self._can_speak(16) and random.random() < 0.18:
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

    def _new_context_menu(self, parent):
        return tk.Menu(
            parent,
            tearoff=0,
            bg="#1a1a2e",
            fg="#fef9e7",
            activebackground="#3a86c8",
            activeforeground="#ffffff",
            font=("Consolas", 10),
        )

    def _build_skin_menu(self, parent):
        menu = self._new_context_menu(parent)
        selected_skin = tk.StringVar(value=self.skin_key)
        for skin_key, skin_data in sorted(self.skins.items()):
            if skin_key not in self.available_skin_keys():
                continue
            label = skin_data.get("label", skin_key)
            if self._is_favorite("skin", skin_key):
                label = "★ " + label
            menu.add_radiobutton(
                label=label,
                value=skin_key,
                variable=selected_skin,
                command=lambda chosen=skin_key: self._set_skin(chosen),
            )
        return menu

    def _build_toy_menu(self, parent):
        menu = self._new_context_menu(parent)
        toys = self.available_toys()
        if not toys:
            menu.add_command(label="No toys loaded", state="disabled")
            return menu
        for toy in toys:
            base_label = ("★ " if toy.get("favorite") else "") + toy["label"]
            label = base_label if toy["cooldown_ms"] <= 0 else f"{base_label} ({max(1, toy['cooldown_ms'] // 1000)}s)"
            menu.add_command(
                label=label,
                command=lambda chosen=toy["key"]: self._trigger_toy_from_menu(chosen),
                state="normal" if toy["cooldown_ms"] <= 0 and not toy["active"] else "disabled",
            )
        return menu

    def _build_desk_item_menu(self, parent):
        menu = self._new_context_menu(parent)
        items = self.available_desk_items()
        if not items:
            menu.add_command(label="No desk items loaded", state="disabled")
            return menu
        for desk_item in items:
            label = (
                desk_item["label"]
                if desk_item["cooldown_ms"] <= 0
                else f"{desk_item['label']} ({max(1, desk_item['cooldown_ms'] // 1000)}s)"
            )
            menu.add_command(
                label=label,
                command=lambda chosen=desk_item["key"]: self._trigger_desk_item_from_menu(chosen),
                state="normal" if desk_item["cooldown_ms"] <= 0 and not desk_item["active"] else "disabled",
            )
        return menu

    def _build_companion_menu(self, parent):
        menu = self._new_context_menu(parent)
        menu.add_checkbutton(
            label="Show Companion",
            onvalue=True,
            offvalue=False,
            variable=tk.BooleanVar(value=self.companion_enabled),
            command=self._toggle_companion_enabled,
        )
        menu.add_separator()
        companions = self.available_companions()
        if not companions:
            menu.add_command(label="No companions loaded", state="disabled")
            return menu
        selected = tk.StringVar(value=self.selected_companion_key)
        for companion in companions:
            label = companion["label"]
            if companion.get("state_label"):
                label = f"{label} | {companion['state_label']}"
            menu.add_radiobutton(
                label=label,
                value=companion["key"],
                variable=selected,
                command=lambda chosen=companion["key"]: self._set_companion(chosen),
            )
        menu.add_separator()
        interactions = self.available_companion_interactions()
        if not interactions:
            menu.add_command(label="No interactions", state="disabled")
            return menu
        for interaction in interactions:
            label = (
                interaction["label"]
                if interaction["cooldown_ms"] <= 0
                else f"{interaction['label']} ({max(1, interaction['cooldown_ms'] // 1000)}s)"
            )
            menu.add_command(
                label=label,
                command=lambda chosen=interaction["key"]: self._trigger_companion_interaction_from_menu(chosen),
                state="normal" if interaction["cooldown_ms"] <= 0 and not interaction["active"] else "disabled",
            )
        return menu

    def _build_quote_pack_menu(self, parent):
        menu = self._new_context_menu(parent)
        packs = self.available_quote_packs()
        if not packs:
            menu.add_command(label="No quote packs loaded", state="disabled")
            return menu
        for pack in packs:
            menu.add_checkbutton(
                label=("★ " if pack.get("favorite") else "") + pack["label"],
                onvalue=True,
                offvalue=False,
                variable=tk.BooleanVar(value=pack["enabled"]),
                command=lambda chosen=pack["key"]: self._toggle_quote_pack(chosen),
            )
        return menu

    def _build_scenario_menu(self, parent):
        menu = self._new_context_menu(parent)
        scenarios = self.available_scenarios()
        if not scenarios:
            menu.add_command(label="No scenarios unlocked", state="disabled")
            return menu
        for scenario in scenarios:
            if not scenario["unlocked"]:
                continue
            base_label = ("★ " if scenario.get("favorite") else "") + scenario["label"]
            label = (
                base_label
                if scenario["cooldown_ms"] <= 0
                else f"{base_label} ({max(1, scenario['cooldown_ms'] // 1000)}s)"
            )
            menu.add_command(
                label=label,
                command=lambda chosen=scenario["key"]: self._trigger_scenario_from_menu(chosen),
                state="normal" if scenario["cooldown_ms"] <= 0 and not scenario["active"] else "disabled",
            )
        return menu

    def _build_special_mode_menu(self, parent):
        menu = self._new_context_menu(parent)
        selected = tk.StringVar(value=self.seasonal_mode_override)
        for option in self.available_seasonal_modes():
            menu.add_radiobutton(
                label=option["label"],
                value=option["key"],
                variable=selected,
                command=lambda chosen=option["key"]: self._set_seasonal_mode(chosen),
            )
        return menu

    def _build_behavior_tuning_menu(self, parent):
        menu = self._new_context_menu(parent)
        activity_menu = self._new_context_menu(menu)
        activity_var = tk.StringVar(value=self.activity_level)
        for key, label in (("low", "Low Activity"), ("normal", "Normal Activity"), ("high", "High Activity")):
            activity_menu.add_radiobutton(
                label=label,
                value=key,
                variable=activity_var,
                command=lambda chosen=key: self._set_activity_level(chosen),
            )
        quote_menu = self._new_context_menu(menu)
        quote_var = tk.StringVar(value=self.quote_frequency)
        for key, label in (("quiet", "Quiet Quotes"), ("normal", "Normal Quotes"), ("chatty", "Chatty Quotes")):
            quote_menu.add_radiobutton(
                label=label,
                value=key,
                variable=quote_var,
                command=lambda chosen=key: self._set_quote_frequency(chosen),
            )
        companion_menu = self._new_context_menu(menu)
        companion_var = tk.StringVar(value=self.companion_frequency)
        for key, label in (("low", "Low Companion"), ("normal", "Normal Companion"), ("high", "High Companion")):
            companion_menu.add_radiobutton(
                label=label,
                value=key,
                variable=companion_var,
                command=lambda chosen=key: self._set_companion_frequency(chosen),
            )
        menu.add_cascade(label="Activity", menu=activity_menu)
        menu.add_cascade(label="Quote Frequency", menu=quote_menu)
        menu.add_cascade(label="Companion Frequency", menu=companion_menu)
        return menu

    def _on_right_click(self, event):
        menu = self._new_context_menu(self.root)
        menu.add_command(label=f"Mood: {MOODS[self.mood]['label']}", state="disabled")
        menu.add_command(label=f"State: {self._personality_label()}", state="disabled")
        menu.add_command(label=f"Name: {self.pet_name}", state="disabled")
        if self.companion_enabled:
            menu.add_command(
                label=f"Companion: {self.companion_manager.current_companion_label()} | {self.companion_manager.current_state_label()}",
                state="disabled",
            )
        if self._active_toy_label():
            menu.add_command(label=f"Toy: {self._active_toy_label()}", state="disabled")
        elif self._active_desk_item_label():
            menu.add_command(label=f"Desk Item: {self._active_desk_item_label()}", state="disabled")
        elif self._active_scenario_label():
            menu.add_command(label=f"Scenario: {self._active_scenario_label()}", state="disabled")
        menu.add_command(label="Trigger Quote", command=lambda: self._show_saying(True))
        menu.add_command(label="Dance!", command=lambda: self._trigger_dance(True))
        menu.add_cascade(label="Companion", menu=self._build_companion_menu(menu))
        menu.add_command(label="Repeat Last Saying", command=self.repeat_last_saying)
        menu.add_command(label="Favorite Last Saying", command=self.favorite_last_saying)
        menu.add_command(label="Random Favorite", command=self.say_random_favorite)
        menu.add_command(label="Summon a Friend", command=self._summon_friend)
        menu.add_command(label="Bring Back On Screen", command=self.bring_back_on_screen)
        menu.add_command(label="Settings", command=self._open_settings_window)
        menu.add_cascade(label="Choose Skin", menu=self._build_skin_menu(menu))
        menu.add_cascade(label="Desk Items", menu=self._build_desk_item_menu(menu))
        menu.add_cascade(label="Toys", menu=self._build_toy_menu(menu))
        menu.add_cascade(label="Scenarios", menu=self._build_scenario_menu(menu))
        menu.add_cascade(label="Quote Packs", menu=self._build_quote_pack_menu(menu))
        menu.add_cascade(label="Behavior Tuning", menu=self._build_behavior_tuning_menu(menu))
        menu.add_cascade(label="Special Mode", menu=self._build_special_mode_menu(menu))
        menu.add_checkbutton(
            label="Mute Sounds",
            onvalue=True,
            offvalue=False,
            variable=tk.BooleanVar(value=not self.sound_enabled),
            command=self._toggle_sound_enabled,
        )
        menu.add_checkbutton(
            label="Rare Events",
            onvalue=True,
            offvalue=False,
            variable=tk.BooleanVar(value=self.rare_events_enabled),
            command=self._toggle_rare_events_enabled,
        )
        menu.add_checkbutton(
            label="Chaos Mode",
            onvalue=True,
            offvalue=False,
            variable=tk.BooleanVar(value=self.chaos_mode),
            command=self._toggle_chaos_mode,
        )
        menu.add_checkbutton(
            label="Autonomous Movement",
            onvalue=True,
            offvalue=False,
            variable=tk.BooleanVar(value=self.movement_enabled),
            command=self._toggle_movement_enabled,
        )
        menu.add_checkbutton(
            label="Unlockable Discoveries",
            onvalue=True,
            offvalue=False,
            variable=tk.BooleanVar(value=self.unlocks_enabled),
            command=self._toggle_unlocks_enabled,
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
        if self.seasonal_mode_override == "auto":
            seasonal_label = (
                self.seasonal_manager.primary_mode().label
                if self.seasonal_manager.primary_mode()
                else "Auto"
            )
        elif self.seasonal_mode_override == "off":
            seasonal_label = "Off"
        else:
            seasonal_label = self.seasonal_mode_override.replace("-", " ").title()
        return TrayState(
            pet_name=self.pet_name,
            mood_label=MOODS[self.mood]["label"],
            personality_label=self._personality_label(),
            skin_key=self.skin_key,
            sound_enabled=self.sound_enabled,
            auto_start_enabled=self.startup_manager.is_enabled(),
            rare_events_enabled=self.rare_events_enabled,
            chaos_mode=self.chaos_mode,
            movement_enabled=self.movement_enabled,
            companion_enabled=self.companion_enabled,
            companion_label=self.companion_manager.current_companion_label(),
            companion_state_label=self.companion_manager.current_state_label(),
            unlocks_enabled=self.unlocks_enabled,
            active_toy_label=self._active_toy_label(),
            active_desk_item_label=self._active_desk_item_label(),
            active_scenario_label=self._active_scenario_label(),
            seasonal_mode_label=seasonal_label,
            activity_level=self.activity_level,
            quote_frequency=self.quote_frequency,
            companion_frequency=self.companion_frequency,
            skin_options=[
                TraySkinOption(key=skin_key, label=skin_data.get("label", skin_key))
                for skin_key, skin_data in sorted(self.skins.items())
                if skin_key in self.available_skin_keys()
            ],
            companion_options=[
                TrayCompanionOption(
                    key=companion["key"],
                    label=companion["label"],
                    enabled=companion.get("enabled", False),
                    selected=companion.get("selected", False),
                    state_label=companion.get("state_label", ""),
                )
                for companion in self.available_companions()
            ],
            companion_interactions=[
                TrayCompanionInteractionOption(
                    key=interaction["key"],
                    label=interaction["label"],
                    cooldown_ms=interaction["cooldown_ms"],
                    active=interaction["active"],
                )
                for interaction in self.available_companion_interactions()
            ],
            toy_options=[
                TrayToyOption(
                    key=toy["key"],
                    label=toy["label"],
                    cooldown_ms=toy["cooldown_ms"],
                    active=toy["active"],
                    favorite=toy.get("favorite", False),
                )
                for toy in self.available_toys()
            ],
            desk_item_options=[
                TrayDeskItemOption(
                    key=desk_item["key"],
                    label=desk_item["label"],
                    cooldown_ms=desk_item["cooldown_ms"],
                    active=desk_item["active"],
                )
                for desk_item in self.available_desk_items()
            ],
            quote_packs=[
                TrayQuotePackOption(
                    key=pack["key"],
                    label=pack["label"],
                    enabled=pack["enabled"],
                    favorite=pack.get("favorite", False),
                )
                for pack in self.available_quote_packs()
            ],
            scenario_options=[
                TrayScenarioOption(
                    key=scenario["key"],
                    label=scenario["label"],
                    cooldown_ms=scenario["cooldown_ms"],
                    active=scenario["active"],
                    unlocked=scenario["unlocked"],
                    favorite=scenario.get("favorite", False),
                )
                for scenario in self.available_scenarios()
            ],
            seasonal_options=[
                TraySeasonOption(
                    key=option["key"],
                    label=option["label"],
                    active=option.get("active", False),
                )
                for option in self.available_seasonal_modes()
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
            sound_categories=dict(self.sound_categories),
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
            rare_events_enabled=self.rare_events_enabled,
            chaos_mode=self.chaos_mode,
            movement_enabled=self.movement_enabled,
            companion_enabled=self.companion_enabled,
            selected_companion=self.selected_companion_key,
            activity_level=self.activity_level,
            quote_frequency=self.quote_frequency,
            companion_frequency=self.companion_frequency,
            unlocks_enabled=self.unlocks_enabled,
            seasonal_mode_override=self.seasonal_mode_override,
            last_active_season=self.last_active_season,
            reaction_toggles=dict(self.reaction_toggles),
            quote_pack_states=dict(self.quote_pack_states),
            favorite_skins=list(self.favorite_skin_keys),
            favorite_toys=list(self.favorite_toy_keys),
            favorite_scenarios=list(self.favorite_scenario_keys),
            favorite_quote_packs=list(self.favorite_quote_pack_keys),
            unlocked_skins=self.unlock_manager.unlocked_snapshot()["skins"],
            unlocked_toys=self.unlock_manager.unlocked_snapshot()["toys"],
            unlocked_scenarios=self.unlock_manager.unlocked_snapshot()["scenarios"],
            unlocked_quote_packs=self.unlock_manager.unlocked_snapshot()["quote_packs"],
            discovery_stats=self.unlock_manager.stats(),
            recent_scenarios=list(self.scenario_manager.recent_history()),
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
            personality_state=self.personality.current_state(),
            last_scenario=self.last_scenario_key,
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
        self.companion_manager.shutdown()
        self.desk_item_manager.shutdown()
        self.toy_manager.shutdown()
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
