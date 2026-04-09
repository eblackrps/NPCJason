import unittest
from unittest import mock

from npcjason_app.updates import (
    UpdateChecker,
    UpdateCoordinator,
    is_newer_version,
    parse_latest_release_payload,
    parse_version_tag,
)
from tests.helpers import FakeLogger


class CheckerStub:
    def __init__(self, current_version="1.2.0"):
        self.current_version = current_version
        self.calls = []
        self.callback = None

    def check_async(self, callback, dispatcher=None):
        self.calls.append(dispatcher)
        self.callback = callback


class UpdateTests(unittest.TestCase):
    def test_parse_version_tag_handles_v_prefix(self):
        self.assertEqual((1, 2, 0), parse_version_tag("v1.2"))

    def test_is_newer_version(self):
        self.assertTrue(is_newer_version("1.1.0", "v1.1.1"))
        self.assertFalse(is_newer_version("1.1.0", "v1.0.9"))

    def test_parse_latest_release_payload_detects_newer_release(self):
        payload = {
            "tag_name": "v1.3.0",
            "html_url": "https://example.invalid/release",
            "published_at": "2026-04-09T00:00:00Z",
        }

        parsed = parse_latest_release_payload(payload, current_version="1.2.0")

        self.assertEqual("1.3.0", parsed["version"])
        self.assertTrue(parsed["newer"])

    def test_check_parses_github_response(self):
        checker = UpdateChecker(current_version="1.2.0", repo="eblackrps/NPCJason")

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b'{"tag_name":"v1.2.1","html_url":"https://example.invalid/release"}'

        with mock.patch("urllib.request.urlopen", return_value=FakeResponse()):
            result = checker.check()

        self.assertEqual("1.2.1", result["version"])
        self.assertTrue(result["newer"])

    def test_update_coordinator_merges_manual_request_into_inflight_check(self):
        checker = CheckerStub(current_version="1.2.0")
        logger = FakeLogger()
        coordinator = UpdateCoordinator(checker=checker, logger=logger)
        completed = []

        self.assertTrue(coordinator.request_check(lambda result, error, manual: completed.append((result, error, manual))))
        self.assertFalse(coordinator.request_check(lambda result, error, manual: completed.append((result, error, manual)), manual=True))
        checker.callback({"version": "1.2.1", "newer": True}, None)

        self.assertEqual([({"version": "1.2.1", "newer": True}, None, True)], completed)
        self.assertTrue(any("merged" in message for message in logger.messages["info"]))

    def test_build_prompt_deduplicates_version_and_reports_manual_latest(self):
        coordinator = UpdateCoordinator(checker=CheckerStub(current_version="1.2.0"))

        first = coordinator.build_prompt(
            {"version": "1.3.0", "newer": True},
            None,
            manual=False,
            updates_enabled=True,
            automatic_actions_allowed=True,
        )
        second = coordinator.build_prompt(
            {"version": "1.3.0", "newer": True},
            None,
            manual=False,
            updates_enabled=True,
            automatic_actions_allowed=True,
        )
        manual_latest = coordinator.build_prompt(
            {"version": "1.2.0", "newer": False},
            None,
            manual=True,
            updates_enabled=True,
            automatic_actions_allowed=False,
        )

        self.assertEqual("available", first.kind)
        self.assertEqual("none", second.kind)
        self.assertEqual("up_to_date", manual_latest.kind)
        self.assertEqual("1.2.0", manual_latest.version)


if __name__ == "__main__":
    unittest.main()
