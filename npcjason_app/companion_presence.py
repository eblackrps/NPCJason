from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import random
import time


MAX_RECENT_KEYS = 8
MAX_SEEN_MILESTONES = 48
MAX_ANNOUNCED_UNLOCKS = 48
MAX_PREFERENCE_KEYS = 24


def default_companion_presence():
    return {
        "familiarity": 0,
        "days_used": 0,
        "total_sessions": 0,
        "interaction_streak": 0,
        "last_active_date": "",
        "last_session_started_at": 0.0,
        "last_session_ended_at": 0.0,
        "preferred_categories": {},
        "preferred_behaviors": {},
        "recent_greetings": [],
        "recent_signoffs": [],
        "recent_ambient_bits": [],
        "seen_milestones": [],
        "announced_unlocks": [],
        "today_mode_key": "",
        "today_mode_date": "",
        "theme_rotation_key": "",
        "theme_rotation_date": "",
        "theme_rotation_streak": 0,
    }


def _coerce_int(value, default=0, minimum=0, maximum=None):
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = int(default)
    result = max(int(minimum), result)
    if maximum is not None:
        result = min(int(maximum), result)
    return result


def _coerce_float(value, default=0.0, minimum=0.0):
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = float(default)
    return max(float(minimum), result)


def _coerce_str(value, default=""):
    if value is None:
        return str(default)
    return str(value)


def _sanitize_recent_keys(values, limit=MAX_RECENT_KEYS):
    recent = []
    for value in list(values or [])[-int(limit):]:
        key = _coerce_str(value).strip().lower()
        if key and key not in recent:
            recent.append(key)
    return recent[-int(limit):]


def _sanitize_int_map(values, limit=MAX_PREFERENCE_KEYS):
    if not isinstance(values, dict):
        return {}
    normalized = []
    for key, value in values.items():
        text = _coerce_str(key).strip().lower()
        if not text:
            continue
        normalized.append((text, _coerce_int(value, default=0, minimum=0, maximum=9999)))
    normalized.sort(key=lambda item: (-item[1], item[0]))
    return {key: value for key, value in normalized[: int(limit)] if value > 0}


def sanitize_companion_presence_payload(payload):
    defaults = default_companion_presence()
    payload = payload if isinstance(payload, dict) else {}
    sanitized = dict(defaults)
    sanitized["familiarity"] = _coerce_int(payload.get("familiarity"), minimum=0, maximum=100)
    sanitized["days_used"] = _coerce_int(payload.get("days_used"), minimum=0, maximum=5000)
    sanitized["total_sessions"] = _coerce_int(payload.get("total_sessions"), minimum=0, maximum=50000)
    sanitized["interaction_streak"] = _coerce_int(payload.get("interaction_streak"), minimum=0, maximum=3650)
    sanitized["last_active_date"] = _coerce_str(payload.get("last_active_date", "")).strip()
    sanitized["last_session_started_at"] = _coerce_float(payload.get("last_session_started_at", 0.0), minimum=0.0)
    sanitized["last_session_ended_at"] = _coerce_float(payload.get("last_session_ended_at", 0.0), minimum=0.0)
    sanitized["preferred_categories"] = _sanitize_int_map(payload.get("preferred_categories", {}))
    sanitized["preferred_behaviors"] = _sanitize_int_map(payload.get("preferred_behaviors", {}))
    sanitized["recent_greetings"] = _sanitize_recent_keys(payload.get("recent_greetings", []))
    sanitized["recent_signoffs"] = _sanitize_recent_keys(payload.get("recent_signoffs", []))
    sanitized["recent_ambient_bits"] = _sanitize_recent_keys(payload.get("recent_ambient_bits", []))
    sanitized["seen_milestones"] = _sanitize_recent_keys(
        payload.get("seen_milestones", []),
        limit=MAX_SEEN_MILESTONES,
    )
    sanitized["announced_unlocks"] = _sanitize_recent_keys(
        payload.get("announced_unlocks", []),
        limit=MAX_ANNOUNCED_UNLOCKS,
    )
    sanitized["today_mode_key"] = _coerce_str(payload.get("today_mode_key", "")).strip().lower()
    sanitized["today_mode_date"] = _coerce_str(payload.get("today_mode_date", "")).strip()
    sanitized["theme_rotation_key"] = _coerce_str(payload.get("theme_rotation_key", "")).strip().lower()
    sanitized["theme_rotation_date"] = _coerce_str(payload.get("theme_rotation_date", "")).strip()
    sanitized["theme_rotation_streak"] = _coerce_int(payload.get("theme_rotation_streak", 0), minimum=0, maximum=30)
    return sanitized


@dataclass(frozen=True)
class PresenceFlavor:
    key: str
    label: str
    announcement: str
    contexts: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    packs: tuple[str, ...] = ()
    preferred_states: tuple[str, ...] = ()
    preferred_scenarios: tuple[str, ...] = ()
    preferred_desk_items: tuple[str, ...] = ()
    preferred_companion_interactions: tuple[str, ...] = ()


@dataclass(frozen=True)
class AmbientWorldBeat:
    key: str
    text: str
    state_key: str = ""
    movement_style: str = ""
    focus: str = ""
    desk_item_key: str = ""
    companion_interaction: str = ""
    contexts: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    packs: tuple[str, ...] = ()
    min_familiarity: int = 0


