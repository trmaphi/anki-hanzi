from dataclasses import replace
from pathlib import Path

import pytest

from class_deck.audio import AudioError, AudioSegment, approved_segments, export_segment, validate_segments


def segment(**changes):
    value = AudioSegment(
        segment_id="recording-1:segment:0001",
        start_ms=1000,
        end_ms=2500,
        chinese="你好。",
        pinyin="nǐ hǎo 。",
        confidence=0.92,
        approved=False,
    )
    return replace(value, **changes)


def test_rejects_invalid_and_overlapping_boundaries():
    with pytest.raises(AudioError, match="positive range"):
        validate_segments((segment(end_ms=1000),))
    with pytest.raises(AudioError, match="overlaps"):
        validate_segments((segment(), segment(segment_id="recording-1:segment:0002", start_ms=2000, end_ms=3000)))


def test_corrections_do_not_change_segment_identity():
    original = segment()
    corrected = replace(original, start_ms=900, end_ms=2600, chinese="您好。", pinyin="nín hǎo 。")

    assert corrected.segment_id == original.segment_id


def test_export_segment_invokes_ffmpeg_with_validated_range(tmp_path: Path):
    source = tmp_path / "source.mp3"
    source.write_bytes(b"audio")
    calls = []

    def runner(command):
        calls.append(command)
        Path(command[-1]).write_bytes(b"clip")

    target = export_segment(source, segment(), tmp_path / "clip.mp3", runner=runner)

    assert target.read_bytes() == b"clip"
    assert calls[0][0] == "ffmpeg"
    assert calls[0][calls[0].index("-ss") + 1] == "1.000"
    assert calls[0][calls[0].index("-t") + 1] == "1.500"


def test_missing_ffmpeg_is_reported(tmp_path: Path):
    source = tmp_path / "source.mp3"
    source.write_bytes(b"audio")

    def missing(_command):
        raise FileNotFoundError("ffmpeg")

    with pytest.raises(AudioError, match="ffmpeg is required"):
        export_segment(source, segment(), tmp_path / "clip.mp3", runner=missing)


def test_only_explicitly_approved_segments_are_packaging_candidates():
    segments = (segment(), segment(segment_id="recording-1:segment:0002", start_ms=2600, end_ms=3000, approved=True))

    assert approved_segments(segments) == (segments[1],)
