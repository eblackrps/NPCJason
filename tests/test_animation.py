import unittest

from npcjason_app.animation import AnimationController
from npcjason_app.skins import DANCE_SEQUENCE


class AnimationControllerTests(unittest.TestCase):
    def test_dance_sequence_returns_to_idle_and_keeps_animating(self):
        controller = AnimationController()
        controller.start_dance()

        frames = [controller.next_frame("happy").frame_key for _ in range(len(DANCE_SEQUENCE) * 3 + 2)]

        self.assertEqual(DANCE_SEQUENCE[0], frames[0])
        self.assertFalse(controller.is_dancing)
        self.assertTrue(frames[-1].startswith("idle_"))

    def test_idle_animation_cycles_without_entering_dead_state(self):
        controller = AnimationController()
        frames = [controller.next_frame("tired").frame_key for _ in range(10)]

        self.assertTrue(all(frame.startswith("idle_") for frame in frames))
        self.assertGreater(len(set(frames)), 1)


if __name__ == "__main__":
    unittest.main()
