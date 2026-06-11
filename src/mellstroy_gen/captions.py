"""Базы фраз для субтитров. Подбираются под ГЕО-таргет.

Правила конкурса (mellstroytiktok пост от 24.03.2026): чтобы не словить Азию,
текст и музыка должны быть на языке нужной страны.
"""
from __future__ import annotations

# RU + СНГ — мем-фразы из стримов и общая мем-лексика
RU_CAPTIONS: list[str] = [
    "Когда увидел его реакцию",
    "Пацаны такого не видели",
    "Вот это поворот",
    "Жесть какая",
    "Скажи 300",
    "Лысый, плаки-плаки?",
    "Я не шучу братан",
    "Просто посмотрите на это",
    "Как тебе такое",
    "Это было что-то с чем-то",
    "Когда зашёл в чат",
    "Он реально это сделал",
    "POV: ты на стриме у Мела",
    "Вы только послушайте",
    "Самый кринжовый момент",
    "А я тут просто мимо проходил",
    "Это легенда",
    "Хорошо что не я",
    "Когда понял что попал",
    "Реакция бесценна",
    "Дикий движ на стриме",
    "Боров в ударе",
    "Это надо видеть",
    "А чё так можно было?",
    "Челлендж принят",
    "Вот это охота",
    "Когда сказал что-то не то",
    "Не повторяйте дома",
    "Просто шок-контент",
    "Стрим века",
    "Пацаны в шоке",
    "Когда не ожидал такого",
    "Вот это уровень",
    "Сделали ставочки",
    "А он реально лысый",
    "Когда выиграл занос",
    "Капец что творит",
    "Дикий смех",
    "А ну-ка",
    "Пожалуйста повторите",
    "Это надо в учебники",
    "Когда не туда зашёл",
    "А ты так сможешь?",
    "Запомните этот момент",
    "Тут без слов",
    "Просто шедевр",
    "Когда задонатил всё",
    "Ставлю всё на красное",
    "Бабки = эмоции",
    "Вот так вот живём",
]


# DE (Германия) — мем-фразы на немецком (формат TikTok)
DE_CAPTIONS: list[str] = [
    "Als ich das gesehen habe",
    "POV: du bist live bei Mellstroy",
    "Krass was er macht",
    "Das musst du sehen",
    "Der Typ ist verrückt",
    "Bitte einmal nachmachen",
    "So geht der echte Stream",
    "Wenn dein Kumpel zu viel Wodka hatte",
    "Das war legendär",
    "Wirklich wahr Bro",
    "Der Boss in Action",
    "Wer kennts noch",
    "Das war nicht geplant",
    "Wenn der Stream eskaliert",
    "Reaktion priceless",
    "Der hat einfach gemacht",
    "Glatzkopf in Bestform",
    "Wenn Russen feiern",
    "Sicherheitsabstand bitte",
    "Das ist der echte Mell",
    "Live aus Zypern",
    "Wenn der Bonus kommt",
    "Glücksspiel-Champion",
    "Brabus war nicht genug",
    "Wenn die Nacht erst beginnt",
    "Streamer-Universum",
    "Slawische Energie",
    "Diesen Lacher kennt jeder",
    "Wenn du das auch erkennst",
    "Pure Eskalation",
    "Mellstroy mode aktiviert",
    "Boss Move",
    "Wenn 1Million reinkommt",
    "Das geht nur in Russland",
    "Slawen haben Spaß anders",
    "Der Stream ist ausgerastet",
    "Was zur Hölle",
    "Der hat keine Kontrolle",
    "Lass das mal sacken",
    "Wenn Geld keine Rolle spielt",
]


GEO_CAPTIONS = {
    "RU": RU_CAPTIONS,
    "DE": DE_CAPTIONS,
}


# Хэштеги для описания (правила требуют гео-таргет)
GEO_HASHTAGS = {
    "RU": "#mellstroy #меллстрой #мел #нарезки #прикол #стрим #смех #топ #fyp #рекомендации",
    "DE": "#mellstroy #germany #deutschland #fyp #fürdich #lustig #stream #meme #viral #funny",
}


# Флаги в эмодзи (для добавления в описание)
GEO_FLAG = {
    "RU": "🇷🇺",
    "DE": "🇩🇪",
}
