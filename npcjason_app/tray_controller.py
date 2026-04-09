from __future__ import annotations

from dataclasses import dataclass, field
import threading
from typing import Callable, List

try:
    import pystray
    from pystray import MenuItem as item

    HAS_TRAY = True
except ImportError:
    pystray = None
    item = None
    HAS_TRAY = False

try:
    from PIL import Image, ImageDraw

    HAS_PIL = True
except ImportError:
    Image = None
    ImageDraw = None
    HAS_PIL = False


@dataclass
class TraySkinOption:
    key: str
    label: str


@dataclass
class TrayPetOption:
    pet_id: str
    label: str


@dataclass
class TrayCompanionOption:
    key: str
    label: str
    enabled: bool = True
    selected: bool = False
    state_label: str = ""


@dataclass
class TrayCompanionInteractionOption:
    key: str
    label: str
    cooldown_ms: int = 0
    active: bool = False


@dataclass
class TrayToyOption:
    key: str
    label: str
    cooldown_ms: int = 0
    active: bool = False
    favorite: bool = False


@dataclass
class TrayQuotePackOption:
    key: str
    label: str
    enabled: bool = True
    favorite: bool = False


@dataclass
class TrayScenarioOption:
    key: str
    label: str
    cooldown_ms: int = 0
    active: bool = False
    unlocked: bool = True
    favorite: bool = False


@dataclass
class TraySeasonOption:
    key: str
    label: str
    active: bool = False


@dataclass
class TrayState:
    pet_name: str
    mood_label: str
    personality_label: str
    skin_key: str
    sound_enabled: bool
    auto_start_enabled: bool
    rare_events_enabled: bool = True
    chaos_mode: bool = False
    movement_enabled: bool = True
    companion_enabled: bool = True
    companion_label: str = ""
    companion_state_label: str = ""
    unlocks_enabled: bool = True
    active_toy_label: str = ""
    active_scenario_label: str = ""
    seasonal_mode_label: str = "Auto"
    skin_options: List[TraySkinOption] = field(default_factory=list)
    companion_options: List[TrayCompanionOption] = field(default_factory=list)
    companion_interactions: List[TrayCompanionInteractionOption] = field(default_factory=list)
    toy_options: List[TrayToyOption] = field(default_factory=list)
    quote_packs: List[TrayQuotePackOption] = field(default_factory=list)
    scenario_options: List[TrayScenarioOption] = field(default_factory=list)
    seasonal_options: List[TraySeasonOption] = field(default_factory=list)
    pets: List[TrayPetOption] = field(default_factory=list)
    tray_colors: dict = field(default_factory=dict)


@dataclass
class TrayActions:
    toggle_visibility: Callable
    select_skin: Callable
    dance: Callable
    say: Callable
    repeat_last: Callable
    favorite_last: Callable
    random_favorite: Callable
    summon_friend: Callable
    dismiss_pet: Callable
    open_settings: Callable
    toggle_auto_start: Callable
    toggle_sound: Callable
    toggle_rare_events: Callable
    toggle_chaos_mode: Callable
    toggle_movement: Callable
    toggle_companion: Callable
    select_companion: Callable
    trigger_companion_interaction: Callable
    toggle_unlocks: Callable
    trigger_toy: Callable
    trigger_quote: Callable
    toggle_quote_pack: Callable
    trigger_scenario: Callable
    set_seasonal_mode: Callable
    bring_back: Callable
    check_updates: Callable
    open_releases: Callable
    open_data: Callable
    open_log: Callable
    quit: Callable


def build_tray_snapshot(state):
    title = f"{state.pet_name} | {state.mood_label} | {state.personality_label}"
    if state.active_toy_label:
        title += f" | {state.active_toy_label}"
    elif state.active_scenario_label:
        title += f" | {state.active_scenario_label}"
    return {
        "title": title,
        "skin_labels": [skin.label for skin in state.skin_options],
        "selected_skin": state.skin_key,
        "sound_enabled": bool(state.sound_enabled),
        "auto_start_enabled": bool(state.auto_start_enabled),
        "rare_events_enabled": bool(state.rare_events_enabled),
        "chaos_mode": bool(state.chaos_mode),
        "movement_enabled": bool(state.movement_enabled),
        "companion_enabled": bool(state.companion_enabled),
        "companion_label": state.companion_label,
        "companion_state": state.companion_state_label,
        "unlocks_enabled": bool(state.unlocks_enabled),
        "companion_labels": [companion.label for companion in state.companion_options],
        "companion_interactions": [interaction.label for interaction in state.companion_interactions],
        "toy_labels": [toy.label for toy in state.toy_options],
        "quote_packs": [pack.label for pack in state.quote_packs],
        "scenario_labels": [scenario.label for scenario in state.scenario_options],
        "seasonal_mode": state.seasonal_mode_label,
        "pets": [pet.label for pet in state.pets],
    }


