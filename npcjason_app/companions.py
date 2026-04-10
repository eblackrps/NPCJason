from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
import time

from .windows_platform import clamp_window_position


COMPANION_PIXEL_SCALE = 4
COMPANION_TICK_MS = 120


@dataclass(frozen=True)
class CompanionStateDefinition:
    key: str
    label: str
    animation: tuple[str, ...]
    frame_ms: int = 180
    contexts: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class CompanionPhase:
    key: str
    state: str
    duration_ms: int
    contexts: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    sound_effect: str | None = None
    speech_line: str | None = None
    payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CompanionInteractionDefinition:
    key: str
    label: str
    description: str
    cooldown_ms: int
    contexts: tuple[str, ...]
    tags: tuple[str, ...]
    phases: tuple[CompanionPhase, ...]
    sound_effect: str | None = None


@dataclass(frozen=True)
class CompanionDefinition:
    key: str
    label: str
    description: str
    behavior: str
    metadata: dict
    palette: dict
    frames: dict
    states: dict[str, CompanionStateDefinition]
    interactions: dict[str, CompanionInteractionDefinition]
    tags: tuple[str, ...] = ()
    contexts: tuple[str, ...] = ()
    default_state: str = "idle"
    default_enabled: bool = True
    follow_left_offset: tuple[int, int] = (-44, 44)
    follow_right_offset: tuple[int, int] = (48, 44)
    interaction_offset: tuple[int, int] = (-14, 48)


@dataclass(frozen=True)
class CompanionInteractionResult:
    started: bool
    reason: str = ""
    companion_key: str | None = None
    interaction_key: str | None = None
    sound_effect: str | None = None
    contexts: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    remaining_cooldown_ms: int = 0


@dataclass(frozen=True)
class CompanionTickResult:
    active: bool
    next_delay_ms: int
    companion_key: str | None = None
    companion_label: str = ""
    state_key: str = ""
    state_label: str = ""
    contexts: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    speech_line: str | None = None
    sound_effect: str | None = None
    active_interaction: str | None = None
    state_changed: bool = False


