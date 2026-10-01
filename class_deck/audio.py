from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable


class AudioError(ValueError):
    """Audio boundaries or clip export are invalid."""


@dataclass(frozen=True)
class AudioSegment:
    segment_id: str
    start_ms: int
    end_ms: int
    chinese: str
    pinyin: str
    confidence: float
    approved: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def validate_segments(segments: Iterable[AudioSegment], *, duration_ms: int | None = None) -> tuple[AudioSegment, ...]:
    ordered = tuple(segments)
    identifiers: set[str] = set()
    previous_end = 0
    for index, segment in enumerate(ordered):
        path = f"segments[{index}]"
        if not segment.segment_id or segment.segment_id in identifiers:
            raise AudioError(f"{path}.segment_id: expected a unique non-empty ID")
        identifiers.add(segment.segment_id)
        if segment.start_ms < 0 or segment.end_ms <= segment.start_ms:
            raise AudioError(f"{path}: expected a positive range")
        if index and segment.start_ms < previous_end:
            raise AudioError(f"{path}: overlaps the previous segment")
        if duration_ms is not None and segment.end_ms > duration_ms:
            raise AudioError(f"{path}.end_ms: exceeds recording duration {duration_ms}")
        if not 0 <= segment.confidence <= 1:
            raise AudioError(f"{path}.confidence: expected a value from 0 to 1")
        previous_end = segment.end_ms
    return ordered


def _subprocess_runner(command: list[str]) -> None:
    subprocess.run(command, check=True, capture_output=True)


def export_segment(
    source: Path,
    segment: AudioSegment,
    target: Path,
    *,
    runner: Callable[[list[str]], None] = _subprocess_runner,
) -> Path:
    source = Path(source)
    target = Path(target)
    validate_segments((segment,))
    if not source.is_file():
        raise AudioError(f"recording not found: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-ss", f"{segment.start_ms / 1000:.3f}",
        "-i", str(source),
        "-t", f"{(segment.end_ms - segment.start_ms) / 1000:.3f}",
        "-vn", "-codec:a", "libmp3lame", "-q:a", "3", str(target),
    ]
    try:
        runner(command)
    except FileNotFoundError as exc:
        raise AudioError("ffmpeg is required to export listening clips") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace").strip() if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
        raise AudioError(f"ffmpeg failed to export {segment.segment_id}: {detail}") from exc
    if not target.is_file() or target.stat().st_size == 0:
        raise AudioError(f"ffmpeg did not create clip: {target}")
    return target


def approved_segments(segments: Iterable[AudioSegment]) -> tuple[AudioSegment, ...]:
    return tuple(segment for segment in validate_segments(segments) if segment.approved)
