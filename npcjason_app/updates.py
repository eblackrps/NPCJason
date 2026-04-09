from __future__ import annotations

import json
from dataclasses import dataclass
import threading
import urllib.request

from .version import APP_VERSION, GITHUB_REPO, GITHUB_RELEASES_URL


def parse_version_tag(tag):
    cleaned = str(tag).strip().lstrip("vV")
    parts = []
    for part in cleaned.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer_version(current_version, candidate_version):
    return parse_version_tag(candidate_version) > parse_version_tag(current_version)


def parse_latest_release_payload(payload, current_version=APP_VERSION):
    if not isinstance(payload, dict):
        raise ValueError("Release payload must be a JSON object.")
    tag_name = str(payload.get("tag_name", "")).strip()
    newer = bool(tag_name and is_newer_version(current_version, tag_name))
    return {
        "version": tag_name.lstrip("vV"),
        "tag_name": tag_name,
        "html_url": payload.get("html_url", GITHUB_RELEASES_URL),
        "published_at": payload.get("published_at"),
        "newer": newer,
    }


@dataclass
class UpdatePrompt:
    kind: str = "none"
    manual: bool = False
    version: str = ""
    error: Exception | None = None


class UpdateChecker:
    def __init__(self, current_version=APP_VERSION, repo=GITHUB_REPO):
        self.current_version = current_version
        self.repo = repo
        self.latest = None

    def latest_release_url(self):
        if self.latest and self.latest.get("html_url"):
            return self.latest["html_url"]
        return GITHUB_RELEASES_URL

    def check(self):
        request = urllib.request.Request(
            f"https://api.github.com/repos/{self.repo}/releases/latest",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "NPCJason",
            },
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))

        self.latest = parse_latest_release_payload(payload, current_version=self.current_version)
        return self.latest

    def check_async(self, callback, dispatcher=None):
        def worker():
            try:
                result = self.check()
            except (OSError, ValueError) as exc:
                if dispatcher:
                    dispatcher(callback, None, exc)
                else:
                    callback(None, exc)
                return
            if dispatcher:
                dispatcher(callback, result, None)
            else:
                callback(result, None)

        threading.Thread(target=worker, daemon=True).start()


class UpdateCoordinator:
    def __init__(self, checker=None, logger=None):
        self.checker = checker or UpdateChecker()
        self.logger = logger
        self._in_flight = False
        self._manual_requested = False
        self._last_prompted_version = None

    def request_check(self, callback, dispatcher=None, manual=False):
        if self._in_flight:
            if manual:
                self._manual_requested = True
                self._log("info", "Manual update check merged into the in-flight request")
            return False

        self._in_flight = True
        self._manual_requested = bool(manual)

        def handle_complete(result, error):
            manual_requested = self._manual_requested
            self._manual_requested = False
            self._in_flight = False
            callback(result, error, manual_requested)

        self.checker.check_async(handle_complete, dispatcher=dispatcher)
        return True

    def build_prompt(self, result, error, manual, updates_enabled, automatic_actions_allowed):
        if error:
            if manual:
                return UpdatePrompt(kind="error", manual=True, error=error)
            return UpdatePrompt()
        if not result:
            return UpdatePrompt()
        version = str(result.get("version", "")).strip()
        if (
            result.get("newer")
            and version
            and version != self._last_prompted_version
            and updates_enabled
            and (manual or automatic_actions_allowed)
        ):
            self._last_prompted_version = version
            return UpdatePrompt(kind="available", manual=manual, version=version)
        if manual:
            return UpdatePrompt(kind="up_to_date", manual=True, version=self.checker.current_version)
        return UpdatePrompt()

    def _log(self, level, message):
        if not self.logger:
            return
        log_method = getattr(self.logger, level, None)
        if callable(log_method):
            log_method(f"updates: {message}")
