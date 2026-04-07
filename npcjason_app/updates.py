import json
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

        tag_name = payload.get("tag_name", "")
        newer = bool(tag_name and is_newer_version(self.current_version, tag_name))
        self.latest = {
            "version": tag_name.lstrip("vV"),
            "tag_name": tag_name,
            "html_url": payload.get("html_url", GITHUB_RELEASES_URL),
            "published_at": payload.get("published_at"),
            "newer": newer,
        }
        return self.latest

    def check_async(self, callback):
        def worker():
            try:
                result = self.check()
            except Exception as exc:
                callback(None, exc)
                return
            callback(result, None)

        threading.Thread(target=worker, daemon=True).start()
