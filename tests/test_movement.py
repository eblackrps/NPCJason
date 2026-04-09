from dataclasses import dataclass
import unittest

from npcjason_app.movement import EDGE_MARGIN, MovementController, MovementIntent


@dataclass
class Bounds:
    left: int
    top: int
    right: int
    bottom: int


class StableRng:
    def choice(self, items):
        return list(items)[0]

    def randint(self, minimum, _maximum):
        return minimum

    def random(self):
        return 0.99


class MovementTests(unittest.TestCase):
    def setUp(self):
        self.now = [1000.0]
        self.controller = MovementController(clock=lambda: self.now[0])
        self.bounds = Bounds(left=0, top=0, right=300, bottom=200)

    def test_scripted_focus_targets_requested_edge(self):
        self.controller.set_scripted("inspect", duration_ms=2000, focus="top-right")
        self.controller.tick(120, 80, self.bounds, style="linger", rng=StableRng())

        self.assertIsNotNone(self.controller._intent)
        self.assertEqual("top-right", self.controller._intent.focus)
        self.assertEqual(self.bounds.right - EDGE_MARGIN, self.controller._intent.target_x)
        self.assertEqual(self.bounds.top + EDGE_MARGIN, self.controller._intent.target_y)

    def test_recovery_intent_moves_back_in_bounds_when_stuck(self):
        self.controller._intent = MovementIntent(
            style="pace",
            target_x=999,
            target_y=100,
            hold_until_ms=0,
            expires_at_ms=9_999_999,
        )

        result = self.controller.tick(300, 100, self.bounds, style="pace", rng=StableRng())

        self.assertFalse(result.moved)
        self.assertEqual("recover", result.debug_note)
        self.assertLess(self.controller._intent.target_x, self.bounds.right)


if __name__ == "__main__":
    unittest.main()
