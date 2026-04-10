import unittest

from npcjason_app.companions import CompanionManager
from npcjason_app.windows_platform import DesktopBounds


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance_ms(self, milliseconds):
        self.value += float(milliseconds) / 1000.0


class CompanionManagerTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.manager = CompanionManager(root=None, clock=self.clock)
        self.bounds = DesktopBounds(left=0, top=0, right=400, bottom=300)
        self.manager.configure(enabled=True, selected_key="mouse")

    def test_mouse_companion_is_available(self):
        companions = self.manager.available_companions()
        interactions = self.manager.available_interactions()

        self.assertEqual("mouse", companions[0]["key"])
        self.assertEqual("feed-cheese", interactions[0]["key"])
        self.assertTrue(
            {
                "desk-patrol",
                "cable-audit",
                "victory-scamper",
                "crumb-heist",
                "mug-recon",
                "zip-tie-recovery",
            }.issubset({item["key"] for item in interactions})
        )

    def test_feed_cheese_eventually_emits_required_line(self):
        result = self.manager.trigger_interaction("feed-cheese")
        self.assertTrue(result.started)

        line = None
        for _ in range(40):
            tick = self.manager.tick(
                owner_x=220,
                owner_y=180,
                work_area=self.bounds,
                owner_context={"personality_state": "curious", "active_toy": ""},
            )
            if tick.speech_line:
                line = tick.speech_line
                break
            self.clock.advance_ms(tick.next_delay_ms)

        self.assertEqual("Ansible Chris made me do it", line)

    def test_feed_cheese_temporarily_blocks_owner_movement(self):
        self.manager.trigger_interaction("feed-cheese")

        self.assertTrue(self.manager.blocks_owner_movement())


if __name__ == "__main__":
    unittest.main()
