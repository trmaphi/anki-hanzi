from dataclasses import replace

from class_deck.identity import (
    class_deck_id,
    class_deck_name,
    media_name,
    note_guid,
    note_key,
)
from class_deck.models import ClassSource


def reviewed_source():
    return {
        "version": 1,
        "deck_name": "Chinese Classes",
        "classes": [
            {
                "date": "2026-09-22",
                "folder_id": "folder-22",
                "approved": True,
                "source_files": [],
                "notes": [
                    {
                        "type": "vocabulary",
                        "chinese": "感冒",
                        "traditional": "感冒",
                        "pinyin": "gǎnmào",
                        "meaning": "common cold",
                        "example": "我感冒了。",
                        "example_translation": "I caught a cold.",
                    }
                ],
                "issues": {},
            }
        ],
    }


def vocabulary_note():
    return ClassSource.from_dict(reviewed_source()).classes[0].notes[0]


def test_mutable_fields_do_not_change_guid():
    note = vocabulary_note()
    corrected = replace(
        note,
        pinyin="gǎn mào",
        meaning="to catch a cold",
        example="他感冒了。",
        image="replacement image.jpg",
        audio="replacement audio.mp3",
    )

    assert note_key(note) == "2026-09-22:vocabulary:感冒"
    assert note_guid(note) == note_guid(corrected)
    assert len(note_guid(note)) == 14


def test_date_and_note_type_change_guid():
    note = vocabulary_note()

    assert note_guid(note) != note_guid(replace(note, date="2026-09-23"))
    assert note_guid(note) != note_guid(replace(note, type="sentence"))


def test_version_two_identity_is_independent_of_mutable_chinese():
    raw = reviewed_source()
    raw["version"] = 2
    raw["classes"][0]["notes"][0]["item_id"] = "folder-22:item-001"
    note = ClassSource.from_dict(raw).classes[0].notes[0]

    assert note_key(note) == "2026-09-22:vocabulary:folder-22:item-001"
    assert note_guid(note) == note_guid(replace(note, chinese="重感冒"))


def test_identity_seed_reproduces_legacy_guid_after_correction():
    legacy = vocabulary_note()
    migrated = replace(
        legacy,
        item_id="folder-22:item-001",
        identity_seed=note_key(legacy),
        chinese="感冒了",
    )

    assert note_key(migrated) == "2026-09-22:vocabulary:感冒"
    assert note_guid(migrated) == note_guid(legacy)


def test_media_names_are_unicode_safe_and_collision_resistant():
    first = media_name("2026-09-22:vocabulary:感冒", "image", "Bài học 1.JPG")
    second = media_name("2026-09-22:vocabulary:发烧", "image", "Bài học 1.JPG")

    assert first.endswith(".jpg")
    assert first.isascii()
    assert " " not in first
    assert first != second
    assert first == media_name("2026-09-22:vocabulary:感冒", "image", "Bài học 1.JPG")

    name = class_deck_name("2026-09-22")
    assert name == "Chinese Classes::2026-09-22"
    assert 2**30 <= class_deck_id(name) < 2**31
    assert class_deck_id(name) == class_deck_id(name)
