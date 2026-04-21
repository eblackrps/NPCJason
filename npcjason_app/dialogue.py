from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import random
import re

from .paths import RESOURCE_DIALOGUE_PACKS_DIR, RESOURCE_SAYINGS_PATH


GENERAL_SAYINGS = [
    "I used to be an adventurer like you...\nthen I took a reboot to the BIOS.",
    "Have you tried turning it off\nand never turning it back on?",
    "I'm not lazy.\nI'm on energy-saving mode.",
    "Welcome, traveler!\nI have no quests.\nJust vibes.",
    "Do I look like I know\nwhat a JPEG is?",
    "Error 404:\nMotivation not found.",
    "I'd give you a quest,\nbut I'm on break.",
    "The real treasure was\nthe uptime we had along the way.",
    "Sure, I could help...\nbut have you checked Stack Overflow?",
    "NPC life is hard.\nSame dialogue. Every. Day.",
    "I guard this desktop\nwith my life.\nNo, literally. I can't leave.",
    "You look like someone\nwho closes terminals\nwithout saving.",
    "My therapist says I need\nto stop living in other\npeople's taskbars.",
    "You're doing great.\nSeriously. Keep going.",
    "Every expert was once\na beginner who refused to quit.",
    "Ship it.\nYou can fix it in prod.\n(Don't actually do that.)",
    "Today's a good day\nto write clean code.",
    "Remember:\nDone is better than perfect.",
    "You've mass-deployed VMs\nbefore breakfast.\nYou can handle this.",
    "Believe in yourself.\nI believe in you.\nAnd I'm just pixels.",
    "There are 10 types of people:\nthose who understand binary\nand those who don't.",
    "A SQL query walks into a bar,\nsees two tables, and asks...\n'Can I JOIN you?'",
    "It works on my machine.\n...ships machine.",
    "Git commit -m\n'I have no idea what I changed\nbut it works now'",
    "'It's not a bug,\nit's a feature'\n- every dev ever",
    "Roses are red,\nviolets are blue,\nunexpected '{'\non line 32.",
    "To understand recursion,\nyou must first\nunderstand recursion.",
    "There's no place like\n127.0.0.1",
    "UDP joke?\nI'd tell you one\nbut you might not get it.",
    "!false\n...it's funny because it's true.",
    "Am I an NPC?\nOr are you the NPC\nin my story?",
    "If a desktop pet dances\nand no one is watching,\ndoes it still lag?",
    "I think, therefore I use RAM.",
    "We're all just processes\nwaiting to be scheduled.",
    "Do androids dream\nof electric uptime?",
    "It's been two weeks\nand no coffee videos.",
    "Where be my tokens?\nThey go'ed missin.",
    "All yo firewalls\nbelonging to NPCJason.",
    "F*CK Cisco Firepower.",
    "Is this on mang?",
    "Buller... Buller...",
    "Anyone? Anyone?",
    "ALL THE PATCHES?!",
    "Thinking about\nREBOOT'n Winderz...",
]

MOOD_SAYINGS = {
    "happy": [
        "Mood check:\npleasantly pixelated.",
        "Everything is coming up\nNPCJason today.",
        "Quest log updated:\nfeeling optimistic.",
        "Today's vibe is\nvictory music.",
    ],
    "tired": [
        "Running on low mana\nand leftover snacks.",
        "My frames are loading\none yawn at a time.",
        "Please hold.\nSoul buffering.",
        "If I blink too long,\ncall it a feature.",
    ],
    "caffeinated": [
        "I can hear the CPU fans\nwith my soul.",
        "Idle animation?\nMore like overclocked stance.",
        "I have achieved\nespresso firmware.",
        "If this speech bubble shakes,\nthat's just the coffee.",
    ],
}

EVENT_SAYINGS = {
    "usb": [
        "New loot detected:\n{label}",
        "A fresh artifact has entered\nthe inventory:\n{label}",
        "Portable storage quest item:\n{label}",
    ],
    "battery_low": [
        "Power reserves at {percent}%.\nThis may become a nap quest.",
        "Battery low: {percent}%.\nRecommend snacks or a charger.",
        "Mana warning.\nRemaining power: {percent}%.",
    ],
    "window_focus": [
        "New quest window spotted:\n{title}",
        "Foreground target acquired:\n{title}",
        "Attention redirected to:\n{title}",
    ],
    "update": [
        "Update available:\nversion {version} is ready.",
        "Fresh patch spotted:\n{version}",
        "A newer build awaits:\n{version}",
    ],
}

