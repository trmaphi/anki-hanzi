import json
import sqlite3
import zipfile
from pathlib import Path

from class_deck.models import ClassSource
from class_deck.package import MODEL_IDS, build_package, ordered_notes


FIXTURES = Path(__file__).parent / "fixtures"


def test_ordered_notes_groups_categories_and_preserves_source_order():
    raw = json.loads((FIXTURES / "source.json").read_text())
    notes = raw["classes"][1]["notes"]
    raw["classes"][1]["notes"] = [notes[2], notes[1], notes[0]]
    record = ClassSource.from_dict(raw).classes[1]

    ordered = ordered_notes(record)

    assert [note.type for note in ordered] == ["vocabulary", "sentence", "listening"]
    assert [note.chinese for note in ordered] == ["发烧", "你应该吃药。", "你今天觉得怎么样？"]


def test_generated_due_order_is_vocabulary_sentence_listening(tmp_path: Path):
    raw = json.loads((FIXTURES / "source.json").read_text())
    notes = raw["classes"][1]["notes"]
    raw["classes"][1]["notes"] = [notes[2], notes[1], notes[0]]
    source = ClassSource.from_dict(raw)
    package = tmp_path / "ordered.apkg"
    build_package(source, FIXTURES / "media", package)

    with zipfile.ZipFile(package) as archive:
        name = next(item for item in archive.namelist() if item.startswith("collection.anki"))
        collection = tmp_path / name
        collection.write_bytes(archive.read(name))
    with sqlite3.connect(collection) as database:
        decks = json.loads(database.execute("select decks from col").fetchone()[0])
        deck_id = int(next(key for key, value in decks.items() if value["name"] == "Chinese Classes::2026-09-29"))
        model_ids = [row[0] for row in database.execute(
            "select n.mid from cards c join notes n on n.id=c.nid where c.did=? group by n.id order by min(c.due)",
            (deck_id,),
        )]

    assert model_ids == [MODEL_IDS["vocabulary"], MODEL_IDS["sentence"], MODEL_IDS["listening"]]
