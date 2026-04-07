MOODS = {
    "happy": {"label": "Happy", "speed": 1.0},
    "tired": {"label": "Tired", "speed": 1.35},
    "caffeinated": {"label": "Caffeinated", "speed": 0.72},
}


def default_settings():
    return {
        "global": {
            "sound_enabled": True,
            "sound_volume": 70,
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
            "reactions": {
                "usb": True,
                "battery": True,
                "focus": True,
                "updates": True,
                "pet_chat": True,
                "random_sayings": True,
            },
            "favorite_sayings": [],
            "recent_sayings": [],
        },
        "instances": {},
    }


def default_shared_state():
    return {
        "instances": {},
        "conversations": [],
        "commands": [],
    }
