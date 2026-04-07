import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .version import APP_NAME, APP_VERSION


class SettingsWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title(f"{APP_NAME} Settings")
        self.attributes("-topmost", True)
        self.configure(bg="#f4f1de")
        self.geometry("780x640")
        self.minsize(760, 620)

        self.skin_labels = app.available_skin_labels()
        self.label_to_key = {label: key for key, label in self.skin_labels.items()}

        self.pet_name_var = tk.StringVar(value=app.pet_name)
        self.skin_var = tk.StringVar(value=self.skin_labels.get(app.skin_key, app.skin_key))
        self.sound_enabled_var = tk.BooleanVar(value=app.sound_enabled)
        self.sound_volume_var = tk.IntVar(value=app.sound_manager.volume)
        self.auto_start_var = tk.BooleanVar(value=app.startup_manager.is_enabled())
        self.auto_update_var = tk.BooleanVar(value=app.auto_update_enabled)
        self.event_reactions_var = tk.BooleanVar(value=app.event_reactions_enabled)
        self.quiet_hours_enabled_var = tk.BooleanVar(value=app.quiet_hours_enabled)
        self.quiet_start_hour_var = tk.IntVar(value=app.quiet_start_hour)
        self.quiet_end_hour_var = tk.IntVar(value=app.quiet_end_hour)
        self.quiet_fullscreen_var = tk.BooleanVar(value=app.quiet_when_fullscreen)
        self.auto_antics_enabled_var = tk.BooleanVar(value=app.auto_antics_enabled)
        self.auto_antics_min_var = tk.IntVar(value=app.auto_antics_min_minutes)
        self.auto_antics_max_var = tk.IntVar(value=app.auto_antics_max_minutes)
        self.auto_antics_dance_var = tk.IntVar(value=app.auto_antics_dance_chance)
        self.reaction_vars = {
            "usb": tk.BooleanVar(value=app.reaction_toggles.get("usb", True)),
            "battery": tk.BooleanVar(value=app.reaction_toggles.get("battery", True)),
            "focus": tk.BooleanVar(value=app.reaction_toggles.get("focus", True)),
            "updates": tk.BooleanVar(value=app.reaction_toggles.get("updates", True)),
            "pet_chat": tk.BooleanVar(value=app.reaction_toggles.get("pet_chat", True)),
            "random_sayings": tk.BooleanVar(value=app.reaction_toggles.get("random_sayings", True)),
        }
        self.status_var = tk.StringVar(value=f"Version {APP_VERSION}")
        self.skin_meta_var = tk.StringVar()

        self._build()
        self._refresh_skin_metadata()
        self._refresh_active_pets()
        self._refresh_history_lists()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self):
        outer = tk.Frame(self, bg="#f4f1de", padx=12, pady=12)
        outer.pack(fill="both", expand=True)

        title = tk.Label(
            outer,
            text=f"{APP_NAME} Settings",
            bg="#f4f1de",
            fg="#1a1a2e",
            font=("Segoe UI", 14, "bold"),
        )
        title.pack(anchor="w")

        notebook = ttk.Notebook(outer)
        notebook.pack(fill="both", expand=True, pady=(10, 0))

        general = tk.Frame(notebook, bg="#f4f1de")
        behavior = tk.Frame(notebook, bg="#f4f1de")
        pets = tk.Frame(notebook, bg="#f4f1de")
        notebook.add(general, text="General")
        notebook.add(behavior, text="Behavior")
        notebook.add(pets, text="Pets && History")

        self._build_general_tab(general)
        self._build_behavior_tab(behavior)
        self._build_pets_tab(pets)

        footer = tk.Frame(outer, bg="#f4f1de")
        footer.pack(fill="x", pady=(10, 0))
        tk.Label(footer, textvariable=self.status_var, bg="#f4f1de", fg="#1a1a2e").pack(side="left")
        tk.Button(footer, text="Apply", command=self._apply, width=10).pack(side="right")
        tk.Button(footer, text="Close", command=self._close, width=10).pack(side="right", padx=(0, 6))

    def _build_general_tab(self, parent):
        left = tk.LabelFrame(parent, text="Profile", bg="#f4f1de", fg="#1a1a2e", padx=10, pady=8)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)

        tk.Label(left, text="Pet name", bg="#f4f1de", fg="#1a1a2e").grid(row=0, column=0, sticky="w")
        tk.Entry(left, textvariable=self.pet_name_var, width=24).grid(row=1, column=0, sticky="ew", pady=(2, 8))

        tk.Label(left, text="Skin", bg="#f4f1de", fg="#1a1a2e").grid(row=2, column=0, sticky="w")
        skin_values = [self.skin_labels[key] for key in self.app.available_skin_keys()]
        skin_box = ttk.Combobox(
            left,
            textvariable=self.skin_var,
            values=skin_values,
            state="readonly",
            width=24,
        )
        skin_box.grid(row=3, column=0, sticky="ew", pady=(2, 8))
        skin_box.bind("<<ComboboxSelected>>", lambda _event: self._refresh_skin_metadata())

        tk.Label(
            left,
            textvariable=self.skin_meta_var,
            justify="left",
            bg="#f4f1de",
            fg="#1a1a2e",
            wraplength=280,
        ).grid(row=4, column=0, sticky="w")

        if self.app.skin_load_errors:
            tk.Label(
                left,
                text="Skin warnings:\n" + "\n".join(self.app.skin_load_errors[:4]),
                justify="left",
                bg="#f4f1de",
                fg="#9c2f2f",
                wraplength=280,
            ).grid(row=5, column=0, sticky="w", pady=(8, 0))

        sound = tk.LabelFrame(parent, text="Sound && Startup", bg="#f4f1de", fg="#1a1a2e", padx=10, pady=8)
        sound.pack(side="left", fill="both", expand=True, pady=8)

        tk.Checkbutton(
            sound,
            text="Sound effects",
            variable=self.sound_enabled_var,
            bg="#f4f1de",
            fg="#1a1a2e",
            selectcolor="#f4f1de",
        ).pack(anchor="w")
        tk.Label(sound, text="Volume", bg="#f4f1de", fg="#1a1a2e").pack(anchor="w", pady=(8, 0))
        tk.Scale(
            sound,
            from_=0,
            to=100,
            orient="horizontal",
            variable=self.sound_volume_var,
            bg="#f4f1de",
            highlightthickness=0,
            length=230,
        ).pack(anchor="w")

        tk.Checkbutton(
            sound,
            text="Start with Windows",
            variable=self.auto_start_var,
            bg="#f4f1de",
            fg="#1a1a2e",
            selectcolor="#f4f1de",
        ).pack(anchor="w", pady=(8, 0))
        tk.Checkbutton(
            sound,
            text="Check for updates automatically",
            variable=self.auto_update_var,
            bg="#f4f1de",
            fg="#1a1a2e",
            selectcolor="#f4f1de",
        ).pack(anchor="w")

        buttons = tk.Frame(sound, bg="#f4f1de")
        buttons.pack(fill="x", pady=(10, 0))
        tk.Button(buttons, text="Test Sound", command=self._test_sound, width=11).pack(side="left")
        tk.Button(buttons, text="Check Updates", command=self.app.check_for_updates_manual, width=12).pack(side="left", padx=(6, 0))

        maintenance = tk.LabelFrame(parent, text="Maintenance", bg="#f4f1de", fg="#1a1a2e", padx=10, pady=8)
        maintenance.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)

        tk.Button(maintenance, text="Reload Sayings", command=self._reload_dialogue, width=16).pack(anchor="w")
        tk.Button(maintenance, text="Bring Back On Screen", command=self.app._bring_back_on_screen, width=16).pack(anchor="w", pady=(6, 0))
        tk.Button(maintenance, text="Open Data Folder", command=self.app.open_data_folder, width=16).pack(anchor="w", pady=(6, 0))
        tk.Button(maintenance, text="Open Log File", command=self.app.open_log_file, width=16).pack(anchor="w", pady=(6, 0))
        tk.Button(maintenance, text="Export Settings", command=self._export_settings, width=16).pack(anchor="w", pady=(14, 0))
        tk.Button(maintenance, text="Import Settings", command=self._import_settings, width=16).pack(anchor="w", pady=(6, 0))
        tk.Button(maintenance, text="Reset Settings", command=self._reset_settings, width=16).pack(anchor="w", pady=(6, 0))

    def _build_behavior_tab(self, parent):
        quiet = tk.LabelFrame(parent, text="Quiet Hours", bg="#f4f1de", fg="#1a1a2e", padx=10, pady=8)
        quiet.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)

        tk.Checkbutton(
            quiet,
            text="Enable quiet hours",
            variable=self.quiet_hours_enabled_var,
            bg="#f4f1de",
            fg="#1a1a2e",
            selectcolor="#f4f1de",
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(quiet, text="Start hour", bg="#f4f1de", fg="#1a1a2e").grid(row=1, column=0, sticky="w", pady=(8, 0))
        tk.Spinbox(quiet, from_=0, to=23, textvariable=self.quiet_start_hour_var, width=5).grid(row=2, column=0, sticky="w")
        tk.Label(quiet, text="End hour", bg="#f4f1de", fg="#1a1a2e").grid(row=1, column=1, sticky="w", pady=(8, 0))
        tk.Spinbox(quiet, from_=0, to=23, textvariable=self.quiet_end_hour_var, width=5).grid(row=2, column=1, sticky="w")
        tk.Checkbutton(
            quiet,
            text="Suppress automatic chatter when another app is fullscreen",
            variable=self.quiet_fullscreen_var,
            bg="#f4f1de",
            fg="#1a1a2e",
            selectcolor="#f4f1de",
            wraplength=240,
            justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

        antics = tk.LabelFrame(parent, text="Auto Antics", bg="#f4f1de", fg="#1a1a2e", padx=10, pady=8)
        antics.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        tk.Checkbutton(
            antics,
            text="Enable automatic antics",
            variable=self.auto_antics_enabled_var,
            bg="#f4f1de",
            fg="#1a1a2e",
            selectcolor="#f4f1de",
        ).pack(anchor="w")
        tk.Label(antics, text="Minimum minutes between antics", bg="#f4f1de", fg="#1a1a2e").pack(anchor="w", pady=(8, 0))
        tk.Scale(antics, from_=1, to=30, orient="horizontal", variable=self.auto_antics_min_var, bg="#f4f1de", highlightthickness=0, length=220).pack(anchor="w")
        tk.Label(antics, text="Maximum minutes between antics", bg="#f4f1de", fg="#1a1a2e").pack(anchor="w", pady=(8, 0))
        tk.Scale(antics, from_=1, to=30, orient="horizontal", variable=self.auto_antics_max_var, bg="#f4f1de", highlightthickness=0, length=220).pack(anchor="w")
        tk.Label(antics, text="Chance an antic is a dance (%)", bg="#f4f1de", fg="#1a1a2e").pack(anchor="w", pady=(8, 0))
        tk.Scale(antics, from_=0, to=100, orient="horizontal", variable=self.auto_antics_dance_var, bg="#f4f1de", highlightthickness=0, length=220).pack(anchor="w")

        reactions = tk.LabelFrame(parent, text="Reaction Toggles", bg="#f4f1de", fg="#1a1a2e", padx=10, pady=8)
        reactions.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)

        tk.Checkbutton(
            reactions,
            text="Master event reactions switch",
            variable=self.event_reactions_var,
            bg="#f4f1de",
            fg="#1a1a2e",
            selectcolor="#f4f1de",
        ).pack(anchor="w")

        labels = [
            ("usb", "USB / removable drive comments"),
            ("battery", "Low battery comments"),
            ("focus", "Focused window comments"),
            ("updates", "Automatic update prompts"),
            ("pet_chat", "Pet-to-pet chatter"),
            ("random_sayings", "Random ambient sayings"),
        ]
        for key, label in labels:
            tk.Checkbutton(
                reactions,
                text=label,
                variable=self.reaction_vars[key],
                bg="#f4f1de",
                fg="#1a1a2e",
                selectcolor="#f4f1de",
                wraplength=240,
                justify="left",
            ).pack(anchor="w", pady=(6, 0))

    def _build_pets_tab(self, parent):
        pets = tk.LabelFrame(parent, text="Active Pets", bg="#f4f1de", fg="#1a1a2e", padx=10, pady=8)
        pets.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)

        self.pets_list = tk.Listbox(pets, height=12, width=34)
        self.pets_list.pack(fill="both", expand=True)

        pets_buttons = tk.Frame(pets, bg="#f4f1de")
        pets_buttons.pack(fill="x", pady=(8, 0))
        tk.Button(pets_buttons, text="Summon Friend", command=self.app.summon_friend_from_settings, width=12).pack(side="left")
        tk.Button(pets_buttons, text="Dismiss Selected", command=self._dismiss_selected_pet, width=14).pack(side="left", padx=(6, 0))
        tk.Button(pets_buttons, text="Dismiss All", command=self.app.dismiss_all_friends, width=11).pack(side="left", padx=(6, 0))

        history = tk.LabelFrame(parent, text="History && Favorites", bg="#f4f1de", fg="#1a1a2e", padx=10, pady=8)
        history.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        tk.Label(history, text="Recent sayings", bg="#f4f1de", fg="#1a1a2e").pack(anchor="w")
        self.history_list = tk.Listbox(history, height=8, width=42)
        self.history_list.pack(fill="x", expand=False)

        history_buttons = tk.Frame(history, bg="#f4f1de")
        history_buttons.pack(fill="x", pady=(6, 0))
        tk.Button(history_buttons, text="Repeat Last", command=self.app.repeat_last_saying, width=11).pack(side="left")
        tk.Button(history_buttons, text="Favorite Last", command=self._favorite_last, width=11).pack(side="left", padx=(6, 0))

        tk.Label(history, text="Favorite templates", bg="#f4f1de", fg="#1a1a2e").pack(anchor="w", pady=(12, 0))
        self.favorites_list = tk.Listbox(history, height=8, width=42)
        self.favorites_list.pack(fill="x", expand=False)

        favorite_buttons = tk.Frame(history, bg="#f4f1de")
        favorite_buttons.pack(fill="x", pady=(6, 0))
        tk.Button(favorite_buttons, text="Say Random Favorite", command=self.app.say_random_favorite, width=15).pack(side="left")
        tk.Button(favorite_buttons, text="Remove Selected", command=self._remove_selected_favorite, width=14).pack(side="left", padx=(6, 0))

    def _refresh_skin_metadata(self):
        skin_key = self.label_to_key.get(self.skin_var.get(), self.app.skin_key)
        metadata = self.app.skin_metadata(skin_key)
        self.skin_meta_var.set(
            f"Author: {metadata.get('author', 'Unknown')}\n"
            f"Version: {metadata.get('version', '1.0')}\n"
            f"{metadata.get('description', 'No description provided.')}"
        )

    def _apply(self):
        reaction_toggles = {key: variable.get() for key, variable in self.reaction_vars.items()}
        self.app.apply_settings(
            skin_key=self.label_to_key.get(self.skin_var.get(), self.app.skin_key),
            sound_enabled=self.sound_enabled_var.get(),
            sound_volume=self.sound_volume_var.get(),
            auto_start_enabled=self.auto_start_var.get(),
            auto_update_enabled=self.auto_update_var.get(),
            event_reactions_enabled=self.event_reactions_var.get(),
            quiet_hours_enabled=self.quiet_hours_enabled_var.get(),
            quiet_start_hour=self.quiet_start_hour_var.get(),
            quiet_end_hour=self.quiet_end_hour_var.get(),
            quiet_when_fullscreen=self.quiet_fullscreen_var.get(),
            auto_antics_enabled=self.auto_antics_enabled_var.get(),
            auto_antics_min_minutes=self.auto_antics_min_var.get(),
            auto_antics_max_minutes=self.auto_antics_max_var.get(),
            auto_antics_dance_chance=self.auto_antics_dance_var.get(),
            pet_name=self.pet_name_var.get().strip() or self.app.pet_name,
            reaction_toggles=reaction_toggles,
        )
        self._refresh_skin_metadata()
        self._refresh_history_lists()
        self.status_var.set("Settings applied")

    def _test_sound(self):
        self.app.preview_sound(self.sound_volume_var.get(), self.sound_enabled_var.get())
        self.status_var.set("Played sound preview")

    def _reload_dialogue(self):
        self.app.reload_dialogue()
        self.status_var.set("Dialogue packs reloaded")

    def _favorite_last(self):
        if not self.app.last_render_record:
            self.status_var.set("No saying yet")
            return
        self.app.favorite_last_saying()
        self._refresh_history_lists()
        self.status_var.set("Favorited the latest saying")

    def _remove_selected_favorite(self):
        selection = self.favorites_list.curselection()
        if not selection:
            return
        value = self.favorites_list.get(selection[0])
        self.app.remove_favorite_saying(value)
        self._refresh_history_lists()
        self.status_var.set("Removed favorite")

    def _refresh_history_lists(self):
        self.history_list.delete(0, tk.END)
        for record in self.app.recent_saying_texts():
            self.history_list.insert(tk.END, record.get("text", str(record)))

        self.favorites_list.delete(0, tk.END)
        for template in self.app.favorite_saying_texts():
            self.favorites_list.insert(tk.END, template)

    def _refresh_active_pets(self):
        if not self.winfo_exists():
            return
        pets = self.app.list_active_pets()
        self.pets_list.delete(0, tk.END)
        for pet_id, description in pets:
            self.pets_list.insert(tk.END, f"{pet_id} | {description}")
        self._refresh_history_lists()
        self.after(2500, self._refresh_active_pets)

    def _dismiss_selected_pet(self):
        selection = self.pets_list.curselection()
        if not selection:
            return
        pet_line = self.pets_list.get(selection[0])
        pet_id = pet_line.split("|", 1)[0].strip()
        self.app.dismiss_pet(pet_id)
        self.status_var.set(f"Dismiss requested for {pet_id}")

    def _export_settings(self):
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export NPCJason settings",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        self.app.export_settings(path)
        self.status_var.set(f"Exported settings to {path}")

    def _import_settings(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Import NPCJason settings",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self.app.import_settings(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror(APP_NAME, f"Could not import settings.\n\n{exc}")
            return
        self.destroy()

    def _reset_settings(self):
        if not messagebox.askyesno(APP_NAME, "Reset NPCJason settings back to defaults?"):
            return
        self.app.reset_settings()
        self.destroy()

    def _close(self):
        self.destroy()
