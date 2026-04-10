import unittest
from datetime import datetime

from npcjason_app.companion_presence import (
    CompanionPresenceController,
    sanitize_companion_presence_payload,
)


class CompanionPresenceTests(unittest.TestCase):
    def test_sanitize_presence_repairs_invalid_shapes(self):
        sanitized = sanitize_companion_presence_payload(
            {
                "familiarity": "12",
                "days_used": "-5",
                "preferred_categories": {" office ": "3", "": 5},
                "preferred_behaviors": "bad",
                "recent_greetings": [" one ", "", "one", "two"],
                "theme_rotation_streak": "99",
            }
        )

        self.assertEqual(12, sanitized["familiarity"])
        self.assertEqual(0, sanitized["days_used"])
        self.assertEqual({"office": 3}, sanitized["preferred_categories"])
        self.assertEqual({}, sanitized["preferred_behaviors"])
        self.assertEqual(["one", "two"], sanitized["recent_greetings"])
        self.assertEqual(30, sanitized["theme_rotation_streak"])

    def test_begin_session_tracks_days_streak_and_mode(self):
        controller = CompanionPresenceController()

        first = controller.begin_session(now=datetime(2026, 4, 10, 9, 0, 0), mood_key="happy")
        second = controller.begin_session(now=datetime(2026, 4, 11, 9, 0, 0), mood_key="happy")

        self.assertTrue(first["new_day"])
        self.assertTrue(second["new_day"])
        self.assertEqual(2, controller.to_payload()["days_used"])
        self.assertEqual(2, controller.to_payload()["interaction_streak"])
        self.assertGreaterEqual(controller.familiarity(), 4)
        self.assertTrue(controller.session_mode_label())
        self.assertTrue(controller.theme_label())

    def test_behavior_bias_includes_mode_theme_and_preferences(self):
        controller = CompanionPresenceController()
        controller.begin_session(now=datetime(2026, 4, 10, 13, 0, 0), mood_key="caffeinated")
        controller.note_behavior("companion", categories=["network", "network", "office"], familiarity_gain=1)
        bias = controller.behavior_bias()

        self.assertTrue(any(item.startswith("relationship-") for item in bias["contexts"]))
        self.assertIn("network", bias["categories"])
        self.assertTrue(bias["preferred_states"])

    def test_milestone_unlocks_once_when_thresholds_met(self):
        controller = CompanionPresenceController(
            {
                "days_used": 3,
                "familiarity": 20,
                "preferred_behaviors": {"companion": 5},
                "last_session_started_at": 0.0,
            }
        )
        controller.begin_session(now=datetime(2026, 4, 10, 10, 0, 0), mood_key="happy")

        milestone = controller.next_milestone(
            {
                "runtime_minutes": 90,
                "quotes_spoken": 30,
                "scenario_runs": 9,
            },
            now=datetime(2026, 4, 10, 11, 30, 0),
            consume=True,
        )

        self.assertIsNotNone(milestone)
        self.assertTrue(milestone.key)
        second = controller.next_milestone(
            {
                "runtime_minutes": 90,
                "quotes_spoken": 30,
                "scenario_runs": 9,
            },
            now=datetime(2026, 4, 10, 11, 31, 0),
            consume=True,
        )

        self.assertIsNotNone(second)
        self.assertNotEqual(milestone.key, second.key)

    def test_milestone_preview_does_not_consume_until_marked(self):
        controller = CompanionPresenceController({"days_used": 3, "familiarity": 20})
        controller.begin_session(now=datetime(2026, 4, 10, 10, 0, 0), mood_key="happy")

        preview = controller.next_milestone(
            {
                "runtime_minutes": 90,
                "quotes_spoken": 30,
                "scenario_runs": 9,
            },
            now=datetime(2026, 4, 10, 11, 30, 0),
            consume=False,
        )
        repeat_preview = controller.next_milestone(
            {
                "runtime_minutes": 90,
                "quotes_spoken": 30,
                "scenario_runs": 9,
            },
            now=datetime(2026, 4, 10, 11, 31, 0),
            consume=False,
        )

        self.assertIsNotNone(preview)
        self.assertEqual(preview.key, repeat_preview.key)
        self.assertTrue(controller.mark_milestone_seen(preview.key, familiarity_gain=1))
        self.assertFalse(controller.mark_milestone_seen(preview.key, familiarity_gain=1))

    def test_legacy_backfill_seeds_relationship_state(self):
        controller = CompanionPresenceController()

        changed = controller.backfill_from_legacy_activity(
            launches=9,
            runtime_minutes=720,
            quotes_spoken=60,
            scenario_runs=6,
            discoveries=3,
            unlocked_count=2,
            favorite_count=4,
        )

        payload = controller.to_payload()
        self.assertTrue(changed)
        self.assertGreater(payload["familiarity"], 0)
        self.assertGreaterEqual(payload["days_used"], 1)
        self.assertEqual(9, payload["total_sessions"])
        self.assertEqual(1, payload["interaction_streak"])

    def test_ambient_beat_respects_available_interactions(self):
        controller = CompanionPresenceController({"familiarity": 15})
        controller.begin_session(now=datetime(2026, 4, 10, 14, 0, 0), mood_key="happy")

        beat = controller.pick_ambient_world_beat(
            {
                "available_desk_items": ["keyboard"],
                "available_companion_interactions": [],
                "personality_state": "busy",
            }
        )

        self.assertIsNotNone(beat)
        self.assertNotEqual("crumb-heist", beat.companion_interaction)


if __name__ == "__main__":
    unittest.main()
