import unittest

from npcjason_app.app import quiet_hours_active


class AppHelperTests(unittest.TestCase):
    def test_quiet_hours_handles_overnight_range(self):
        self.assertTrue(quiet_hours_active(True, 22, 8, now=23))
        self.assertTrue(quiet_hours_active(True, 22, 8, now=7))
        self.assertFalse(quiet_hours_active(True, 22, 8, now=14))

    def test_quiet_hours_equal_hours_means_always_on(self):
        self.assertTrue(quiet_hours_active(True, 9, 9, now=3))
        self.assertFalse(quiet_hours_active(False, 9, 9, now=3))


if __name__ == "__main__":
    unittest.main()