PET_CONVERSATIONS = [
    ("You good over there, {other_pet_name}?", "Still desktoping professionally, {pet_name}."),
    ("Any quests for us, {other_pet_name}?", "Only vibes and window watching, {pet_name}."),
    ("Status report, {other_pet_name}.", "Snacks low. Morale high."),
    ("You seeing this too, {other_pet_name}?", "Affirmative. Still weird."),
    ("We should look busy, {other_pet_name}.", "I am literally animated."),
    ("Mood check, {other_pet_name}?", "Somewhere between happy and overclocked, {pet_name}."),
]

TOKEN_PATTERN = re.compile(r"\{([a-z_]+)\}")
SKIN_SECTION_PATTERN = re.compile(r"^\[skin:\s*([a-z0-9_-]+)\s*\]$", re.IGNORECASE)
SECTION_NAMES = {"any", "all", "happy", "tired", "caffeinated"}
ALLOWED_TEMPLATE_TOKENS = {
    "pet_name",
    "other_pet_name",
    "mood",
    "mood_key",
    "personality",
    "personality_key",
    "time",
    "date",
    "active_window",
    "battery_percent",
    "skin",
    "skin_key",
    "companion",
    "dance_routine",
    "desk_item",
    "label",
    "percent",
    "title",
    "toy",
    "version",
}
AFFINITY_KEYS = ("skins", "tags", "contexts", "toys", "moods", "packs", "categories")


@dataclass(frozen=True)
class FollowUpQuote:
    text: str
    delay_ms: int = 1200
    chance: float = 1.0
    require_contexts: tuple[str, ...] = ()
    exclude_contexts: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()


@dataclass(frozen=True)
class QuoteEntry:
    text: str
    moods: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    weight: int = 1
    affinity: dict | None = None
    follow_ups: tuple[FollowUpQuote, ...] = ()

    @property
    def normalized_affinity(self):
        return dict(self.affinity or {key: [] for key in AFFINITY_KEYS})


@dataclass(frozen=True)
class QuotePack:
    key: str
    label: str
    description: str
    source: str
    weight: int = 1
    enabled_by_default: bool = True
    categories: tuple[str, ...] = ()
    affinity: dict | None = None
    quotes: tuple[QuoteEntry, ...] = ()

    @property
    def normalized_affinity(self):
        return dict(self.affinity or {key: [] for key in AFFINITY_KEYS})


@dataclass(frozen=True)
class DialogueChoice:
    template: str
    pack_key: str
    pack_label: str
    source: str
    categories: tuple[str, ...] = ()
    follow_ups: tuple[FollowUpQuote, ...] = ()


def empty_pool():
    return {
        "any": [],
        "happy": [],
        "tired": [],
        "caffeinated": [],
        "skins": {},
    }


def _normalize_text_block(lines):
    cleaned = [line.rstrip() for line in lines]
    return "\n".join(cleaned).strip()


def unknown_template_tokens(text):
    return sorted({token for token in TOKEN_PATTERN.findall(str(text)) if token not in ALLOWED_TEMPLATE_TOKENS})


def parse_dialogue_source(text, source_name="<memory>"):
    custom = empty_pool()
    current_section = "any"
    current_lines = []
    warnings = []

    def flush_current():
        saying = _normalize_text_block(current_lines)
        if saying:
            if isinstance(current_section, tuple) and current_section[0] == "skin":
                custom["skins"].setdefault(current_section[1], []).append(saying)
            else:
                custom[current_section].append(saying)
            unknown_tokens = unknown_template_tokens(saying)
            if unknown_tokens:
                warnings.append(
                    f"{source_name}: unknown template token(s) {', '.join(unknown_tokens)}"
                )
        current_lines.clear()

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        lowered = stripped.lower()

        if lowered in {"[any]", "[all]"}:
            flush_current()
            current_section = "any"
            continue
        if lowered in {"[happy]", "[tired]", "[caffeinated]"}:
            flush_current()
            current_section = lowered[1:-1]
            continue
        skin_match = SKIN_SECTION_PATTERN.match(stripped)
        if skin_match:
            flush_current()
            current_section = ("skin", skin_match.group(1).lower())
            continue
        if stripped.startswith("[") and stripped.endswith("]") and lowered[1:-1] not in SECTION_NAMES:
            flush_current()
            warnings.append(f"{source_name}: unknown section {stripped}; treating following lines as [any]")
            current_section = "any"
            continue
        if stripped.startswith("#") or stripped.startswith(";"):
            continue
        if stripped == "":
            flush_current()
            continue

        current_lines.append(raw_line)

    flush_current()
    return custom, warnings


