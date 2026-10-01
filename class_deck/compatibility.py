from __future__ import annotations

import json
import sqlite3
import tempfile
import zipfile
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from .templates import MODEL_IDS


class CompatibilityError(ValueError):
    """A generated collection would reset or remove released Anki progress."""


@dataclass(frozen=True)
class CompatibilityReport:
    preserved_notes: int
    preserved_cards: int
    new_notes: int
    new_cards: int
    new_writing_cards: int
    removed_notes: int
    removed_cards: int


@contextmanager
def _database_path(path: Path) -> Iterator[Path]:
    path = Path(path)
    if path.suffix != ".apkg":
        yield path
        return
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory(prefix="class-deck-compat-") as directory:
        name = next(item for item in archive.namelist() if item.startswith("collection.anki"))
        extracted = Path(directory) / name
        extracted.write_bytes(archive.read(name))
        yield extracted


def _snapshot(path: Path) -> dict:
    with sqlite3.connect(path) as database:
        models = json.loads(database.execute("select models from col").fetchone()[0])
        decks = json.loads(database.execute("select decks from col").fetchone()[0])
        notes = {guid: mid for guid, mid in database.execute("select guid,mid from notes")}
        cards = {
            (guid, ordinal): (mid, due, interval, factor, reps, lapses)
            for guid, ordinal, mid, due, interval, factor, reps, lapses in database.execute(
                "select n.guid,c.ord,n.mid,c.due,c.ivl,c.factor,c.reps,c.lapses "
                "from cards c join notes n on n.id=c.nid"
            )
        }
    return {"models": models, "decks": decks, "notes": notes, "cards": cards}


def compare_collections(
    before: Path,
    after: Path,
    *,
    require_schedule: bool = True,
) -> CompatibilityReport:
    with ExitStack() as stack:
        before_path = stack.enter_context(_database_path(before))
        after_path = stack.enter_context(_database_path(after))
        old = _snapshot(before_path)
        new = _snapshot(after_path)

    for model_id, old_model in old["models"].items():
        new_model = new["models"].get(model_id)
        if new_model is None:
            raise CompatibilityError(f"released model removed: {model_id}")
        old_fields = [field["name"] for field in old_model["flds"]]
        new_fields = [field["name"] for field in new_model["flds"]]
        if new_fields[: len(old_fields)] != old_fields:
            raise CompatibilityError(f"released field ordinals changed for model {model_id}")
        old_templates = [(item["ord"], item["name"]) for item in old_model["tmpls"]]
        new_templates = [(item["ord"], item["name"]) for item in new_model["tmpls"]]
        if new_templates[: len(old_templates)] != old_templates:
            raise CompatibilityError(f"released template ordinals changed for model {model_id}")

    old_decks = {value["name"]: int(key) for key, value in old["decks"].items() if value["name"] != "Default"}
    new_decks = {value["name"]: int(key) for key, value in new["decks"].items() if value["name"] != "Default"}
    for name, deck_id in old_decks.items():
        if new_decks.get(name) != deck_id:
            raise CompatibilityError(f"released deck ID changed or disappeared: {name}")

    removed_notes = set(old["notes"]) - set(new["notes"])
    if removed_notes:
        raise CompatibilityError(f"released notes removed: {len(removed_notes)}")
    for guid, model_id in old["notes"].items():
        if new["notes"][guid] != model_id:
            raise CompatibilityError(f"released note model changed: {guid}")

    removed_cards = set(old["cards"]) - set(new["cards"])
    if removed_cards:
        raise CompatibilityError(f"released cards removed: {len(removed_cards)}")
    for key, old_card in old["cards"].items():
        new_card = new["cards"][key]
        if new_card[0] != old_card[0]:
            raise CompatibilityError(f"released card model changed: {key}")
        if require_schedule and new_card[1:] != old_card[1:]:
            raise CompatibilityError(f"released card scheduling changed: {key}")

    added_notes = set(new["notes"]) - set(old["notes"])
    added_cards = set(new["cards"]) - set(old["cards"])
    writing = {
        key for key in added_cards
        if key[1] == 3 and new["cards"][key][0] == MODEL_IDS["vocabulary"]
    }
    unexpected_existing_note_cards = {
        key for key in added_cards if key[0] in old["notes"] and key not in writing
    }
    if unexpected_existing_note_cards:
        raise CompatibilityError(
            f"unexpected cards added to released notes: {sorted(unexpected_existing_note_cards)[:3]}"
        )
    for key in writing:
        _, due, interval, factor, reps, lapses = new["cards"][key]
        if interval or factor or reps or lapses:
            raise CompatibilityError(f"new Writing card is not New: {key}")

    return CompatibilityReport(
        preserved_notes=len(old["notes"]),
        preserved_cards=len(old["cards"]),
        new_notes=len(added_notes),
        new_cards=len(added_cards),
        new_writing_cards=len(writing),
        removed_notes=0,
        removed_cards=0,
    )
