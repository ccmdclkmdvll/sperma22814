"""Предустановленные стили монтажа для разнообразия видео."""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class MontageStyle:
    """Описывает визуальный стиль одного видео."""

    name: str = "classic"
    mellstroy_position: str = "center_bottom"
    mellstroy_scale: float = 0.8
    subtitle_color: tuple[int, int, int] = (255, 255, 255)
    subtitle_stroke_color: tuple[int, int, int] = (0, 0, 0)
    subtitle_position: str = "top"
    subtitle_font_size: int = 80
    effect: str = "none"
    bg_speed: float = 1.0

    @staticmethod
    def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip("#")
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )


PRESET_STYLES: list[MontageStyle] = [
    MontageStyle(
        name="classic",
        mellstroy_position="center_bottom",
        mellstroy_scale=0.8,
        subtitle_color=(255, 255, 255),
        subtitle_stroke_color=(0, 0, 0),
        subtitle_position="top",
        effect="none",
    ),
    MontageStyle(
        name="dramatic",
        mellstroy_position="center_bottom",
        mellstroy_scale=0.9,
        subtitle_color=(255, 50, 50),
        subtitle_stroke_color=(0, 0, 0),
        subtitle_position="top",
        effect="zoom_in",
    ),
    MontageStyle(
        name="left_react",
        mellstroy_position="left",
        mellstroy_scale=0.7,
        subtitle_color=(255, 255, 0),
        subtitle_stroke_color=(0, 0, 0),
        subtitle_position="top",
        effect="none",
    ),
    MontageStyle(
        name="right_react",
        mellstroy_position="right",
        mellstroy_scale=0.7,
        subtitle_color=(0, 255, 255),
        subtitle_stroke_color=(0, 0, 0),
        subtitle_position="top",
        effect="none",
    ),
    MontageStyle(
        name="big_center",
        mellstroy_position="center_bottom",
        mellstroy_scale=1.0,
        subtitle_color=(255, 255, 255),
        subtitle_stroke_color=(255, 0, 0),
        subtitle_position="center",
        effect="none",
    ),
    MontageStyle(
        name="shake_chaos",
        mellstroy_position="center_bottom",
        mellstroy_scale=0.85,
        subtitle_color=(0, 255, 0),
        subtitle_stroke_color=(0, 0, 0),
        subtitle_position="top",
        effect="shake",
    ),
    MontageStyle(
        name="flash_impact",
        mellstroy_position="center_bottom",
        mellstroy_scale=0.9,
        subtitle_color=(255, 255, 255),
        subtitle_stroke_color=(0, 0, 0),
        subtitle_position="top",
        effect="flash",
    ),
    MontageStyle(
        name="minimal",
        mellstroy_position="center_bottom",
        mellstroy_scale=0.6,
        subtitle_color=(255, 255, 255),
        subtitle_stroke_color=(0, 0, 0),
        subtitle_position="bottom",
        subtitle_font_size=60,
        effect="none",
    ),
    MontageStyle(
        name="neon_pink",
        mellstroy_position="center_bottom",
        mellstroy_scale=0.8,
        subtitle_color=(255, 0, 200),
        subtitle_stroke_color=(255, 255, 255),
        subtitle_position="top",
        effect="none",
    ),
    MontageStyle(
        name="slow_zoom",
        mellstroy_position="center_bottom",
        mellstroy_scale=0.85,
        subtitle_color=(255, 200, 0),
        subtitle_stroke_color=(0, 0, 0),
        subtitle_position="top",
        effect="zoom_in",
        bg_speed=0.9,
    ),
]


def pick_random_style() -> MontageStyle:
    return random.choice(PRESET_STYLES)