MOUSE_FRAMES = {
    "idle_a": (
        "............",
        "..P..P......",
        ".PMMMM......",
        "PMMKKMMTT...",
        ".PMMMMMTTT..",
        "..PMMMMTT...",
        "...TTTT.....",
        "............",
    ),
    "idle_b": (
        "............",
        "..P..P......",
        ".PMMMM......",
        "PMMKKMMTT...",
        ".PMMMMMTTT..",
        "..PMMMTT....",
        "...TTTTT....",
        "............",
    ),
    "wait_a": (
        "............",
        "...P..P.....",
        "..PMMMM.....",
        ".PMMKKMMT...",
        "..PMMMMMTT..",
        "...PMMMTTT..",
        "....TTTT....",
        "............",
    ),
    "wait_b": (
        "............",
        "...P..P.....",
        "..PMMMM.....",
        ".PMMKKMMT...",
        "..PMMMMMTT..",
        "...PMMTTT...",
        "....TTTTT...",
        "............",
    ),
    "run_a": (
        "............",
        "..P..P......",
        ".PMMMM......",
        "PMMKKMMTT...",
        ".PMMMMMTT...",
        "..PMMMT.TT..",
        ".TT..TT.....",
        "............",
    ),
    "run_b": (
        "............",
        "..P..P......",
        ".PMMMM......",
        "PMMKKMMTT...",
        ".PMMMMMTTT..",
        "..PMMTT.T...",
        "...TT..TT...",
        "............",
    ),
    "sniff_a": (
        "............",
        "..P..P......",
        ".PMMMM......",
        "PMMKKMMTT...",
        ".PMMMMMTTT..",
        "..PMMMMT....",
        "....TTTT....",
        ".....P......",
    ),
    "sniff_b": (
        "............",
        "..P..P......",
        ".PMMMM......",
        "PMMKKMMTT...",
        ".PMMMMMTTT..",
        "..PMMMMT....",
        "...TTTT.....",
        "......P.....",
    ),
    "cheese_a": (
        "............",
        "..P..P......",
        ".PMMMM......",
        "PMMKKMMTT...",
        ".PMMMMMTTC..",
        "..PMMMMTTCC.",
        "...TTTT..C..",
        "............",
    ),
    "cheese_b": (
        "............",
        "..P..P......",
        ".PMMMM......",
        "PMMKKMMTT...",
        ".PMMMMMTTC..",
        "..PMMMMTCCC.",
        "...TTTT.C...",
        "............",
    ),
    "flip_1": (
        "............",
        "...P..P.....",
        "..PMMMM.....",
        ".PMMKKMM....",
        "..PMMMMTT...",
        "...PMMTTT...",
        "..TTTT......",
        "............",
    ),
    "flip_2": (
        ".....P......",
        "....PMM.....",
        "...PMKKM....",
        "..PMMMMM....",
        "..TTMMMT....",
        "...TTTT.....",
        "............",
        "............",
    ),
    "flip_3": (
        "....TT......",
        "...PMM......",
        "..PMMMMM....",
        "..PMKKM.....",
        "...PMM......",
        "....P.......",
        "............",
        "............",
    ),
    "flip_4": (
        "............",
        "..TTTT......",
        "...TTTMP....",
        "...MMMMMP...",
        "....MKKMMP..",
        ".....MMM....",
        "......P.....",
        "............",
    ),
    "flip_5": (
        "............",
        "............",
        "...TTTT.....",
        "..TTMMMT....",
        "..PMMMMM....",
        "...PMKKM....",
        "....PMM.....",
        ".....P......",
    ),
    "flip_6": (
        "............",
        "..TTTT......",
        "...PMMTTT...",
        "..PMMMMTT...",
        ".PMMKKMM....",
        "..PMMMM.....",
        "...P..P.....",
        "............",
    ),
    "proud": (
        "............",
        "..P..P......",
        ".PMMMM......",
        "PMMKKMMTT...",
        ".PMMMMMTTT..",
        "..PMMMMT....",
        "...TTTT.....",
        "....C.......",
    ),
}


MOUSE_STATE_DEFINITIONS = {
    "idle": CompanionStateDefinition("idle", "Idle", ("idle_a", "idle_b"), 240, ("companion", "mouse-idle"), ("companion", "mouse")),
    "following": CompanionStateDefinition("following", "Following", ("run_a", "run_b"), 100, ("companion", "mouse-follow"), ("companion", "mouse", "follow")),
    "waiting": CompanionStateDefinition("waiting", "Waiting", ("wait_a", "wait_b"), 250, ("companion", "mouse-wait"), ("companion", "mouse")),
    "sniffing": CompanionStateDefinition("sniffing", "Sniffing", ("sniff_a", "sniff_b"), 210, ("companion", "mouse-sniff"), ("companion", "mouse", "curious")),
    "nibbling": CompanionStateDefinition("nibbling", "Nibbling", ("cheese_a", "cheese_b"), 150, ("companion", "mouse-cheese"), ("companion", "mouse", "cheese")),
    "backflip": CompanionStateDefinition("backflip", "Backflipping", ("flip_1", "flip_2", "flip_3", "flip_4", "flip_5", "flip_6"), 80, ("companion", "mouse-backflip"), ("companion", "mouse", "backflip", "playful")),
    "proud": CompanionStateDefinition("proud", "Looking Extremely Pleased", ("proud", "idle_b"), 230, ("companion", "mouse-proud"), ("companion", "mouse", "smug")),
}


