"""Скачивает chromakey-клипы Меллстроя в `assets/chromakey/`.

Источники:
1. greenscreenhub.com — прямые .mp4 на Google Drive. Парсим страницы и достаём
   ссылку из кнопки "Click Here to Download it".

Использование:
    python -m mellstroy_gen.collect_chromakey
    python -m mellstroy_gen.collect_chromakey --discover  # обновить список ссылок
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path
from typing import Iterable

import requests
from tqdm import tqdm

from .sources import (
    GREENSCREENHUB_INDEX_URLS,
    GREENSCREENHUB_SOURCES,
    ChromakeySource,
)

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    return s


def discover_greenscreenhub_sources(
    index_urls: Iterable[str],
) -> list[ChromakeySource]:
    """Парсит страницы greenscreenhub и возвращает список ChromakeySource."""
    sess = _session()
    discovered: list[ChromakeySource] = []
    drive_id_re = re.compile(
        r"drive\.google\.com/(?:uc\?export=download&id=|file/d/)([A-Za-z0-9_-]{20,})"
    )
    for page in index_urls:
        try:
            html = sess.get(page, timeout=20).text
        except requests.RequestException as exc:
            print(f"[warn] не смог открыть {page}: {exc}", file=sys.stderr)
            continue

        ids = drive_id_re.findall(html)
        if not ids:
            print(f"[warn] на {page} нет drive-ссылок", file=sys.stderr)
            continue

        # извлекаем slug из URL ('download-mellstroy-funny-dance-green' -> 'funny_dance')
        slug = page.rstrip("/").rsplit("/", 1)[-1].replace(".html", "")
        slug = re.sub(r"^download-mellstroy-", "", slug)
        slug = re.sub(r"-green(-screen)?(-meme)?$", "", slug)
        slug = slug.replace("-", "_") or "clip"

        # берём первый найденный Drive ID
        drive_id = ids[0]
        url = f"https://drive.google.com/uc?export=download&id={drive_id}"
        discovered.append(
            ChromakeySource(name=slug, url=url, page=page, description="")
        )
    return discovered


def _drive_download(url: str, out: Path, sess: requests.Session) -> None:
    """Скачивает файл с Google Drive с обработкой confirm-токена больших файлов."""
    with sess.get(url, stream=True, allow_redirects=True, timeout=60) as r:
        r.raise_for_status()
        # Drive для больших файлов отдаёт html с confirm-токеном
        ctype = r.headers.get("content-type", "")
        if "text/html" in ctype:
            html = r.text
            m = re.search(r'confirm=([0-9A-Za-z_-]+)', html)
            if m:
                token = m.group(1)
                final = url + f"&confirm={token}"
                with sess.get(final, stream=True, timeout=120) as r2:
                    r2.raise_for_status()
                    _stream_to(r2, out)
                return
            raise RuntimeError("Drive отдал HTML без confirm-токена")
        _stream_to(r, out)


def _stream_to(resp: requests.Response, out: Path) -> None:
    total = int(resp.headers.get("content-length") or 0) or None
    with out.open("wb") as f, tqdm(
        total=total, unit="B", unit_scale=True, desc=out.name, leave=False
    ) as bar:
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            if chunk:
                f.write(chunk)
                bar.update(len(chunk))


def collect(
    sources: list[ChromakeySource],
    dest: Path,
    overwrite: bool = False,
) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    sess = _session()
    saved: list[Path] = []
    for src in sources:
        out = dest / f"{src.name}.mp4"
        if out.exists() and not overwrite:
            print(f"[skip] {out.name} уже существует")
            saved.append(out)
            continue
        try:
            print(f"[get ] {src.name} <- {src.page}")
            _drive_download(src.url, out, sess)
            saved.append(out)
            time.sleep(1)
        except Exception as exc:
            print(f"[fail] {src.name}: {exc}", file=sys.stderr)
            if out.exists():
                out.unlink()
    return saved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default="assets/chromakey",
        help="папка куда скачивать (по-умолчанию assets/chromakey)",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="не использовать встроенный список, а парсить страницы greenscreenhub",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="перекачать существующие файлы",
    )
    args = parser.parse_args(argv)

    if args.discover:
        sources = discover_greenscreenhub_sources(GREENSCREENHUB_INDEX_URLS)
        if not sources:
            print("Ничего не нашёл при discover. Откатываемся к встроенному списку.")
            sources = list(GREENSCREENHUB_SOURCES)
    else:
        sources = list(GREENSCREENHUB_SOURCES)

    print(f"Источников: {len(sources)}")
    saved = collect(sources, Path(args.out), overwrite=args.overwrite)
    print(f"Скачано/готово файлов: {len(saved)}")
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
