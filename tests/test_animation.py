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

    def test_custom_sequences_are_used(self):
        controller = AnimationController()
        controller.set_sequences(
            idle_sequence=[{"frame": "idle_blink", "offset_y": 2, "delay_ms": 300}],
            interaction_sequence=[{"frame": "dance3", "offset_y": 1, "delay_ms": 140}],
        )

        idle = controller.next_frame("happy")
        controller.start_dance()
        interaction = controller.next_frame("happy")

        self.assertEqual("idle_blink", idle.frame_key)
        self.assertEqual(2, idle.offset_y)
        self.assertEqual("dance3", interaction.frame_key)
        self.assertEqual(1, interaction.offset_y)

    def test_multiple_dance_routines_are_available(self):
        controller = AnimationController()

        routines = [routine.key for routine in controller.available_dance_routines()]

        self.assertIn("classic-bounce", routines)
        self.assertIn("desk-shuffle", routines)
        self.assertIn("victory-stomp", routines)

    def test_start_dance_uses_requested_routine(self):
        controller = AnimationController()

        controller.start_dance("victory-stomp")
        frames = [controller.next_frame("happy").frame_key for _ in range(4)]

        self.assertEqual("victory-stomp", controller.current_dance_key())
        self.assertIn("dance3", frames)


if __name__ == "__main__":
    unittest.main()
