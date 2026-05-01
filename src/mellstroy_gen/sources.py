"""Источники chromakey-материалов с Меллстроем.

Все ссылки на Google Drive / прямые .mp4 проверены вручную (см. README).
Если какой-то источник перестал отдавать файл — обнови сюда новую ссылку.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChromakeySource:
    name: str           # короткое имя для файла
    url: str            # прямой URL .mp4 (Google Drive uc?export=download&id=...)
    page: str           # исходная страница (для проверки/обновления)
    description: str    # суть клипа


# Greenscreenhub (Google Drive direct downloads).
# При устаревании ссылок открыть `page` и заменить `url` на новую кнопку Download.
GREENSCREENHUB_SOURCES: list[ChromakeySource] = [
    ChromakeySource(
        name="funny_dance",
        url="https://drive.google.com/uc?export=download&id=1JbaPhaKpszn3NNtGKVLgwH7aqq7sSf3H",
        page="https://www.greenscreenhub.com/2024/07/download-mellstroy-funny-dance-green.html",
        description="Меллстрой танцует, размашистые движения. ~14 сек.",
    ),
    # Остальные ссылки нужно вытащить со страниц greenscreenhub — у каждого поста
    # своя кнопка Google Drive. Run `python -m mellstroy_gen.collect_chromakey --discover`
    # чтобы спарсить все mellstroy-зеленые экраны автоматически.
]


# Список индексных URL на greenscreenhub для discover-а.
GREENSCREENHUB_INDEX_URLS: list[str] = [
    "https://www.greenscreenhub.com/2024/07/download-mellstroy-funny-dance-green.html",
    "https://www.greenscreenhub.com/2024/07/download-mellstroy-staring-at-you-green.html",
    "https://www.greenscreenhub.com/2024/07/download-mellstroy-swearing-green-screen.html",
    "https://www.greenscreenhub.com/2024/10/download-mellstroy-who-is-all-this-meme.html",
    "https://www.greenscreenhub.com/2024/11/download-mellstroy-meme-green-screen.html",
]


# Telegram-стикерпаки с Меллстроем (видео-стикеры WEBM). Для скачки нужен бот-токен:
# сделай бота через @BotFather и положи в env TELEGRAM_BOT_TOKEN.
TELEGRAM_STICKER_PACKS: list[str] = [
    "tellstroy",            # 50 video stickers
    "Mellstroy_memes",      # 40 video stickers
    "mellstroy271pack",
]


# Текущие Kick-аккаунты Меллстроя (он создаёт новые после банов).
# Проверить актуальный: https://mellstroy.net/stream
KICK_ACCOUNTS: list[str] = [
    "mellstroy475",
    "mellstroy271",
    "mellstroy987",
    "mellstroylive282",
]
