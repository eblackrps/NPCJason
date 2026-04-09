from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import os


IS_WINDOWS = os.name == "nt"
SPI_GETWORKAREA = 0x0030


@dataclass(frozen=True)
class DesktopBounds:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self):
        return max(0, int(self.right - self.left))

    @property
    def height(self):
        return max(0, int(self.bottom - self.top))


def screen_bounds(screen_width, screen_height):
    return DesktopBounds(0, 0, max(0, int(screen_width)), max(0, int(screen_height)))


def primary_work_area(screen_width, screen_height):
    fallback = screen_bounds(screen_width, screen_height)
    if not IS_WINDOWS:
        return fallback

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]

    rect = RECT()
    if not ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
        return fallback

    bounds = DesktopBounds(int(rect.left), int(rect.top), int(rect.right), int(rect.bottom))
    if bounds.width <= 0 or bounds.height <= 0:
        return fallback
    return bounds


def clamp_window_position(
    x,
    y,
    window_width,
    window_height,
    bounds,
    right_padding=4,
    bottom_padding=8,
):
    minimum_x = int(bounds.left)
    minimum_y = int(bounds.top)
    maximum_x = max(minimum_x, int(bounds.right) - int(window_width) - int(right_padding))
    maximum_y = max(minimum_y, int(bounds.bottom) - int(window_height) - int(bottom_padding))
    return (
        max(minimum_x, min(int(x), maximum_x)),
        max(minimum_y, min(int(y), maximum_y)),
    )


def snap_window_position(
    x,
    y,
    window_width,
    window_height,
    bounds,
    margin,
    right_padding=4,
    bottom_padding=8,
):
    clamped_x, clamped_y = clamp_window_position(
        x,
        y,
        window_width,
        window_height,
        bounds,
        right_padding=right_padding,
        bottom_padding=bottom_padding,
    )
    right_limit = max(int(bounds.left), int(bounds.right) - int(window_width) - int(right_padding))
    bottom_limit = max(int(bounds.top), int(bounds.bottom) - int(window_height) - int(bottom_padding))

    if abs(clamped_x - int(bounds.left)) <= int(margin):
        clamped_x = int(bounds.left)
    elif abs(clamped_x - right_limit) <= int(margin):
        clamped_x = right_limit

    if abs(clamped_y - int(bounds.top)) <= int(margin):
        clamped_y = int(bounds.top)
    elif abs(clamped_y - bottom_limit) <= int(margin):
        clamped_y = bottom_limit

    return clamped_x, clamped_y


def default_window_position(bounds, window_width, window_height, right_offset=120, bottom_offset=80):
    return clamp_window_position(
        int(bounds.right) - int(window_width) - int(right_offset),
        int(bounds.bottom) - int(window_height) - int(bottom_offset),
        window_width,
        window_height,
        bounds,
    )


def friend_spawn_position(
    origin_x,
    origin_y,
    window_width,
    window_height,
    bounds,
    gap=40,
    y_offset=-10,
):
    offset_x = int(origin_x) + int(window_width) + int(gap)
    right_limit = int(bounds.right) - int(window_width) - 4
    if offset_x > right_limit:
        offset_x = int(origin_x) - int(window_width) - int(gap)
    offset_y = int(origin_y) + int(y_offset)
    return clamp_window_position(offset_x, offset_y, window_width, window_height, bounds)


def bubble_position(parent_x, parent_y, bubble_width, bubble_height, bounds, margin=6):
    x = int(parent_x) - int(bubble_width) // 2
    y = int(parent_y) - int(bubble_height) - 10
    minimum_x = int(bounds.left) + int(margin)
    minimum_y = int(bounds.top) + int(margin)
    maximum_x = max(minimum_x, int(bounds.right) - int(bubble_width) - int(margin))
    maximum_y = max(minimum_y, int(bounds.bottom) - int(bubble_height) - int(margin))
    return (
        max(minimum_x, min(x, maximum_x)),
        max(minimum_y, min(y, maximum_y)),
    )


def is_rect_fullscreen(rect, bounds, tolerance=24):
    if not rect:
        return False
    return (
        int(rect["width"]) >= max(1, int(bounds.width) - int(tolerance))
        and int(rect["height"]) >= max(1, int(bounds.height) - int(tolerance))
    )