def parse_dialogue_text(text):
    parsed, _warnings = parse_dialogue_source(text)
    return parsed


def merge_pools(*pools):
    merged = empty_pool()
    for pool in pools:
        for mood_key in ("any", "happy", "tired", "caffeinated"):
            merged[mood_key].extend(pool.get(mood_key, []))
        for skin_key, entries in dict(pool.get("skins", {})).items():
            merged["skins"].setdefault(str(skin_key).lower(), []).extend(entries)
    return merged


def render_template(text, context=None):
    context = context or {}

    def replace(match):
        token = match.group(1)
        if token in context:
            return str(context[token])
        return match.group(0)

    return TOKEN_PATTERN.sub(replace, str(text))


def _normalize_string_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]
    normalized = []
    seen = set()
    for item in values:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


def _normalize_affinity(value, warnings, source_name, field_name):
    if value is None:
        return {key: [] for key in AFFINITY_KEYS}
    if not isinstance(value, dict):
        warnings.append(f"{source_name}: '{field_name}' must be an object")
        return {key: [] for key in AFFINITY_KEYS}
    return {key: _normalize_string_list(value.get(key, [])) for key in AFFINITY_KEYS}


def _build_follow_up(raw_value, source_name, warnings, base_categories=None):
    base_categories = tuple(_normalize_string_list(base_categories))
    if isinstance(raw_value, str):
        text = str(raw_value)
        delay_ms = 1200
        chance = 1.0
        require_contexts = ()
        exclude_contexts = ()
        categories = base_categories
    elif isinstance(raw_value, dict):
        text = str(raw_value.get("text", ""))
        try:
            delay_ms = max(250, int(raw_value.get("delay_ms", 1200)))
        except (TypeError, ValueError):
            warnings.append(f"{source_name}: invalid follow-up delay; defaulting to 1200ms")
            delay_ms = 1200
        try:
            chance = float(raw_value.get("chance", 1.0))
        except (TypeError, ValueError):
            warnings.append(f"{source_name}: invalid follow-up chance; defaulting to 1.0")
            chance = 1.0
        chance = max(0.0, min(1.0, chance))
        require_contexts = tuple(_normalize_string_list(raw_value.get("require_contexts", [])))
        exclude_contexts = tuple(_normalize_string_list(raw_value.get("exclude_contexts", [])))
        categories = tuple(base_categories + tuple(
            category for category in _normalize_string_list(raw_value.get("categories", []))
            if category not in base_categories
        ))
    else:
        warnings.append(f"{source_name}: follow-up entries must be a string or object")
        return None

    if not text.strip():
        return None
    unknown_tokens = unknown_template_tokens(text)
    if unknown_tokens:
        warnings.append(f"{source_name}: unknown template token(s) {', '.join(unknown_tokens)}")
    return FollowUpQuote(
        text=text,
        delay_ms=delay_ms,
        chance=chance,
        require_contexts=require_contexts,
        exclude_contexts=exclude_contexts,
        categories=categories,
    )


def _build_entry(raw_text, source_name, warnings, moods=None, categories=None, weight=1, affinity=None, follow_ups=None):
    text = str(raw_text)
    if not text.strip():
        return None
    unknown_tokens = unknown_template_tokens(text)
    if unknown_tokens:
        warnings.append(f"{source_name}: unknown template token(s) {', '.join(unknown_tokens)}")
    normalized_categories = tuple(_normalize_string_list(categories))
    normalized_follow_ups = []
    for raw_follow_up in list(follow_ups or []):
        follow_up = _build_follow_up(raw_follow_up, source_name, warnings, base_categories=normalized_categories)
        if follow_up is not None:
            normalized_follow_ups.append(follow_up)
    return QuoteEntry(
        text=text,
        moods=tuple(_normalize_string_list(moods)),
        categories=normalized_categories,
        weight=max(1, int(weight)),
        affinity=_normalize_affinity(affinity, warnings, source_name, "entry.affinity"),
        follow_ups=tuple(normalized_follow_ups),
    )


