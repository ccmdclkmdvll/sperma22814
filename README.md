# mellstroy-meme-gen

Авто-генератор коротких мем-видео с **Меллстроем** для TikTok / Instagram Reels / YouTube Shorts.

Один запуск → N готовых 9:16 (1080×1920) видео в папке `output/`. Без ручной правки.

```bash
# Обычный режим (захардкоженные фразы)
python -m mellstroy_gen.generate --count 100 --geo RU

# Smart-режим (AI-фразы + AI-стили через Gemini)
export GEMINI_API_KEY="твой_ключ"
python -m mellstroy_gen.generate --count 50 --geo RU --smart
```

---

## Что внутри

```
mellstroy-meme-gen/
├── src/mellstroy_gen/
│   ├── generate.py           ← главный пайплайн (обычный + --smart AI-режим)
│   ├── render.py             ← FFmpeg-композиция + PIL-субтитры + MontageStyle
│   ├── captions.py           ← базы фраз RU и DE + хэштеги по ГЕО (fallback)
│   ├── sources.py            ← каталог источников
│   ├── learn.py              ← парсер мемов: ссылка → анализ → база знаний
│   ├── humor_db.py           ← локальная база выученных мем-паттернов
│   ├── ai_captions.py        ← Gemini: генерация фраз на основе базы
│   ├── ai_style.py           ← Gemini: подбор стиля монтажа
│   ├── styles.py             ← 10+ предустановленных стилей (позиции, цвета, эффекты)
│   ├── green_detect.py       ← авто-детект зелёного фона (без AI)
│   ├── collect_chromakey.py  ← скачивает .mp4 с greenscreenhub (Google Drive)
│   ├── collect_stickers.py   ← скачивает Telegram-стикерпаки (Bot API)
│   ├── collect_streams.py    ← скачивает стримы / клипы с Kick (yt-dlp)
│   ├── collect_backgrounds.py ← авто-скачка gameplay-видео
│   └── auto_cut.py           ← Whisper + детект пиков → авто-нарезки
├── assets/
│   ├── chromakey/            ← клипы Меллстроя
│   ├── backgrounds/          ← gameplay-видео
│   └── music/                ← опц. фоновая музыка
├── data/
│   └── humor_db.json         ← база выученных мем-паттернов (создаётся автоматически)
├── output/                   ← готовые .mp4 + .txt
├── tests/
│   └── test_smoke.py
└── requirements.txt
```

---

## Установка (Windows / macOS / Linux)

### 1. FFmpeg (обязательно)

- **Linux (Ubuntu/Debian)**: `sudo apt install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Windows**: скачай статический build с https://www.gyan.dev/ffmpeg/builds/ и
  добавь `bin/` в `PATH`. Проверь: `ffmpeg -version`.

### 2. Python 3.10+ и зависимости

```bash
git clone https://github.com/Pionerpinersa/mellstroy-meme-gen.git
cd mellstroy-meme-gen
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Жирный шрифт для субтитров

- **Linux**: `sudo apt install fonts-dejavu-core` (обычно уже стоит)
- **macOS / Windows**: скрипт автоматически подхватит системный Arial/Helvetica Bold

---

## Подготовка материалов

### A. Chromakey-клипы Меллстроя

**Способ 1 — greenscreenhub (Google Drive):**
```bash
python -m mellstroy_gen.collect_chromakey
```
Скачает встроенный список клипов в `assets/chromakey/`. На сегодня в списке —
проверенный `funny_dance.mp4` (1920×1080, со звуком). Если найдёшь свежие посты
на https://www.greenscreenhub.com/search/label/mellstroy%20green%20screen — добавь
их в `src/mellstroy_gen/sources.py:GREENSCREENHUB_SOURCES`.

