from dataclasses import replace
from pathlib import Path

from class_deck.enrichment import EnrichmentAssets, LexiconEntry, enrich_note
from class_deck.models import ListeningNote, SentenceNote, VocabularyNote


def assets():
    return EnrichmentAssets(
        entries={
            "感冒": LexiconEntry(
                traditional="感冒",
                part_of_speech="verb",
                definitions="to catch a cold; common cold",
                breakdown="感: feeling; 冒: risk",
                radical="心",
                hsk_level="HSK 3",
                frequency="2814",
            )
        }
    )


def vocabulary(**changes):
    note = VocabularyNote(date="2026-09-22", type="vocabulary", chinese="感冒", item_id="item-1")
    return replace(note, **changes)


def test_preserves_every_reviewed_value():
    reviewed = vocabulary(
        traditional="老師傳統", pinyin="teacher pinyin", zhuyin="teacher zhuyin",
        part_of_speech="teacher POS", definitions="teacher definition",
        breakdown="teacher breakdown", radical="teacher radical",
        hsk_level="teacher HSK", frequency="teacher frequency",
    )

    result = enrich_note(reviewed, assets())

    assert result.note == reviewed
    assert result.autofilled_fields == ()


def test_fills_only_blank_supported_fields():
    result = enrich_note(vocabulary(pinyin="reviewed pinyin"), assets())

    assert result.note.pinyin == "reviewed pinyin"
    assert result.note.traditional == "感冒"
    assert result.note.part_of_speech == "verb"
    assert result.note.definitions == "to catch a cold; common cold"
    assert result.note.radical == "心"
    assert set(result.autofilled_fields) >= {"traditional", "part_of_speech", "definitions", "radical"}


def test_generates_pinyin_and_zhuyin():
    result = enrich_note(vocabulary(), assets())

    assert result.note.pinyin == "gǎn mào"
    assert result.note.zhuyin == "ㄍㄢˇ ㄇㄠˋ"
    assert {"pinyin", "zhuyin"} <= set(result.autofilled_fields)


def test_records_autofilled_and_unresolved_fields():
    result = enrich_note(vocabulary(chinese="不存在"), EnrichmentAssets(entries={}))

    assert result.autofilled_fields == ("pinyin", "zhuyin")
    assert result.unresolved_fields == (
        "traditional", "part_of_speech", "definitions", "breakdown", "radical", "hsk_level", "frequency"
    )


def test_sentence_and_listening_scope_excludes_vocabulary_metadata():
    sentence = SentenceNote(date="2026-09-22", type="sentence", chinese="我感冒了", item_id="sentence-1")
    listening = ListeningNote(
        date="2026-09-22", type="listening", chinese="我感冒了",
        recording_id="recording-1", segment_id="segment-1",
    )

    sentence_result = enrich_note(sentence, assets())
    listening_result = enrich_note(listening, assets())

    assert sentence_result.note.pinyin == "wǒ gǎn mào le"
    assert listening_result.note.pinyin == "wǒ gǎn mào le"
    assert sentence_result.autofilled_fields == ("pinyin",)
    assert listening_result.autofilled_fields == ("pinyin",)
    assert sentence_result.unresolved_fields == listening_result.unresolved_fields == ()


def test_loads_committed_cedict_archive():
    archive = Path(__file__).parents[2] / "static/data/cedict.db.zip"

    entry = EnrichmentAssets.from_cedict_archive(archive).entries["感冒"]

    assert entry.traditional == "感冒"
    assert entry.definitions
    assert entry.frequency.isdigit()
