import unittest

from npcjason_app.speech_history import SpeechHistory
from tests.helpers import FakeLogger


class SpeechHistoryTests(unittest.TestCase):
    def test_record_and_favorite_flow_trims_lists(self):
        logger = FakeLogger()
        history = SpeechHistory(logger=logger, clock=lambda: 42.0)
        for index in range(35):
            history.record(f"Template {index}", f"Rendered {index}", "test")

        self.assertEqual(30, len(history.recent()))
        self.assertEqual("Rendered 34", history.recent()[-1]["text"])

        self.assertTrue(history.favorite_last())
        self.assertFalse(history.favorite_last())
        self.assertEqual(["Template 34"], history.favorites())
        self.assertTrue(any("Favorited saying template" in message for message in logger.messages["info"]))

    def test_load_normalizes_recent_and_favorites(self):
        history = SpeechHistory(
            recent=[
                {"template": "One", "text": "Rendered one", "source": "ambient", "timestamp": 1.0},
                "Two",
                {"text": "Rendered three"},
            ],
            favorites=["One", "", " Two "],
        )

        self.assertEqual(3, len(history.recent()))
        self.assertEqual("Rendered three", history.last_record.text)
        self.assertEqual(["One", "Two"], history.favorites())

    def test_remove_favorite_returns_false_for_missing_template(self):
        history = SpeechHistory(favorites=["Alpha", "Beta"])

        self.assertFalse(history.remove_favorite("Gamma"))
        self.assertTrue(history.remove_favorite("Alpha"))
        self.assertEqual(["Beta"], history.favorites())


if __name__ == "__main__":
    unittest.main()
