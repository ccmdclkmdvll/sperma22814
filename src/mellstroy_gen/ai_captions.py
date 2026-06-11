"""Генерация мем-фраз через Gemini на основе выученных паттернов.

Работает в двух режимах:
1. smart — берёт паттерны из humor_db и генерирует фразы через Gemini
2. fallback — возвращает захардкоженные фразы из captions.py (если нет API-ключа)
"""
from __future__ import annotations

import json
import logging
import os

from .captions import GEO_CAPTIONS
from .humor_db import HumorDB

log = logging.getLogger(__name__)

_GENERATE_PROMPT = """\
Ты — копирайтер мем-контента для TikTok/Reels с Меллстроем (стример).

На основе анализа залетевших мемов, вот что работает лучше всего:
{patterns}

Сгенерируй {count} НОВЫХ уникальных мем-фраз для видео с Меллстроем.
Язык: {language}.

Правила:
- Каждая фраза — 3-8 слов (короткие залетают лучше)
- Используй формулы юмора из анализа
- НЕ повторяй примеры выше, делай НОВЫЕ вариации
- Фразы должны работать как субтитры поверх видео
- Используй разные стили: "Когда...", "POV:", утверждение, вопрос
- Фразы должны быть СМЕШНЫМИ и вирусными

Верни ТОЛЬКО JSON-массив строк, без комментариев:
["фраза1", "фраза2", ...]
"""

_GEO_LANGUAGES = {
    "RU": "русский",
    "DE": "немецкий (разговорный, TikTok-стиль)",
}


def _get_gemini_model():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai.GenerativeModel("gemini-2.0-flash")
    except Exception as exc:
        log.warning("Не удалось инициализировать Gemini: %s", exc)
        return None


def generate_captions_ai(
    count: int,
    geo: str,
    db: HumorDB | None = None,
) -> list[str]:
    """Генерирует фразы через Gemini. Возвращает список строк."""
    model = _get_gemini_model()
    if model is None:
        log.info("Gemini недоступен, используем fallback-фразы")
        return _fallback_captions(count, geo)

    db = db or HumorDB()
    patterns = db.export_for_prompt()
    language = _GEO_LANGUAGES.get(geo, "русский")

    prompt = _GENERATE_PROMPT.format(
        patterns=patterns,
        count=count,
        language=language,
    )
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
            text = text.rsplit("```", 1)[0]
        captions = json.loads(text)
        if isinstance(captions, list) and all(isinstance(c, str) for c in captions):
            log.info("Gemini сгенерировал %d фраз", len(captions))
            return captions[:count]
    except Exception as exc:
        log.warning("Ошибка генерации через Gemini: %s", exc)

    return _fallback_captions(count, geo)


def _fallback_captions(count: int, geo: str) -> list[str]:
    """Захардкоженные фразы из captions.py как запасной вариант."""
    import random
    pool = GEO_CAPTIONS.get(geo, GEO_CAPTIONS["RU"])[:]
    random.shuffle(pool)
    if count <= len(pool):
        return pool[:count]
    result = []
    while len(result) < count:
        result.extend(pool)
    return result[:count]
