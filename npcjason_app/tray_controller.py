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
class TrayState:
    pet_name: str
    mood_label: str
    skin_key: str
    sound_enabled: bool
    auto_start_enabled: bool
    skin_options: List[TraySkinOption] = field(default_factory=list)
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
    bring_back: Callable
    check_updates: Callable
    open_releases: Callable
    open_data: Callable
    open_log: Callable
    quit: Callable


def build_tray_snapshot(state):
    return {
        "title": f"{state.pet_name} | {state.mood_label}",
        "skin_labels": [skin.label for skin in state.skin_options],
        "selected_skin": state.skin_key,
        "sound_enabled": bool(state.sound_enabled),
        "auto_start_enabled": bool(state.auto_start_enabled),
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
        return pystray.Menu(
            item("Show/Hide", self._dispatch(self.actions.toggle_visibility), default=True),
            item(lambda menu_item: snapshot["title"], lambda icon, menu_item: None, enabled=False),
            item("Choose Skin", pystray.Menu(*skin_items)),
            item("Dance!", self._dispatch(self.actions.dance)),
            item("Say Something", self._dispatch(self.actions.say)),
            item("Repeat Last Saying", self._dispatch(self.actions.repeat_last)),
            item("Favorite Last Saying", self._dispatch(self.actions.favorite_last)),
            item("Random Favorite", self._dispatch(self.actions.random_favorite)),
            item("Summon a Friend", self._dispatch(self.actions.summon_friend)),
            item("Pets", pets_menu),
            item("Settings", self._dispatch(self.actions.open_settings)),
            item("Start With Windows", self._dispatch(self.actions.toggle_auto_start), checked=lambda menu_item: self.state_provider().auto_start_enabled),
            item("Sound Effects", self._dispatch(self.actions.toggle_sound), checked=lambda menu_item: self.state_provider().sound_enabled),
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
