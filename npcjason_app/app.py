import argparse
import os
from pathlib import Path
import random
import subprocess
import sys
import threading
import time
import tkinter as tk
import uuid
import webbrowser

try:
    import pystray
    from pystray import MenuItem as item

    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False
    pystray = None
    item = None

try:
    from PIL import Image, ImageDraw

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    Image = None
    ImageDraw = None

from .data.defaults import MOODS, default_settings, default_shared_state
from .dialogue import DialogueLibrary, PET_CONVERSATIONS
from .paths import RESOURCE_DIR, SETTINGS_PATH, SHARED_STATE_PATH
from .settings_window import SettingsWindow
from .skins import (
    BASE_PALETTE,
    CANVAS_H,
    CANVAS_W,
    DANCE_SEQUENCE,
    IDLE_SEQUENCE,
    PIXEL_SCALE,
    build_skin_assets,
    load_skin_files,
)
from .sound import SoundManager
from .startup import StartupManager
from .store import JsonStore, clamp
from .updates import UpdateChecker
from .version import APP_NAME, APP_VERSION
from .windows_events import (
    WindowsEventBridge,
    get_battery_snapshot,
    get_removable_drives,
)


PRESENCE_STALE_SECONDS = 35
CONVERSATION_TTL_SECONDS = 180
IDLE_BASE_DELAY_MS = 240
DANCE_BASE_DELAY_MS = 135
RANDOM_SAYING_RANGE_MS = (3 * 60 * 1000, 8 * 60 * 1000)
MOOD_SHIFT_RANGE_MS = (4 * 60 * 1000, 7 * 60 * 1000)
PRESENCE_POLL_MS = 8000
CONVERSATION_POLL_MS = 2500
CONVERSATION_ATTEMPT_RANGE_MS = (45000, 90000)
COMMAND_POLL_MS = 1500
HOT_RELOAD_MS = 3000
UPDATE_CHECK_DELAY_MS = 10000


class SpeechBubble(tk.Toplevel):
    def __init__(self, parent_x, parent_y, text, master=None):
        super().__init__(master)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg="#1a1a2e")

        frame = tk.Frame(
            self,
            bg="#fef9e7",
            bd=0,
            highlightthickness=2,
            highlightbackground="#1a1a2e",
        )
        frame.pack(padx=2, pady=2)

        label = tk.Label(
            frame,
            text=text,
            bg="#fef9e7",
            fg="#1a1a2e",
            font=("Consolas", 10, "bold"),
            justify="left",
            padx=10,
            pady=6,
            wraplength=260,
        )
        label.pack()

        self.update_idletasks()
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        bubble_x = parent_x - width // 2
        bubble_y = parent_y - height - 10
        self.geometry(f"+{bubble_x}+{bubble_y}")
        self.after(4000 + len(text) * 40, self._fade_out)

    def _fade_out(self):
        try:
            self.destroy()
        except Exception:
            pass


