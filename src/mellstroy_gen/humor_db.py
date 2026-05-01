"""Локальная база выученных мем-паттернов.

Хранит проанализированные мемы в JSON-файле и агрегирует паттерны
(топ типов юмора, формулы, ключевые элементы).
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "humor_db.json"


@dataclass
class MemeAnalysis:
    humor_type: str = ""
    humor_formula: str = ""
    what_is_funny: str = ""
    key_elements: list[str] = field(default_factory=list)
    caption_style: str = ""
    target_audience: str = ""
    virality_score: int = 0
    similar_ideas: list[str] = field(default_factory=list)


@dataclass
class MemeEntry:
    id: str
    url: str
    source: str = ""
    subtitle_text: str = ""
    description: str = ""
    hashtags: list[str] = field(default_factory=list)
    duration_sec: float = 0.0
    view_count: int = 0
    analyzed_at: str = ""
    analysis: MemeAnalysis = field(default_factory=MemeAnalysis)


class HumorDB:
    """CRUD + аналитика для базы мемов."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _DEFAULT_DB_PATH
        self._memes: list[MemeEntry] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        for m in raw.get("memes", []):
            analysis_raw = m.get("analysis", {})
            analysis = MemeAnalysis(**{
                k: analysis_raw[k]
                for k in MemeAnalysis.__dataclass_fields__
                if k in analysis_raw
            })
            entry = MemeEntry(
                id=m["id"],
                url=m.get("url", ""),
                source=m.get("source", ""),
                subtitle_text=m.get("subtitle_text", ""),
                description=m.get("description", ""),
                hashtags=m.get("hashtags", []),
                duration_sec=m.get("duration_sec", 0.0),
                view_count=m.get("view_count", 0),
                analyzed_at=m.get("analyzed_at", ""),
                analysis=analysis,
            )
            self._memes.append(entry)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "memes": [asdict(m) for m in self._memes],
            "patterns": self.get_patterns(),
        }
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add_meme(self, entry: MemeEntry) -> None:
        existing_ids = {m.id for m in self._memes}
        if entry.id in existing_ids:
            self._memes = [m if m.id != entry.id else entry for m in self._memes]
        else:
            self._memes.append(entry)
        self.save()

    @property
    def memes(self) -> list[MemeEntry]:
        return list(self._memes)

    def __len__(self) -> int:
        return len(self._memes)

    def get_patterns(self) -> dict:
        if not self._memes:
            return {}
        humor_types = Counter(m.analysis.humor_type for m in self._memes if m.analysis.humor_type)
        caption_styles = Counter(m.analysis.caption_style for m in self._memes if m.analysis.caption_style)
        all_elements: list[str] = []
        for m in self._memes:
            all_elements.extend(m.analysis.key_elements)
        elements = Counter(all_elements)
        avg_virality: dict[str, float] = {}
        for ht in humor_types:
            scores = [
                m.analysis.virality_score
                for m in self._memes
                if m.analysis.humor_type == ht and m.analysis.virality_score > 0
            ]
            if scores:
                avg_virality[ht] = round(sum(scores) / len(scores), 1)
        return {
            "total_memes": len(self._memes),
            "top_humor_types": dict(humor_types.most_common(10)),
            "top_caption_styles": dict(caption_styles.most_common(10)),
            "top_elements": dict(elements.most_common(15)),
            "avg_virality_by_type": avg_virality,
        }

    def get_top_formulas(self, n: int = 5) -> list[str]:
        scored = sorted(self._memes, key=lambda m: -m.analysis.virality_score)
        return [m.analysis.humor_formula for m in scored[:n] if m.analysis.humor_formula]

    def get_examples_by_type(self, humor_type: str, n: int = 3) -> list[MemeEntry]:
        matches = [m for m in self._memes if m.analysis.humor_type == humor_type]
        matches.sort(key=lambda m: -m.analysis.virality_score)
        return matches[:n]

    def export_for_prompt(self, max_examples: int = 10) -> str:
        """Формирует текстовую выжимку для вставки в Gemini-промпт."""
        patterns = self.get_patterns()
        if not patterns:
            return "База пуста. Сгенерируй фразы на основе общих трендов TikTok."
        lines = [
            f"Проанализировано мемов: {patterns['total_memes']}",
            f"Топ типов юмора: {patterns['top_humor_types']}",
            f"Топ стилей фраз: {patterns['top_caption_styles']}",
            f"Ключевые элементы: {patterns['top_elements']}",
            f"Средний вирусный балл по типу: {patterns['avg_virality_by_type']}",
            "",
            "Топ формулы юмора:",
        ]
        for f in self.get_top_formulas(5):
            lines.append(f"  - {f}")
        lines.append("")
        lines.append("Примеры залетевших фраз:")
        top = sorted(self._memes, key=lambda m: -m.analysis.virality_score)[:max_examples]
        for m in top:
            views = f"{m.view_count:,}" if m.view_count else "?"
            lines.append(f'  - "{m.subtitle_text}" ({views} просм, тип: {m.analysis.humor_type})')
        return "\n".join(lines)
