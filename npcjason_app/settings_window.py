import tkinter as tk
from tkinter import ttk

from .version import APP_NAME, APP_VERSION


class SettingsWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.title(f"{APP_NAME} Settings")
        self.attributes("-topmost", True)
        self.configure(bg="#f4f1de")
        self.resizable(False, False)

        self.skin_labels = app.available_skin_labels()
        self.label_to_key = {label: key for key, label in self.skin_labels.items()}
        self.skin_var = tk.StringVar(value=self.skin_labels.get(app.skin_key, app.skin_key))
        self.sound_enabled_var = tk.BooleanVar(value=app.sound_enabled)
        self.sound_volume_var = tk.IntVar(value=app.sound_manager.volume)
        self.auto_start_var = tk.BooleanVar(value=app.startup_manager.is_enabled())
        self.auto_update_var = tk.BooleanVar(value=app.auto_update_enabled)
        self.event_reactions_var = tk.BooleanVar(value=app.event_reactions_enabled)
        self.status_var = tk.StringVar(value=f"Version {APP_VERSION}")

        self._build()
        self._refresh_active_pets()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self):
        outer = tk.Frame(self, bg="#f4f1de", padx=12, pady=12)
        outer.pack(fill="both", expand=True)

        title = tk.Label(
            outer,
            text=f"{APP_NAME} Settings",
            bg="#f4f1de",
            fg="#1a1a2e",
            font=("Segoe UI", 13, "bold"),
        )
        title.pack(anchor="w")

        main = tk.Frame(outer, bg="#f4f1de")
        main.pack(fill="both", expand=True, pady=(10, 0))

        left = tk.LabelFrame(main, text="General", bg="#f4f1de", fg="#1a1a2e", padx=10, pady=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        tk.Label(left, text="Skin", bg="#f4f1de", fg="#1a1a2e").grid(row=0, column=0, sticky="w")
        skin_values = [self.skin_labels[key] for key in self.app.available_skin_keys()]
        ttk.Combobox(
            left,
            textvariable=self.skin_var,
            values=skin_values,
            state="readonly",
            width=18,
        ).grid(row=1, column=0, sticky="ew", pady=(2, 8))

        tk.Checkbutton(
            left,
            text="Sound effects",
            variable=self.sound_enabled_var,
            bg="#f4f1de",
            fg="#1a1a2e",
            selectcolor="#f4f1de",
        ).grid(row=2, column=0, sticky="w")

        tk.Label(left, text="Volume", bg="#f4f1de", fg="#1a1a2e").grid(row=3, column=0, sticky="w", pady=(8, 0))
        tk.Scale(
            left,
            from_=0,
            to=100,
            orient="horizontal",
            variable=self.sound_volume_var,
            bg="#f4f1de",
            highlightthickness=0,
            length=180,
        ).grid(row=4, column=0, sticky="ew")

        tk.Checkbutton(
            left,
            text="Start with Windows",
            variable=self.auto_start_var,
            bg="#f4f1de",
            fg="#1a1a2e",
            selectcolor="#f4f1de",
        ).grid(row=5, column=0, sticky="w", pady=(8, 0))

        tk.Checkbutton(
            left,
            text="Check for updates automatically",
            variable=self.auto_update_var,
            bg="#f4f1de",
            fg="#1a1a2e",
            selectcolor="#f4f1de",
        ).grid(row=6, column=0, sticky="w")

        tk.Checkbutton(
            left,
            text="React to system events",
            variable=self.event_reactions_var,
            bg="#f4f1de",
            fg="#1a1a2e",
            selectcolor="#f4f1de",
        ).grid(row=7, column=0, sticky="w")

        buttons = tk.Frame(left, bg="#f4f1de")
        buttons.grid(row=8, column=0, sticky="ew", pady=(10, 0))
        tk.Button(buttons, text="Apply", command=self._apply, width=9).pack(side="left")
        tk.Button(buttons, text="Test Sound", command=self._test_sound, width=10).pack(side="left", padx=(6, 0))
        tk.Button(buttons, text="Reload Sayings", command=self._reload_dialogue, width=12).pack(side="left", padx=(6, 0))

        right = tk.LabelFrame(main, text="Pets", bg="#f4f1de", fg="#1a1a2e", padx=10, pady=8)
        right.grid(row=0, column=1, sticky="nsew")

        self.pets_list = tk.Listbox(right, height=10, width=28)
        self.pets_list.pack(fill="both", expand=True)

        pets_buttons = tk.Frame(right, bg="#f4f1de")
        pets_buttons.pack(fill="x", pady=(8, 0))
        tk.Button(pets_buttons, text="Summon Friend", command=self.app.summon_friend_from_settings, width=12).pack(side="left")
        tk.Button(pets_buttons, text="Dismiss Selected", command=self._dismiss_selected_pet, width=14).pack(side="left", padx=(6, 0))

        footer = tk.Frame(outer, bg="#f4f1de")
        footer.pack(fill="x", pady=(10, 0))
        tk.Label(footer, textvariable=self.status_var, bg="#f4f1de", fg="#1a1a2e").pack(side="left")
        tk.Button(footer, text="Dismiss All Friends", command=self.app.dismiss_all_friends).pack(side="right")
        tk.Button(footer, text="Check for Updates", command=self.app.check_for_updates_manual).pack(side="right", padx=(0, 6))

    def _apply(self):
        self.app.apply_settings(
            skin_key=self.label_to_key.get(self.skin_var.get(), self.app.skin_key),
            sound_enabled=self.sound_enabled_var.get(),
            sound_volume=self.sound_volume_var.get(),
            auto_start_enabled=self.auto_start_var.get(),
            auto_update_enabled=self.auto_update_var.get(),
            event_reactions_enabled=self.event_reactions_var.get(),
        )
        self.status_var.set("Settings applied")

    def _test_sound(self):
        self.app.preview_sound(self.sound_volume_var.get(), self.sound_enabled_var.get())
        self.status_var.set("Played sound preview")

    def _reload_dialogue(self):
        self.app.reload_dialogue()
        self.status_var.set("Dialogue packs reloaded")

    def _refresh_active_pets(self):
        if not self.winfo_exists():
            return
        pets = self.app.list_active_pets()
        self.pets_list.delete(0, tk.END)
        for pet_id, description in pets:
            self.pets_list.insert(tk.END, f"{pet_id} | {description}")
        self.after(2500, self._refresh_active_pets)

    def _dismiss_selected_pet(self):
        selection = self.pets_list.curselection()
        if not selection:
            return
        pet_line = self.pets_list.get(selection[0])
        pet_id = pet_line.split("|", 1)[0].strip()
        self.app.dismiss_pet(pet_id)
        self.status_var.set(f"Dismiss requested for {pet_id}")

    def _close(self):
        self.destroy()
