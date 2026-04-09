SETTINGS_SCHEMA_VERSION = 5
SHARED_STATE_SCHEMA_VERSION = 1

MOODS = {
    "happy": {"label": "Happy", "speed": 1.0},
    "tired": {"label": "Tired", "speed": 1.35},
    "caffeinated": {"label": "Caffeinated", "speed": 0.72},
}


def default_settings():
    return {
        "schema_version": SETTINGS_SCHEMA_VERSION,
        "global": {
            "sound_enabled": True,
            "sound_volume": 70,
            "sound_categories": {
                "speech": True,
                "toy": True,
                "state": True,
                "scenario": True,
            },
            "default_skin": "jason",
            "auto_update_enabled": True,
            "auto_start_enabled": False,
            "event_reactions_enabled": True,
            "quiet_hours_enabled": False,
            "quiet_start_hour": 22,
            "quiet_end_hour": 8,
            "quiet_when_fullscreen": True,
            "auto_antics_enabled": True,
            "auto_antics_min_minutes": 4,
            "auto_antics_max_minutes": 9,
            "auto_antics_dance_chance": 55,
            "rare_events_enabled": True,
            "chaos_mode": False,
            "movement_enabled": True,
            "unlocks_enabled": True,
            "seasonal_mode_override": "auto",
            "last_active_season": "",
            "reactions": {
                "usb": True,
                "battery": True,
                "focus": True,
                "updates": True,
                "pet_chat": True,
                "random_sayings": True,
            },
            "quote_pack_states": {},
            "favorite_skins": [],
            "favorite_toys": [],
            "favorite_scenarios": [],
            "favorite_quote_packs": [],
            "unlocked_skins": [],
            "unlocked_toys": [],
            "unlocked_scenarios": [],
            "unlocked_quote_packs": [],
            "discovery_stats": {
                "launches": 0,
                "quotes_spoken": 0,
                "toy_uses": 0,
                "scenario_runs": 0,
                "state_changes": 0,
                "curious_beats": 0,
                "confused_beats": 0,
                "runtime_minutes": 0,
                "discoveries": 0,
            },
            "recent_scenarios": [],
            "favorite_sayings": [],
            "recent_sayings": [],
        },
        "instances": {},
    }


def default_shared_state():
    return {
        "schema_version": SHARED_STATE_SCHEMA_VERSION,
        "instances": {},
        "conversations": [],
        "commands": [],
    }