MOUSE_INTERACTIONS = {
    "feed-cheese": CompanionInteractionDefinition(
        key="feed-cheese",
        label="Feed Cheese",
        description="Feed the mouse a tiny piece of cheese and accept the consequences.",
        cooldown_ms=55_000,
        contexts=("companion", "mouse", "feed-cheese"),
        tags=("companion", "mouse", "cheese"),
        phases=(
            CompanionPhase("approach", "following", 420, ("companion", "mouse-approach"), ("companion", "mouse")),
            CompanionPhase("nibble", "nibbling", 940, ("companion", "mouse-cheese"), ("companion", "mouse", "cheese")),
            CompanionPhase("backflip", "backflip", 1_520, ("companion", "mouse-backflip", "dance"), ("companion", "mouse", "backflip", "playful"), payload={"flips": 2}),
            CompanionPhase("credit", "proud", 1_600, ("companion", "mouse-proud"), ("companion", "mouse", "smug"), speech_line="Ansible Chris made me do it"),
        ),
    ),
    "desk-patrol": CompanionInteractionDefinition(
        key="desk-patrol",
        label="Desk Patrol",
        description="Send the mouse on a very official little perimeter check.",
        cooldown_ms=46_000,
        contexts=("companion", "mouse", "desk-patrol"),
        tags=("companion", "mouse", "desk", "patrol"),
        phases=(
            CompanionPhase("approach", "following", 520, ("companion", "mouse-approach"), ("companion", "mouse")),
            CompanionPhase("sniff", "sniffing", 860, ("companion", "mouse-sniff"), ("companion", "mouse", "curious")),
            CompanionPhase("report", "waiting", 1_240, ("companion", "mouse-wait"), ("companion", "mouse", "desk"), speech_line="Desk perimeter checked.\nStill weird."),
        ),
    ),
    "cable-audit": CompanionInteractionDefinition(
        key="cable-audit",
        label="Cable Audit",
        description="Let the mouse investigate the cable situation with absolute false confidence.",
        cooldown_ms=58_000,
        contexts=("companion", "mouse", "cable-audit"),
        tags=("companion", "mouse", "network", "cable"),
        phases=(
            CompanionPhase("approach", "following", 460, ("companion", "mouse-approach"), ("companion", "mouse")),
            CompanionPhase("inspect", "sniffing", 980, ("companion", "mouse-sniff", "network"), ("companion", "mouse", "network")),
            CompanionPhase("report", "proud", 1_380, ("companion", "mouse-proud"), ("companion", "mouse", "smug"), speech_line="I inspected the cable.\nNo further clarity."),
        ),
    ),
    "victory-scamper": CompanionInteractionDefinition(
        key="victory-scamper",
        label="Victory Scamper",
        description="A tiny celebratory sprint for moments that absolutely did not need one.",
        cooldown_ms=52_000,
        contexts=("companion", "mouse", "victory-scamper"),
        tags=("companion", "mouse", "celebrating", "playful"),
        phases=(
            CompanionPhase("launch", "following", 420, ("companion", "mouse-follow"), ("companion", "mouse", "playful")),
            CompanionPhase("scamper", "following", 960, ("companion", "mouse-follow", "dance"), ("companion", "mouse", "celebrating"), payload={"frame_ms": 85}),
            CompanionPhase("pose", "proud", 1_280, ("companion", "mouse-proud"), ("companion", "mouse", "smug"), speech_line="Tiny victory lap complete."),
        ),
    ),
    "crumb-heist": CompanionInteractionDefinition(
        key="crumb-heist",
        label="Crumb Heist",
        description="Allow the mouse to recover one suspiciously strategic desk crumb.",
        cooldown_ms=49_000,
        contexts=("companion", "mouse", "crumb-heist"),
        tags=("companion", "mouse", "desk", "snack"),
        phases=(
            CompanionPhase("approach", "following", 440, ("companion", "mouse-approach"), ("companion", "mouse")),
            CompanionPhase("sniff", "sniffing", 840, ("companion", "mouse-sniff"), ("companion", "mouse", "curious")),
            CompanionPhase("recover", "nibbling", 920, ("companion", "mouse-cheese"), ("companion", "mouse", "desk")),
            CompanionPhase("report", "proud", 1_260, ("companion", "mouse-proud"), ("companion", "mouse", "smug"), speech_line="Recovered one desk crumb.\nClassified."),
        ),
    ),
    "mug-recon": CompanionInteractionDefinition(
        key="mug-recon",
        label="Mug Recon",
        description="Send the mouse to investigate the coffee situation with tiny field notes.",
        cooldown_ms=63_000,
        contexts=("companion", "mouse", "mug-recon"),
        tags=("companion", "mouse", "coffee", "office"),
        phases=(
            CompanionPhase("approach", "following", 430, ("companion", "mouse-approach"), ("companion", "mouse")),
            CompanionPhase("inspect", "sniffing", 900, ("companion", "mouse-sniff"), ("companion", "mouse", "coffee")),
            CompanionPhase("hover", "waiting", 880, ("companion", "mouse-wait"), ("companion", "mouse", "office")),
            CompanionPhase("report", "proud", 1_260, ("companion", "mouse-proud"), ("companion", "mouse", "smug"), speech_line="Steam levels acceptable.\nSmells like tickets."),
        ),
    ),
    "zip-tie-recovery": CompanionInteractionDefinition(
        key="zip-tie-recovery",
        label="Zip Tie Recovery",
        description="Have the mouse search for tiny forbidden infrastructure beneath the desk vibe.",
        cooldown_ms=61_000,
        contexts=("companion", "mouse", "zip-tie-recovery"),
        tags=("companion", "mouse", "network", "desk"),
        phases=(
            CompanionPhase("approach", "following", 460, ("companion", "mouse-follow"), ("companion", "mouse")),
            CompanionPhase("search", "sniffing", 980, ("companion", "mouse-sniff", "network"), ("companion", "mouse", "network")),
            CompanionPhase("stash", "waiting", 960, ("companion", "mouse-wait"), ("companion", "mouse", "desk")),
            CompanionPhase("report", "proud", 1_320, ("companion", "mouse-proud"), ("companion", "mouse", "smug"), speech_line="I found a zip tie.\nI now outrank someone."),
        ),
    ),
}


