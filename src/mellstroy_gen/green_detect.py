"""Детект зелёного фона в видео-клипе (без AI, через FFmpeg + PIL).

Извлекает первый кадр и считает долю пикселей с зелёным оттенком (HSV).
Если > 25% кадра — считаем что клип на зелёном экране.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image

_GREEN_HUE_MIN = 80
_GREEN_HUE_MAX = 160
_GREEN_SAT_MIN = 60
_GREEN_THRESHOLD = 0.25


def _extract_first_frame(video: Path) -> Image.Image:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        frame_path = Path(tmp.name)
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-i", str(video),
                "-vframes", "1",
                "-f", "image2",
                str(frame_path),
            ],
            check=True,
        )
        return Image.open(frame_path).convert("RGB")
    finally:
        frame_path.unlink(missing_ok=True)


def green_ratio(video: Path) -> float:
    """Возвращает долю зелёных пикселей (0.0–1.0) на первом кадре."""
    img = _extract_first_frame(video)
    hsv = img.convert("HSV")
    _get = getattr(hsv, "get_flattened_data", None) or hsv.getdata
    pixels = list(_get())
    if not pixels:
        return 0.0
    green_count = sum(
        1 for h, s, _v in pixels
        if _GREEN_HUE_MIN <= h <= _GREEN_HUE_MAX and s >= _GREEN_SAT_MIN
    )
    return green_count / len(pixels)


def has_green_background(video: Path, threshold: float = _GREEN_THRESHOLD) -> bool:
    """True если клип снят на зелёном экране."""
    return green_ratio(video) >= threshold
