from __future__ import annotations

from dataclasses import dataclass
import random
import time
from typing import Iterable, List, Optional


MAX_RECENT_SAYINGS = 30
MAX_FAVORITE_SAYINGS = 30


@dataclass
class SpeechRecord:
    template: str
    text: str
    source: str
    timestamp: float

    def as_dict(self):
        return {
            "template": self.template,
            "text": self.text,
            "source": self.source,
            "timestamp": self.timestamp,
        }


class SpeechHistory:
    def __init__(self, recent=None, favorites=None, logger=None, clock=None):
        self.logger = logger
        self.clock = clock or time.time
        self.last_record: Optional[SpeechRecord] = None
        self._recent: List[dict] = []
        self._favorites: List[str] = []
        self.load(recent=recent, favorites=favorites)

    def load(self, recent=None, favorites=None):
        self._recent = self._normalize_recent(recent)
        self._favorites = self._normalize_favorites(favorites)
        if self._recent:
            last = self._recent[-1]
            self.last_record = SpeechRecord(
                template=str(last.get("template", last.get("text", ""))),
                text=str(last.get("text", "")),
                source=str(last.get("source", "history")),
                timestamp=float(last.get("timestamp", 0.0)),
            )
        else:
            self.last_record = None

    def record(self, template_text, rendered_text, source):
        record = SpeechRecord(
            template=str(template_text or rendered_text),
            text=str(rendered_text),
            source=str(source),
            timestamp=float(self.clock()),
        )
        self.last_record = record
        self._recent.append(record.as_dict())
        self._recent = self._recent[-MAX_RECENT_SAYINGS:]
        return record.as_dict()

    def recent(self):
        return list(self._recent)

    def recent_texts(self):
        return list(reversed(self._recent))

    def favorites(self):
        return list(self._favorites)

    def favorite_last(self):
        if not self.last_record:
            return False
        template = self.last_record.template
        if template in self._favorites:
            return False
        self._favorites.append(template)
        self._favorites = self._favorites[-MAX_FAVORITE_SAYINGS:]
        self._log("info", "Favorited saying template")
        return True

    def remove_favorite(self, template_text):
        template = str(template_text)
        if template not in self._favorites:
            return False
        self._favorites = [item for item in self._favorites if item != template]
        return True

    def pick_random_favorite(self):
        if not self._favorites:
            return None
        return random.choice(self._favorites)

    def _normalize_recent(self, items):
        normalized = []
        for item in list(items or [])[-MAX_RECENT_SAYINGS:]:
            if isinstance(item, dict):
                template = str(item.get("template", item.get("text", ""))).strip()
                text = str(item.get("text", template)).strip()
                if not text:
                    continue
                normalized.append(
                    {
                        "template": template or text,
                        "text": text,
                        "source": str(item.get("source", "history")).strip() or "history",
                        "timestamp": float(item.get("timestamp", 0.0)),
                    }
                )
                continue
            text = str(item).strip()
            if text:
                normalized.append(
                    {
                        "template": text,
                        "text": text,
                        "source": "history",
                        "timestamp": 0.0,
                    }
                )
        return normalized[-MAX_RECENT_SAYINGS:]

    def _normalize_favorites(self, items: Optional[Iterable[str]]):
        normalized = []
        for item in list(items or [])[-MAX_FAVORITE_SAYINGS:]:
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized[-MAX_FAVORITE_SAYINGS:]

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(message)
