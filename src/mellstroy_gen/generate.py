"""Главный пайплайн: собирает финальные TikTok-видео.

Входы (должны быть подготовлены заранее):
    assets/chromakey/*.mp4    — клипы Меллстроя на зелёном или сырые нарезки
    assets/backgrounds/*.mp4  — длинные gameplay-видео (Subway Surfers, Minecraft)
    assets/music/*.mp3        — опц. фоновая музыка (тихо, под голос)

Что делает на каждой итерации:
    1. рандомный chromakey-клип
    2. рандомный отрезок background-видео той же длительности
    3. рандомная фраза из captions[geo] + хэштеги/флаг
    4. рендер субтитра (PNG) + FFmpeg-композиция
    5. сохранение в output/<geo>_<idx>.mp4 + .txt с описанием

Использование:
    python -m mellstroy_gen.generate --count 100 --geo RU
    python -m mellstroy_gen.generate --count 50 --geo DE
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
import traceback
from pathlib import Path

from .captions import GEO_CAPTIONS, GEO_FLAG, GEO_HASHTAGS
from .render import CompositionInputs, compose, probe_duration, render_caption


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


def generate_one(
    chromakey: Path,
    background: Path,
    caption_text: str,
    geo: str,
    out: Path,
    music: Path | None = None,
    tmpdir: Path | None = None,
) -> Path:
    clip_dur = probe_duration(chromakey)
    bg_dur = probe_duration(background)
    bg_offset = pick_bg_offset(bg_dur, clip_dur)

    tmpdir = tmpdir or Path(tempfile.mkdtemp(prefix="mellgen_"))
    cap_png = tmpdir / f"caption_{out.stem}.png"
    render_caption(caption_text, cap_png)

    compose(CompositionInputs(
        chromakey=chromakey,
        background=background,
        bg_offset=bg_offset,
        duration=clip_dur,
        caption_png=cap_png,
        music=music,
        out=out,
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
    args = parser.parse_args(argv)

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
        print(f"Нет background-видео в {args.bg_dir}. Положи туда хотя бы 1 длинное "
              f"gameplay-видео (Subway Surfers / Minecraft parkour, 5-10 минут).", file=sys.stderr)
        return 2

    captions = GEO_CAPTIONS[args.geo][:]
    random.shuffle(captions)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    made: list[Path] = []
    seen_pairs: set[tuple[str, str, str]] = set()
    idx = args.start_idx
    attempts = 0
    while len(made) < args.count and attempts < args.count * 5:
        attempts += 1
        chrom = random.choice(chromakey_files)
        bg = random.choice(bg_files)
        cap = captions[(idx - args.start_idx) % len(captions)]
        key = (chrom.name, cap, bg.name)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)

        music = random.choice(music_files) if music_files else None
        out_mp4 = out_dir / f"{args.geo}_{idx:04d}.mp4"
        try:
            generate_one(
                chromakey=chrom,
                background=bg,
                caption_text=cap,
                geo=args.geo,
                out=out_mp4,
                music=music,
            )
            print(f"[ok ] {out_mp4.name}  ({chrom.name} + '{cap[:40]}')")
            made.append(out_mp4)
            idx += 1
        except Exception as exc:
            print(f"[err] {out_mp4.name}: {exc}", file=sys.stderr)
            traceback.print_exc()

    print(f"\nГотово: {len(made)} / {args.count} видео в {out_dir}/")
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main())
