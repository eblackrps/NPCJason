import unittest

from npcjason_app.windows_platform import (
    DesktopBounds,
    bubble_position,
    clamp_window_position,
    default_window_position,
    friend_spawn_position,
    is_rect_fullscreen,
    snap_window_position,
)


class WindowsPlatformTests(unittest.TestCase):
    def test_default_window_position_stays_inside_bounds(self):
        bounds = DesktopBounds(0, 0, 1920, 1080)

        x, y = default_window_position(bounds, 64, 80)

        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)
        self.assertLessEqual(x, 1920 - 64)
        self.assertLessEqual(y, 1080 - 80)

    def test_clamp_and_snap_window_position_respect_work_area(self):
        bounds = DesktopBounds(100, 50, 1820, 1000)

        x, y = clamp_window_position(-20, 9999, 64, 80, bounds)
        snapped_x, snapped_y = snap_window_position(103, 55, 64, 80, bounds, margin=8)

        self.assertEqual((100, 912), (x, y))
        self.assertEqual((100, 50), (snapped_x, snapped_y))

    def test_friend_spawn_position_flips_when_right_side_is_unavailable(self):
        bounds = DesktopBounds(0, 0, 300, 200)

        x, y = friend_spawn_position(220, 50, 64, 80, bounds, gap=40)

        self.assertLess(x, 220)
        self.assertGreaterEqual(y, 0)

    def test_bubble_position_is_clamped_inside_bounds(self):
        bounds = DesktopBounds(0, 0, 320, 200)

        x, y = bubble_position(5, 10, 180, 60, bounds, margin=6)

        self.assertGreaterEqual(x, 6)
        self.assertGreaterEqual(y, 6)

    def test_is_rect_fullscreen_uses_tolerance(self):
        bounds = DesktopBounds(0, 0, 1920, 1080)
        rect = {"width": 1910, "height": 1070}

        self.assertTrue(is_rect_fullscreen(rect, bounds, tolerance=24))
        self.assertFalse(is_rect_fullscreen({"width": 1200, "height": 800}, bounds, tolerance=24))


if __name__ == "__main__":
    unittest.main()
