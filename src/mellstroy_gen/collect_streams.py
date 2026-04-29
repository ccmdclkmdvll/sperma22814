"""Качает свежие стримы / клипы Меллстроя с Kick через yt-dlp.

Kick хранит VOD-ы примерно 7 дней. Каждый день он стримит — материал свежий.
Для скачивания используется yt-dlp (extractor для Kick добавлен в августе 2024).

Использование:
    # скачать последний полный стрим (тяжёлый файл!)
    python -m mellstroy_gen.collect_streams --vod LATEST

    # скачать все клипы текущего аккаунта
    python -m mellstroy_gen.collect_streams --clips

    # указать конкретный аккаунт (если основной забанен и Мел сделал новый)
    python -m mellstroy_gen.collect_streams --clips --account mellstroy475
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from .sources import KICK_ACCOUNTS


def _ensure_yt_dlp() -> str:
    yt = shutil.which("yt-dlp")
    if yt:
        return yt
    # как fallback — python -m yt_dlp
    return f"{sys.executable} -m yt_dlp"


def download_clips(account: str, dest: Path, max_clips: int = 30) -> int:
    """Скачивает клипы (короткие нарезки, не полные стримы) с Kick-аккаунта."""
    dest.mkdir(parents=True, exist_ok=True)
    url = f"https://kick.com/{account}/clips"
    cmd = [
        *_ensure_yt_dlp().split(),
        "-N", "4",                            # 4 параллельных потока
        "-o", str(dest / "%(id)s_%(title).80s.%(ext)s"),
        "--max-downloads", str(max_clips),
        "--no-warnings",
        "--ignore-errors",
        "--restrict-filenames",
        url,
    ]
    print("$", " ".join(cmd))
    return subprocess.call(cmd)


def download_latest_vod(account: str, dest: Path) -> int:
    """Скачивает последний полный VOD с Kick (тяжёлый, 4-8 часов)."""
    dest.mkdir(parents=True, exist_ok=True)
    url = f"https://kick.com/{account}/videos"
    cmd = [
        *_ensure_yt_dlp().split(),
        "-N", "4",
        "-o", str(dest / "%(upload_date)s_%(title).80s.%(ext)s"),
        "--playlist-items", "1",
        "--no-warnings",
        "--ignore-errors",
        "--restrict-filenames",
        url,
    ]
    print("$", " ".join(cmd))
    return subprocess.call(cmd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--account",
        default=KICK_ACCOUNTS[0],
        help=f"Kick-username Меллстроя (по умолчанию {KICK_ACCOUNTS[0]}). "
             f"При банах он создаёт новые: {KICK_ACCOUNTS}.",
    )
    parser.add_argument(
        "--clips",
        action="store_true",
        help="скачать готовые клипы (рекомендую — короткие, со звуком)",
    )
    parser.add_argument(
        "--vod",
        choices=["LATEST"],
        help="скачать последний полный VOD (нужно для Whisper-нарезки)",
    )
    parser.add_argument(
        "--out",
        default="assets/stream_clips",
        help="папка для сохранения",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=30,
        help="максимум клипов (для --clips)",
    )
    args = parser.parse_args(argv)

    out = Path(args.out)

    if not (args.clips or args.vod):
        parser.error("укажи --clips или --vod LATEST")

    rc = 0
    if args.clips:
        rc |= download_clips(args.account, out, max_clips=args.max)
    if args.vod == "LATEST":
        rc |= download_latest_vod(args.account, out)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
