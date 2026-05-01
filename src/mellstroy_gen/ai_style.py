"""AI-подбор стиля монтажа через Gemini.

Gemini получает фразу и подбирает оптимальный стиль визуального оформления.
Работает батчами (10 фраз за 1 запрос) для экономии токенов.
Fallback: рандомный выбор из предустановленных стилей.
"""
from __future__ import annotations

import json
import logging
import os

from .styles import MontageStyle, pick_random_style

log = logging.getLogger(__name__)

_STYLE_PROMPT = """\
Ты подбираешь стиль монтажа для мем-видео с Меллстроем на TikTok.

Для каждой фразы подбери оптимальный визуальный стиль.
Фразы:
{captions_json}

Для каждой фразы верни JSON-объект:
{{
  "mellstroy_position": "center_bottom" | "left" | "right",
  "mellstroy_scale": число от 0.6 до 1.0,
  "subtitle_color": hex-цвет (например "#FFFFFF"),
  "subtitle_stroke_color": hex-цвет,
  "subtitle_position": "top" | "center" | "bottom",
  "subtitle_font_size": число от 60 до 100,
  "effect": "none" | "zoom_in" | "shake" | "flash"
}}

Правила:
- Драматичные/шок фразы → zoom_in или flash, красные субтитры
- Смешные/абсурдные → shake, жёлтые или зелёные субтитры
- Спокойные/POV → none, белые субтитры
- Размер Меллстроя: для реакций 0.8-0.9, для полноэкранных моментов 1.0

Верни ТОЛЬКО JSON-массив объектов (без комментариев), по одному на фразу:
[{{}}, {{}}, ...]
"""


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


def _parse_style_from_dict(d: dict, idx: int) -> MontageStyle:
    try:
        sub_color = MontageStyle.hex_to_rgb(d.get("subtitle_color", "#FFFFFF"))
        stroke_color = MontageStyle.hex_to_rgb(d.get("subtitle_stroke_color", "#000000"))
        return MontageStyle(
            name=f"ai_{idx}",
            mellstroy_position=d.get("mellstroy_position", "center_bottom"),
            mellstroy_scale=max(0.5, min(1.0, float(d.get("mellstroy_scale", 0.8)))),
            subtitle_color=sub_color,
            subtitle_stroke_color=stroke_color,
            subtitle_position=d.get("subtitle_position", "top"),
            subtitle_font_size=max(50, min(120, int(d.get("subtitle_font_size", 80)))),
            effect=d.get("effect", "none"),
        )
    except (ValueError, TypeError):
        return pick_random_style()


def select_styles_ai(captions: list[str], batch_size: int = 10) -> list[MontageStyle]:
    """Подбирает стили через Gemini батчами. Fallback: рандомные пресеты."""
    model = _get_gemini_model()
    if model is None:
        log.info("Gemini недоступен для стилей, используем рандомные пресеты")
        return [pick_random_style() for _ in captions]

    styles: list[MontageStyle] = []
    for i in range(0, len(captions), batch_size):
        batch = captions[i : i + batch_size]
        prompt = _STYLE_PROMPT.format(captions_json=json.dumps(batch, ensure_ascii=False))
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                text = text.rsplit("```", 1)[0]
            parsed = json.loads(text)
            if isinstance(parsed, list):
                for j, d in enumerate(parsed):
                    styles.append(_parse_style_from_dict(d, i + j))
            while len(styles) < i + len(batch):
                styles.append(pick_random_style())
        except Exception as exc:
            log.warning("Ошибка AI-стилей для батча %d: %s", i, exc)
            styles.extend(pick_random_style() for _ in batch)

    return styles[: len(captions)]
