"""Скачивает Telegram-стикерпаки с Меллстроем.

Использует Bot API. Создай бота через @BotFather и положи токен в env:
    export TELEGRAM_BOT_TOKEN=123456:ABC...

После скачивания .webm-стикеры конвертируются в .mp4 и копируются в `assets/chromakey/`.
ВАЖНО: video-стикеры с Меллстроем обычно НЕ на зелёном фоне (чёрный/прозрачный) —
поэтому в generate.py они композятся как есть, без chromakey-фильтра. Если стикер
на зелёном фоне, он сработает с chromakey автоматически.

Использование:
    python -m mellstroy_gen.collect_stickers
    python -m mellstroy_gen.collect_stickers --packs tellstroy Mellstroy_memes
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import requests
from tqdm import tqdm

from .sources import TELEGRAM_STICKER_PACKS

API = "https://api.telegram.org/bot{token}"


def get_sticker_set(token: str, name: str) -> dict:
    r = requests.get(f"{API.format(token=token)}/getStickerSet",
                     params={"name": name}, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"getStickerSet({name}): {data}")
    return data["result"]


def get_file_path(token: str, file_id: str) -> str:
    r = requests.get(f"{API.format(token=token)}/getFile",
                     params={"file_id": file_id}, timeout=20)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"getFile({file_id}): {data}")
    return data["result"]["file_path"]


def download_file(token: str, file_path: str, out: Path) -> None:
    url = f"https://api.telegram.org/file/bot{token}/{file_path}"
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("wb") as f:
            for chunk in r.iter_content(64 * 1024):
                f.write(chunk)


def webm_to_mp4(src: Path, dst: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(src),
        # video sticker → playable mp4. Если был alpha — теряется (mp4 не поддерживает).
        # Композиция в generate.py будет работать без chromakey (просто overlay).
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
        "-an",
        str(dst),
    ]
    subprocess.run(cmd, check=True)


def collect_pack(token: str, pack_name: str, raw_dir: Path, out_dir: Path) -> int:
    info = get_sticker_set(token, pack_name)
    stickers = info.get("stickers", [])
    if not stickers:
        print(f"[warn] {pack_name}: пусто")
        return 0
    print(f"[pack] {pack_name}: {len(stickers)} стикеров (тип: {info.get('sticker_type')})")
    n = 0
    for i, st in enumerate(tqdm(stickers, desc=pack_name, leave=False), 1):
        try:
            file_path = get_file_path(token, st["file_id"])
            ext = Path(file_path).suffix.lower() or ".bin"
            raw_out = raw_dir / f"{pack_name}_{i:03d}{ext}"
            download_file(token, file_path, raw_out)
            if ext == ".webm":
                mp4_out = out_dir / f"{pack_name}_{i:03d}.mp4"
                webm_to_mp4(raw_out, mp4_out)
                n += 1
            elif ext == ".mp4":
                shutil.copy(raw_out, out_dir / f"{pack_name}_{i:03d}.mp4")
                n += 1
            # tgs (анимированные lottie) — пропускаем
        except Exception as exc:
            print(f"[warn] {pack_name}_{i:03d}: {exc}")
    return n


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packs", nargs="*", default=TELEGRAM_STICKER_PACKS)
    parser.add_argument("--out", default="assets/chromakey")
    parser.add_argument("--raw-dir", default="assets/sticker_raw")
    parser.add_argument("--token", default=os.environ.get("TELEGRAM_BOT_TOKEN"))
    args = parser.parse_args(argv)

    if not args.token:
        print("Нужен токен бота. Создай через @BotFather и положи в env "
              "TELEGRAM_BOT_TOKEN, либо передай --token", file=sys.stderr)
        return 2

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    for pack in args.packs:
        try:
            total += collect_pack(args.token, pack, raw_dir, out_dir)
        except Exception as exc:
            print(f"[fail] {pack}: {exc}", file=sys.stderr)
    print(f"\nГотово: {total} стикеров → {out_dir}")
    return 0 if total else 1


if __name__ == "__main__":
    raise SystemExit(main())