def _legacy_pool_to_entries(parsed_pool, source_name, warnings):
    entries = []
    for mood_key, sayings in parsed_pool.items():
        if mood_key == "skins":
            continue
        for saying in sayings:
            entry = _build_entry(
                saying,
                source_name,
                warnings,
                moods=[] if mood_key == "any" else [mood_key],
                categories=["legacy", mood_key],
                weight=1,
                affinity=None,
            )
            if entry is not None:
                entries.append(entry)
    for skin_key, sayings in dict(parsed_pool.get("skins", {})).items():
        normalized_skin = str(skin_key).strip().lower()
        if not normalized_skin:
            continue
        for saying in sayings:
            entry = _build_entry(
                saying,
                source_name,
                warnings,
                moods=[],
                categories=["legacy", "skin"],
                weight=1,
                affinity={"skins": [normalized_skin]},
            )
            if entry is not None:
                entries.append(entry)
    return entries


def _pack_key_from_path(path):
    stem = path.stem.strip().lower().replace(" ", "-")
    return stem or "quotes"


def _label_from_key(key):
    return " ".join(part.capitalize() for part in str(key).replace("_", "-").split("-") if part)


def _parse_json_pack(path):
    warnings = []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, [f"{path.name}: could not parse JSON"]

    if not isinstance(payload, dict):
        return None, [f"{path.name}: quote pack must be a JSON object"]

    key = str(payload.get("key", _pack_key_from_path(path))).strip() or _pack_key_from_path(path)
    label = str(payload.get("label", _label_from_key(key))).strip() or _label_from_key(key)
    description = str(payload.get("description", "")).strip()
    try:
        weight = max(1, int(payload.get("weight", 1)))
    except (TypeError, ValueError):
        warnings.append(f"{path.name}: invalid pack weight; defaulting to 1")
        weight = 1
    enabled_by_default = bool(payload.get("enabled", True))
    categories = tuple(_normalize_string_list(payload.get("categories", [])))
    affinity = _normalize_affinity(payload.get("affinity"), warnings, path.name, "affinity")

    quotes_raw = payload.get("quotes", [])
    if not isinstance(quotes_raw, list):
        warnings.append(f"{path.name}: 'quotes' must be a list")
        quotes_raw = []

    quotes = []
    for index, entry in enumerate(quotes_raw):
        if isinstance(entry, str):
            quote = _build_entry(
                entry,
                path.name,
                warnings,
                categories=categories,
            )
        elif isinstance(entry, dict):
            raw_text = entry.get("text", "")
            try:
                entry_weight = max(1, int(entry.get("weight", 1)))
            except (TypeError, ValueError):
                warnings.append(f"{path.name}: invalid weight for quote {index}; defaulting to 1")
                entry_weight = 1
            quote = _build_entry(
                raw_text,
                path.name,
                warnings,
                moods=entry.get("moods", []),
                categories=list(categories) + _normalize_string_list(entry.get("categories", [])),
                weight=entry_weight,
                affinity=entry.get("affinity"),
                follow_ups=entry.get("follow_ups", []),
            )
        else:
            warnings.append(f"{path.name}: quote {index} must be a string or object")
            quote = None
        if quote is not None:
            quotes.append(quote)

    return QuotePack(
        key=key,
        label=label,
        description=description,
        source=path.name,
        weight=weight,
        enabled_by_default=enabled_by_default,
        categories=categories,
        affinity=affinity,
        quotes=tuple(quotes),
    ), warnings


def _parse_legacy_pack(path):
    try:
        parsed, warnings = parse_dialogue_source(path.read_text(encoding="utf-8"), source_name=path.name)
    except (OSError, UnicodeDecodeError):
        return None, [f"{path.name}: could not be read"]

    entries = _legacy_pool_to_entries(parsed, path.name, warnings)
    return QuotePack(
        key=_pack_key_from_path(path),
        label=_label_from_key(_pack_key_from_path(path)),
        description="Legacy text-based dialogue pack.",
        source=path.name,
        weight=1,
        enabled_by_default=True,
        categories=("legacy",),
        affinity={key: [] for key in AFFINITY_KEYS},
        quotes=tuple(entries),
    ), warnings


