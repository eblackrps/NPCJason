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
        },
        "instances": {},
    }


def default_shared_state():
    return {
        "instances": {},
        "conversations": [],
        "commands": [],
    }
