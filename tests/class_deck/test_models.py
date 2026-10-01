import pytest

from class_deck.models import ClassSource, SourceValidationError


def reviewed_source():
    return {
        "version": 1,
        "deck_name": "Chinese Classes",
        "classes": [
            {
                "date": "2026-09-22",
                "folder_id": "folder-22",
                "approved": True,
                "source_files": [
                    {
                        "id": "image-1",
                        "name": "lesson.jpg",
                        "mime_type": "image/jpeg",
                        "modified_time": "2026-09-23T03:22:24.450Z",
                    }
                ],
                "notes": [
                    {
                        "type": "vocabulary",
                        "chinese": "感冒",
                        "traditional": "感冒",
                        "pinyin": "gǎnmào",
                        "meaning": "common cold",
                        "example": "我感冒了。",
                        "example_translation": "I caught a cold.",
                        "source_ref": "image-1",
                    },
                    {
                        "type": "sentence",
                        "chinese": "你觉得这个菜怎么样？",
                        "pinyin": "Nǐ juéde zhège cài zěnmeyàng?",
                        "meaning": "What do you think of this dish?",
                        "answer": "太辣了。",
                        "source_ref": "image-1",
                    },
                ],
                "issues": {"unmatched_audio": ["audio-9"]},
            }
        ],
    }


def test_valid_reviewed_source_round_trip():
    raw = reviewed_source()
    source = ClassSource.from_dict(raw)

    assert source.deck_name == "Chinese Classes"
    assert source.classes[0].date == "2026-09-22"
    assert source.classes[0].notes[0].date == "2026-09-22"
    assert source.to_dict() == raw


def test_invalid_date_reports_json_path():
    raw = reviewed_source()
    raw["classes"][0]["date"] = "22/09/2026"

    with pytest.raises(SourceValidationError, match=r"classes\[0\]\.date"):
        ClassSource.from_dict(raw)


def test_missing_primary_chinese_is_rejected():
    raw = reviewed_source()
    del raw["classes"][0]["notes"][0]["chinese"]

    with pytest.raises(SourceValidationError, match=r"classes\[0\]\.notes\[0\]\.chinese"):
        ClassSource.from_dict(raw)


def test_version_two_requires_persistent_item_ids():
    raw = reviewed_source()
    raw["version"] = 2

    with pytest.raises(SourceValidationError, match=r"classes\[0\]\.notes\[0\]\.item_id"):
        ClassSource.from_dict(raw)


def test_version_two_rejects_duplicate_item_ids():
    raw = reviewed_source()
    raw["version"] = 2
    for note in raw["classes"][0]["notes"]:
        note["item_id"] = "same-item"

    with pytest.raises(SourceValidationError, match=r"duplicate item_id"):
        ClassSource.from_dict(raw)


def test_listening_requires_unique_recording_segment_identity():
    raw = reviewed_source()
    raw["version"] = 2
    raw["classes"][0]["notes"] = [
        {"type": "listening", "chinese": "你好", "recording_id": "rec-1", "segment_id": "seg-1"},
        {"type": "listening", "chinese": "你好吗", "recording_id": "rec-1", "segment_id": "seg-1"},
    ]

    with pytest.raises(SourceValidationError, match=r"duplicate recording_id/segment_id"):
        ClassSource.from_dict(raw)
