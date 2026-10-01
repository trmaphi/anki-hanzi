from pathlib import Path

import pytest

from class_deck.transcribe import AsrSegment, TranscriptionError, transcribe_recording


class FakeTranscriber:
    def transcribe(self, source: Path, *, model_name: str, language: str):
        assert model_name == "small"
        assert language == "zh"
        return (
            AsrSegment(0, 2000, "你好。你好吗？", 0.9),
            AsrSegment(2100, 3100, "我很好。", 0.8),
        )


def test_transcribes_and_splits_sentences_with_deterministic_ids(tmp_path: Path):
    source = tmp_path / "class.mp3"
    source.write_bytes(b"audio")

    segments = transcribe_recording(source, "recording-1", "small", FakeTranscriber())

    assert [item.segment_id for item in segments] == [
        "recording-1:segment:0001", "recording-1:segment:0002", "recording-1:segment:0003"
    ]
    assert [item.chinese for item in segments] == ["你好。", "你好吗？", "我很好。"]
    assert segments[0].pinyin == "nǐ hǎo 。"
    assert all(not item.approved for item in segments)
    assert segments[0].end_ms == segments[1].start_ms


def test_missing_model_error_has_actionable_context(tmp_path: Path):
    class Broken:
        def transcribe(self, source: Path, *, model_name: str, language: str):
            raise OSError("model unavailable")

    source = tmp_path / "class.mp3"
    source.write_bytes(b"audio")
    with pytest.raises(TranscriptionError, match="model 'missing'.*model unavailable"):
        transcribe_recording(source, "recording-1", "missing", Broken())


def test_missing_recording_is_rejected(tmp_path: Path):
    with pytest.raises(TranscriptionError, match="recording not found"):
        transcribe_recording(tmp_path / "missing.mp3", "recording-1", "small", FakeTranscriber())