@dataclass(frozen=True)
class MilestoneMoment:
    key: str
    text: str
    days_used: int = 0
    total_sessions: int = 0
    interaction_streak: int = 0
    familiarity: int = 0
    runtime_minutes: int = 0
    quotes_spoken: int = 0
    scenario_runs: int = 0
    companion_uses: int = 0
    session_minutes: int = 0
    state_key: str = ""
    companion_interaction: str = ""
    dance: bool = False
    contexts: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    packs: tuple[str, ...] = ()


SESSION_MODES = {
    "patch-goblin": PresenceFlavor(
        key="patch-goblin",
        label="Patch Goblin",
        announcement="Today's mode: Patch Goblin.\nI may overreact to updates.",
        contexts=("today-mode", "patch-goblin", "updates"),
        categories=("office", "helpdesk", "network"),
        packs=("networking-meltdown-helpdesk-chaos", "app-title-humor"),
        preferred_states=("busy", "curious"),
        preferred_scenarios=("busy-it-morning", "office-chaos"),
        preferred_desk_items=("keyboard",),
        preferred_companion_interactions=("desk-patrol",),
    ),
    "quiet-audit": PresenceFlavor(
        key="quiet-audit",
        label="Quiet Audit",
        announcement="Today's mode: Quiet Audit.\nI am pretending this is a formal inspection.",
        contexts=("today-mode", "quiet-audit", "responsible"),
        categories=("responsible", "office", "what-do"),
        packs=("app-title-humor",),
        preferred_states=("busy", "confused"),
        preferred_scenarios=("responsible-adult-moment",),
        preferred_desk_items=("keyboard", "coffee-mug"),
        preferred_companion_interactions=("desk-patrol",),
    ),
    "cable-philosopher": PresenceFlavor(
        key="cable-philosopher",
        label="Cable Philosopher",
        announcement="Today's mode: Cable Philosopher.\nThe wires are saying things again.",
        contexts=("today-mode", "cable-philosopher", "network"),
        categories=("network", "cisco", "homelab"),
        packs=("cisco-jokes", "networking-meltdown-helpdesk-chaos"),
        preferred_states=("curious", "confused"),
        preferred_scenarios=("homelab-troubleshooting",),
        preferred_desk_items=("tiny-network-rack",),
        preferred_companion_interactions=("cable-audit",),
    ),
    "tiny-victory": PresenceFlavor(
        key="tiny-victory",
        label="Tiny Victory Mode",
        announcement="Today's mode: Tiny Victory Mode.\nEverything successful will be treated as a parade.",
        contexts=("today-mode", "tiny-victory", "celebrating"),
        categories=("celebrating", "playful", "network"),
        packs=("jason-quotes", "app-title-humor"),
        preferred_states=("celebrating", "smug"),
        preferred_scenarios=("network-victory-lap",),
        preferred_companion_interactions=("victory-scamper",),
    ),
    "helpdesk-mirage": PresenceFlavor(
        key="helpdesk-mirage",
        label="Helpdesk Mirage",
        announcement="Today's mode: Helpdesk Mirage.\nI look busy enough to become a ticket magnet.",
        contexts=("today-mode", "helpdesk-mirage", "office"),
        categories=("office", "helpdesk", "playful"),
        packs=("networking-meltdown-helpdesk-chaos", "app-title-humor"),
        preferred_states=("busy", "annoyed"),
        preferred_scenarios=("busy-it-morning", "office-chaos"),
        preferred_desk_items=("keyboard", "coffee-mug"),
        preferred_companion_interactions=("crumb-heist", "mug-recon"),
    ),
}


THEME_SPOTLIGHTS = {
    "office-chaos": PresenceFlavor(
        key="office-chaos",
        label="Office Chaos Spotlight",
        announcement="Theme spotlight: Office Chaos.\nProfessionalism remains mostly decorative.",
        contexts=("theme-spotlight", "office-chaos", "office"),
        categories=("office", "responsible", "helpdesk"),
        packs=("networking-meltdown-helpdesk-chaos", "app-title-humor"),
        preferred_states=("busy", "annoyed"),
        preferred_scenarios=("busy-it-morning", "office-chaos", "responsible-adult-moment"),
        preferred_desk_items=("keyboard", "coffee-mug"),
        preferred_companion_interactions=("desk-patrol", "crumb-heist"),
    ),
    "homelab-drift": PresenceFlavor(
        key="homelab-drift",
        label="Homelab Drift",
        announcement="Theme spotlight: Homelab Drift.\nA blinking light has claimed the room.",
        contexts=("theme-spotlight", "homelab-drift", "homelab"),
        categories=("homelab", "network", "what-do"),
        packs=("what-do", "cisco-jokes"),
        preferred_states=("curious", "confused"),
        preferred_scenarios=("homelab-troubleshooting", "orbital-desk-patrol"),
        preferred_desk_items=("tiny-network-rack",),
        preferred_companion_interactions=("cable-audit", "zip-tie-recovery"),
    ),
    "sidekick-shift": PresenceFlavor(
        key="sidekick-shift",
        label="Sidekick Shift",
        announcement="Theme spotlight: Sidekick Shift.\nThe tiny staffing budget has improved.",
        contexts=("theme-spotlight", "sidekick-shift", "mouse-sidekick"),
        categories=("playful", "desk"),
        packs=("jason-quotes",),
        preferred_states=("curious", "smug"),
        preferred_companion_interactions=("desk-patrol", "crumb-heist", "mug-recon", "zip-tie-recovery"),
    ),
    "network-noise": PresenceFlavor(
        key="network-noise",
        label="Network Noise",
        announcement="Theme spotlight: Network Noise.\nThe packets feel judgmental today.",
        contexts=("theme-spotlight", "network-noise", "network"),
        categories=("network", "cisco", "celebrating"),
        packs=("cisco-jokes", "networking-meltdown-helpdesk-chaos"),
        preferred_states=("curious", "celebrating"),
        preferred_scenarios=("network-victory-lap", "homelab-troubleshooting"),
        preferred_desk_items=("tiny-network-rack",),
        preferred_companion_interactions=("cable-audit", "victory-scamper"),
    ),
    "responsible-facade": PresenceFlavor(
        key="responsible-facade",
        label="Responsible Facade",
        announcement="Theme spotlight: Responsible Facade.\nWe are all pretending to have a plan.",
        contexts=("theme-spotlight", "responsible-facade", "responsible"),
        categories=("responsible", "office", "playful"),
        packs=("app-title-humor",),
        preferred_states=("busy", "exhausted"),
        preferred_scenarios=("responsible-adult-moment", "busy-it-morning"),
        preferred_desk_items=("coffee-mug", "keyboard"),
        preferred_companion_interactions=("mug-recon",),
    ),
}


