from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from pypinyin import Style, lazy_pinyin

from .audio import AudioSegment, validate_segments


SENTENCE = re.compile(r"[^。！？!?；;]+[。！？!?；;]?", re.UNICODE)


class TranscriptionError(RuntimeError):
    """A recording could not be transcribed into reviewable segments."""


@dataclass(frozen=True)
class AsrSegment:
    start_ms: int
    end_ms: int
    text: str
    confidence: float


class Transcriber(Protocol):
    def transcribe(self, source: Path, *, model_name: str, language: str) -> Iterable[AsrSegment]: ...


class FasterWhisperTranscriber:
    def transcribe(self, source: Path, *, model_name: str, language: str) -> tuple[AsrSegment, ...]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise TranscriptionError("faster-whisper is not installed") from exc
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        raw_segments, _ = model.transcribe(str(source), language=language, beam_size=5, vad_filter=True)
        result = []
        for segment in raw_segments:
            confidence = max(0.0, min(1.0, math.exp(float(segment.avg_logprob))))
            result.append(
                AsrSegment(
                    start_ms=round(float(segment.start) * 1000),
                    end_ms=round(float(segment.end) * 1000),
                    text=str(segment.text).strip(),
                    confidence=confidence,
                )
            )
        return tuple(result)


def _pinyin(text: str) -> str:
    return " ".join(lazy_pinyin(text, style=Style.TONE, neutral_tone_with_five=False)).strip()


def _sentences(text: str) -> tuple[str, ...]:
    return tuple(match.group(0).strip() for match in SENTENCE.finditer(text.strip()) if match.group(0).strip())


def transcribe_recording(
    source: Path,
    recording_id: str,
    model_name: str,
    transcriber: Transcriber,
) -> tuple[AudioSegment, ...]:
    source = Path(source)
    if not source.is_file():
        raise TranscriptionError(f"recording not found: {source}")
    if not recording_id.strip():
        raise TranscriptionError("recording_id: expected non-empty text")
    try:
        raw_segments = tuple(transcriber.transcribe(source, model_name=model_name, language="zh"))
    except TranscriptionError:
        raise
    except Exception as exc:
        raise TranscriptionError(f"model {model_name!r} failed for {source.name}: {exc}") from exc
    output: list[AudioSegment] = []
    ordinal = 0
    for raw_index, raw in enumerate(raw_segments):
        if raw.end_ms <= raw.start_ms:
            raise TranscriptionError(f"ASR segment {raw_index}: invalid time range")
        sentences = _sentences(raw.text)
        if not sentences:
            continue
        weights = [max(1, len(sentence)) for sentence in sentences]
        total = sum(weights)
        cursor = raw.start_ms
        consumed = 0
        for index, (sentence, weight) in enumerate(zip(sentences, weights)):
            ordinal += 1
            consumed += weight
            end = raw.end_ms if index == len(sentences) - 1 else raw.start_ms + round((raw.end_ms - raw.start_ms) * consumed / total)
            output.append(
                AudioSegment(
                    segment_id=f"{recording_id}:segment:{ordinal:04d}",
                    start_ms=cursor,
                    end_ms=end,
                    chinese=sentence,
                    pinyin=_pinyin(sentence),
                    confidence=max(0.0, min(1.0, raw.confidence)),
                    approved=False,
                )
            )
            cursor = end
    return validate_segments(output)
