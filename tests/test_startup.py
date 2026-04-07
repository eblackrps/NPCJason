import unittest

from npcjason_app.startup import build_startup_script


class StartupTests(unittest.TestCase):
    def test_startup_script_contains_start_command(self):
        script = build_startup_script()
        self.assertIn("@echo off", script)
        self.assertIn("start", script.lower())


if __name__ == "__main__":
    unittest.main()
