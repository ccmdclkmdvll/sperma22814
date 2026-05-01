"""Парсер мемов: ссылка → скачка → анализ → сохранение в базу знаний.

Поддерживает TikTok, YouTube Shorts, Instagram Reels и любые URL,
которые понимает yt-dlp.

Использование:
    python -m mellstroy_gen.learn "https://www.tiktok.com/@user/video/12345"
    python -m mellstroy_gen.learn urls.txt
    python -m mellstroy_gen.learn --show
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .humor_db import HumorDB, MemeAnalysis, MemeEntry

log = logging.getLogger(__name__)

_ANALYZE_PROMPT = """\
Ты — эксперт по вирусному контенту на TikTok/Reels.

Проанализируй этот мем-ролик с Меллстроем:
- Текст субтитров/речь: "{subtitle_text}"
- Описание: "{description}"
- Хэштеги: {hashtags}
- Длительность: {duration} сек
- Просмотры: {view_count}

Верни ТОЛЬКО JSON (без комментариев):
{{
  "humor_type": "один из: reaction, absurd, relatable, shock, cringe, wholesome, meta",
  "humor_formula": "короткое описание формулы юмора (10-20 слов)",
  "what_is_funny": "почему это смешно (1-2 предложения)",
  "key_elements": ["ключевые элементы: реакция, крик, танец, деньги, ..."],
  "caption_style": "стиль подписи: вопрос, утверждение, POV, когда...",
  "target_audience": "RU_meme или DE_meme или universal",
  "virality_score": "число 1-10",
  "similar_ideas": ["3 идеи для новых мемов в таком же стиле"]
}}
"""


def _download_metadata(url: str) -> dict:
    """Скачивает метаданные видео через yt-dlp (без скачки самого видео)."""
    yt = shutil.which("yt-dlp") or f"{sys.executable} -m yt_dlp"
    cmd = [
        *yt.split(),
        "--dump-json",
        "--no-download",
        "--no-warnings",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp ошибка: {result.stderr[:300]}")
    return json.loads(result.stdout)


def _download_video(url: str, dest: Path) -> Path:
    """Скачивает видео через yt-dlp."""
    yt = shutil.which("yt-dlp") or f"{sys.executable} -m yt_dlp"
    out_path = dest / "%(id)s.%(ext)s"
    cmd = [
        *yt.split(),
        "-o", str(out_path),
        "--no-warnings",
        "--restrict-filenames",
        url,
    ]
    subprocess.run(cmd, check=True, timeout=300)
    files = list(dest.glob("*.*"))
    video_files = [f for f in files if f.suffix.lower() in (".mp4", ".webm", ".mkv")]
    if not video_files:
        raise FileNotFoundError("yt-dlp не скачал видео")
    return video_files[0]


def _transcribe_video(video_path: Path) -> str:
    """Извлекает текст из видео через Whisper."""
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("base", compute_type="auto")
        segments, _ = model.transcribe(str(video_path), language="ru", vad_filter=True)
        return " ".join(s.text.strip() for s in segments)
    except ImportError:
        pass
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(str(video_path), language="ru")
        return result.get("text", "")
    except ImportError:
        log.warning("Whisper не установлен, текст из видео не извлечён")
        return ""


def _analyze_with_gemini(
    subtitle_text: str,
    description: str,
    hashtags: list[str],
    duration: float,
    view_count: int,
) -> MemeAnalysis:
    """Анализирует мем через Gemini."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log.warning("GEMINI_API_KEY не задан, анализ невозможен")
        return MemeAnalysis()

    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = _ANALYZE_PROMPT.format(
        subtitle_text=subtitle_text[:500],
        description=description[:300],
        hashtags=json.dumps(hashtags[:15], ensure_ascii=False),
        duration=f"{duration:.1f}",
        view_count=view_count or "неизвестно",
    )
    response = model.generate_content(prompt)
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
    data = json.loads(text)
    return MemeAnalysis(
        humor_type=str(data.get("humor_type", "")),
        humor_formula=str(data.get("humor_formula", "")),
        what_is_funny=str(data.get("what_is_funny", "")),
        key_elements=list(data.get("key_elements", [])),
        caption_style=str(data.get("caption_style", "")),
        target_audience=str(data.get("target_audience", "")),
        virality_score=int(data.get("virality_score", 0)),
        similar_ideas=list(data.get("similar_ideas", [])),
    )


