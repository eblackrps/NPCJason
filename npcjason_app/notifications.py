from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class NotificationReactionDefinition:
    key: str
    label: str
    required_contexts: tuple[str, ...]
    chance: float
    cooldown_ms: int
    state_key: str
    preferred_categories: tuple[str, ...] = ()
    preferred_packs: tuple[str, ...] = ()
    desk_item_key: str = ""
    companion_interaction: str = ""
    quote_contexts: tuple[str, ...] = ()
    render_overrides: dict | None = None


REACTION_DEFINITIONS = (
    NotificationReactionDefinition(
        key="ticket-triage",
        label="Ticket Triage",
        required_contexts=("title-ticket",),
        chance=0.24,
        cooldown_ms=48_000,
        state_key="busy",
        preferred_categories=("office", "responsible", "helpdesk"),
        preferred_packs=("networking-meltdown-helpdesk-chaos", "app-title-humor"),
        desk_item_key="keyboard",
        quote_contexts=("notification", "ticket-triage"),
    ),
    NotificationReactionDefinition(
        key="meeting-coffee-stare",
        label="Meeting Coffee Stare",
        required_contexts=("title-meeting",),
        chance=0.17,
        cooldown_ms=55_000,
        state_key="annoyed",
        preferred_categories=("office", "playful"),
        preferred_packs=("app-title-humor",),
        desk_item_key="coffee-mug",
        quote_contexts=("notification", "meeting-coffee"),
    ),
    NotificationReactionDefinition(
        key="rack-check",
        label="Rack Check",
        required_contexts=("title-cisco", "title-homelab", "title-networking"),
        chance=0.25,
        cooldown_ms=46_000,
        state_key="curious",
        preferred_categories=("network", "homelab", "cisco"),
        preferred_packs=("networking-meltdown-helpdesk-chaos", "cisco-jokes", "app-title-humor"),
        desk_item_key="tiny-network-rack",
        companion_interaction="cable-audit",
        quote_contexts=("notification", "rack-check"),
    ),
    NotificationReactionDefinition(
        key="code-mutter",
        label="Code Mutter",
        required_contexts=("title-code", "title-terminal"),
        chance=0.16,
        cooldown_ms=42_000,
        state_key="curious",
        preferred_categories=("office", "playful"),
        preferred_packs=("app-title-humor",),
        desk_item_key="keyboard",
        quote_contexts=("notification", "code-mutter"),
    ),
)


def pick_notification_reaction(observation, runtime_context=None, rng=None):
    observation = observation if isinstance(observation, dict) else {}
    contexts = {str(item).strip() for item in observation.get("contexts", []) if str(item).strip()}
    runtime_context = runtime_context if isinstance(runtime_context, dict) else {}
    rng = rng or random
    if not contexts:
        return None

    weighted = []
    for definition in REACTION_DEFINITIONS:
        matches = len(contexts & set(definition.required_contexts))
        if matches <= 0:
            continue
        weight = 2 + (matches * 3)
        if definition.desk_item_key and definition.desk_item_key == str(runtime_context.get("active_desk_item", "")).strip():
            weight = max(1, weight - 2)
        if definition.companion_interaction and definition.companion_interaction == str(runtime_context.get("active_companion_interaction", "")).strip():
            weight = max(1, weight - 2)
        if definition.state_key == str(runtime_context.get("personality_state", "")).strip():
            weight += 1
        weighted.append((definition, weight))

    if not weighted:
        return None

    total = sum(weight for _definition, weight in weighted)
    pick = rng.uniform(0, total)
    current = 0.0
    for definition, weight in weighted:
        current += weight
        if pick <= current:
            return definition
    return weighted[-1][0]
