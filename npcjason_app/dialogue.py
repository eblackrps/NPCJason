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
SECTION_NAMES = {"any", "all", "happy", "tired", "caffeinated"}
ALLOWED_TEMPLATE_TOKENS = {
    "pet_name",
    "other_pet_name",
    "mood",
    "mood_key",
    "time",
    "date",
    "active_window",
    "battery_percent",
    "skin",
    "label",
    "percent",
    "title",
    "version",
}


def empty_pool():
    return {
        "any": [],
        "happy": [],
        "tired": [],
        "caffeinated": [],
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
        for mood_key in merged:
            merged[mood_key].extend(pool.get(mood_key, []))
    return merged


def render_template(text, context=None):
    context = context or {}

    def replace(match):
        token = match.group(1)
        if token in context:
            return str(context[token])
        return match.group(0)

    return TOKEN_PATTERN.sub(replace, str(text))


class DialogueLibrary:
    def __init__(self, sayings_path=RESOURCE_SAYINGS_PATH, packs_dir=RESOURCE_DIALOGUE_PACKS_DIR):
        self.sayings_path = Path(sayings_path)
        self.packs_dir = Path(packs_dir)
        self._signature = None
        self._custom_pool = empty_pool()
        self.warnings = []
        self.reload_if_needed(force=True)

    def _iter_files(self):
        files = []
        if self.sayings_path.exists():
            files.append(self.sayings_path)
        if self.packs_dir.exists():
            files.extend(sorted(path for path in self.packs_dir.glob("*.txt") if path.is_file()))
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

    def reload_if_needed(self, force=False):
        signature = self._compute_signature()
        if not force and signature == self._signature:
            return False

        pools = []
        warnings = []
        for path in self._iter_files():
            try:
                parsed, parse_warnings = parse_dialogue_source(
                    path.read_text(encoding="utf-8"),
                    source_name=path.name,
                )
                pools.append(parsed)
                warnings.extend(parse_warnings)
            except (OSError, UnicodeDecodeError):
                warnings.append(f"{path.name}: could not be read")
                continue

        self._custom_pool = merge_pools(*pools) if pools else empty_pool()
        self._signature = signature
        self.warnings = warnings
        return True

    def ambient_pool(self, mood):
        pool = list(GENERAL_SAYINGS)
        pool.extend(MOOD_SAYINGS.get(mood, []))
        pool.extend(self._custom_pool.get("any", []))
        pool.extend(self._custom_pool.get(mood, []))
        return pool or ["Still loading personality module."]

    def random_saying(self, mood, context=None):
        self.reload_if_needed()
        return render_template(random.choice(self.ambient_pool(mood)), context)

    def format_event_text(self, event_key, **context):
        options = EVENT_SAYINGS.get(event_key)
        if not options:
            return render_template("Event noticed.", context)
        return render_template(random.choice(options), context)
