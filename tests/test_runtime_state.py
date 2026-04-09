import unittest

from npcjason_app.runtime_state import RuntimeStateController, is_screenshot_window_title


class RuntimeStateTests(unittest.TestCase):
    def test_screenshot_suppression_expires_and_recovers(self):
        now = {"value": 100.0}
        state = RuntimeStateController(clock=lambda: now["value"], screenshot_ttl_seconds=2.0)
        state.mark_initialized()
        state.mark_running()

        state.note_foreground_window("Snipping Tool")
        active = state.snapshot()

        self.assertTrue(active.screenshot_suppressed)
        self.assertFalse(active.automatic_actions_allowed)
        self.assertTrue(active.should_move)

        now["value"] += 3.0
        recovered = state.snapshot()

        self.assertFalse(recovered.screenshot_suppressed)
        self.assertTrue(recovered.automatic_actions_allowed)

    def test_hidden_state_stops_animation_without_marking_shutdown(self):
        state = RuntimeStateController(clock=lambda: 10.0)
        state.mark_initialized()
        state.mark_running()
        state.set_visibility(True, reason="tray")

        snapshot = state.snapshot()

        self.assertTrue(snapshot.running)
        self.assertFalse(snapshot.should_animate)
        self.assertFalse(snapshot.should_move)
        self.assertTrue(snapshot.manually_hidden)
        self.assertEqual("tray", snapshot.hidden_reason)

    def test_fullscreen_and_quiet_hours_flags_are_reported(self):
        state = RuntimeStateController(clock=lambda: 10.0)
        state.mark_initialized()
        state.mark_running()
        state.update_fullscreen(True)
        state.update_quiet_hours(True)

        snapshot = state.snapshot()

        self.assertTrue(snapshot.fullscreen_suppressed)
        self.assertTrue(snapshot.quiet_hours_suppressed)
        self.assertFalse(snapshot.automatic_actions_allowed)

    def test_screenshot_title_detection_matches_known_capture_tools(self):
        self.assertTrue(is_screenshot_window_title("Snipping Tool"))
        self.assertTrue(is_screenshot_window_title("Screen Snipping"))
        self.assertFalse(is_screenshot_window_title("Visual Studio Code"))

    def test_begin_shutdown_disables_runtime_activity(self):
        state = RuntimeStateController(clock=lambda: 10.0)
        state.mark_initialized()
        state.mark_running()
        state.begin_shutdown()

        snapshot = state.snapshot()

        self.assertTrue(snapshot.shutting_down)
        self.assertFalse(snapshot.running)
        self.assertFalse(snapshot.should_animate)

    def test_pause_reasons_are_reported_and_recover_cleanly(self):
        state = RuntimeStateController(clock=lambda: 10.0)
        state.mark_initialized()
        state.mark_running()
        state.set_pause("drag", True)
        state.set_pause("settings", True)

        paused = state.snapshot()
        self.assertTrue(paused.paused)
        self.assertEqual(("drag", "settings"), paused.pause_reasons)
        self.assertFalse(paused.automatic_actions_allowed)

        state.set_pause("drag", False)
        state.set_pause("settings", False)
        resumed = state.snapshot()
        self.assertFalse(resumed.paused)
        self.assertEqual((), resumed.pause_reasons)
        self.assertTrue(resumed.automatic_actions_allowed)


if __name__ == "__main__":
    unittest.main()