AMBIENT_WORLD_BEATS = (
    AmbientWorldBeat(
        key="edge-check",
        text="Back from checking the perimeter.\nStill mostly desktop.",
        state_key="curious",
        movement_style="inspect",
        focus="right-edge",
        contexts=("ambient-world", "edge-check", "curious"),
        categories=("what-do", "playful"),
        min_familiarity=2,
    ),
    AmbientWorldBeat(
        key="imaginary-ticket",
        text="Closed an imaginary ticket.\nIt reopened spiritually.",
        state_key="busy",
        desk_item_key="keyboard",
        contexts=("ambient-world", "imaginary-ticket", "office"),
        categories=("office", "helpdesk"),
        packs=("networking-meltdown-helpdesk-chaos",),
    ),
    AmbientWorldBeat(
        key="mug-consult",
        text="Quick strategy session with the mug.\nNo minutes were taken.",
        state_key="exhausted",
        desk_item_key="coffee-mug",
        contexts=("ambient-world", "mug-consult", "coffee-break"),
        categories=("office", "responsible"),
    ),
    AmbientWorldBeat(
        key="rack-mutter",
        text="I inspected the blinking lights.\nThey denied everything.",
        state_key="curious",
        desk_item_key="tiny-network-rack",
        contexts=("ambient-world", "rack-mutter", "network"),
        categories=("network", "homelab"),
        packs=("cisco-jokes", "networking-meltdown-helpdesk-chaos"),
    ),
    AmbientWorldBeat(
        key="mouse-errand",
        text="I delegated a tiny desk errand.\nManagement remains informal.",
        state_key="curious",
        companion_interaction="crumb-heist",
        contexts=("ambient-world", "mouse-errand", "mouse-sidekick"),
        categories=("playful",),
        min_familiarity=10,
    ),
)


MILESTONE_MOMENTS = (
    MilestoneMoment(
        key="day-3",
        text="Three days in.\nThis desk is starting to feel unionized.",
        days_used=3,
        state_key="smug",
        contexts=("milestone", "days-used"),
        categories=("playful", "smug"),
    ),
    MilestoneMoment(
        key="streak-3",
        text="Three-day streak achieved.\nSuspiciously consistent behavior.",
        interaction_streak=3,
        state_key="celebrating",
        contexts=("milestone", "streak"),
        categories=("celebrating", "playful"),
    ),
    MilestoneMoment(
        key="session-long",
        text="Long shift milestone.\nI have become part of the uptime now.",
        session_minutes=75,
        runtime_minutes=75,
        state_key="exhausted",
        contexts=("milestone", "long-session"),
        categories=("responsible",),
    ),
    MilestoneMoment(
        key="quotes-25",
        text="Twenty-five remarks logged.\nThis is now a documented condition.",
        quotes_spoken=25,
        state_key="smug",
        contexts=("milestone", "quotes"),
        categories=("playful", "smug"),
    ),
    MilestoneMoment(
        key="scenarios-8",
        text="Several scenarios later and still no paperwork.\nDeeply respectable.",
        scenario_runs=8,
        state_key="celebrating",
        dance=True,
        contexts=("milestone", "scenario-runs"),
        categories=("celebrating", "playful"),
    ),
    MilestoneMoment(
        key="mouse-regular",
        text="The mouse has become a recurring department.\nThis feels budgetarily unsound.",
        companion_uses=5,
        companion_interaction="victory-scamper",
        contexts=("milestone", "companion"),
        categories=("playful",),
    ),
    MilestoneMoment(
        key="familiarity-20",
        text="We've been doing this long enough\nthat the desktop would notice if I left.",
        familiarity=20,
        state_key="smug",
        contexts=("milestone", "familiarity"),
        categories=("smug", "playful"),
    ),
)


