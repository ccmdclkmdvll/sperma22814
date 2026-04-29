# mellstroy-meme-gen

Авто-генератор коротких мем-видео с **Меллстроем** для TikTok / Instagram Reels / YouTube Shorts.

Один запуск → N готовых 9:16 (1080×1920) видео в папке `output/`. Без ручной правки.

```
python -m mellstroy_gen.generate --count 100 --geo RU
python -m mellstroy_gen.generate --count 100 --geo DE
```

---

## Что внутри

```
mellstroy-meme-gen/
├── src/mellstroy_gen/
│   ├── sources.py            ← каталог источников (greenscreenhub, telegram-стикеры, kick-аккаунты)
│   ├── captions.py           ← базы фраз RU и DE + хэштеги по ГЕО
│   ├── render.py             ← FFmpeg-композиция + PIL-субтитры
│   ├── collect_chromakey.py  ← скачивает .mp4 с greenscreenhub (Google Drive)
│   ├── collect_stickers.py   ← скачивает Telegram-стикерпаки (Bot API)
│   ├── collect_streams.py    ← скачивает свежие стримы / клипы Меллстроя с Kick (yt-dlp)
│   ├── auto_cut.py           ← Whisper + детект пиков → авто-нарезки длинного стрима
│   └── generate.py           ← главный пайплайн
├── assets/
│   ├── chromakey/            ← клипы Меллстроя (зелёный фон или просто короткие нарезки)
│   ├── backgrounds/          ← gameplay-видео (Subway Surfers / Minecraft parkour, 5–10 минут)
│   └── music/                ← опц. фоновая музыка
├── output/                   ← готовые .mp4 + .txt с описанием/хэштегами
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
git clone https://github.com/<your-account>/mellstroy-meme-gen.git
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

Скачай 5–15 минутный ролик типа Subway Surfers / Minecraft Parkour / GTA / Truck Driver
и положи в `assets/backgrounds/` под любым именем (например, `subway_long.mp4`).

Скачать с YouTube:
```bash
yt-dlp -f "best[height<=720]" -o assets/backgrounds/%(title).40s.%(ext)s \
  "https://www.youtube.com/watch?v=ВИДЕО_ID"
```

### C. (Опционально) Музыка

Положи трендовые TikTok/Reels звуки в `assets/music/` (.mp3/.m4a). Скрипт берёт
случайный трек и микширует на ~18% громкости поверх голоса Меллстроя.

---

## Генерация

```bash
# 100 видео для русскоязычной TikTok-аудитории
python -m mellstroy_gen.generate --count 100 --geo RU

# 100 видео под Германию
python -m mellstroy_gen.generate --count 100 --geo DE
```

Что получишь в `output/`:
```
RU_0001.mp4   ← готовое 1080×1920, 30 fps, H.264 + AAC
RU_0001.txt   ← готовое описание/хэштеги, копи-пасть в TikTok
RU_0002.mp4
RU_0002.txt
...
```

Параметры:
- `--count N` — сколько видео (рекомендую 50–100 за прогон)
- `--geo {RU, DE}` — ГЕО, определяет язык субтитров и хэштеги
- `--seed N` — для воспроизводимости комбинаций
- `--start-idx 101` — продолжить нумерацию (если уже есть RU_0001…RU_0100)

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
