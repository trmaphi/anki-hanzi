import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path

import pytest

from class_deck.identity import note_guid
from class_deck.manifest import migrate_source_identities
from class_deck.models import ClassSource


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / ".class-deck/current/reviewed-source.json"
PRE_UNIFIED = ROOT / "output/class-decks/Chinese-Classes.pre-unified.apkg"
PACKAGE = PRE_UNIFIED if PRE_UNIFIED.is_file() else ROOT / "output/class-decks/Chinese-Classes.apkg"


def test_released_package_migration_recovers_all_320_guids():
    if not SOURCE.is_file() or not PACKAGE.is_file():
        pytest.skip("private released-package migration fixtures are not available")

    legacy = ClassSource.from_dict(json.loads(SOURCE.read_text(encoding="utf-8")))
    migrated = migrate_source_identities(legacy)
    computed = {note_guid(note) for record in migrated.classes for note in record.notes}
    computed_released = {
        note_guid(note)
        for record in migrated.classes
        for note in record.notes
        if note.type != "listening"
    }

    with zipfile.ZipFile(PACKAGE) as archive, tempfile.TemporaryDirectory() as directory:
        collection_name = next(name for name in archive.namelist() if name.startswith("collection.anki"))
        collection = Path(directory) / collection_name
        collection.write_bytes(archive.read(collection_name))
        with sqlite3.connect(collection) as database:
            released = {row[0] for row in database.execute("select guid from notes")}
            cards = database.execute("select count(*) from cards").fetchone()[0]

    assert len(released) == 320
    assert cards == 581
    assert len(computed_released) == 320
    assert computed_released == released
    assert released <= computed
