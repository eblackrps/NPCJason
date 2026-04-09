from .runtime_state import quiet_hours_active


class NPCJasonApp:
    def __new__(cls, *args, **kwargs):
        from .app_controller import NPCJasonApp as _NPCJasonApp

        return _NPCJasonApp(*args, **kwargs)


def parse_args(argv):
    from .app_controller import parse_args as _parse_args

    return _parse_args(argv)


__all__ = ["NPCJasonApp", "parse_args", "quiet_hours_active"]
