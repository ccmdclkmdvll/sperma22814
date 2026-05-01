"""Главный пайплайн: собирает финальные TikTok-видео.

Входы (должны быть подготовлены заранее):
    assets/chromakey/*.mp4    — клипы Меллстроя (зелёный фон или сырые нарезки)
    assets/backgrounds/*.mp4  — длинные gameplay-видео (Subway Surfers, Minecraft)
    assets/music/*.mp3        — опц. фоновая музыка (тихо, под голос)

Режимы:
    Обычный — захардкоженные фразы, рандомный стиль:
        python -m mellstroy_gen.generate --count 100 --geo RU

    Smart — AI-фразы из humor_db + AI-стили + авто-детект зелёного фона:
        python -m mellstroy_gen.generate --count 50 --geo RU --smart
"""
from __future__ import annotations

import argparse
import logging
import random
import sys
import tempfile
import traceback
from pathlib import Path

from .captions import GEO_CAPTIONS, GEO_FLAG, GEO_HASHTAGS
from .render import CompositionInputs, compose, probe_duration, render_caption
from .styles import MontageStyle, pick_random_style

log = logging.getLogger(__name__)


def list_assets(folder: Path, exts: tuple[str, ...]) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir() if p.suffix.lower() in exts)


def pick_bg_offset(bg_dur: float, clip_dur: float) -> float:
    if bg_dur <= clip_dur + 1:
        return 0.0
    return random.uniform(0, bg_dur - clip_dur - 0.5)


def write_description(out_mp4: Path, caption: str, geo: str) -> Path:
    flag = GEO_FLAG.get(geo, "")
    tags = GEO_HASHTAGS.get(geo, "")
    text = f"{flag} {caption}\n\n{tags}\n"
    desc = out_mp4.with_suffix(".txt")
    desc.write_text(text, encoding="utf-8")
    return desc


def _detect_green(clip: Path) -> bool:
    """Проверяет, снят ли клип на зелёном экране."""
    try:
        from .green_detect import has_green_background
        return has_green_background(clip)
    except Exception:
        return True


def generate_one(
    chromakey: Path,
    background: Path,
    caption_text: str,
    geo: str,
    out: Path,
    music: Path | None = None,
    tmpdir: Path | None = None,
    style: MontageStyle | None = None,
    use_chromakey: bool | None = None,
) -> Path:
    clip_dur = probe_duration(chromakey)
    bg_dur = probe_duration(background)
    bg_offset = pick_bg_offset(bg_dur, clip_dur)

    if use_chromakey is None:
        use_chromakey = _detect_green(chromakey)

    style = style or MontageStyle()

    tmpdir = tmpdir or Path(tempfile.mkdtemp(prefix="mellgen_"))
    cap_png = tmpdir / f"caption_{out.stem}.png"
    render_caption(
        caption_text,
        cap_png,
        font_size=style.subtitle_font_size,
        fill_color=style.subtitle_color,
        stroke_color=style.subtitle_stroke_color,
    )

    compose(CompositionInputs(
        chromakey=chromakey,
        background=background,
        bg_offset=bg_offset,
        duration=clip_dur,
        caption_png=cap_png,
        music=music,
        out=out,
        use_chromakey=use_chromakey,
        style=style,
    ))
    write_description(out, caption_text, geo)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10, help="сколько видео")
    parser.add_argument("--geo", default="RU", choices=sorted(GEO_CAPTIONS.keys()),
                        help="ГЕО-таргет (определяет язык субтитров и хэштеги)")
    parser.add_argument("--chromakey-dir", default="assets/chromakey")
    parser.add_argument("--bg-dir", default="assets/backgrounds")
    parser.add_argument("--music-dir", default="assets/music")
    parser.add_argument("--out-dir", default="output")
    parser.add_argument("--start-idx", type=int, default=1)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--smart", action="store_true",
                        help="AI-режим: Gemini генерирует фразы и стили на основе humor_db")
    parser.add_argument("--no-ai", action="store_true",
                        help="в smart-режиме использовать рандомные стили без Gemini")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.seed is not None:
        random.seed(args.seed)

    chromakey_files = list_assets(Path(args.chromakey_dir), (".mp4", ".webm", ".mov"))
    bg_files = list_assets(Path(args.bg_dir), (".mp4", ".webm", ".mov"))
    music_files = list_assets(Path(args.music_dir), (".mp3", ".m4a", ".aac", ".wav"))

    if not chromakey_files:
        print(f"Нет клипов в {args.chromakey_dir}. Сначала запусти "
              f"`python -m mellstroy_gen.collect_chromakey`", file=sys.stderr)
        return 2
    if not bg_files:
        print(f"Нет background-видео в {args.bg_dir}. Запусти "
              f"`python -m mellstroy_gen.collect_backgrounds --all`", file=sys.stderr)
        return 2

    if args.smart:
        captions, styles = _prepare_smart(args.count, args.geo, args.no_ai)
    else:
        pool = GEO_CAPTIONS[args.geo][:]
        random.shuffle(pool)
        captions = []
        for i in range(args.count):
            captions.append(pool[i % len(pool)])
        styles = [pick_random_style() for _ in range(args.count)]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    green_cache: dict[str, bool] = {}

    made: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="mellgen_") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        for i in range(args.count):
            chrom = random.choice(chromakey_files)
            bg = random.choice(bg_files)
            cap = captions[i]
            style = styles[i]
            music = random.choice(music_files) if music_files else None

            idx = args.start_idx + i
            out_mp4 = out_dir / f"{args.geo}_{idx:04d}.mp4"

            if chrom.name not in green_cache:
                green_cache[chrom.name] = _detect_green(chrom)
            use_green = green_cache[chrom.name]

            try:
                generate_one(
                    chromakey=chrom,
                    background=bg,
                    caption_text=cap,
                    geo=args.geo,
                    out=out_mp4,
                    music=music,
                    tmpdir=tmpdir,
                    style=style,
                    use_chromakey=use_green,
                )
                print(f"[ok ] {out_mp4.name}  ({chrom.name} + '{cap[:40]}' стиль:{style.name})")
                made.append(out_mp4)
            except Exception as exc:
                print(f"[err] {out_mp4.name}: {exc}", file=sys.stderr)
                traceback.print_exc()

    print(f"\nГотово: {len(made)} / {args.count} видео в {out_dir}/")
    return 0 if made else 1


def _prepare_smart(count: int, geo: str, no_ai: bool) -> tuple[list[str], list[MontageStyle]]:
    """Подготавливает фразы и стили через AI (или fallback)."""
    from .ai_captions import generate_captions_ai
    from .humor_db import HumorDB

    db = HumorDB()
    print(f"[smart] Мемов в базе знаний: {len(db)}")

    if no_ai:
        from .ai_captions import _fallback_captions
        captions = _fallback_captions(count, geo)
        styles = [pick_random_style() for _ in range(count)]
    else:
        print(f"[smart] Генерирую {count} фраз через Gemini...")
        captions = generate_captions_ai(count, geo, db)
        print("[smart] Подбираю стили монтажа...")
        from .ai_style import select_styles_ai
        styles = select_styles_ai(captions)

    return captions, styles


if __name__ == "__main__":
    raise SystemExit(main())
