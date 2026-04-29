"""Smoke-тест end-to-end пайплайна: рендерит 1 короткое видео и проверяет его свойства."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from mellstroy_gen.captions import GEO_CAPTIONS
from mellstroy_gen.generate import generate_one
from mellstroy_gen.render import probe_duration


def _ffmpeg_or_skip() -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("FFmpeg не установлен")


def _make_synthetic_chromakey(out: Path, duration: float = 3.0) -> None:
    """Зелёный фон с белым прямоугольником (имитация фигуры на хромакее)."""
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i",
        f"color=c=0x00FF00:size=640x360:rate=30:duration={duration}",
        "-f", "lavfi", "-i",
        f"color=c=white:size=120x180:rate=30:duration={duration}",
        "-f", "lavfi", "-i",
        f"sine=frequency=440:duration={duration}",
        "-filter_complex", "[0:v][1:v]overlay=(W-w)/2:(H-h)/2[v]",
        "-map", "[v]", "-map", "2:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
        "-c:a", "aac",
        str(out),
    ]
    subprocess.run(cmd, check=True)


def _make_synthetic_bg(out: Path, duration: float = 10.0) -> None:
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi",
        "-i", f"gradients=size=720x1280:rate=30:duration={duration}:c0=0x4a148c:c1=0x00bcd4:speed=0.05",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
        str(out),
    ]
    subprocess.run(cmd, check=True)


def test_generate_one_produces_valid_9_16(tmp_path: Path) -> None:
    _ffmpeg_or_skip()
    chrom = tmp_path / "chrom.mp4"
    bg = tmp_path / "bg.mp4"
    out = tmp_path / "test_out.mp4"

    _make_synthetic_chromakey(chrom)
    _make_synthetic_bg(bg)

    result = generate_one(
        chromakey=chrom,
        background=bg,
        caption_text=GEO_CAPTIONS["RU"][0],
        geo="RU",
        out=out,
    )
    assert result.exists()
    assert result.stat().st_size > 1000

    # 9:16 ровно
    probe = subprocess.run(
        ["ffprobe", "-v", "error",
         "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=p=0", str(result)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert probe == "1080,1920", f"ожидали 1080x1920, получили {probe}"

    # длительность ≈ длительности chromakey-клипа
    dur_ck = probe_duration(chrom)
    dur_out = probe_duration(result)
    assert abs(dur_out - dur_ck) < 0.5

    # описание создано
    desc = out.with_suffix(".txt")
    assert desc.exists()
    assert "🇷🇺" in desc.read_text(encoding="utf-8")


def test_captions_have_required_geos() -> None:
    assert "RU" in GEO_CAPTIONS
    assert "DE" in GEO_CAPTIONS
    assert len(GEO_CAPTIONS["RU"]) >= 30
    assert len(GEO_CAPTIONS["DE"]) >= 30
