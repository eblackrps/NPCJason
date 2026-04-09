import unittest

from npcjason_app.unlocks import UnlockManager


class UnlockManagerTests(unittest.TestCase):
    def setUp(self):
        self.manager = UnlockManager()
        self.manager.load()

    def test_default_unlocks_and_progress_metadata_exist(self):
        catalog = {item["key"]: item for item in self.manager.discovery_catalog()}

        self.assertTrue(catalog["astronaut"]["unlocked"])
        self.assertEqual("Ready", catalog["astronaut"]["progress_text"])
        self.assertFalse(catalog["what-do"]["unlocked"])
        self.assertIn("curious_beats 0/2", catalog["what-do"]["progress_text"])

    def test_progress_unlocks_pack_and_pending_can_be_restored(self):
        self.manager.note_progress("curious_beats", 2)
        unlocked_now = self.manager.note_progress("confused_beats", 1)

        self.assertEqual(["what-do"], [item.key for item in unlocked_now])

        pending = self.manager.pending_discoveries()
        self.assertEqual(["what-do"], [item.key for item in pending])

        self.manager.restore_pending(pending)
        pending_again = self.manager.pending_discoveries()

        self.assertEqual(["what-do"], [item.key for item in pending_again])
        self.assertTrue(self.manager.is_unlocked("quote_pack", "what-do"))


if __name__ == "__main__":
    unittest.main()
