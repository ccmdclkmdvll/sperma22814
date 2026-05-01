"""Авто-нарезка стрима Меллстроя на короткие моменты.

Стратегия:
1. Whisper транскрибирует речь со штампами.
2. Детектим пики громкости (RMS) — обычно крик/смех Мела.
3. Возвращаем топ-N сегментов длиной ~15-30 секунд вокруг пиков, проверяем что
   в сегменте есть речь (transcript не пустой).

Использование:
    python -m mellstroy_gen.auto_cut <stream.mp4> --out assets/chromakey --top 20
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Segment:
    start: float
    end: float
    text: str
    score: float


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def extract_loudness(media: Path, hop: float = 0.5) -> tuple[np.ndarray, np.ndarray]:
    """Возвращает (timestamps, RMS) — громкость каждые `hop` секунд."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav = Path(tmp.name)
    try:
        _run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(media),
            "-ac", "1", "-ar", "16000",
            str(wav),
        ])
        # читаем PCM
        import wave
        with wave.open(str(wav), "rb") as wf:
            n = wf.getnframes()
            rate = wf.getframerate()
            data = np.frombuffer(wf.readframes(n), dtype=np.int16).astype(np.float32)
        win = int(hop * rate)
        # RMS по окнам
        usable = (len(data) // win) * win
        if usable == 0:
            return np.array([0.0]), np.array([0.0])
        chunks = data[:usable].reshape(-1, win)
        rms = np.sqrt(np.mean(chunks ** 2, axis=1))
        ts = np.arange(len(rms)) * hop
        return ts, rms
    finally:
        wav.unlink(missing_ok=True)


def transcribe(media: Path, model_size: str = "small") -> list[dict]:
    """Whisper-транскрипция с таймштампами. Возвращает список сегментов."""
    try:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel(model_size, compute_type="auto")
        segs, _ = model.transcribe(str(media), language="ru", vad_filter=True)
        return [{"start": s.start, "end": s.end, "text": s.text} for s in segs]
    except ImportError:
        import whisper  # type: ignore
        model = whisper.load_model(model_size)
        result = model.transcribe(str(media), language="ru")
        return [{"start": s["start"], "end": s["end"], "text": s["text"]}
                for s in result.get("segments", [])]


def find_top_moments(
    media: Path,
    top: int = 20,
    target_dur: float = 22.0,
    min_gap: float = 60.0,
) -> list[Segment]:
    """Ищет топ моментов: пики громкости + наличие речи."""
    print(f"[auto_cut] анализ громкости {media} ...")
    ts, rms = extract_loudness(media)
    if len(rms) < 4:
        return []

    print(f"[auto_cut] Whisper транскрипция {media} ...")
    transcript = transcribe(media)

    # нормализуем громкость
    rms_norm = (rms - rms.min()) / (rms.max() - rms.min() + 1e-9)

    # для каждого whisper-сегмента вычисляем средний RMS внутри окна target_dur
    candidates: list[Segment] = []
    for seg in transcript:
        text = seg["text"].strip()
        if len(text) < 3:
            continue
        center = (seg["start"] + seg["end"]) / 2
        start = max(0.0, center - target_dur / 2)
        end = start + target_dur
        i0 = int(start / 0.5)
        i1 = int(end / 0.5)
        if i1 <= i0 or i0 >= len(rms_norm):
            continue
        score = float(rms_norm[i0:i1].mean()) + 0.2 * (len(text) / 80)
        # бонус за восклицание/мат
        if any(ch in text for ch in "!?") or any(
            w in text.lower() for w in ["бл", "сук", "ах", "ого", "е*", "пизд", "хуй"]
        ):
            score += 0.3
        candidates.append(Segment(start, end, text, score))

    # сортируем по score, пропускаем слишком близкие
    candidates.sort(key=lambda s: -s.score)
    chosen: list[Segment] = []
    for c in candidates:
        if all(abs(c.start - x.start) > min_gap for x in chosen):
            chosen.append(c)
            if len(chosen) >= top:
                break
    return chosen


def cut_segments(
    media: Path,
    segments: list[Segment],
    out_dir: Path,
    name_prefix: str = "auto",
) -> list[Path]:
    """Режет media на куски FFmpeg-ом без перекодирования (быстро)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for i, seg in enumerate(segments, 1):
        out = out_dir / f"{name_prefix}_{i:03d}.mp4"
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", f"{seg.start:.2f}",
            "-i", str(media),
            "-t", f"{seg.end - seg.start:.2f}",
            "-c", "copy",
            str(out),
        ]
        rc = subprocess.call(cmd)
        if rc == 0 and out.exists():
            saved.append(out)
            print(f"[cut ] {out.name} ({seg.start:.1f}-{seg.end:.1f}) {seg.text[:60]}")
    return saved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", help="входной видео-файл (mp4)")
    parser.add_argument("--out", default="assets/stream_clips", help="папка для нарезок")
    parser.add_argument("--top", type=int, default=20, help="сколько лучших моментов взять")
    parser.add_argument("--dur", type=float, default=22.0, help="длительность каждой нарезки, сек")
    parser.add_argument("--manifest", action="store_true", help="сохранить json с описанием")
    args = parser.parse_args(argv)

    media = Path(args.media)
    if not media.exists():
        print(f"Файл не найден: {media}", file=sys.stderr)
        return 2

    segs = find_top_moments(media, top=args.top, target_dur=args.dur)
    if not segs:
        print("Не нашёл подходящих моментов.", file=sys.stderr)
        return 1
    print(f"[auto_cut] выбрано {len(segs)} лучших моментов")
    out = Path(args.out)
    saved = cut_segments(media, segs, out, name_prefix=media.stem)
    if args.manifest:
        manifest = out / f"{media.stem}_manifest.json"
        manifest.write_text(json.dumps(
            [{"file": s.name, **vars(seg)} for s, seg in zip(saved, segs)],
            ensure_ascii=False, indent=2,
        ))
        print(f"[auto_cut] manifest -> {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