def _built_in_packs():
    general_quotes = tuple(
        QuoteEntry(
            text=line,
            categories=("builtin", "ambient"),
            weight=1,
            affinity={key: [] for key in AFFINITY_KEYS},
        )
        for line in GENERAL_SAYINGS
    )
    mood_quotes = []
    for mood_key, lines in MOOD_SAYINGS.items():
        for line in lines:
            mood_quotes.append(
                QuoteEntry(
                    text=line,
                    moods=(mood_key,),
                    categories=("builtin", "mood", mood_key),
                    weight=1,
                    affinity={key: [] for key in AFFINITY_KEYS},
                )
            )
    return {
        "builtin-general": QuotePack(
            key="builtin-general",
            label="Built-in Ambient",
            description="Core NPCJason ambient lines.",
            source="builtin",
            weight=1,
            enabled_by_default=True,
            categories=("builtin", "ambient"),
            affinity={key: [] for key in AFFINITY_KEYS},
            quotes=general_quotes,
        ),
        "builtin-moods": QuotePack(
            key="builtin-moods",
            label="Built-in Mood Lines",
            description="Mood-specific built-in lines.",
            source="builtin",
            weight=1,
            enabled_by_default=True,
            categories=("builtin", "mood"),
            affinity={key: [] for key in AFFINITY_KEYS},
            quotes=tuple(mood_quotes),
        ),
    }


def _weighted_choice(weighted_items, rng):
    total = sum(weight for _item, weight in weighted_items)
    if total <= 0:
        return weighted_items[0][0]
    target = rng.uniform(0, total)
    cumulative = 0.0
    for item, weight in weighted_items:
        cumulative += weight
        if target <= cumulative:
            return item
    return weighted_items[-1][0]


