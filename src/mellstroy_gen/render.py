"""Низкоуровневые помощники: рендер субтитров (PIL → PNG) и композиция через FFmpeg.

Финальный формат: 1080x1920 (9:16), 30 fps, H.264, AAC.
Поддерживает MontageStyle для разнообразия визуального оформления и
автоматический детект зелёного фона (chromakey vs. обычный overlay).
"""
from __future__ import annotations

import json
import logging
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .styles import MontageStyle

log = logging.getLogger(__name__)

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
    fill_color: tuple[int, int, int] = (255, 255, 255),
    stroke_color: tuple[int, int, int] = (0, 0, 0),
) -> Path:
    """Рендерит крупную TikTok-стилизованную надпись на прозрачном PNG."""
    font_path = _find_font()
    font = ImageFont.truetype(font_path, font_size)

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

    line_h = int(font_size * 1.15)
    pad = 30
    img_h = line_h * len(lines) + pad * 2
    img = Image.new("RGBA", (W, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    stroke_w = max(4, font_size // 14)
    fill_rgba = (*fill_color, 255)
    stroke_rgba = (*stroke_color, 255)
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        y = pad + i * line_h
        draw.text(
            (x, y),
            line,
            font=font,
            fill=fill_rgba,
            stroke_width=stroke_w,
            stroke_fill=stroke_rgba,
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
    chromakey: Path
    background: Path
    bg_offset: float
    duration: float
    caption_png: Path
    music: Path | None
    out: Path
    use_chromakey: bool = True
    style: MontageStyle | None = None


def _fg_scale_height(style: MontageStyle) -> int:
    return int(1500 * style.mellstroy_scale)


def _fg_overlay_expr(style: MontageStyle) -> str:
    """Возвращает выражение overlay x:y для позиции Меллстроя."""
    if style.mellstroy_position == "left":
        return "0:(H-h)/2+80"
    if style.mellstroy_position == "right":
        return "W-w:(H-h)/2+80"
    return "(W-w)/2:(H-h)/2+80"


def _subtitle_overlay_expr(style: MontageStyle) -> str:
    """Возвращает выражение overlay для позиции субтитра."""
    if style.subtitle_position == "center":
        return "(W-w)/2:(H-h)/2"
    if style.subtitle_position == "bottom":
        return "(W-w)/2:H*0.80"
    return "(W-w)/2:H*0.10"


def _build_effect_filter(style: MontageStyle) -> str:
    """Возвращает дополнительный FFmpeg-фильтр для эффекта (применяется к [outv])."""
    if style.effect == "zoom_in":
        return ",zoompan=z='min(zoom+0.0008\\,1.15)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
    if style.effect == "shake":
        return ",crop=in_w-20:in_h-20:10*sin(n*0.5):5*cos(n*0.7),scale=1080:1920:flags=lanczos"
    if style.effect == "flash":
        return ",eq=brightness=if(lt(n\\,3)\\,0.3\\,0)"
    return ""


def compose(inputs: CompositionInputs) -> Path:
    """FFmpeg-композиция: gameplay фон + Меллстрой сверху + субтитры + аудио."""
    style = inputs.style or MontageStyle()
    has_chromakey_audio = probe_has_audio(inputs.chromakey)

    music_path = inputs.music if inputs.music and inputs.music.exists() else None
    inputs_ff = [
        "-ss", f"{inputs.bg_offset:.2f}", "-t", f"{inputs.duration:.2f}",
        "-i", str(inputs.background),
        "-i", str(inputs.chromakey),
        "-i", str(inputs.caption_png),
    ]
    if music_path:
        inputs_ff += ["-stream_loop", "-1", "-i", str(music_path)]

    fg_h = _fg_scale_height(style)
    fg_overlay = _fg_overlay_expr(style)
    sub_overlay = _subtitle_overlay_expr(style)

    bg_filter = (
        "[0:v]scale=if(gt(a\\,1080/1920)\\,-2\\,1080):if(gt(a\\,1080/1920)\\,1920\\,-2):flags=lanczos,"
        "crop=1080:1920,setsar=1,fps=30,format=yuv420p[bg];"
    )

    if inputs.use_chromakey:
        fg_filter = (
            f"[1:v]chromakey=0x00FF00:0.20:0.12,"
            f"scale=-2:{fg_h}:flags=lanczos,"
            f"crop=min(in_w\\,1080):{fg_h}:(in_w-min(in_w\\,1080))/2:0,"
            f"setsar=1,fps=30[fg];"
        )
    else:
        fg_filter = (
            f"[1:v]scale=-2:{fg_h}:flags=lanczos,"
            f"crop=min(in_w\\,1080):{fg_h}:(in_w-min(in_w\\,1080))/2:0,"
            f"setsar=1,fps=30[fg];"
        )

    effect_filter = _build_effect_filter(style)

    fc = (
        bg_filter
        + fg_filter
        + f"[bg][fg]overlay={fg_overlay}:format=auto[v1];"
        + f"[v1][2:v]overlay={sub_overlay}[outv_raw];"
        + f"[outv_raw]null{effect_filter}[outv]"
    )

    map_args = ["-map", "[outv]"]

    if has_chromakey_audio and music_path:
        fc += ";[1:a]volume=1.0[a1];[3:a]volume=0.18[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=0[outa]"
        map_args += ["-map", "[outa]"]
    elif has_chromakey_audio:
        fc += ";[1:a]volume=1.0[outa]"
        map_args += ["-map", "[outa]"]
    elif music_path:
        fc += ";[3:a]volume=0.6[outa]"
        map_args += ["-map", "[outa]"]

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
    log.info("$ %s", " ".join(shlex.quote(c) for c in cmd))
    subprocess.run(cmd, check=True)
    return inputs.out
