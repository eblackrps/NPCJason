from pathlib import Path
import unittest

from npcjason_app.startup import StartupManager, build_startup_script
from tests.helpers import workspace_tempdir


class StartupTests(unittest.TestCase):
    def test_startup_script_contains_start_command(self):
        script = build_startup_script()
        self.assertIn("@echo off", script)
        self.assertIn("start", script.lower())

    def test_startup_manager_enable_disable_round_trip(self):
        with workspace_tempdir() as temp_dir:
            script_path = Path(temp_dir) / "NPCJason.cmd"
            manager = StartupManager(script_path=script_path)

            manager.set_enabled(True)
            self.assertTrue(manager.is_enabled())
            self.assertIn("start", script_path.read_text(encoding="utf-8").lower())

            manager.set_enabled(False)
            self.assertFalse(manager.is_enabled())


if __name__ == "__main__":
    unittest.main()
