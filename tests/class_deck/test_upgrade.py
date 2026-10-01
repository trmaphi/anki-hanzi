import json
import shutil
import sqlite3
import zipfile
from pathlib import Path

import pytest

from class_deck.compatibility import CompatibilityError, compare_collections
from class_deck.models import ClassSource
from class_deck.package import build_package


ROOT = Path(__file__).parents[2]
PRE_UNIFIED = ROOT / "output/class-decks/Chinese-Classes.pre-unified.apkg"
BASELINE = PRE_UNIFIED if PRE_UNIFIED.is_file() else ROOT / "output/class-decks/Chinese-Classes.apkg"
SOURCE = ROOT / ".class-deck/current/reviewed-source.json"
MEDIA = ROOT / ".class-deck/current/media"


def extract_collection(package: Path, target: Path) -> Path:
    with zipfile.ZipFile(package) as archive:
        name = next(item for item in archive.namelist() if item.startswith("collection.anki"))
        target.write_bytes(archive.read(name))
    return target


@pytest.fixture(scope="module")
def upgrade_collections(tmp_path_factory):
    if not BASELINE.is_file() or not SOURCE.is_file():
        pytest.skip("private released upgrade fixtures are unavailable")
    directory = tmp_path_factory.mktemp("upgrade")
    before = extract_collection(BASELINE, directory / "before.anki2")
    source = ClassSource.from_dict(json.loads(SOURCE.read_text(encoding="utf-8")))
    package = directory / "unified.apkg"
    report = build_package(source, MEDIA, package)
    generated = extract_collection(package, directory / "generated.anki2")
    after = directory / "after.anki2"
    shutil.copyfile(generated, after)

    with sqlite3.connect(before) as old:
        old.execute(
            "update cards set due=(id % 997)+10, ivl=(id % 83)+1, factor=2350, "
            "reps=(id % 29)+1, lapses=(id % 5)"
        )
        old.commit()
        schedules = old.execute(
            "select n.guid,c.ord,c.due,c.ivl,c.factor,c.reps,c.lapses "
            "from cards c join notes n on n.id=c.nid"
        ).fetchall()
    with sqlite3.connect(after) as new:
        for guid, ordinal, due, interval, factor, reps, lapses in schedules:
            new.execute(
                "update cards set due=?,ivl=?,factor=?,reps=?,lapses=? where id=("
                "select c.id from cards c join notes n on n.id=c.nid where n.guid=? and c.ord=?)",
                (due, interval, factor, reps, lapses, guid, ordinal),
            )
        new.commit()
    return before, after, report


def test_seeded_upgrade_preserves_all_released_progress(upgrade_collections):
    before, after, report = upgrade_collections
    source = ClassSource.from_dict(json.loads(SOURCE.read_text(encoding="utf-8")))
    listening_notes = sum(
        note.type == "listening"
        for record in source.classes
        for note in record.notes
    )

    result = compare_collections(before, after)

    assert result.preserved_notes == 320
    assert result.preserved_cards == 581
    assert result.new_notes == listening_notes
    assert result.new_writing_cards == 261
    assert result.new_cards == result.new_writing_cards + listening_notes
    assert report.notes == 320 + listening_notes
    assert report.cards == 842 + listening_notes


def test_second_identical_import_has_zero_duplicates(upgrade_collections):
    _, after, _ = upgrade_collections

    result = compare_collections(after, after)

    assert result.new_notes == result.new_cards == 0
    assert result.removed_notes == result.removed_cards == 0


def test_scheduling_regression_is_blocked(upgrade_collections, tmp_path):
    before, after, _ = upgrade_collections
    broken = tmp_path / "broken.anki2"
    shutil.copyfile(after, broken)
    with sqlite3.connect(broken) as database:
        database.execute(
            "update cards set reps=reps+1 where id=(select min(c.id) from cards c join notes n on n.id=c.nid where c.ord<3)"
        )
        database.commit()

    with pytest.raises(CompatibilityError, match="scheduling changed"):
        compare_collections(before, broken)