def _url_to_id(url: str) -> str:
    m = re.search(r"/video/(\d+)", url)
    if m:
        return f"tiktok_{m.group(1)}"
    m = re.search(r"shorts/([A-Za-z0-9_-]+)", url)
    if m:
        return f"yt_{m.group(1)}"
    return "meme_" + hashlib.md5(url.encode()).hexdigest()[:12]


def learn_meme(url: str, db: HumorDB | None = None) -> MemeEntry:
    """Полный пайплайн: скачка → транскрипция → анализ → сохранение."""
    db = db or HumorDB()

    print(f"[learn] Скачиваю метаданные: {url}")
    try:
        meta = _download_metadata(url)
    except Exception as exc:
        print(f"[warn] Не удалось получить метаданные: {exc}", file=sys.stderr)
        meta = {}

    description = meta.get("description", "") or meta.get("title", "")
    hashtags = meta.get("tags", []) or []
    duration = meta.get("duration", 0) or 0
    view_count = meta.get("view_count", 0) or 0
    meme_id = _url_to_id(url)

    subtitle_text = ""
    with tempfile.TemporaryDirectory(prefix="melllearn_") as tmpdir:
        try:
            print("[learn] Скачиваю видео для транскрипции...")
            video_path = _download_video(url, Path(tmpdir))
            print("[learn] Транскрибирую через Whisper...")
            subtitle_text = _transcribe_video(video_path)
            if subtitle_text:
                print(f"[learn] Текст: {subtitle_text[:100]}...")
        except Exception as exc:
            print(f"[warn] Не удалось извлечь текст: {exc}", file=sys.stderr)

    if not subtitle_text:
        subtitle_text = description

    print("[learn] Анализирую через Gemini...")
    try:
        analysis = _analyze_with_gemini(
            subtitle_text=subtitle_text,
            description=description,
            hashtags=hashtags,
            duration=duration,
            view_count=view_count,
        )
    except Exception as exc:
        print(f"[err] Gemini анализ не удался: {exc}", file=sys.stderr)
        analysis = MemeAnalysis()

    entry = MemeEntry(
        id=meme_id,
        url=url,
        source="tiktok" if "tiktok" in url else "youtube" if "youtube" in url or "youtu.be" in url else "other",
        subtitle_text=subtitle_text[:500],
        description=description[:300],
        hashtags=hashtags[:15],
        duration_sec=duration,
        view_count=view_count,
        analyzed_at=datetime.now(timezone.utc).isoformat(),
        analysis=analysis,
    )
    db.add_meme(entry)

    print(f"[learn] Сохранено в базу: {meme_id}")
    if analysis.humor_type:
        print(f"  тип юмора: {analysis.humor_type}")
        print(f"  формула: {analysis.humor_formula}")
        print(f"  вирусность: {analysis.virality_score}/10")
        if analysis.similar_ideas:
            print("  идеи для новых мемов:")
            for idea in analysis.similar_ideas:
                print(f"    - {idea}")
    return entry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="*", help="URL(ы) мемов или файл со списком URL")
    parser.add_argument("--show", action="store_true", help="показать содержимое базы")
    parser.add_argument("--db", default=None, help="путь к humor_db.json")
    args = parser.parse_args(argv)

    db = HumorDB(Path(args.db)) if args.db else HumorDB()

    if args.show:
        print(f"Мемов в базе: {len(db)}")
        patterns = db.get_patterns()
        if patterns:
            print(json.dumps(patterns, ensure_ascii=False, indent=2))
        else:
            print("База пуста. Скорми мемы: python -m mellstroy_gen.learn <url>")
        return 0

    urls: list[str] = []
    for u in args.urls:
        p = Path(u)
        if p.exists() and p.is_file():
            urls.extend(
                line.strip()
                for line in p.read_text().splitlines()
                if line.strip() and not line.strip().startswith("#")
            )
        else:
            urls.append(u)

    if not urls:
        parser.error("укажи URL мема или файл со списком URL, или --show")

    ok = 0
    for url in urls:
        try:
            learn_meme(url, db)
            ok += 1
        except Exception as exc:
            print(f"[fail] {url}: {exc}", file=sys.stderr)

    print(f"\nОбработано: {ok}/{len(urls)}. Всего в базе: {len(db)} мемов.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
