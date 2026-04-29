"""Низкоуровневые помощники: рендер субтитров (PIL → PNG) и композиция через FFmpeg.

Финальный формат: 1080x1920 (9:16), 30 fps, H.264, AAC.
"""
from __future__ import annotations

import json
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 30


def _find_font() -> str:
    """Ищет жирный sans-serif шрифт в системе."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    raise FileNotFoundError(
        "Не нашёл жирный шрифт. Поставь `fonts-dejavu` (Linux) или укажи путь вручную."
    )


def render_caption(
    text: str,
    out: Path,
    width: int = W - 80,
    max_lines: int = 3,
    font_size: int = 80,
) -> Path:
    """Рендерит крупную TikTok-стилизованную надпись на прозрачном PNG.

    Стиль: белый текст с чёрной обводкой, разбит по словам по строкам.
    """
    font_path = _find_font()
    font = ImageFont.truetype(font_path, font_size)

    # переносим по словам, чтоб каждая строка <= width
    words = text.split()
    lines: list[str] = []
    cur = ""
    dummy_img = Image.new("RGBA", (1, 1))
    dd = ImageDraw.Draw(dummy_img)
    for w in words:
        trial = (cur + " " + w).strip()
        bbox = dd.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    lines = lines[:max_lines]

    # размер картинки
    line_h = int(font_size * 1.15)
    pad = 30
    img_h = line_h * len(lines) + pad * 2
    img = Image.new("RGBA", (W, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    stroke_w = max(4, font_size // 14)
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        y = pad + i * line_h
        # белый текст с чёрной обводкой
        draw.text(
            (x, y),
            line,
            font=font,
            fill=(255, 255, 255, 255),
            stroke_width=stroke_w,
            stroke_fill=(0, 0, 0, 255),
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(path),
        ],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def probe_has_audio(path: Path) -> bool:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "a",
            "-show_entries", "stream=codec_type",
            "-of", "json",
            str(path),
        ],
        capture_output=True, text=True, check=True,
    ).stdout
    streams = json.loads(out).get("streams", [])
    return any(s.get("codec_type") == "audio" for s in streams)


@dataclass
class CompositionInputs:
    chromakey: Path           # mp4 c Меллстроем на зелёном
    background: Path          # длинное gameplay-видео (Subway/Minecraft)
    bg_offset: float          # с какой секунды резать background
    duration: float           # длительность финального ролика
    caption_png: Path         # PNG с субтитром (прозрачный фон)
    music: Path | None        # фоновый звук (низкая громкость) либо None
    out: Path                 # путь финального .mp4


def compose(inputs: CompositionInputs) -> Path:
    """FFmpeg-композиция: gameplay фон + Меллстрой сверху + субтитры + аудио."""
    has_chromakey_audio = probe_has_audio(inputs.chromakey)

    # видеограф:
    # [0:v] background → trim, scale до 1080x1920 с crop по центру
    # [1:v] chromakey → масштабируем до ширины 1080, удаляем зелёный, alpha
    # [2:v] caption_png  → overlay сверху примерно на 1/4 высоты
    # output: 1080x1920 9:16
    music_path = inputs.music if inputs.music and inputs.music.exists() else None
    inputs_ff = [
        "-ss", f"{inputs.bg_offset:.2f}", "-t", f"{inputs.duration:.2f}",
        "-i", str(inputs.background),
        "-i", str(inputs.chromakey),
        "-i", str(inputs.caption_png),
    ]
    if music_path:
        inputs_ff += ["-stream_loop", "-1", "-i", str(music_path)]

    fc = (
        # bg: scale так чтоб закрыть 1080x1920, crop по центру (zoom-in)
        "[0:v]scale=if(gt(a\\,1080/1920)\\,-2\\,1080):if(gt(a\\,1080/1920)\\,1920\\,-2):flags=lanczos,"
        "crop=1080:1920,setsar=1,fps=30,format=yuv420p[bg];"
        # chromakey: чистим зелёный (chromakey + despill через colorchannelmixer),
        # затем scale так чтоб Меллстрой занимал большую часть кадра, центр-crop по горизонтали
        "[1:v]chromakey=0x00FF00:0.20:0.12,"
        "scale=-2:1500:flags=lanczos,"
        "crop=min(in_w\\,1080):1500:(in_w-min(in_w\\,1080))/2:0,"
        "setsar=1,fps=30[fg];"
        # bg + fg: Меллстрой посажен чуть ниже центра экрана
        "[bg][fg]overlay=(W-w)/2:(H-h)/2+80:format=auto[v1];"
        # subtitle overlay на 10% от верха
        "[v1][2:v]overlay=(W-w)/2:H*0.10[outv]"
    )

    map_args = ["-map", "[outv]"]

    # аудио микс
    if has_chromakey_audio and music_path:
        fc += ";[1:a]volume=1.0[a1];[3:a]volume=0.18[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=0[outa]"
        map_args += ["-map", "[outa]"]
    elif has_chromakey_audio:
        fc += ";[1:a]volume=1.0[outa]"
        map_args += ["-map", "[outa]"]
    elif music_path:
        fc += ";[3:a]volume=0.6[outa]"
        map_args += ["-map", "[outa]"]
    # else: без звука (плохо, FFmpeg добавит пустой)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-stats",
        *inputs_ff,
        "-filter_complex", fc,
        *map_args,
        "-t", f"{inputs.duration:.2f}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        str(inputs.out),
    ]
    inputs.out.parent.mkdir(parents=True, exist_ok=True)
    print("$", " ".join(shlex.quote(c) for c in cmd))
    subprocess.run(cmd, check=True)
    return inputs.out