**Способ 2 — Telegram-стикерпаки** (50+ клипов):
1. Создай бота через [@BotFather](https://t.me/BotFather) (`/newbot`, ~1 минута)
2. Получишь токен вида `123456:ABCDEF...`
3. Запусти:
```bash
export TELEGRAM_BOT_TOKEN="123456:ABCDEF..."
python -m mellstroy_gen.collect_stickers
```
Скачает паки `tellstroy` (50 шт) и `Mellstroy_memes` (40 шт) в `assets/chromakey/`.

**Способ 3 — клипы со стримов на Kick:**
```bash
# актуальный аккаунт смотри на https://mellstroy.net/stream
python -m mellstroy_gen.collect_streams --clips --account mellstroy475 --max 30
```

**Способ 4 — авто-нарезка длинного стрима (Whisper):**
```bash
python -m mellstroy_gen.collect_streams --vod LATEST  # тяжёлый!
python -m mellstroy_gen.auto_cut assets/stream_clips/<vod>.mp4 --top 30
```
Whisper транскрибирует речь, детектит пики громкости/смеха и нарезает топ-30
моментов длительностью ~22 сек. Готовые куски попадают в `assets/stream_clips/`,
их можно вручную перенести в `assets/chromakey/`.

### B. Background gameplay

**Автоматически (рекомендуется):**
```bash
python -m mellstroy_gen.collect_backgrounds --all
```
Скачает Subway Surfers, Minecraft parkour, GTA driving, satisfying-видео.

**Вручную (конкретное видео):**
```bash
python -m mellstroy_gen.collect_backgrounds --url "https://youtube.com/watch?v=..." --name subway
```

### C. (Опционально) Музыка

Положи трендовые TikTok/Reels звуки в `assets/music/` (.mp3/.m4a). Скрипт берёт
случайный трек и микширует на ~18% громкости поверх голоса Меллстроя.

---

## Генерация

### Обычный режим (без AI)
```bash
python -m mellstroy_gen.generate --count 100 --geo RU
python -m mellstroy_gen.generate --count 100 --geo DE
```

### Smart-режим (AI через Gemini)
```bash
export GEMINI_API_KEY="твой_ключ"  # бесплатно: https://aistudio.google.com/apikey
python -m mellstroy_gen.generate --count 50 --geo RU --smart
```

Smart-режим:
1. Берёт паттерны из `data/humor_db.json` (база выученного юмора)
2. Gemini генерирует уникальные мем-фразы батчем (1 запрос на все 50)
3. Gemini подбирает стиль монтажа для каждого видео
4. Авто-детект зелёного фона (chromakey vs. обычный overlay)
5. Расход: ~7 запросов из 1500 бесплатных/день

Что получишь в `output/`:
```
RU_0001.mp4   ← готовое 1080×1920, 30 fps, H.264 + AAC
RU_0001.txt   ← описание/хэштеги для TikTok
...
```

Параметры:
- `--count N` — сколько видео (рекомендую 50–100 за прогон)
- `--geo {RU, DE}` — ГЕО, определяет язык субтитров и хэштеги
- `--smart` — AI-режим (нужен `GEMINI_API_KEY`)
- `--no-ai` — в smart-режиме использовать рандомные стили без Gemini
- `--seed N` — для воспроизводимости комбинаций
- `--start-idx 101` — продолжить нумерацию

---

## Обучение на мемах

Скорми AI залетевшие ролики — он проанализирует юмор и будет генерировать
фразы в стиле того, что реально набирает просмотры:

```bash
# Скормить залетевший мем
python -m mellstroy_gen.learn "https://www.tiktok.com/@user/video/12345"

# Скормить список из файла
python -m mellstroy_gen.learn urls.txt

# Посмотреть что в базе
python -m mellstroy_gen.learn --show
```

Чем больше мемов скормишь — тем точнее AI подбирает фразы и стиль.
Всё хранится локально в `data/humor_db.json`.

---

## Правила конкурса (выжимка из telegra.ph)

1. **Меллстрой — главный персонаж** (не второстепенный → не оплачивается)
2. Минимум **100K просмотров** на ролик чтобы получить выплату
3. **ГЕО-таргет**: текст и музыка на языке нужной страны (иначе словишь Азию → не платят)
4. **Один ролик = одна площадка**. На каждый ролик отдельная заявка модератору.
5. Запрещены: политика/наркота, лево-сомнительный traffic, реклама других стримеров
6. Выплаты — **только USDT TRC20** (адрес начинается с заглавной T)
7. Заявки: **@moderatortik** (загрузки), **@moderatortik2** (вопросы), **@mellstroysup** (споры)
8. Контест-канал: **@mellstroytiktok** (72K), правила: https://telegra.ph/Informaciyaotvety-na-voprosypravila-polucheniya-vyplat-04-27

Скрипт автоматически:
- Использует `--geo` для языка/хэштегов
- Делает Меллстроя визуально главным (overlay на всю высоту, центр-низ)
- Добавляет флаг страны в .txt-описание

---

## Источники материала (проверено вручную)

| Источник | Ссылка | Содержимое |
|---|---|---|
| greenscreenhub | https://www.greenscreenhub.com/search/label/mellstroy%20green%20screen | прямые .mp4 на Google Drive |
| TG-стикерпак `tellstroy` | https://t.me/addstickers/tellstroy | 50 video-стикеров WEBM |
| TG-стикерпак `Mellstroy_memes` | https://t.me/addstickers/Mellstroy_memes | 40 video-стикеров WEBM |
| TG-канал @tellstroy | https://t.me/s/tellstroy | основной канал Мела (920K) |
| TG-канал @mellstroy_memes | https://t.me/mellstroy_memes | официальные исходники для нарезчиков |
| TG-канал @mellstroytiktok | https://t.me/s/mellstroytiktok | конкурс + топ-10 мемов |
| Kick стримы | https://kick.com/mellstroy475 | хранятся 7 дней, yt-dlp поддерживает |
| Агрегатор актуального аккаунта | https://mellstroy.net/stream | если аккаунт забанен |
| CapCut шаблоны | https://www.capcut.com/discover?q=mellstroy | референсы трендов |

---

## Smoke test

```bash
# Запустит pytest на одном маленьком конце-в-конец прогоне
pytest tests/
```

---

## Лицензия и оговорки

Контент Меллстроя — публичный, его собственный. Используй только для участия в его
официальном конкурсе ([правила](https://telegra.ph/Informaciyaotvety-na-voprosypravila-polucheniya-vyplat-04-27))
или личных целях. Скрипт автоматизирует только техническую часть монтажа.