class TrayController:
    def __init__(self, app_name, app_version, dispatch, state_provider, actions, logger=None):
        self.app_name = app_name
        self.app_version = app_version
        self.dispatch = dispatch
        self.state_provider = state_provider
        self.actions = actions
        self.logger = logger
        self.icon = None
        self._thread = None
        self._stop_requested = False

    def available(self):
        return HAS_TRAY and HAS_PIL

    def start(self):
        if not self.available():
            self._log("warning", "System tray dependencies are unavailable; tray icon disabled")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop_requested = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def refresh(self):
        if not self.icon:
            return
        try:
            state = self.state_provider()
            self.icon.icon = self._make_icon(state)
            self.icon.menu = self._build_menu(state)
            self.icon.update_menu()
        except Exception:
            self._log("exception", "Failed to refresh tray menu")

    def stop(self):
        self._stop_requested = True
        if not self.icon:
            return
        try:
            self.icon.stop()
        except Exception:
            self._log("exception", "Failed to stop tray icon")
        finally:
            self.icon = None

    def _run(self):
        try:
            if self._stop_requested:
                return
            state = self.state_provider()
            self.icon = pystray.Icon(
                self.app_name,
                self._make_icon(state),
                f"{self.app_name} {self.app_version}",
                menu=self._build_menu(state),
            )
            self.icon.run()
        except Exception:
            self._log("exception", "System tray setup failed")
        finally:
            if self._stop_requested:
                self.icon = None

    def _dispatch(self, callback, *args):
        def handler(icon=None, menu_item=None):
            self.dispatch(callback, *args)

        return handler

    def _build_menu(self, state):
        snapshot = build_tray_snapshot(state)
        skin_items = [
            item(
                skin.label,
                self._dispatch(self.actions.select_skin, skin.key),
                checked=lambda menu_item, chosen=skin.key: self.state_provider().skin_key == chosen,
                radio=True,
            )
            for skin in state.skin_options
        ]
        pets_menu = (
            pystray.Menu(
                *(
                    item(
                        "Dismiss " + pet.label,
                        self._dispatch(self.actions.dismiss_pet, pet.pet_id),
                    )
                    for pet in state.pets
                )
            )
            if state.pets
            else pystray.Menu(item("No other pets", lambda icon, menu_item: None, enabled=False))
        )
        toy_items = [
            item(
                toy.label if toy.cooldown_ms <= 0 else f"{toy.label} ({max(1, toy.cooldown_ms // 1000)}s)",
                self._dispatch(self.actions.trigger_toy, toy.key),
                enabled=lambda menu_item, chosen=toy.key: any(
                    option.key == chosen and option.cooldown_ms <= 0 and not option.active
                    for option in self.state_provider().toy_options
                ),
            )
            for toy in state.toy_options
        ]
        quote_pack_items = [
            item(
                ("★ " if pack.favorite else "") + pack.label,
                self._dispatch(self.actions.toggle_quote_pack, pack.key),
                checked=lambda menu_item, chosen=pack.key: any(
                    option.key == chosen and option.enabled
                    for option in self.state_provider().quote_packs
                ),
            )
            for pack in state.quote_packs
        ]
        scenario_items = [
            item(
                ("★ " if scenario.favorite else "") + (
                    scenario.label
                    if scenario.cooldown_ms <= 0
                    else f"{scenario.label} ({max(1, scenario.cooldown_ms // 1000)}s)"
                ),
                self._dispatch(self.actions.trigger_scenario, scenario.key),
                enabled=lambda menu_item, chosen=scenario.key: any(
                    option.key == chosen and option.cooldown_ms <= 0 and option.unlocked and not option.active
                    for option in self.state_provider().scenario_options
                ),
            )
            for scenario in state.scenario_options
        ]
        companion_items = [
            item(
                companion.label,
                self._dispatch(self.actions.select_companion, companion.key),
                checked=lambda menu_item, chosen=companion.key: any(
                    option.key == chosen and option.selected
                    for option in self.state_provider().companion_options
                ),
                radio=True,
            )
            for companion in state.companion_options
        ]
        companion_interaction_items = [
            item(
                interaction.label if interaction.cooldown_ms <= 0 else f"{interaction.label} ({max(1, interaction.cooldown_ms // 1000)}s)",
                self._dispatch(self.actions.trigger_companion_interaction, interaction.key),
                enabled=lambda menu_item, chosen=interaction.key: any(
                    option.key == chosen and option.cooldown_ms <= 0 and not option.active
                    for option in self.state_provider().companion_interactions
                ),
            )
            for interaction in state.companion_interactions
        ]
        seasonal_items = [
            item(
                option.label,
                self._dispatch(self.actions.set_seasonal_mode, option.key),
                checked=lambda menu_item, chosen=option.key: any(
                    current.key == chosen and current.active
                    for current in self.state_provider().seasonal_options
                ),
                radio=True,
            )
            for option in state.seasonal_options
        ]
        return pystray.Menu(
            item("Show/Hide", self._dispatch(self.actions.toggle_visibility), default=True),
            item(lambda menu_item: snapshot["title"], lambda icon, menu_item: None, enabled=False),
            item("Choose Skin", pystray.Menu(*skin_items)),
            item("Toys", pystray.Menu(*toy_items) if toy_items else pystray.Menu(item("No toys", lambda icon, menu_item: None, enabled=False))),
            item(
                "Scenarios",
                pystray.Menu(*scenario_items)
                if scenario_items
                else pystray.Menu(item("No scenarios", lambda icon, menu_item: None, enabled=False)),
            ),
            item("Dance!", self._dispatch(self.actions.dance)),
            item(
                "Companion",
                pystray.Menu(
                    item("Show Companion", self._dispatch(self.actions.toggle_companion), checked=lambda menu_item: self.state_provider().companion_enabled),
                    item(
                        lambda menu_item: (
                            f"{self.state_provider().companion_label} | {self.state_provider().companion_state_label}"
                            if self.state_provider().companion_label
                            else "No companion selected"
                        ),
                        lambda icon, menu_item: None,
                        enabled=False,
                    ),
                    item(
                        "Choose Companion",
                        pystray.Menu(*companion_items)
                        if companion_items
                        else pystray.Menu(item("No companions", lambda icon, menu_item: None, enabled=False)),
                    ),
                    item(
                        "Interactions",
                        pystray.Menu(*companion_interaction_items)
                        if companion_interaction_items
                        else pystray.Menu(item("No interactions", lambda icon, menu_item: None, enabled=False)),
                    ),
                ),
            ),
            item("Trigger Quote", self._dispatch(self.actions.trigger_quote)),
            item("Quote Packs", pystray.Menu(*quote_pack_items) if quote_pack_items else pystray.Menu(item("No packs", lambda icon, menu_item: None, enabled=False))),
            item(
                "Special Mode",
                pystray.Menu(*seasonal_items)
                if seasonal_items
                else pystray.Menu(item("Auto", lambda icon, menu_item: None, enabled=False)),
            ),
            item("Repeat Last Saying", self._dispatch(self.actions.repeat_last)),
            item("Favorite Last Saying", self._dispatch(self.actions.favorite_last)),
            item("Random Favorite", self._dispatch(self.actions.random_favorite)),
            item("Summon a Friend", self._dispatch(self.actions.summon_friend)),
            item("Pets", pets_menu),
            item("Settings", self._dispatch(self.actions.open_settings)),
            item("Start With Windows", self._dispatch(self.actions.toggle_auto_start), checked=lambda menu_item: self.state_provider().auto_start_enabled),
            item("Mute Sounds", self._dispatch(self.actions.toggle_sound), checked=lambda menu_item: not self.state_provider().sound_enabled),
            item("Rare Events", self._dispatch(self.actions.toggle_rare_events), checked=lambda menu_item: self.state_provider().rare_events_enabled),
            item("Chaos Mode", self._dispatch(self.actions.toggle_chaos_mode), checked=lambda menu_item: self.state_provider().chaos_mode),
            item("Autonomous Movement", self._dispatch(self.actions.toggle_movement), checked=lambda menu_item: self.state_provider().movement_enabled),
            item("Unlockable Discoveries", self._dispatch(self.actions.toggle_unlocks), checked=lambda menu_item: self.state_provider().unlocks_enabled),
            item("Bring Back On Screen", self._dispatch(self.actions.bring_back)),
            item("Check for Updates", self._dispatch(self.actions.check_updates)),
            item("Open Releases Page", self._dispatch(self.actions.open_releases)),
            item("Open Data Folder", self._dispatch(self.actions.open_data)),
            item("Open Log File", self._dispatch(self.actions.open_log)),
            pystray.Menu.SEPARATOR,
            item("Quit", self._dispatch(self.actions.quit)),
        )

    def _make_icon(self, state):
        colors = {
            "hair": state.tray_colors.get("hair", "#4a3728"),
            "body": state.tray_colors.get("body", "#3a86c8"),
            "legs": state.tray_colors.get("legs", "#2d4263"),
        }
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([16, 8, 48, 40], fill="#e8c170", outline="#1a1a2e", width=2)
        draw.rectangle([14, 4, 50, 16], fill=colors["hair"], outline="#1a1a2e", width=1)
        draw.rectangle([22, 20, 28, 26], fill="#16213e")
        draw.rectangle([36, 20, 42, 26], fill="#16213e")
        draw.rectangle([28, 30, 36, 34], fill="#c84b31")
        draw.rectangle([20, 40, 44, 56], fill=colors["body"], outline="#1a1a2e", width=1)
        draw.rectangle([22, 56, 30, 64], fill=colors["legs"])
        draw.rectangle([34, 56, 42, 64], fill=colors["legs"])
        return img

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message)
