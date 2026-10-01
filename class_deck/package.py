from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import time
import re
import sqlite3
import zipfile
from dataclasses import dataclass
from pathlib import Path

import genanki
import chevron

from .identity import PARENT_DECK, class_deck_id, class_deck_name, media_name, note_guid, note_key
from .models import BaseNote, ClassRecord, ClassSource, ListeningNote, MediaRef, Note, SentenceNote, VocabularyNote
from .templates import MODEL_IDS, build_models
from .assets import build_asset_manifest, stage_assets


@dataclass(frozen=True)
class BuildReport:
    notes: int
    cards: int
    decks: int
    media: tuple[str, ...]
    warnings: tuple[str, ...]
    output_sha256: str


class PackageBuildError(ValueError):
    """The package would contain an unusable card or inconsistent count."""


def ordered_notes(record: ClassRecord) -> tuple[Note, ...]:
    rank = {"vocabulary": 0, "sentence": 1, "listening": 2}
    return tuple(note for _, note in sorted(enumerate(record.notes), key=lambda item: (rank[item[1].type], item[0])))


def _approved_media(value: MediaRef | str | None) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    if isinstance(value, str):
        return value, None
    if value.confidence != "approved":
        return None, value.confidence
    return value.local_name or value.source_name, None


def _media_field(
    note: BaseNote,
    role: str,
    value: MediaRef | str | None,
    media_root: Path,
    staging: Path,
    media_files: dict[str, Path],
    warnings: list[str],
) -> str:
    source_name, confidence = _approved_media(value)
    if confidence:
        warnings.append(f"{note.date} {note.type} {note.chinese}: {role} is {confidence}")
        return ""
    if not source_name:
        return ""
    source = media_root / source_name
    if not source.is_file():
        warnings.append(f"{note.date} {note.type} {note.chinese}: missing {role} {source_name}")
        return ""
    target_name = media_name(note_key(note), role, source_name)
    target = staging / target_name
    shutil.copyfile(source, target)
    media_files[target_name] = target
    if role == "audio":
        return f"[sound:{target_name}]"
    return f'<img src="{target_name}">'


def _fields_for(note: BaseNote, image: str, audio: str) -> list[str]:
    if isinstance(note, VocabularyNote):
        return [
            note.chinese,
            note.traditional,
            note.pinyin,
            note.meaning,
            note.example,
            note.example_translation,
            image,
            audio,
            note.date,
            note.source_ref,
            note.zhuyin,
            note.part_of_speech,
            note.definitions,
            note.breakdown,
            note.radical,
            note.hsk_level,
            note.frequency,
        ]
    if isinstance(note, SentenceNote):
        return [
            note.chinese,
            note.pinyin,
            note.meaning,
            note.answer,
            note.explanation,
            audio,
            note.date,
            note.source_ref,
        ]
    if isinstance(note, ListeningNote):
        return [note.chinese, note.pinyin, note.meaning, audio, note.date, note.source_ref]
    raise TypeError(f"Unsupported note: {type(note).__name__}")


def _validate_fronts(anki_note: genanki.Note) -> None:
    values = {field["name"]: value for field, value in zip(anki_note.model.fields, anki_note.fields)}
    for card in anki_note.cards:
        rendered = chevron.render(anki_note.model.templates[card.ord]["qfmt"], values)
        visible = re.sub(r"<(script|style)\b[^>]*>[\s\S]*?</\1>", "", rendered, flags=re.IGNORECASE)
        visible = re.sub(r"<[^>]+>", "", visible)
        if not visible.strip():
            raise PackageBuildError(
                f"blank front for {anki_note.guid} template {card.ord}"
            )


def _collection_counts(path: Path) -> tuple[int, int]:
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory(prefix="class-deck-count-") as directory:
        name = next(item for item in archive.namelist() if item.startswith("collection.anki"))
        collection = Path(directory) / name
        collection.write_bytes(archive.read(name))
        with sqlite3.connect(collection) as database:
            notes = database.execute("select count(*) from notes").fetchone()[0]
            cards = database.execute("select count(*) from cards").fetchone()[0]
    return notes, cards


def build_package(source: ClassSource, media_root: Path, output: Path) -> BuildReport:
    media_root = Path(media_root)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    models = build_models()
    warnings: list[str] = []
    media_files: dict[str, Path] = {}
    note_count = 0

    parent = genanki.Deck(class_deck_id(PARENT_DECK), PARENT_DECK)
    decks: list[genanki.Deck] = [parent]

    with tempfile.TemporaryDirectory(prefix="class-deck-media-") as temp_media:
        staging = Path(temp_media)
        asset_manifest = build_asset_manifest(Path(__file__).parents[1])
        for path in stage_assets(asset_manifest, staging):
            media_files[path.name] = path
        for class_record in sorted(source.classes, key=lambda item: item.date):
            if not class_record.approved:
                warnings.append(f"{class_record.date}: class is not approved")
                continue
            deck_name = class_deck_name(class_record.date)
            deck = genanki.Deck(class_deck_id(deck_name), deck_name)
            decks.append(deck)
            due = 1
            for note in ordered_notes(class_record):
                image = _media_field(note, "image", note.image, media_root, staging, media_files, warnings)
                audio = _media_field(note, "audio", note.audio, media_root, staging, media_files, warnings)
                if isinstance(note, ListeningNote) and not audio:
                    if note.audio is None:
                        warnings.append(f"{note.date} listening {note.chinese}: missing approved audio")
                    continue
                anki_note = genanki.Note(
                    model=models[note.type],
                    fields=_fields_for(note, image, audio),
                    tags=[f"Class::{note.date}", f"Type::{note.type.title()}"],
                    guid=note_guid(note),
                    due=due,
                )
                _validate_fronts(anki_note)
                deck.add_note(anki_note)
                note_count += 1
                due += 1

        package = genanki.Package(decks, media_files=[str(path) for _, path in sorted(media_files.items())])
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            package.write_to_file(str(temporary), timestamp=time.time())
            os.replace(temporary, output)
        finally:
            if temporary.exists():
                temporary.unlink()

    actual_notes, actual_cards = _collection_counts(output)
    if actual_notes != note_count:
        raise PackageBuildError(f"generated note count changed: expected {note_count}, found {actual_notes}")
    output_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    return BuildReport(
        notes=note_count,
        cards=actual_cards,
        decks=len(decks),
        media=tuple(sorted(media_files)),
        warnings=tuple(warnings),
        output_sha256=output_hash,
    )


__all__ = ["MODEL_IDS", "BuildReport", "PackageBuildError", "build_package", "ordered_notes"]