GREETING_LINES = {
    "new": {
        "morning": (
            ("new-boot-check", "Morning. I have initialized in a professionally suspicious way."),
            ("new-coffee", "Morning shift online.\nI am not certified for any of this."),
        ),
        "day": (
            ("new-online", "Desktop creature online.\nPlease keep expectations atmospheric."),
            ("new-shift", "I am now on shift.\nThe shift remains unclear."),
        ),
        "night": (
            ("new-night", "Evening operations engaged.\nEverything looks slightly more haunted."),
            ("new-night-audit", "Night shift activated.\nThe pixels are louder now."),
        ),
    },
    "known": {
        "morning": (
            ("known-good-morning", "Morning. I am back and mildly more familiar with this desk."),
            ("known-boot", "Booted up clean enough.\nLet's call that a win."),
        ),
        "day": (
            ("known-return", "Back on desktop duty.\nNothing seems less weird, which is reassuring."),
            ("known-logged-in", "Present and vaguely operational.\nAs usual."),
        ),
        "night": (
            ("known-evening", "Evening shift resumed.\nThe taskbar remains emotionally unstable."),
            ("known-late", "Back for the late shift.\nThe icons are pretending not to stare."),
        ),
    },
    "established": {
        "morning": (
            ("established-morning", "Morning. We appear to be doing this again.\nExcellent."),
            ("established-uptime", "Morning uptime check complete.\nYou still have me."),
        ),
        "day": (
            ("established-return", "Back in position.\nThe desk has not improved in my absence."),
            ("established-familiar", "I know this desktop well enough now to judge it."),
        ),
        "night": (
            ("established-night", "Evening. The long-haul desktop nonsense may continue."),
            ("established-quiet", "Back for the quieter hours.\nThe nonsense is now more concentrated."),
        ),
    },
    "veteran": {
        "morning": (
            ("veteran-morning", "Morning, old associate.\nI remain committed to desktop weirdness."),
            ("veteran-familiar", "Morning. We've been here long enough for this to count as tradition."),
        ),
        "day": (
            ("veteran-return", "Resuming our long-running desktop arrangement."),
            ("veteran-known", "Still here. Still weird. I respect the consistency."),
        ),
        "night": (
            ("veteran-night", "Evening, veteran shift edition.\nWe know the routine."),
            ("veteran-late", "Late-hours desktop watch resumed.\nAs discussed by no one."),
        ),
    },
}


SIGNOFF_LINES = {
    "generic": (
        ("signoff-generic-1", "Clocking out of active nonsense.\nTry not to let the desktop escalate."),
        ("signoff-generic-2", "Going quiet for a bit.\nPlease keep the weirdness in tolerance."),
        ("signoff-generic-3", "Standing down.\nThe desktop can free-range for a minute."),
    ),
    "known": (
        ("signoff-known-1", "I'll be back.\nThis desk clearly still needs supervision."),
        ("signoff-known-2", "Powering down my active commentary.\nThe vibes remain monitored."),
    ),
    "veteran": (
        ("signoff-veteran-1", "Usual arrangement resumed.\nI'll haunt the desktop again later."),
        ("signoff-veteran-2", "Quieting down, long-haul edition.\nDo not give the taskbar ideas."),
    ),
    "quiet": (
        ("signoff-quiet-1", "Going low-noise for a while.\nStill on the clock in spirit."),
        ("signoff-quiet-2", "Reducing commentary.\nThe desktop may continue under observation."),
    ),
}


REACTION_LINES = {
    "cooldown": (
        ("reaction-cooldown-1", "That bit is recharging.\nProfessional nonsense requires pacing."),
        ("reaction-cooldown-2", "I cannot responsibly overuse that routine.\nGive it a second."),
    ),
    "busy": (
        ("reaction-busy-1", "I am already in the middle of a whole situation."),
        ("reaction-busy-2", "One bit at a time.\nI have tiny bandwidth."),
    ),
    "confused": (
        ("reaction-confused-1", "That almost became a plan.\nDisturbing."),
        ("reaction-confused-2", "I had a concept.\nIt fled."),
    ),
    "success": (
        ("reaction-success-1", "Operationally unnecessary.\nEmotionally correct."),
        ("reaction-success-2", "Small success recorded.\nPlease act impressed."),
    ),
    "interrupted": (
        ("reaction-interrupted-1", "Sequence interrupted by reality.\nRude."),
        ("reaction-interrupted-2", "The bit was cut short.\nI blame conditions."),
    ),
}


def _top_keys(counts, limit=2):
    ordered = sorted(
        (
            (str(key).strip().lower(), int(value))
            for key, value in dict(counts or {}).items()
            if str(key).strip() and int(value) > 0
        ),
        key=lambda item: (-item[1], item[0]),
    )
    return [key for key, _value in ordered[: int(limit)]]


class CompanionPresenceController:
    def __init__(self, payload=None, logger=None, rng=None, clock=None):
        self.logger = logger
        self.rng = rng or random.Random()
        self.clock = clock or time.time
        self._data = sanitize_companion_presence_payload(payload)
        self._session_recent_reactions = []
        self.session_started_at = None

    def to_payload(self):
        return sanitize_companion_presence_payload(self._data)

    def needs_history_backfill(self):
        return (
            int(self._data.get("familiarity", 0)) <= 0
            and int(self._data.get("days_used", 0)) <= 0
            and int(self._data.get("total_sessions", 0)) <= 0
            and not str(self._data.get("last_active_date", "")).strip()
            and not self._data.get("seen_milestones", [])
            and not self._data.get("announced_unlocks", [])
        )

    def backfill_from_legacy_activity(
        self,
        launches=0,
        runtime_minutes=0,
        quotes_spoken=0,
        scenario_runs=0,
        discoveries=0,
        unlocked_count=0,
        favorite_count=0,
    ):
        launches = max(0, int(launches or 0))
        runtime_minutes = max(0, int(runtime_minutes or 0))
        quotes_spoken = max(0, int(quotes_spoken or 0))
        scenario_runs = max(0, int(scenario_runs or 0))
        discoveries = max(0, int(discoveries or 0))
        unlocked_count = max(0, int(unlocked_count or 0))
        favorite_count = max(0, int(favorite_count or 0))
        if max(
            launches,
            runtime_minutes,
            quotes_spoken,
            scenario_runs,
            discoveries,
            unlocked_count,
            favorite_count,
        ) <= 0:
            return False
        familiarity = (
            (launches // 3)
            + (runtime_minutes // 240)
            + (quotes_spoken // 30)
            + (scenario_runs // 3)
            + (discoveries * 2)
            + unlocked_count
            + min(2, favorite_count)
        )
        estimated_days = min(
            max(launches, 1),
            max(
                1,
                runtime_minutes // 240,
                quotes_spoken // 20,
                scenario_runs // 3,
                discoveries * 2,
            ),
        )
        self._data["familiarity"] = max(
            int(self._data.get("familiarity", 0)),
            min(28, familiarity),
        )
        self._data["days_used"] = max(int(self._data.get("days_used", 0)), int(estimated_days))
        self._data["total_sessions"] = max(int(self._data.get("total_sessions", 0)), int(launches))
        if self._data["days_used"] > 0 and int(self._data.get("interaction_streak", 0)) <= 0:
            self._data["interaction_streak"] = 1
        return True

    def begin_session(self, now=None, mood_key="happy", time_of_day=None):
        now_dt = self._coerce_datetime(now)
        date_key = now_dt.date().isoformat()
        last_active = str(self._data.get("last_active_date", "")).strip()
        is_new_day = date_key != last_active
        if is_new_day:
            self._data["days_used"] = _coerce_int(self._data.get("days_used", 0) + 1, maximum=5000)
            if last_active and self._is_consecutive_day(last_active, date_key):
                self._data["interaction_streak"] = _coerce_int(
                    self._data.get("interaction_streak", 0) + 1,
                    maximum=3650,
                )
            else:
                self._data["interaction_streak"] = 1
            self._bump_familiarity(2)
        elif int(self._data.get("total_sessions", 0)) <= 0:
            self._data["interaction_streak"] = max(1, int(self._data.get("interaction_streak", 0)))
        self._data["last_active_date"] = date_key
        self._data["total_sessions"] = _coerce_int(
            self._data.get("total_sessions", 0) + 1,
            maximum=50000,
        )
        self._data["last_session_started_at"] = float(now_dt.timestamp())
        self.session_started_at = now_dt
        selected_mode = self._ensure_today_mode(now_dt, mood_key=mood_key, time_of_day=time_of_day)
        selected_theme = self._ensure_theme_rotation(now_dt, selected_mode=selected_mode, mood_key=mood_key)
        self._log(
            "info",
            f"presence: session started ({self.relationship_label()} / {selected_mode.label} / {selected_theme.label})",
        )
        return {
            "new_day": is_new_day,
            "relationship_label": self.relationship_label(),
            "relationship_tier": self.relationship_tier(),
            "mode_label": selected_mode.label,
            "theme_label": selected_theme.label,
            "mode_announcement": selected_mode.announcement,
        }

    def end_session(self, now=None):
        now_dt = self._coerce_datetime(now)
        self._data["last_session_ended_at"] = float(now_dt.timestamp())
        if self.session_started_at is not None and (now_dt - self.session_started_at).total_seconds() >= 25 * 60:
            self._bump_familiarity(1)
        self._log("info", "presence: session ended")

    def relationship_tier(self):
        familiarity = self.familiarity()
        if familiarity >= 40:
            return "veteran"
        if familiarity >= 20:
            return "established"
        if familiarity >= 8:
            return "known"
        return "new"

    def relationship_label(self):
        return {
            "new": "New Desk Incident",
            "known": "Known Desk Problem",
            "established": "Established Menace",
            "veteran": "Long-Haul Gremlin",
        }.get(self.relationship_tier(), "Desktop Creature")

    def familiarity(self):
        return int(self._data.get("familiarity", 0))

    def note_behavior(self, behavior_key, categories=None, amount=1, familiarity_gain=0):
        behavior = _coerce_str(behavior_key).strip().lower()
        amount = max(1, int(amount))
        if behavior:
            behaviors = dict(self._data.get("preferred_behaviors", {}))
            behaviors[behavior] = _coerce_int(behaviors.get(behavior, 0) + amount, maximum=9999)
            self._data["preferred_behaviors"] = _sanitize_int_map(behaviors)
        category_counts = dict(self._data.get("preferred_categories", {}))
        for category in list(categories or []):
            key = _coerce_str(category).strip().lower()
            if not key:
                continue
            category_counts[key] = _coerce_int(category_counts.get(key, 0) + amount, maximum=9999)
        self._data["preferred_categories"] = _sanitize_int_map(category_counts)
        if int(familiarity_gain or 0) > 0:
            self._bump_familiarity(int(familiarity_gain))

    def session_minutes(self, now=None):
        now_dt = self._coerce_datetime(now)
        started_at = self.session_started_at
        if started_at is None:
            started_raw = float(self._data.get("last_session_started_at", 0.0) or 0.0)
            if started_raw <= 0:
                return 0
            started_at = datetime.fromtimestamp(started_raw)
        elapsed = max(0.0, (now_dt - started_at).total_seconds())
        return int(elapsed // 60)

    def current_mode(self):
        return SESSION_MODES.get(
            str(self._data.get("today_mode_key", "")).strip().lower(),
            next(iter(SESSION_MODES.values())),
        )

    def current_theme(self):
        return THEME_SPOTLIGHTS.get(
            str(self._data.get("theme_rotation_key", "")).strip().lower(),
            next(iter(THEME_SPOTLIGHTS.values())),
        )

    def session_mode_label(self):
        return self.current_mode().label

    def theme_label(self):
        return self.current_theme().label

    def behavior_bias(self):
        mode = self.current_mode()
        theme = self.current_theme()
        top_categories = _top_keys(self._data.get("preferred_categories", {}), limit=2)
        top_behaviors = _top_keys(self._data.get("preferred_behaviors", {}), limit=2)
        contexts = [
            f"relationship-{self.relationship_tier()}",
            f"today-mode-{mode.key}",
            f"theme-{theme.key}",
        ]
        categories = list(mode.categories) + [value for value in theme.categories if value not in mode.categories]
        categories.extend(category for category in top_categories if category not in categories)
        packs = list(mode.packs) + [value for value in theme.packs if value not in mode.packs]
        desk_items = list(mode.preferred_desk_items) + [
            value for value in theme.preferred_desk_items if value not in mode.preferred_desk_items
        ]
        companion_interactions = list(mode.preferred_companion_interactions) + [
            value
            for value in theme.preferred_companion_interactions
            if value not in mode.preferred_companion_interactions
        ]
        preferred_states = list(mode.preferred_states) + [
            value for value in theme.preferred_states if value not in mode.preferred_states
        ]
        preferred_scenarios = list(mode.preferred_scenarios) + [
            value for value in theme.preferred_scenarios if value not in mode.preferred_scenarios
        ]
        return {
            "contexts": contexts,
            "categories": categories,
            "packs": packs,
            "preferred_states": preferred_states,
            "preferred_scenarios": preferred_scenarios,
            "preferred_desk_items": desk_items,
            "preferred_companion_interactions": companion_interactions,
            "top_behaviors": top_behaviors,
        }

    def pick_greeting(self, time_of_day=None):
        time_key = self._normalize_time_of_day(time_of_day)
        tier = self.relationship_tier()
        options = list(GREETING_LINES.get(tier, GREETING_LINES["new"]).get(time_key, ()))
        key, text = self._pick_unique_tuple(options, recent_key="recent_greetings")
        return {
            "key": key,
            "text": text,
            "contexts": [
                "greeting",
                f"relationship-{tier}",
                f"time-{time_key}",
                f"today-mode-{self.current_mode().key}",
            ],
            "categories": list(self.current_mode().categories),
            "packs": list(self.current_mode().packs),
        }

    def pick_signoff(self, quiet=False):
        pool = []
        if quiet:
            pool.extend(SIGNOFF_LINES["quiet"])
        if self.relationship_tier() in {"known", "established"}:
            pool.extend(SIGNOFF_LINES["known"])
        if self.relationship_tier() == "veteran":
            pool.extend(SIGNOFF_LINES["veteran"])
        pool.extend(SIGNOFF_LINES["generic"])
        key, text = self._pick_unique_tuple(pool, recent_key="recent_signoffs")
        contexts = ["signoff", "quieting" if quiet else "shutdown", f"relationship-{self.relationship_tier()}"]
        return {
            "key": key,
            "text": text,
            "contexts": contexts,
            "categories": ["responsible", "playful"],
            "packs": [],
        }

    def pick_reaction(self, reaction_key):
        reaction_key = _coerce_str(reaction_key).strip().lower()
        options = list(REACTION_LINES.get(reaction_key, REACTION_LINES["confused"]))
        key, text = self._pick_unique_tuple(options, use_persistent_history=False)
        self._session_recent_reactions.append(key)
        self._session_recent_reactions = self._session_recent_reactions[-MAX_RECENT_KEYS:]
        return {"key": key, "text": text}

    def pick_ambient_world_beat(self, context=None):
        context = context if isinstance(context, dict) else {}
        available_desk_items = {
            _coerce_str(item).strip().lower()
            for item in context.get("available_desk_items", [])
            if _coerce_str(item).strip()
        }
        available_companion = {
            _coerce_str(item).strip().lower()
            for item in context.get("available_companion_interactions", [])
            if _coerce_str(item).strip()
        }
        current_state = _coerce_str(context.get("personality_state", "")).strip().lower()
        recent_key = str(self._data.get("recent_ambient_bits", [])[-1] if self._data.get("recent_ambient_bits") else "")
        weighted = []
        for beat in AMBIENT_WORLD_BEATS:
            if self.familiarity() < int(beat.min_familiarity):
                continue
            if beat.desk_item_key and beat.desk_item_key not in available_desk_items:
                continue
            if beat.companion_interaction and beat.companion_interaction not in available_companion:
                continue
            weight = 2
            if beat.key == recent_key:
                weight = 1
            if current_state and current_state == beat.state_key:
                weight += 2
            if beat.companion_interaction and "companion" in _top_keys(self._data.get("preferred_behaviors", {}), limit=3):
                weight += 2
            weighted.append((beat, weight))
        if not weighted:
            return None
        beat = self._weighted_choice(weighted)
        self._remember_recent("recent_ambient_bits", beat.key)
        return beat

    def next_milestone(self, stats=None, now=None, consume=False):
        stats = stats if isinstance(stats, dict) else {}
        seen = set(self._data.get("seen_milestones", []))
        session_minutes = self.session_minutes(now=now)
        companion_uses = int(self._data.get("preferred_behaviors", {}).get("companion", 0))
        for milestone in MILESTONE_MOMENTS:
            if milestone.key in seen:
                continue
            if milestone.days_used and int(self._data.get("days_used", 0)) < milestone.days_used:
                continue
            if milestone.total_sessions and int(self._data.get("total_sessions", 0)) < milestone.total_sessions:
                continue
            if milestone.interaction_streak and int(self._data.get("interaction_streak", 0)) < milestone.interaction_streak:
                continue
            if milestone.familiarity and self.familiarity() < milestone.familiarity:
                continue
            if milestone.runtime_minutes and int(stats.get("runtime_minutes", 0)) < milestone.runtime_minutes:
                continue
            if milestone.quotes_spoken and int(stats.get("quotes_spoken", 0)) < milestone.quotes_spoken:
                continue
            if milestone.scenario_runs and int(stats.get("scenario_runs", 0)) < milestone.scenario_runs:
                continue
            if milestone.companion_uses and companion_uses < milestone.companion_uses:
                continue
            if milestone.session_minutes and session_minutes < milestone.session_minutes:
                continue
            if consume:
                self.mark_milestone_seen(milestone.key, familiarity_gain=1)
            return milestone
        return None

    def unannounced_unlocks(self, catalog):
        announced = set(self._data.get("announced_unlocks", []))
        pending = []
        for item in list(catalog or []):
            key = _coerce_str(item.get("key", "")).strip().lower()
            if not key or not item.get("unlocked") or item.get("default_unlocked"):
                continue
            if key not in announced:
                pending.append(item)
        return pending

    def mark_unlocks_announced(self, unlock_keys):
        for key in list(unlock_keys or []):
            normalized = _coerce_str(key).strip().lower()
            if normalized:
                self._remember_recent("announced_unlocks", normalized, limit=MAX_ANNOUNCED_UNLOCKS)

    def backfill_existing_unlocks_as_announced(self, catalog):
        keys = []
        for item in list(catalog or []):
            key = _coerce_str(item.get("key", "")).strip().lower()
            if not key or not item.get("unlocked") or item.get("default_unlocked"):
                continue
            keys.append(key)
        self.mark_unlocks_announced(keys)

    def backfill_existing_milestones_as_seen(self, stats=None, now=None):
        stats = stats if isinstance(stats, dict) else {}
        session_minutes = self.session_minutes(now=now)
        companion_uses = int(self._data.get("preferred_behaviors", {}).get("companion", 0))
        seen = set(self._data.get("seen_milestones", []))
        for milestone in MILESTONE_MOMENTS:
            if milestone.key in seen:
                continue
            if milestone.days_used and int(self._data.get("days_used", 0)) < milestone.days_used:
                continue
            if milestone.total_sessions and int(self._data.get("total_sessions", 0)) < milestone.total_sessions:
                continue
            if milestone.interaction_streak and int(self._data.get("interaction_streak", 0)) < milestone.interaction_streak:
                continue
            if milestone.familiarity and self.familiarity() < milestone.familiarity:
                continue
            if milestone.runtime_minutes and int(stats.get("runtime_minutes", 0)) < milestone.runtime_minutes:
                continue
            if milestone.quotes_spoken and int(stats.get("quotes_spoken", 0)) < milestone.quotes_spoken:
                continue
            if milestone.scenario_runs and int(stats.get("scenario_runs", 0)) < milestone.scenario_runs:
                continue
            if milestone.companion_uses and companion_uses < milestone.companion_uses:
                continue
            if milestone.session_minutes and session_minutes < milestone.session_minutes:
                continue
            self.mark_milestone_seen(milestone.key)

    def mark_milestone_seen(self, milestone_key, familiarity_gain=0):
        normalized = _coerce_str(milestone_key).strip().lower()
        if not normalized:
            return False
        seen = set(self._data.get("seen_milestones", []))
        if normalized in seen:
            return False
        self._remember_recent("seen_milestones", normalized, limit=MAX_SEEN_MILESTONES)
        if int(familiarity_gain or 0) > 0:
            self._bump_familiarity(int(familiarity_gain))
        return True

    def build_unlock_announcement(self, discoveries):
        entries = list(discoveries or [])
        if not entries:
            return "New weird little thing unlocked."
        first = entries[0]
        label = _coerce_str(first.get("label", first.get("key", "Discovery"))).strip() or "Discovery"
        item_type = _coerce_str(first.get("item_type", "thing")).strip().lower()
        lead = {
            "quote_pack": f"New packet of nonsense unlocked:\n{label}",
            "scenario": f"Fresh desktop incident unlocked:\n{label}",
            "skin": f"Wardrobe irregularity unlocked:\n{label}",
            "toy": f"Toy-grade nonsense unlocked:\n{label}",
        }.get(item_type, f"New weird little thing unlocked:\n{label}")
        if len(entries) > 1:
            lead += f"\n+{len(entries) - 1} additional desk surprise(s)."
        return lead

    def _ensure_today_mode(self, now_dt, mood_key="happy", time_of_day=None):
        date_key = now_dt.date().isoformat()
        current_key = str(self._data.get("today_mode_key", "")).strip().lower()
        if current_key in SESSION_MODES and self._data.get("today_mode_date") == date_key:
            return SESSION_MODES[current_key]
        weighted = []
        normalized_time = self._normalize_time_of_day(time_of_day or now_dt)
        for mode in SESSION_MODES.values():
            weight = 2
            if normalized_time == "morning" and mode.key in {"patch-goblin", "quiet-audit"}:
                weight += 2
            if normalized_time == "night" and mode.key in {"cable-philosopher", "tiny-victory"}:
                weight += 1
            if str(mood_key).strip().lower() == "tired" and mode.key in {"quiet-audit", "helpdesk-mirage"}:
                weight += 2
            if str(mood_key).strip().lower() == "caffeinated" and mode.key in {"patch-goblin", "tiny-victory"}:
                weight += 2
            if self.relationship_tier() in {"established", "veteran"} and mode.key == "cable-philosopher":
                weight += 1
            weighted.append((mode, weight))
        selected = self._weighted_choice(weighted)
        self._data["today_mode_key"] = selected.key
        self._data["today_mode_date"] = date_key
        return selected

    def _ensure_theme_rotation(self, now_dt, selected_mode, mood_key="happy"):
        date_key = now_dt.date().isoformat()
        current_key = str(self._data.get("theme_rotation_key", "")).strip().lower()
        if current_key in THEME_SPOTLIGHTS and self._data.get("theme_rotation_date") == date_key:
            return THEME_SPOTLIGHTS[current_key]
        prior_key = current_key
        prior_streak = int(self._data.get("theme_rotation_streak", 0))
        weighted = []
        for theme in THEME_SPOTLIGHTS.values():
            if prior_key and theme.key == prior_key and prior_streak >= 2:
                continue
            weight = 2
            if set(theme.categories) & set(selected_mode.categories):
                weight += 2
            if theme.key == "sidekick-shift" and int(self._data.get("preferred_behaviors", {}).get("companion", 0)) >= 3:
                weight += 3
            if theme.key == "homelab-drift" and str(mood_key).strip().lower() == "caffeinated":
                weight += 1
            weighted.append((theme, weight))
        if not weighted:
            weighted = (
                [(THEME_SPOTLIGHTS[prior_key], 1)]
                if prior_key in THEME_SPOTLIGHTS
                else [(next(iter(THEME_SPOTLIGHTS.values())), 1)]
            )
        selected = self._weighted_choice(weighted)
        self._data["theme_rotation_key"] = selected.key
        self._data["theme_rotation_date"] = date_key
        self._data["theme_rotation_streak"] = (
            _coerce_int(prior_streak + 1, maximum=30)
            if selected.key == prior_key and prior_key
            else 1
        )
        return selected

    def _remember_recent(self, field_name, key, limit=MAX_RECENT_KEYS):
        normalized = _coerce_str(key).strip().lower()
        if not normalized:
            return
        recent = [item for item in list(self._data.get(field_name, [])) if item != normalized]
        recent.append(normalized)
        self._data[field_name] = recent[-int(limit):]

    def _pick_unique_tuple(self, options, recent_key=None, use_persistent_history=True):
        if not options:
            return "presence-fallback", "Still here."
        candidates = list(options)
        recent_values = []
        if use_persistent_history and recent_key:
            recent_values.extend(list(self._data.get(recent_key, [])))
        if not use_persistent_history:
            recent_values.extend(self._session_recent_reactions)
        recent_set = {str(value).strip().lower() for value in recent_values if str(value).strip()}
        filtered = [item for item in candidates if item[0] not in recent_set]
        if filtered:
            candidates = filtered
        choice = self.rng.choice(candidates)
        if use_persistent_history and recent_key:
            self._remember_recent(recent_key, choice[0])
        return choice

    def _weighted_choice(self, weighted):
        total = sum(max(1, int(weight)) for _item, weight in weighted)
        pick = self.rng.uniform(0, total)
        current = 0.0
        for item, weight in weighted:
            current += max(1, int(weight))
            if pick <= current:
                return item
        return weighted[-1][0]

    def _bump_familiarity(self, amount):
        self._data["familiarity"] = _coerce_int(
            int(self._data.get("familiarity", 0)) + max(0, int(amount)),
            minimum=0,
            maximum=100,
        )

    @staticmethod
    def _normalize_time_of_day(value):
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"morning", "day", "night"}:
                return lowered
        hour = int(getattr(value, "hour", datetime.now().hour))
        if hour < 12:
            return "morning"
        if hour < 18:
            return "day"
        return "night"

    @staticmethod
    def _coerce_datetime(value):
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value))
        return datetime.now()

    @staticmethod
    def _is_consecutive_day(previous, current):
        try:
            previous_date = datetime.fromisoformat(str(previous)).date()
            current_date = datetime.fromisoformat(str(current)).date()
        except ValueError:
            return False
        return (current_date - previous_date).days == 1

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message)
