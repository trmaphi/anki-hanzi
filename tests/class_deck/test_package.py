import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from class_deck.models import ClassSource
from class_deck.package import MODEL_IDS, build_package


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture()
def built(tmp_path):
    source = ClassSource.from_dict(json.loads((FIXTURES / "source.json").read_text()))
    output = tmp_path / "Chinese-Classes.apkg"
    report = build_package(source, FIXTURES / "media", output)
    return output, report


def collection_rows(apkg, tmp_path):
    with zipfile.ZipFile(apkg) as archive:
        collection_name = next(name for name in archive.namelist() if name.startswith("collection.anki"))
        collection = tmp_path / collection_name
        collection.write_bytes(archive.read(collection_name))
        media = json.loads(archive.read("media"))
    database = sqlite3.connect(collection)
    return database, media


def test_builds_parent_and_dated_subdecks(built, tmp_path):
    output, report = built
    database, _ = collection_rows(output, tmp_path)
    decks = json.loads(database.execute("select decks from col").fetchone()[0])
    names = {value["name"] for value in decks.values()}

    assert output.exists()
    assert names - {"Default"} == {
        "Chinese Classes",
        "Chinese Classes::2026-09-22",
        "Chinese Classes::2026-09-29",
    }
    assert report.decks == 3


def test_vocabulary_has_recognition_production_and_conditional_listening(built, tmp_path):
    output, report = built
    database, _ = collection_rows(output, tmp_path)
    vocabulary_cards = database.execute(
        "select n.flds, c.ord from cards c join notes n on n.id=c.nid where n.mid=? order by n.flds, c.ord",
        (MODEL_IDS["vocabulary"],),
    ).fetchall()

    by_chinese = {}
    for fields, ordinal in vocabulary_cards:
        by_chinese.setdefault(fields.split("\x1f")[0], []).append(ordinal)
    assert by_chinese["感冒"] == [0, 1, 2]
    assert by_chinese["发烧"] == [0, 1]
    assert report.cards == 9


def test_sentence_and_listening_models_have_fixed_ordinals(built, tmp_path):
    output, _ = built
    database, _ = collection_rows(output, tmp_path)
    models = json.loads(database.execute("select models from col").fetchone()[0])

    assert MODEL_IDS == {
        "vocabulary": 1956836792,
        "sentence": 1740209695,
        "listening": 1680100180,
    }
    sentence = models[str(MODEL_IDS["sentence"])]
    listening = models[str(MODEL_IDS["listening"])]
    assert [(item["name"], item["ord"]) for item in sentence["tmpls"]] == [
        ("Produce", 0),
        ("Listen", 1),
    ]
    assert [(item["name"], item["ord"]) for item in listening["tmpls"]] == [("Listen", 0)]


def test_ambiguous_audio_is_warning_not_card(built, tmp_path):
    output, report = built
    database, _ = collection_rows(output, tmp_path)
    listening_notes = database.execute(
        "select count(*) from notes where mid=?", (MODEL_IDS["listening"],)
    ).fetchone()[0]

    assert listening_notes == 1
    assert report.notes == 5
    assert any("ambiguous" in warning and "2026-09-22" in warning for warning in report.warnings)


def test_media_names_resolve_without_collisions(built, tmp_path):
    output, report = built
    database, media_map = collection_rows(output, tmp_path)
    with zipfile.ZipFile(output) as archive:
        archived_names = set(archive.namelist())
        mapped_names = set(media_map.values())
        assert set(media_map) <= archived_names

    fields = [row[0] for row in database.execute("select flds from notes")]
    referenced = {
        name
        for field_blob in fields
        for name in mapped_names
        if name in field_blob
    }
    image_names = {name for name in mapped_names if name.endswith(".jpg")}
    assert len(image_names) == 2
    assert len(report.media) == 5
    assert referenced == mapped_names


def test_collection_database_round_trip(built, tmp_path):
    output, report = built
    database, _ = collection_rows(output, tmp_path)

    assert database.execute("pragma integrity_check").fetchone()[0] == "ok"
    assert database.execute("select count(*) from notes").fetchone()[0] == report.notes == 5
    assert database.execute("select count(*) from cards").fetchone()[0] == report.cards == 9
    assert database.execute("select count(distinct guid) from notes").fetchone()[0] == 5
    tags = " ".join(row[0] for row in database.execute("select tags from notes"))
    assert "Class::2026-09-22" in tags
    assert "Class::2026-09-29" in tags
    assert "Type::Vocabulary" in tags