class DialogueLibrary:
    def __init__(self, sayings_path=RESOURCE_SAYINGS_PATH, packs_dir=RESOURCE_DIALOGUE_PACKS_DIR, pack_states=None):
        self.sayings_path = Path(sayings_path)
        self.packs_dir = Path(packs_dir)
        pack_states = pack_states if isinstance(pack_states, dict) else {}
        self.pack_states = {
            str(key).strip(): bool(value)
            for key, value in dict(pack_states or {}).items()
            if str(key).strip()
        }
        self._signature = None
        self._packs = {}
        self.warnings = []
        self.reload_if_needed(force=True)

    def _iter_files(self):
        files = []
        if self.sayings_path.exists():
            files.append(self.sayings_path)
        if self.packs_dir.exists():
            txt_packs = sorted(path for path in self.packs_dir.glob("*.txt") if path.is_file())
            json_packs = sorted(path for path in self.packs_dir.glob("*.json") if path.is_file())
            files.extend(txt_packs)
            files.extend(json_packs)
        return files

    def _compute_signature(self):
        signature = []
        for path in self._iter_files():
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            signature.append((str(path), stat.st_mtime_ns, stat.st_size))
        return tuple(signature)

    def set_pack_states(self, pack_states):
        pack_states = pack_states if isinstance(pack_states, dict) else {}
        self.pack_states = {
            str(key).strip(): bool(value)
            for key, value in dict(pack_states or {}).items()
            if str(key).strip()
        }

    def pack_state_overrides(self):
        return dict(self.pack_states)

    def pack_enabled(self, pack_key):
        pack = self._packs.get(pack_key)
        if not pack:
            return False
        if pack_key in self.pack_states:
            return bool(self.pack_states[pack_key])
        return bool(pack.enabled_by_default)

    def set_pack_enabled(self, pack_key, enabled):
        pack = self._packs.get(pack_key)
        if pack is None:
            return False
        enabled = bool(enabled)
        if enabled == bool(pack.enabled_by_default):
            self.pack_states.pop(pack_key, None)
        else:
            self.pack_states[pack_key] = enabled
        return True

    def available_packs(self):
        packs = []
        for pack in sorted(self._packs.values(), key=lambda value: (value.source, value.label.lower())):
            packs.append(
                {
                    "key": pack.key,
                    "label": pack.label,
                    "description": pack.description,
                    "enabled": self.pack_enabled(pack.key),
                    "weight": pack.weight,
                    "quote_count": len(pack.quotes),
                    "source": pack.source,
                    "categories": list(pack.categories),
                }
            )
        return packs

    def reload_if_needed(self, force=False):
        signature = self._compute_signature()
        if not force and signature == self._signature:
            return False

        warnings = []
        packs = dict(_built_in_packs())

        for path in self._iter_files():
            if path.suffix.lower() == ".json":
                pack, pack_warnings = _parse_json_pack(path)
            else:
                pack, pack_warnings = _parse_legacy_pack(path)
            warnings.extend(pack_warnings)
            if pack is None:
                continue
            if pack.key in packs:
                warnings.append(f"{path.name}: overriding existing quote pack key '{pack.key}'")
            packs[pack.key] = pack

        self._packs = packs
        self._signature = signature
        self.warnings = warnings
        return True

    def _ambient_candidates(self, mood, context=None):
        context = context or {}
        candidates = []
        for pack in self._packs.values():
            if not self.pack_enabled(pack.key):
                continue
            for quote in pack.quotes:
                if quote.moods and mood not in quote.moods:
                    continue
                weight = self._candidate_weight(pack, quote, mood, context)
                if weight <= 0:
                    continue
                categories = tuple(sorted(set(pack.categories) | set(quote.categories)))
                candidates.append(
                    (
                        DialogueChoice(
                            template=quote.text,
                            pack_key=pack.key,
                            pack_label=pack.label,
                            source=pack.source,
                            categories=categories,
                            follow_ups=quote.follow_ups,
                        ),
                        weight,
                    )
                )
        return candidates

    def _candidate_weight(self, pack, quote, mood, context):
        weight = max(1, int(pack.weight)) * max(1, int(quote.weight))

        preferred_packs = set(_normalize_string_list(context.get("preferred_packs", [])))
        preferred_categories = set(_normalize_string_list(context.get("preferred_categories", [])))
        context_tags = set(_normalize_string_list(context.get("contexts", [])))
        skin_key = str(context.get("skin_key", "")).strip()
        skin_tags = set(_normalize_string_list(context.get("skin_tags", [])))
        toy_key = str(context.get("toy", context.get("toy_key", ""))).strip()
        mood_key = str(context.get("mood_key", mood)).strip() or mood

        quote_affinity = quote.normalized_affinity
        if "skin" in set(quote.categories) and quote_affinity.get("skins"):
            if not skin_key or skin_key not in set(quote_affinity.get("skins", [])):
                return 0

        bonus = 1
        if pack.key in preferred_packs:
            bonus += 4
        if preferred_categories & set(pack.categories):
            bonus += 2
        if preferred_categories & set(quote.categories):
            bonus += 3

        bonus += self._affinity_bonus(pack.normalized_affinity, skin_key, skin_tags, context_tags, toy_key, mood_key)
        bonus += self._affinity_bonus(quote_affinity, skin_key, skin_tags, context_tags, toy_key, mood_key)
        return weight * max(1, bonus)

    @staticmethod
    def _affinity_bonus(affinity, skin_key, skin_tags, context_tags, toy_key, mood_key):
        bonus = 0
        if skin_key and skin_key in affinity.get("skins", []):
            bonus += 2
        if toy_key and toy_key in affinity.get("toys", []):
            bonus += 2
        if mood_key and mood_key in affinity.get("moods", []):
            bonus += 1
        if skin_tags & set(affinity.get("tags", [])):
            bonus += 2
        if context_tags & set(affinity.get("contexts", [])):
            bonus += 3
        return bonus

    def ambient_pool(self, mood, context=None, skin_key=None):
        self.reload_if_needed()
        ambient_context = dict(context or {})
        if skin_key and "skin_key" not in ambient_context:
            ambient_context["skin_key"] = skin_key
        return [choice.template for choice, _weight in self._ambient_candidates(mood, ambient_context)]

    def pick_ambient(self, mood, context=None, recent_templates=None, rng=None):
        self.reload_if_needed()
        rng = rng or random
        candidates = self._ambient_candidates(mood, context)
        if not candidates:
            return DialogueChoice(
                template="Still loading personality module.",
                pack_key="builtin-fallback",
                pack_label="Fallback",
                source="builtin",
                categories=("builtin", "fallback"),
                follow_ups=(),
            )

        recent_templates = [str(template) for template in list(recent_templates or [])[-6:]]
        recent_set = set(recent_templates)
        if recent_set:
            non_recent = [(choice, weight) for choice, weight in candidates if choice.template not in recent_set]
            if non_recent:
                candidates = non_recent

        return _weighted_choice(candidates, rng)

    def random_saying(self, mood, context=None, recent_templates=None, rng=None):
        choice = self.pick_ambient(mood, context=context, recent_templates=recent_templates, rng=rng)
        return render_template(choice.template, context)

    def format_event_text(self, event_key, **context):
        options = EVENT_SAYINGS.get(event_key)
        if not options:
            return render_template("Event noticed.", context)
        return render_template(random.choice(options), context)
