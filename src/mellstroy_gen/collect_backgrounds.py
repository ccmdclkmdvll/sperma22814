"""Автоскачка background gameplay-видео для монтажа.

Скачивает Subway Surfers / Minecraft parkour / satisfying gameplay
через yt-dlp. Используются ролики без комментариев (gameplay only).

Использование:
    python -m mellstroy_gen.collect_backgrounds
    python -m mellstroy_gen.collect_backgrounds --url "https://youtube.com/watch?v=..."
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

BACKGROUND_SOURCES: list[dict[str, str]] = [
    {
        "name": "subway_surfers_gameplay",
        "query": "subway surfers gameplay no commentary 10 minutes",
        "description": "Subway Surfers — классический TikTok-фон",
    },
    {
        "name": "minecraft_parkour",
        "query": "minecraft parkour gameplay no commentary",
        "description": "Minecraft паркур — популярный фон для мемов",
    },
    {
        "name": "gta_driving",
        "query": "gta 5 free driving no commentary gameplay",
        "description": "GTA свободная езда",
    },
    {
        "name": "satisfying_slime",
        "query": "satisfying slime asmr compilation",
        "description": "Satisfying видео — залетает как фон",
    },
]


def _ensure_yt_dlp() -> list[str]:
    yt = shutil.which("yt-dlp")
    if yt:
        return [yt]
    return [sys.executable, "-m", "yt_dlp"]


def download_by_url(url: str, dest: Path, name: str | None = None) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    template = str(dest / (f"{name}.%(ext)s" if name else "%(title).60s.%(ext)s"))
    cmd = [
        *_ensure_yt_dlp(),
        "-f", "best[height<=720]",
        "-o", template,
        "--no-warnings",
        "--restrict-filenames",
        url,
    ]
    print(f"[bg] Скачиваю: {url}")
    return subprocess.call(cmd)


def search_and_download(query: str, dest: Path, name: str, max_results: int = 1) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    template = str(dest / f"{name}.%(ext)s")
    cmd = [
        *_ensure_yt_dlp(),
        "-f", "best[height<=720]",
        "-o", template,
        "--no-warnings",
        "--restrict-filenames",
        "--max-downloads", str(max_results),
        f"ytsearch{max_results}:{query}",
    ]
    print(f"[bg] Поиск и скачка: {query}")
    return subprocess.call(cmd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="assets/backgrounds", help="папка для сохранения")
    parser.add_argument("--url", help="скачать конкретное видео по URL")
    parser.add_argument("--name", help="имя файла (без расширения)")
    parser.add_argument("--all", action="store_true", help="скачать все встроенные источники")
    args = parser.parse_args(argv)

    dest = Path(args.out)

    if args.url:
        return download_by_url(args.url, dest, args.name)

    if args.all:
        ok = 0
        for src in BACKGROUND_SOURCES:
            existing = list(dest.glob(f"{src['name']}.*"))
            if existing:
                print(f"[skip] {src['name']} уже существует")
                ok += 1
                continue
            rc = search_and_download(src["query"], dest, src["name"])
            if rc == 0:
                ok += 1
        print(f"\nСкачано: {ok}/{len(BACKGROUND_SOURCES)} backgrounds в {dest}/")
        return 0 if ok else 1

    print("Укажи --url <ссылка> или --all для скачки встроенных источников.")
    print("\nВстроенные источники:")
    for src in BACKGROUND_SOURCES:
        print(f"  {src['name']}: {src['description']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
