from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class TitleRule:
    key: str
    keywords: tuple[str, ...]
    contexts: tuple[str, ...]
    categories: tuple[str, ...]
    preferred_packs: tuple[str, ...] = ()


TITLE_RULES = (
    TitleRule(
        key="cisco",
        keywords=("cisco", "meraki", "firepower", "anyconnect", "packet tracer", "smart licensing", "ise", "dnac", "catalyst", "asa"),
        contexts=("title-observed", "title-networking", "title-cisco"),
        categories=("network", "cisco"),
        preferred_packs=("cisco-jokes", "app-title-humor"),
    ),
    TitleRule(
        key="terminal",
        keywords=("powershell", "terminal", "cmd", "putty", "securecrt", "ssh"),
        contexts=("title-observed", "title-terminal"),
        categories=("office", "playful"),
        preferred_packs=("app-title-humor",),
    ),
    TitleRule(
        key="ticket",
        keywords=("jira", "servicenow", "ticket", "incident", "request", "change"),
        contexts=("title-observed", "title-ticket"),
        categories=("office", "responsible"),
        preferred_packs=("app-title-humor",),
    ),
    TitleRule(
        key="meeting",
        keywords=("teams", "zoom", "webex", "meet", "meeting", "call"),
        contexts=("title-observed", "title-meeting"),
        categories=("office", "annoyed"),
        preferred_packs=("app-title-humor",),
    ),
    TitleRule(
        key="code",
        keywords=("visual studio", "vscode", "pycharm", "intellij", "github", "gitlab"),
        contexts=("title-observed", "title-code"),
        categories=("office", "playful"),
        preferred_packs=("app-title-humor",),
    ),
    TitleRule(
        key="homelab",
        keywords=("proxmox", "truenas", "uptime kuma", "grafana", "prometheus", "plex", "unifi"),
        contexts=("title-observed", "title-homelab"),
        categories=("homelab", "network"),
        preferred_packs=("app-title-humor", "cisco-jokes"),
    ),
)

BORING_TITLES = {
    "",
    "new tab",
    "home",
    "start",
    "settings",
    "task view",
    "program manager",
}

SPACE_PATTERN = re.compile(r"\s+")
PUNCT_ONLY_PATTERN = re.compile(r"^[\W_]+$")
STRUCTURED_TITLE_PATTERN = re.compile(r"[-:/|\\\[\]()#@]")


def normalize_title(title):
    return SPACE_PATTERN.sub(" ", str(title or "").strip())


def classify_window_title(title):
    trimmed = normalize_title(title)
    lowered = trimmed.lower()
    if not trimmed or lowered in BORING_TITLES or PUNCT_ONLY_PATTERN.match(trimmed):
        return {
            "useful": False,
            "interesting": False,
            "title": "",
            "reaction_key": "",
            "contexts": [],
            "categories": [],
            "preferred_packs": [],
            "chance": 0.0,
            "render_overrides": {},
        }

    contexts = ["title-observed"]
    categories = []
    preferred_packs = ["app-title-humor"]
    score = 0

    for rule in TITLE_RULES:
        if any(keyword in lowered for keyword in rule.keywords):
            score += 1
            for context in rule.contexts:
                if context not in contexts:
                    contexts.append(context)
            for category in rule.categories:
                if category not in categories:
                    categories.append(category)
            for pack in rule.preferred_packs:
                if pack not in preferred_packs:
                    preferred_packs.append(pack)

    if not categories:
        categories.append("office")
    generic_interest = len(trimmed) >= 18 and STRUCTURED_TITLE_PATTERN.search(trimmed)
    chance = 0.23 if score > 0 else (0.08 if generic_interest else 0.0)
    return {
        "useful": score > 0 or generic_interest,
        "interesting": score > 0 or generic_interest,
        "title": trimmed,
        "reaction_key": lowered[:96],
        "contexts": contexts,
        "categories": categories,
        "preferred_packs": preferred_packs,
        "chance": chance,
        "render_overrides": {
            "title": trimmed,
            "active_window": trimmed,
        },
    }