COMPANION_DEFINITIONS = {
    "mouse": CompanionDefinition(
        key="mouse",
        label="Mouse Sidekick",
        description="A tiny mouse with strong opinions about cheese and desktop operations.",
        behavior="mouse",
        metadata={
            "author": "NPCJason",
            "description": "A lightweight companion who scurries around Jason and gets far too confident after cheese.",
        },
        palette={"M": "#9aa5b1", "P": "#ffb4c1", "K": "#273043", "T": "#697886", "C": "#ffd166"},
        frames=MOUSE_FRAMES,
        states=MOUSE_STATE_DEFINITIONS,
        interactions=MOUSE_INTERACTIONS,
        tags=("companion", "mouse", "desk"),
        contexts=("companion", "mouse"),
        default_state="idle",
        default_enabled=True,
        follow_left_offset=(-46, 46),
        follow_right_offset=(48, 46),
        interaction_offset=(-10, 48),
    ),
}


class BaseCompanionBehavior:
    def __init__(self, definition, root=None, logger=None, clock=None, rng=None):
        self.definition = definition
        self.root = root
        self.logger = logger
        self.clock = clock or time.monotonic
        self.rng = rng or random.Random()
        self.window = None
        self._window_failed = False
        self.width = max(len(row) for row in next(iter(definition.frames.values())))
        self.height = len(next(iter(definition.frames.values())))
        self.pixel_width = self.width * COMPANION_PIXEL_SCALE
        self.pixel_height = self.height * COMPANION_PIXEL_SCALE
        self.x = 0
        self.y = 0
        self.side = "left"
        self._initialized = False
        self._state = definition.default_state
        self._state_entered_at_ms = self._now_ms()
        self._state_until_ms = self._state_entered_at_ms + 2_200
        self._active_interaction_key = None
        self._phase_index = 0
        self._phase_started_at_ms = 0
        self._entered_phase_index = None
        self._cooldowns = {}

    def state_label(self):
        state = self.definition.states.get(self._state)
        if state:
            return state.label
        return self._state.replace("-", " ").title()

    def active_interaction_key(self):
        return self._active_interaction_key

    def active_contexts(self):
        contexts = list(self.definition.contexts)
        state = self.definition.states.get(self._state)
        if state:
            contexts.extend(state.contexts)
        if self._active_interaction_key:
            interaction = self.definition.interactions.get(self._active_interaction_key)
            if interaction:
                contexts.extend(interaction.contexts)
                phase = self._current_phase(interaction)
                if phase is not None:
                    contexts.extend(phase.contexts)
        return tuple(_dedupe(contexts))

    def active_tags(self):
        tags = list(self.definition.tags)
        state = self.definition.states.get(self._state)
        if state:
            tags.extend(state.tags)
        if self._active_interaction_key:
            interaction = self.definition.interactions.get(self._active_interaction_key)
            if interaction:
                tags.extend(interaction.tags)
                phase = self._current_phase(interaction)
                if phase is not None:
                    tags.extend(phase.tags)
        return tuple(_dedupe(tags))

    def remaining_cooldown_ms(self, interaction_key):
        return max(0, int(self._cooldowns.get(str(interaction_key or ""), 0) - self._now_ms()))

    def available_interactions(self):
        items = []
        for interaction in self.definition.interactions.values():
            cooldown_ms = self.remaining_cooldown_ms(interaction.key)
            items.append(
                {
                    "key": interaction.key,
                    "label": interaction.label,
                    "description": interaction.description,
                    "cooldown_ms": cooldown_ms,
                    "active": interaction.key == self._active_interaction_key,
                    "contexts": list(interaction.contexts),
                    "tags": list(interaction.tags),
                }
            )
        return items

    def blocks_owner_movement(self):
        return self._active_interaction_key is not None

    def trigger_interaction(self, interaction_key):
        interaction = self.definition.interactions.get(str(interaction_key or "").strip())
        if interaction is None:
            return CompanionInteractionResult(started=False, reason="unknown-interaction")
        if self._active_interaction_key is not None:
            return CompanionInteractionResult(
                started=False,
                reason="busy",
                companion_key=self.definition.key,
                interaction_key=self._active_interaction_key,
            )
        cooldown_ms = self.remaining_cooldown_ms(interaction.key)
        if cooldown_ms > 0:
            return CompanionInteractionResult(
                started=False,
                reason="cooldown",
                companion_key=self.definition.key,
                interaction_key=interaction.key,
                remaining_cooldown_ms=cooldown_ms,
            )
        self._active_interaction_key = interaction.key
        self._phase_index = 0
        self._phase_started_at_ms = self._now_ms()
        self._entered_phase_index = None
        self._set_state(interaction.phases[0].state, duration_ms=interaction.phases[0].duration_ms)
        self._cooldowns[interaction.key] = self._now_ms() + int(interaction.cooldown_ms)
        return CompanionInteractionResult(
            started=True,
            companion_key=self.definition.key,
            interaction_key=interaction.key,
            sound_effect=interaction.sound_effect,
            contexts=interaction.contexts,
            tags=interaction.tags,
        )

    def tick(self, owner_x, owner_y, work_area, hidden=False, owner_context=None):
        owner_context = dict(owner_context or {})
        now_ms = self._now_ms()
        target_x, target_y = self._target_position(owner_x, owner_y, work_area, owner_context)
        if not self._initialized:
            self.x = target_x
            self.y = target_y
            self._initialized = True

        state_changed = False
        speech_line = None
        sound_effect = None
        phase = None
        entered_phase = False

        if self._active_interaction_key:
            phase, entered_phase = self._advance_interaction(now_ms)
            if entered_phase and phase is not None:
                state_changed = True
                speech_line = phase.speech_line
                sound_effect = phase.sound_effect
        else:
            state_changed = self._advance_idle_state(now_ms, owner_context, target_x, target_y)

        self._update_position(target_x, target_y, now_ms, phase)
        frame_key = self._current_frame(now_ms, phase)
        if hidden:
            self._hide_window()
        else:
            self._render(frame_key)

        return CompanionTickResult(
            active=True,
            next_delay_ms=COMPANION_TICK_MS,
            companion_key=self.definition.key,
            companion_label=self.definition.label,
            state_key=self._state,
            state_label=self.state_label(),
            contexts=self.active_contexts(),
            tags=self.active_tags(),
            speech_line=speech_line,
            sound_effect=sound_effect,
            active_interaction=self._active_interaction_key,
            state_changed=state_changed,
        )

    def shutdown(self):
        if self.window and self.window.exists():
            self.window.destroy()
        self.window = None

    def _advance_interaction(self, now_ms):
        interaction = self.definition.interactions.get(self._active_interaction_key or "")
        if interaction is None:
            self._active_interaction_key = None
            return None, False
        while self._phase_index < len(interaction.phases):
            phase = interaction.phases[self._phase_index]
            if self._entered_phase_index != self._phase_index:
                self._entered_phase_index = self._phase_index
                self._phase_started_at_ms = now_ms
                self._set_state(phase.state, duration_ms=phase.duration_ms)
                return phase, True
            if now_ms - self._phase_started_at_ms < int(phase.duration_ms):
                return phase, False
            self._phase_index += 1
            self._entered_phase_index = None
        self._active_interaction_key = None
        self._phase_index = 0
        self._entered_phase_index = None
        self._set_state("proud", duration_ms=2_100)
        return None, True

    def _advance_idle_state(self, now_ms, owner_context, target_x, target_y):
        if self._distance_to(target_x, target_y) > 18:
            if self._state != "following":
                self._set_state("following", duration_ms=800)
                return True
            return False
        if self._state == "following":
            self._set_state("waiting", duration_ms=1_400)
            return True
        if now_ms < self._state_until_ms:
            return False
        next_state = self._pick_idle_state(owner_context)
        self._set_state(next_state, duration_ms=self.rng.randint(1_200, 2_800))
        return True

    def _pick_idle_state(self, owner_context):
        weighted = [("idle", 4), ("waiting", 3), ("sniffing", 2)]
        personality = str(owner_context.get("personality_state", "")).strip()
        active_toy = str(owner_context.get("active_toy", "")).strip()
        if personality in {"curious", "confused"}:
            weighted.append(("sniffing", 2))
        if personality in {"busy", "annoyed"}:
            weighted.append(("waiting", 2))
        if active_toy:
            weighted.append(("waiting", 2))
        total = sum(weight for _state, weight in weighted)
        pick = self.rng.uniform(0, total)
        current = 0.0
        for state_key, weight in weighted:
            current += weight
            if pick <= current:
                return state_key
        return weighted[-1][0]

    def _target_position(self, owner_x, owner_y, bounds, owner_context):
        left_target = (
            int(owner_x) + int(self.definition.follow_left_offset[0]),
            int(owner_y) + int(self.definition.follow_left_offset[1]),
        )
        right_target = (
            int(owner_x) + int(self.definition.follow_right_offset[0]),
            int(owner_y) + int(self.definition.follow_right_offset[1]),
        )
        left_fit = left_target[0] >= int(bounds.left)
        right_fit = right_target[0] + int(self.pixel_width) <= int(bounds.right)
        if left_fit or not right_fit:
            self.side = "left"
            target = left_target
        else:
            self.side = "right"
            target = right_target
        if self._active_interaction_key:
            target = (
                int(owner_x) + int(self.definition.interaction_offset[0]),
                int(owner_y) + int(self.definition.interaction_offset[1]),
            )
        if owner_context.get("active_toy") == "tricycle" and not self._active_interaction_key:
            target = (target[0] - 14, target[1] + 2)
        clamped_x, clamped_y = clamp_window_position(
            target[0],
            target[1],
            self.pixel_width,
            self.pixel_height,
            bounds,
        )
        return clamped_x, clamped_y

    def _update_position(self, target_x, target_y, now_ms, phase):
        phase_key = phase.key if phase else ""
        if phase_key == "backflip":
            progress = self._phase_progress(now_ms, phase)
            flips = max(1, int(phase.payload.get("flips", 2)))
            arc = math.sin(progress * math.pi * flips)
            self.x = int(target_x + (8 if self.side == "left" else -8) * arc)
            self.y = int(target_y - abs(arc) * 18)
            return
        step_x = 10 if self._state in {"following", "nibbling"} else 4
        step_y = 8 if self._state in {"following", "nibbling"} else 3
        self.x = _move_toward(self.x, target_x, step_x)
        self.y = _move_toward(self.y, target_y, step_y)
        if self._state in {"idle", "waiting", "sniffing", "proud"}:
            bob = int(math.sin((now_ms - self._state_entered_at_ms) / 210.0) * (1 if self._state != "proud" else 2))
            self.y += bob

    def _current_frame(self, now_ms, phase):
        state = self.definition.states.get(self._state, self.definition.states[self.definition.default_state])
        animation = tuple(state.animation or ())
        if not animation:
            return next(iter(self.definition.frames))
        frame_ms = max(60, int(state.frame_ms))
        if phase and phase.payload.get("frame_ms") is not None:
            frame_ms = max(50, int(phase.payload["frame_ms"]))
        index = max(0, int((now_ms - self._state_entered_at_ms) / frame_ms))
        return animation[index % len(animation)]

    def _phase_progress(self, now_ms, phase):
        if phase is None:
            return 0.0
        duration_ms = max(1, int(phase.duration_ms))
        elapsed = max(0, int(now_ms - self._phase_started_at_ms))
        return min(1.0, elapsed / duration_ms)

    def _current_phase(self, interaction):
        if not interaction or self._entered_phase_index is None:
            return None
        if self._entered_phase_index >= len(interaction.phases):
            return None
        return interaction.phases[self._entered_phase_index]

    def _set_state(self, state_key, duration_ms=1_600):
        target = str(state_key or self.definition.default_state).strip()
        if target not in self.definition.states:
            target = self.definition.default_state
        self._state = target
        self._state_entered_at_ms = self._now_ms()
        self._state_until_ms = self._state_entered_at_ms + max(350, int(duration_ms))

    def _distance_to(self, target_x, target_y):
        return abs(int(target_x) - int(self.x)) + abs(int(target_y) - int(self.y))

    def _hide_window(self):
        if self.window and self.window.exists():
            self.window.hide()

    def _render(self, frame_key):
        if self.root is None or self._window_failed:
            return
        if self.window is None:
            try:
                from .toy_window import ToyWindow
            except Exception as exc:
                self._window_failed = True
                self._log("warning", f"companion: window unavailable ({exc})")
                return
            self.window = ToyWindow(self.root, self.pixel_width, self.pixel_height, logger=self.logger)
        if not self.window.exists():
            return
        self.window.show()
        self.window.render_frame(
            self.definition.frames[frame_key],
            self.definition.palette,
            COMPANION_PIXEL_SCALE,
        )
        self.window.move_to(self.x, self.y)

    def _now_ms(self):
        return int(self.clock() * 1000)

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message)


