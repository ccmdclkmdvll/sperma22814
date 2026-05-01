"""Smoke-тесты для пайплайна генерации мем-видео."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from mellstroy_gen.captions import GEO_CAPTIONS
from mellstroy_gen.generate import generate_one
from mellstroy_gen.render import probe_duration
from mellstroy_gen.styles import MontageStyle, PRESET_STYLES, pick_random_style


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
        "-i", f"color=c=0x4a148c:size=720x1280:rate=30:duration={duration}",
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

    probe = subprocess.run(
        ["ffprobe", "-v", "error",
         "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-of", "csv=p=0", str(result)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert probe == "1080,1920", f"ожидали 1080x1920, получили {probe}"

    dur_ck = probe_duration(chrom)
    dur_out = probe_duration(result)
    assert abs(dur_out - dur_ck) < 0.5

    desc = out.with_suffix(".txt")
    assert desc.exists()
    assert "🇷🇺" in desc.read_text(encoding="utf-8")


def test_generate_one_with_style(tmp_path: Path) -> None:
    """Тест генерации с кастомным стилем монтажа."""
    _ffmpeg_or_skip()
    chrom = tmp_path / "chrom.mp4"
    bg = tmp_path / "bg.mp4"
    out = tmp_path / "styled_out.mp4"

    _make_synthetic_chromakey(chrom)
    _make_synthetic_bg(bg)

    style = MontageStyle(
        name="test_style",
        mellstroy_position="left",
        mellstroy_scale=0.7,
        subtitle_color=(255, 255, 0),
        subtitle_stroke_color=(0, 0, 0),
        subtitle_position="center",
        subtitle_font_size=70,
        effect="none",
    )

    result = generate_one(
        chromakey=chrom,
        background=bg,
        caption_text="Тестовый стиль",
        geo="RU",
        out=out,
        style=style,
        use_chromakey=True,
    )
    assert result.exists()
    assert result.stat().st_size > 1000


def test_generate_one_no_chromakey(tmp_path: Path) -> None:
    """Тест генерации без chromakey-фильтра (для стикеров)."""
    _ffmpeg_or_skip()
    chrom = tmp_path / "chrom.mp4"
    bg = tmp_path / "bg.mp4"
    out = tmp_path / "no_ck_out.mp4"

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i",
        "color=c=blue:size=640x360:rate=30:duration=2",
        "-f", "lavfi", "-i",
        "sine=frequency=440:duration=2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
        "-c:a", "aac",
        str(chrom),
    ]
    subprocess.run(cmd, check=True)
    _make_synthetic_bg(bg)

    result = generate_one(
        chromakey=chrom,
        background=bg,
        caption_text="Без хромакея",
        geo="RU",
        out=out,
        use_chromakey=False,
    )
    assert result.exists()
    assert result.stat().st_size > 1000


def test_captions_have_required_geos() -> None:
    assert "RU" in GEO_CAPTIONS
    assert "DE" in GEO_CAPTIONS
    assert len(GEO_CAPTIONS["RU"]) >= 30
    assert len(GEO_CAPTIONS["DE"]) >= 30


def test_styles_preset_count() -> None:
    assert len(PRESET_STYLES) >= 8
    style = pick_random_style()
    assert isinstance(style, MontageStyle)
    assert style.name in [s.name for s in PRESET_STYLES]


def test_green_detect_synthetic(tmp_path: Path) -> None:
    """Тест детекции зелёного фона."""
    _ffmpeg_or_skip()
    from mellstroy_gen.green_detect import has_green_background

    green_vid = tmp_path / "green.mp4"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i",
        "color=c=0x00FF00:size=320x240:rate=30:duration=1",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
        str(green_vid),
    ]
    subprocess.run(cmd, check=True)
    assert has_green_background(green_vid) is True

    blue_vid = tmp_path / "blue.mp4"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi", "-i",
        "color=c=blue:size=320x240:rate=30:duration=1",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
        str(blue_vid),
    ]
    subprocess.run(cmd, check=True)
    assert has_green_background(blue_vid) is False


def test_humor_db_crud(tmp_path: Path) -> None:
    """Тест CRUD операций базы знаний."""
    from mellstroy_gen.humor_db import HumorDB, MemeAnalysis, MemeEntry

    db = HumorDB(tmp_path / "test_db.json")
    assert len(db) == 0

    entry = MemeEntry(
        id="test_1",
        url="https://tiktok.com/test",
        subtitle_text="Тестовый мем",
        analysis=MemeAnalysis(
            humor_type="reaction",
            humor_formula="контраст ожидания",
            virality_score=8,
            key_elements=["реакция", "крик"],
            caption_style="когда...",
        ),
    )
    db.add_meme(entry)
    assert len(db) == 1

    db2 = HumorDB(tmp_path / "test_db.json")
    assert len(db2) == 1
    assert db2.memes[0].analysis.humor_type == "reaction"

    patterns = db2.get_patterns()
    assert patterns["total_memes"] == 1
    assert "reaction" in patterns["top_humor_types"]

    prompt_text = db2.export_for_prompt()
    assert "reaction" in prompt_text
    assert "контраст ожидания" in prompt_text