class NPCJasonApp:
    def __init__(self, args):
        self.args = args
        self.pet_id = args.pet_id or "main"
        self.friend_of = args.friend_of
        self.is_quitting = False

        self.settings_store = JsonStore(SETTINGS_PATH, default_settings)
        self.shared_state_store = JsonStore(SHARED_STATE_PATH, default_shared_state)
        self.dialogue = DialogueLibrary()
        self.startup_manager = StartupManager()
        self.update_checker = UpdateChecker()
        self.settings_window = None

        settings = self.settings_store.read()
        instance_settings = settings.get("instances", {}).get(self.pet_id, {})
        global_settings = settings.get("global", {})

        self.sound_enabled = bool(global_settings.get("sound_enabled", True))
        self.sound_volume = int(global_settings.get("sound_volume", 70))
        self.auto_update_enabled = bool(global_settings.get("auto_update_enabled", True))
        self.event_reactions_enabled = bool(global_settings.get("event_reactions_enabled", True))

        self.sound_manager = SoundManager(self.sound_enabled, self.sound_volume)

        self.skins = load_skin_files()
        self.skin_key = instance_settings.get("skin", global_settings.get("default_skin", "jason"))
        if self.skin_key not in self.skins:
            self.skin_key = "jason"

        self.mood = instance_settings.get("mood")
        if self.mood not in MOODS:
            self.mood = random.choice(list(MOODS.keys()))

        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        try:
            self.root.attributes("-transparentcolor", "#010101")
            self.bg_color = "#010101"
        except Exception:
            self.bg_color = "#2d2d2d"
        self.root.configure(bg=self.bg_color)

        self.canvas = tk.Canvas(
            self.root,
            width=CANVAS_W,
            height=CANVAS_H,
            bg=self.bg_color,
            highlightthickness=0,
            cursor="hand2",
        )
        self.canvas.pack()

        self.is_dancing = False
        self.dance_frame_idx = 0
        self.idle_frame_idx = 0
        self.current_bubble = None
        self.dragging = False
        self.drag_start_root = (0, 0)
        self.drag_pointer_offset = (0, 0)
        self.settings_save_after_id = None
        self.last_speech_at = 0.0
        self.last_update_prompt_version = None
        self.manual_update_check_pending = False
        self.last_conversation_started_at = 0.0
        self.seen_conversation_ids = []

        self._apply_skin_assets()

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        default_x = screen_w - CANVAS_W - 120
        default_y = screen_h - CANVAS_H - 80
        start_x = args.x if args.x is not None else instance_settings.get("x", default_x)
        start_y = args.y if args.y is not None else instance_settings.get("y", default_y)
        self.window_x, self.window_y = self._clamp_window_position(start_x, start_y)
        self._apply_window_position(0)

        self.removable_drives = get_removable_drives()
        battery = get_battery_snapshot()
        self.was_battery_low = bool(
            battery and battery["percent"] <= 20 and not battery["charging"]
        )

        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_right_click)

        self.tray_icon = None
        if HAS_TRAY and HAS_PIL:
            threading.Thread(target=self._setup_tray, daemon=True).start()

        self.event_bridge = WindowsEventBridge(
            self.root,
            on_usb_change=self._handle_usb_change_event,
            on_power_change=self._handle_power_change_event,
            on_foreground_change=self._handle_foreground_change_event,
        )
        try:
            self.event_bridge.install()
        except Exception:
            self.event_bridge = None

        self._draw_frame(self.active_frames["idle_open"])
        self._publish_presence()
        self.root.after(0, self._animation_loop)
        self._schedule_random_saying()
        self._schedule_mood_shift()
        self.root.after(PRESENCE_POLL_MS, self._presence_heartbeat)
        self.root.after(CONVERSATION_POLL_MS, self._poll_conversations)
        self._schedule_conversation_attempt()
        self.root.after(COMMAND_POLL_MS, self._poll_commands)
        self.root.after(HOT_RELOAD_MS, self._reload_assets_tick)
        if self.auto_update_enabled:
            self.root.after(UPDATE_CHECK_DELAY_MS, self._auto_check_for_updates)

        if self.friend_of:
            self.root.after(
                1800,
                lambda: self._show_text("Co-op mode engaged.\nDesktop duty accepted."),
            )

        self.root.protocol("WM_DELETE_WINDOW", self._quit)

    def _apply_skin_assets(self):
        assets = build_skin_assets(self.skins[self.skin_key])
        self.active_frames = assets["frames"]
        self.active_palette = dict(BASE_PALETTE)
        self.active_palette.update(assets["palette"])
        self.tray_colors = assets["tray"]

    def _clamp_window_position(self, x, y):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        clamped_x = clamp(int(x), 0, max(0, screen_w - CANVAS_W - 4))
        clamped_y = clamp(int(y), 0, max(0, screen_h - CANVAS_H - 8))
        return clamped_x, clamped_y

    def _apply_window_position(self, offset_y):
        self.root.geometry(f"+{self.window_x}+{self.window_y + int(offset_y)}")

    def _draw_frame(self, frame_data):
        self.canvas.delete("all")
        for row_idx, row in enumerate(frame_data):
            for col_idx, char in enumerate(row):
                if char == "." or char not in self.active_palette:
                    continue
                color = self.active_palette[char]
                x1 = col_idx * PIXEL_SCALE
                y1 = row_idx * PIXEL_SCALE
                x2 = x1 + PIXEL_SCALE
                y2 = y1 + PIXEL_SCALE
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline=color)

    def _render_pose(self, frame_key, offset_y=0):
        self._draw_frame(self.active_frames[frame_key])
        self._apply_window_position(offset_y)

    def _animation_loop(self):
        if self.is_quitting:
            return

        if self.is_dancing:
            frame_key = DANCE_SEQUENCE[self.dance_frame_idx % len(DANCE_SEQUENCE)]
            self._render_pose(frame_key, 0)
            self.dance_frame_idx += 1
            if self.dance_frame_idx >= len(DANCE_SEQUENCE) * 3:
                self.is_dancing = False
                self.dance_frame_idx = 0
                self.idle_frame_idx = 0
            delay_ms = max(85, int(DANCE_BASE_DELAY_MS * MOODS[self.mood]["speed"]))
        else:
            frame_key, offset_y = IDLE_SEQUENCE[self.idle_frame_idx % len(IDLE_SEQUENCE)]
            self._render_pose(frame_key, offset_y)
            self.idle_frame_idx += 1
            delay_ms = max(120, int(IDLE_BASE_DELAY_MS * MOODS[self.mood]["speed"]))

        self.root.after(delay_ms, self._animation_loop)

    def _can_speak(self, min_gap_seconds=8):
        return (time.time() - self.last_speech_at) >= min_gap_seconds

    def _show_text(self, text, reveal_if_hidden=False):
        if self.is_quitting:
            return False
        if self.root.state() == "withdrawn":
            if reveal_if_hidden:
                self.root.deiconify()
            else:
                return False

        if self.current_bubble:
            try:
                self.current_bubble.destroy()
            except Exception:
                pass

        center_x = self.root.winfo_x() + CANVAS_W // 2
        top_y = self.root.winfo_y()
        self.current_bubble = SpeechBubble(center_x, top_y, text, master=self.root)
        self.last_speech_at = time.time()
        self.sound_manager.play("speech")
        return True

    def _show_saying(self, reveal_if_hidden=False):
        return self._show_text(self.dialogue.random_saying(self.mood), reveal_if_hidden)

    def _schedule_random_saying(self):
        self.root.after(random.randint(*RANDOM_SAYING_RANGE_MS), self._random_saying_tick)

    def _random_saying_tick(self):
        if self._can_speak(20):
            self._show_saying()
        self._schedule_random_saying()

    def _schedule_mood_shift(self):
        self.root.after(random.randint(*MOOD_SHIFT_RANGE_MS), self._rotate_mood)

    def _rotate_mood(self):
        if self.is_quitting:
            return
        choices = [mood for mood in MOODS if mood != self.mood]
        self.mood = random.choice(choices)
        self._schedule_settings_save()
        self._refresh_tray()
        self._schedule_mood_shift()

    def available_skin_keys(self):
        return sorted(self.skins.keys())

    def available_skin_labels(self):
        return {key: self.skins[key].get("label", key) for key in self.available_skin_keys()}

    def _set_skin(self, skin_key):
        if skin_key not in self.skins or skin_key == self.skin_key:
            return
        self.skin_key = skin_key
        self._apply_skin_assets()
        self.idle_frame_idx = 0
        if not self.is_dancing:
            self._render_pose("idle_open", 0)
        self._schedule_settings_save()
        self._refresh_tray()

    def _toggle_sound_enabled(self):
        self.sound_enabled = not self.sound_enabled
        self.sound_manager.set_enabled(self.sound_enabled)
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
    ):
        self.sound_enabled = bool(sound_enabled)
        self.sound_volume = int(sound_volume)
        self.auto_update_enabled = bool(auto_update_enabled)
        self.event_reactions_enabled = bool(event_reactions_enabled)
        self.sound_manager.set_enabled(self.sound_enabled)
        self.sound_manager.set_volume(self.sound_volume)
        self.startup_manager.set_enabled(auto_start_enabled)
        self._set_skin(skin_key)
        self._schedule_settings_save()

    def preview_sound(self, volume, enabled):
        self.sound_manager.set_volume(volume)
        self.sound_manager.set_enabled(enabled)
        self.sound_manager.play("speech")

    def reload_dialogue(self):
        self.dialogue.reload_if_needed(force=True)

    def _open_settings_window(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return
        self.settings_window = SettingsWindow(self)

    def _reload_assets_tick(self):
        if self.is_quitting:
            return

        self.dialogue.reload_if_needed()
        reloaded_skins = load_skin_files()
        if reloaded_skins != self.skins:
            self.skins = reloaded_skins
            if self.skin_key not in self.skins:
                self.skin_key = "jason"
            self._apply_skin_assets()
            if not self.is_dancing:
                self._render_pose("idle_open", 0)
            self._refresh_tray()

        self.root.after(HOT_RELOAD_MS, self._reload_assets_tick)

    def _on_press(self, event):
        self.dragging = False
        self.drag_start_root = (event.x_root, event.y_root)
        self.drag_pointer_offset = (
            event.x_root - self.root.winfo_x(),
            event.y_root - self.root.winfo_y(),
        )

    def _on_drag(self, event):
        delta_x = abs(event.x_root - self.drag_start_root[0])
        delta_y = abs(event.y_root - self.drag_start_root[1])
        if not self.dragging and max(delta_x, delta_y) < 3:
            return
        self.dragging = True
        actual_x = event.x_root - self.drag_pointer_offset[0]
        actual_y = event.y_root - self.drag_pointer_offset[1]
        self.window_x, self.window_y = self._clamp_window_position(actual_x, actual_y)
        self._apply_window_position(0)

    def _on_release(self, _event):
        if self.dragging:
            self.dragging = False
            self._schedule_settings_save()
            self._publish_presence()
            return
        self._trigger_dance(show_saying=True)

    def _trigger_dance(self, show_saying=False):
        self.is_dancing = True
        self.dance_frame_idx = 0
        self.sound_manager.play("dance")
        if show_saying:
            self._show_saying()

    def _active_other_instances(self):
        now = time.time()
        shared_state = self.shared_state_store.read()
        active = []
        for pet_id, info in shared_state.get("instances", {}).items():
            if pet_id == self.pet_id:
                continue
            if now - info.get("updated_at", 0) > PRESENCE_STALE_SECONDS:
                continue
            active.append((pet_id, info))
        return active

    def list_active_pets(self):
        entries = []
        for pet_id, info in self._active_other_instances():
            description = f"{info.get('skin', 'jason')} | {info.get('mood', 'happy')}"
            entries.append((pet_id, description))
        return entries

    def _friend_spawn_position(self):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        offset_x = self.window_x + CANVAS_W + 40
        if offset_x > screen_w - CANVAS_W - 4:
            offset_x = self.window_x - CANVAS_W - 40
        offset_y = self.window_y - 10
        return self._clamp_window_position(offset_x, clamp(offset_y, 0, screen_h - CANVAS_H))

    def _summon_friend(self):
        friend_id = f"friend-{uuid.uuid4().hex[:6]}"
        friend_x, friend_y = self._friend_spawn_position()
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
            ]
            cwd = str(RESOURCE_DIR)
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
            ]
            cwd = str(RESOURCE_DIR)

        try:
            subprocess.Popen(
                command,
                cwd=cwd,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            self._show_text("Summon spell fizzled.\nCould not launch a friend.")

    def summon_friend_from_settings(self):
        self._summon_friend()

    def _enqueue_command(self, target_pet_id, action):
        def mutate(data):
            self._cleanup_shared_state(data)
            data.setdefault("commands", []).append(
                {
                    "id": uuid.uuid4().hex,
                    "created_at": time.time(),
                    "target": target_pet_id,
                    "action": action,
                }
            )

        self.shared_state_store.update(mutate)

    def dismiss_pet(self, pet_id):
        if pet_id and pet_id != self.pet_id:
            self._enqueue_command(pet_id, "quit")

    def dismiss_all_friends(self):
        for pet_id, _info in self._active_other_instances():
            self._enqueue_command(pet_id, "quit")

    def _cleanup_shared_state(self, data):
        now = time.time()
        instances = data.setdefault("instances", {})
        stale_ids = [
            pet_id
            for pet_id, info in instances.items()
            if now - info.get("updated_at", 0) > PRESENCE_STALE_SECONDS
        ]
        for stale_id in stale_ids:
            instances.pop(stale_id, None)

        data["conversations"] = [
            conversation
            for conversation in data.setdefault("conversations", [])
            if now - conversation.get("created_at", 0) <= CONVERSATION_TTL_SECONDS
        ]
        data["commands"] = [
            command
            for command in data.setdefault("commands", [])
            if now - command.get("created_at", 0) <= 30
        ]

    def _publish_presence(self):
        def mutate(data):
            self._cleanup_shared_state(data)
            data["instances"][self.pet_id] = {
                "updated_at": time.time(),
                "x": self.window_x,
                "y": self.window_y,
                "mood": self.mood,
                "skin": self.skin_key,
                "friend_of": self.friend_of,
                "pid": os.getpid(),
            }

        self.shared_state_store.update(mutate)

    def _presence_heartbeat(self):
        if self.is_quitting:
            return
        self._publish_presence()
        self._refresh_tray()
        self.root.after(PRESENCE_POLL_MS, self._presence_heartbeat)

    def _schedule_conversation_attempt(self):
        self.root.after(random.randint(*CONVERSATION_ATTEMPT_RANGE_MS), self._maybe_start_conversation)

    def _maybe_start_conversation(self):
        if self.is_quitting:
            return
        active_partners = self._active_other_instances()
        now = time.time()
        if (
            active_partners
            and self._can_speak(15)
            and (now - self.last_conversation_started_at) >= 35
            and random.random() < 0.55
        ):
            partner_id, _info = random.choice(active_partners)
            line_self, line_partner = random.choice(PET_CONVERSATIONS)
            conversation_id = uuid.uuid4().hex
            conversation = {
                "id": conversation_id,
                "created_at": now,
                "participants": [self.pet_id, partner_id],
                "lines": {self.pet_id: line_self, partner_id: line_partner},
            }

            def mutate(data):
                self._cleanup_shared_state(data)
                data.setdefault("conversations", []).append(conversation)

            self.shared_state_store.update(mutate)
            self.seen_conversation_ids.append(conversation_id)
            self.last_conversation_started_at = now
            self._show_text(line_self)

        self._schedule_conversation_attempt()

    def _poll_conversations(self):
        if self.is_quitting:
            return

        shared_state = self.shared_state_store.read()
        now = time.time()
        for conversation in shared_state.get("conversations", []):
            conversation_id = conversation.get("id")
            if not conversation_id or conversation_id in self.seen_conversation_ids:
                continue
            if now - conversation.get("created_at", 0) > CONVERSATION_TTL_SECONDS:
                continue
            if self.pet_id not in conversation.get("participants", []):
                continue
            line = conversation.get("lines", {}).get(self.pet_id)
            if line:
                self.seen_conversation_ids.append(conversation_id)
                self.seen_conversation_ids = self.seen_conversation_ids[-64:]
                if self._can_speak(4):
                    self._show_text(line)

        self.root.after(CONVERSATION_POLL_MS, self._poll_conversations)

    def _poll_commands(self):
        if self.is_quitting:
            return

        executed = []
        quit_requested = False
        shared_state = self.shared_state_store.read()
        for command in shared_state.get("commands", []):
            if command.get("target") != self.pet_id:
                continue
            executed.append(command.get("id"))
            if command.get("action") == "quit":
                quit_requested = True

        if executed:
            def mutate(data):
                self._cleanup_shared_state(data)
                data["commands"] = [
                    command
                    for command in data.get("commands", [])
                    if command.get("id") not in executed
                ]

            self.shared_state_store.update(mutate)
            if quit_requested:
                self._do_quit()
                return

        self.root.after(COMMAND_POLL_MS, self._poll_commands)

    def _handle_usb_change_event(self):
        if not self.event_reactions_enabled or not self._can_speak(10):
            self.removable_drives = get_removable_drives()
            return
        current_drives = get_removable_drives()
        new_drives = sorted(current_drives - self.removable_drives)
        if new_drives:
            drive_label = new_drives[0].rstrip("\\")
            self._show_text(self.dialogue.format_event_text("usb", label=drive_label))
        self.removable_drives = current_drives

    def _handle_power_change_event(self):
        if not self.event_reactions_enabled:
            return
        battery = get_battery_snapshot()
        if not battery:
            return
        is_low = battery["percent"] <= 20 and not battery["charging"]
        if is_low and not self.was_battery_low and self._can_speak(12):
            self._show_text(self.dialogue.format_event_text("battery_low", percent=battery["percent"]))
        self.was_battery_low = is_low

    def _trim_window_title(self, title):
        compact = " ".join(title.split())
        if len(compact) > 36:
            return compact[:33].rstrip() + "..."
        return compact

    def _handle_foreground_change_event(self, title):
        if not self.event_reactions_enabled:
            return
        if title in {"", APP_NAME, "Program Manager"}:
            return
        if self._can_speak(16) and random.random() < 0.4:
            self._show_text(
                self.dialogue.format_event_text("window_focus", title=self._trim_window_title(title))
            )

    def _auto_check_for_updates(self):
        if self.is_quitting or not self.auto_update_enabled:
            return
        self.update_checker.check_async(self._on_update_check_complete)

    def check_for_updates_manual(self):
        self.manual_update_check_pending = True
        self.update_checker.check_async(self._on_update_check_complete)

    def _on_update_check_complete(self, result, error):
        manual = self.manual_update_check_pending
        self.manual_update_check_pending = False
        if self.is_quitting:
            return
        if error:
            if manual:
                self._show_text("Update check failed.\nTry again in a bit.")
            return
        if not result:
            return
        if result.get("newer") and result.get("version") != self.last_update_prompt_version:
            self.last_update_prompt_version = result.get("version")
            self._show_text(self.dialogue.format_event_text("update", version=result["version"]))
        elif manual:
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
        menu.add_command(label="Dance!", command=lambda: self._trigger_dance(True))
        menu.add_command(label="Say Something", command=self._show_saying)
        menu.add_command(label="Summon a Friend", command=self._summon_friend)
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
        menu.add_separator()
        menu.add_command(label="Quit NPCJason", command=self._quit)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _tray_select_skin(self, skin_key):
        def handler(icon=None, menu_item=None):
            self.root.after(0, lambda: self._set_skin(skin_key))

        return handler

    def _tray_toggle_sound(self, icon=None, menu_item=None):
        self.root.after(0, self._toggle_sound_enabled)

    def _tray_toggle_visibility(self, icon=None, menu_item=None):
        self.root.after(0, self._do_toggle_visibility)

    def _tray_say(self, icon=None, menu_item=None):
        self.root.after(0, lambda: self._show_saying(reveal_if_hidden=True))

    def _tray_dance(self, icon=None, menu_item=None):
        self.root.after(0, lambda: self._trigger_dance(False))

    def _build_tray_pets_menu(self):
        pets = self._active_other_instances()
        if not pets:
            return pystray.Menu(item("No other pets", lambda icon, menu_item: None, enabled=False))
        return pystray.Menu(
            *(item(f"Dismiss {pet_id}", lambda icon, menu_item, chosen=pet_id: self.root.after(0, lambda: self.dismiss_pet(chosen))) for pet_id, _info in pets)
        )

    def _build_tray_menu(self):
        skin_items = []
        for skin_key, skin_data in sorted(self.skins.items()):
            skin_items.append(
                item(
                    skin_data.get("label", skin_key),
                    self._tray_select_skin(skin_key),
                    checked=lambda menu_item, chosen=skin_key: self.skin_key == chosen,
                    radio=True,
                )
            )
        return pystray.Menu(
            item("Show/Hide", self._tray_toggle_visibility, default=True),
            item(lambda menu_item: f"Mood: {MOODS[self.mood]['label']}", lambda icon, menu_item: None, enabled=False),
            item("Choose Skin", pystray.Menu(*skin_items)),
            item("Dance!", self._tray_dance),
            item("Say Something", self._tray_say),
            item("Summon a Friend", lambda icon, menu_item: self.root.after(0, self._summon_friend)),
            item("Pets", self._build_tray_pets_menu()),
            item("Settings", lambda icon, menu_item: self.root.after(0, self._open_settings_window)),
            item("Start With Windows", lambda icon, menu_item: self.root.after(0, self._toggle_auto_start), checked=lambda menu_item: self.startup_manager.is_enabled()),
            item("Sound Effects", self._tray_toggle_sound, checked=lambda menu_item: self.sound_enabled),
            item("Check for Updates", lambda icon, menu_item: self.root.after(0, self.check_for_updates_manual)),
            item("Open Releases Page", lambda icon, menu_item: self.root.after(0, self._open_releases_page)),
            pystray.Menu.SEPARATOR,
            item("Quit", self._quit),
        )

    def _setup_tray(self):
        icon_img = self._make_tray_icon()
        self.tray_icon = pystray.Icon(APP_NAME, icon_img, f"{APP_NAME} {APP_VERSION}", menu=self._build_tray_menu())
        self.tray_icon.run()

    def _make_tray_icon(self):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([16, 8, 48, 40], fill="#e8c170", outline="#1a1a2e", width=2)
        draw.rectangle([14, 4, 50, 16], fill=self.tray_colors["hair"], outline="#1a1a2e", width=1)
        draw.rectangle([22, 20, 28, 26], fill="#16213e")
        draw.rectangle([36, 20, 42, 26], fill="#16213e")
        draw.rectangle([28, 30, 36, 34], fill="#c84b31")
        draw.rectangle([20, 40, 44, 56], fill=self.tray_colors["body"], outline="#1a1a2e", width=1)
        draw.rectangle([22, 56, 30, 64], fill=self.tray_colors["legs"])
        draw.rectangle([34, 56, 42, 64], fill=self.tray_colors["legs"])
        return img

    def _refresh_tray(self):
        if not self.tray_icon:
            return
        try:
            self.tray_icon.icon = self._make_tray_icon()
            self.tray_icon.menu = self._build_tray_menu()
            self.tray_icon.update_menu()
        except Exception:
            pass

    def _do_toggle_visibility(self):
        if self.root.state() == "withdrawn":
            self.root.deiconify()
        else:
            self.root.withdraw()

    def _toggle_auto_start(self):
        self.startup_manager.set_enabled(not self.startup_manager.is_enabled())
        self._schedule_settings_save()
        self._refresh_tray()

    def _schedule_settings_save(self, delay_ms=350):
        if self.is_quitting:
            return
        if self.settings_save_after_id is not None:
            self.root.after_cancel(self.settings_save_after_id)
        self.settings_save_after_id = self.root.after(delay_ms, self._save_settings)

    def _save_settings(self):
        self.settings_save_after_id = None

        def mutate(data):
            data.setdefault("global", {})
            data.setdefault("instances", {})
            data["global"]["sound_enabled"] = self.sound_enabled
            data["global"]["sound_volume"] = self.sound_volume
            data["global"]["default_skin"] = self.skin_key
            data["global"]["auto_update_enabled"] = self.auto_update_enabled
            data["global"]["auto_start_enabled"] = self.startup_manager.is_enabled()
            data["global"]["event_reactions_enabled"] = self.event_reactions_enabled
            data["instances"][self.pet_id] = {
                "x": self.window_x,
                "y": self.window_y,
                "skin": self.skin_key,
                "mood": self.mood,
                "updated_at": time.time(),
            }

        self.settings_store.update(mutate)

    def _unregister_presence(self):
        def mutate(data):
            self._cleanup_shared_state(data)
            data.get("instances", {}).pop(self.pet_id, None)
            data["commands"] = [
                command for command in data.get("commands", []) if command.get("target") != self.pet_id
            ]

        self.shared_state_store.update(mutate)

    def _quit(self, icon=None, menu_item=None):
        try:
            self.root.after(0, self._do_quit)
        except Exception:
            self._do_quit()

    def _do_quit(self):
        if self.is_quitting:
            return
        self.is_quitting = True
        try:
            self._save_settings()
        except Exception:
            pass
        try:
            self._unregister_presence()
        except Exception:
            pass
        try:
            if self.event_bridge:
                self.event_bridge.uninstall()
        except Exception:
            pass
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


def parse_args(argv):
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--pet-id", default="main")
    parser.add_argument("--x", type=int)
    parser.add_argument("--y", type=int)
    parser.add_argument("--friend-of")
    args, _unknown = parser.parse_known_args(argv)
    return args