class MouseCompanionBehavior(BaseCompanionBehavior):
    pass


BEHAVIOR_TYPES = {
    "mouse": MouseCompanionBehavior,
}


class CompanionManager:
    def __init__(self, root=None, logger=None, clock=None, rng=None):
        self.root = root
        self.logger = logger
        self.clock = clock or time.monotonic
        self.rng = rng or random.Random()
        self.definitions = dict(COMPANION_DEFINITIONS)
        self.enabled = True
        self.selected_key = "mouse"
        self._runtime = None

    def configure(self, enabled=None, selected_key=None):
        if enabled is not None:
            self.enabled = bool(enabled)
        if selected_key:
            normalized = str(selected_key).strip()
            if normalized in self.definitions and normalized != self.selected_key:
                self._destroy_runtime()
                self.selected_key = normalized
        if self.selected_key not in self.definitions and self.definitions:
            self.selected_key = next(iter(self.definitions.keys()))
        if not self.enabled:
            self._hide_runtime()

    def shutdown(self):
        self._destroy_runtime()

    def selected_definition(self):
        return self.definitions.get(self.selected_key)

    def current_companion_key(self):
        if not self.enabled or not self.selected_definition():
            return ""
        return self.selected_definition().key

    def current_companion_label(self):
        if not self.enabled or not self.selected_definition():
            return "None"
        return self.selected_definition().label

    def current_state_label(self):
        runtime = self._ensure_runtime()
        if runtime is None:
            return "Hidden" if not self.enabled else "Unavailable"
        return runtime.state_label()

    def active_interaction_key(self):
        runtime = self._ensure_runtime()
        if runtime is None:
            return ""
        return runtime.active_interaction_key() or ""

    def active_contexts(self):
        if not self.enabled:
            return ()
        runtime = self._ensure_runtime()
        if runtime is None:
            definition = self.selected_definition()
            return tuple(definition.contexts) if definition else ()
        return runtime.active_contexts()

    def active_tags(self):
        if not self.enabled:
            return ()
        runtime = self._ensure_runtime()
        if runtime is None:
            definition = self.selected_definition()
            return tuple(definition.tags) if definition else ()
        return runtime.active_tags()

    def blocks_owner_movement(self):
        runtime = self._ensure_runtime()
        return bool(self.enabled and runtime and runtime.blocks_owner_movement())

    def available_companions(self):
        items = []
        current_state = self.current_state_label()
        for definition in sorted(self.definitions.values(), key=lambda value: value.label.lower()):
            items.append(
                {
                    "key": definition.key,
                    "label": definition.label,
                    "description": definition.description,
                    "enabled": self.enabled and definition.key == self.selected_key,
                    "selected": definition.key == self.selected_key,
                    "state_label": current_state if definition.key == self.selected_key and self.enabled else "Hidden",
                }
            )
        return items

    def available_interactions(self):
        definition = self.selected_definition()
        if definition is None:
            return []
        runtime = self._ensure_runtime()
        if runtime is None:
            return [
                {
                    "key": interaction.key,
                    "label": interaction.label,
                    "description": interaction.description,
                    "cooldown_ms": 0,
                    "active": False,
                    "contexts": list(interaction.contexts),
                    "tags": list(interaction.tags),
                }
                for interaction in definition.interactions.values()
            ]
        return runtime.available_interactions()

    def trigger_interaction(self, interaction_key):
        if not self.enabled:
            return CompanionInteractionResult(started=False, reason="disabled")
        runtime = self._ensure_runtime()
        if runtime is None:
            return CompanionInteractionResult(started=False, reason="ui-unavailable")
        return runtime.trigger_interaction(interaction_key)

    def tick(self, owner_x, owner_y, work_area, hidden=False, owner_context=None):
        if not self.enabled:
            self._hide_runtime()
            return CompanionTickResult(active=False, next_delay_ms=COMPANION_TICK_MS)
        runtime = self._ensure_runtime()
        if runtime is None:
            return CompanionTickResult(active=False, next_delay_ms=COMPANION_TICK_MS)
        return runtime.tick(
            owner_x=owner_x,
            owner_y=owner_y,
            work_area=work_area,
            hidden=hidden,
            owner_context=owner_context,
        )

    def _ensure_runtime(self):
        if not self.enabled:
            return None
        definition = self.selected_definition()
        if definition is None:
            return None
        if self._runtime is not None and self._runtime.definition.key == definition.key:
            return self._runtime
        behavior_type = BEHAVIOR_TYPES.get(definition.behavior)
        if behavior_type is None:
            self._log("warning", f"companion: unsupported behavior '{definition.behavior}'")
            return None
        self._destroy_runtime()
        self._runtime = behavior_type(
            definition,
            root=self.root,
            logger=self.logger,
            clock=self.clock,
            rng=self.rng,
        )
        return self._runtime

    def _hide_runtime(self):
        if self._runtime:
            self._runtime._hide_window()

    def _destroy_runtime(self):
        if self._runtime:
            self._runtime.shutdown()
        self._runtime = None

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message)


def _move_toward(current, target, step):
    if current == target:
        return int(current)
    if current < target:
        return int(min(target, current + max(1, int(step))))
    return int(max(target, current - max(1, int(step))))


def _dedupe(values):
    ordered = []
    seen = set()
    for value in list(values or []):
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered
