from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import tempfile
import zipfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from .identity import PARENT_DECK, class_deck_id, class_deck_name, note_guid
from .manifest import ClassManifest, merge_manifest
from .models import ClassSource, MediaRef, SourceValidationError
from .package import BuildReport, MODEL_IDS, build_package
from .audio import AudioError, export_segment
from .transcribe import FasterWhisperTranscriber, TranscriptionError, transcribe_recording
from .review import recording_review_dict
from .assets import ASSETS


class PackageValidationError(ValueError):
    """The generated package cannot be safely imported."""


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise SourceValidationError(f"source: file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SourceValidationError(
            f"source: invalid JSON at line {exc.lineno}, column {exc.colno}"
        ) from exc


def _load_source(path: Path) -> ClassSource:
    return ClassSource.from_dict(_load_json(path))


def _load_manifest(path: Path) -> ClassManifest | None:
    if not path.is_file():
        return None
    return ClassManifest.from_dict(_load_json(path))


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


EXPECTED_ORDINALS = {
    MODEL_IDS["vocabulary"]: (0, 1, 2, 3),
    MODEL_IDS["sentence"]: (0, 1),
    MODEL_IDS["listening"]: (0,),
}


def inspect_package(
    path: Path,
    expected: BuildReport | None = None,
    source: ClassSource | None = None,
) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            collection_name = next(name for name in names if name.startswith("collection.anki"))
            media_map = json.loads(archive.read("media"))
            missing_media = sorted(set(media_map) - set(names))
            if missing_media:
                raise PackageValidationError(f"media entries absent from archive: {missing_media}")
            with tempfile.TemporaryDirectory(prefix="class-deck-inspect-") as directory:
                collection = Path(directory) / "collection.anki2"
                collection.write_bytes(archive.read(collection_name))
                with sqlite3.connect(collection) as database:
                    integrity = database.execute("pragma integrity_check").fetchone()[0]
                    notes = database.execute("select count(*) from notes").fetchone()[0]
                    cards = database.execute("select count(*) from cards").fetchone()[0]
                    unique_guids = database.execute("select count(distinct guid) from notes").fetchone()[0]
                    note_model_ids = {
                        row[0] for row in database.execute("select distinct mid from notes")
                    }
                    note_rows = database.execute("select guid, flds, tags from notes").fetchall()
                    models = json.loads(database.execute("select models from col").fetchone()[0])
                    decks = json.loads(database.execute("select decks from col").fetchone()[0])
    except (zipfile.BadZipFile, KeyError, StopIteration, sqlite3.DatabaseError) as exc:
        raise PackageValidationError(f"invalid Anki package: {exc}") from exc

    if integrity != "ok":
        raise PackageValidationError(f"collection integrity check failed: {integrity}")
    if unique_guids != notes:
        raise PackageValidationError("duplicate note GUIDs found")
    if expected and (notes != expected.notes or cards != expected.cards):
        raise PackageValidationError(
            f"package count mismatch: expected {expected.notes} notes/{expected.cards} cards, "
            f"found {notes} notes/{cards} cards"
        )
    unexpected_models = sorted(note_model_ids - set(MODEL_IDS.values()))
    if unexpected_models:
        raise PackageValidationError(f"notes use unexpected models: {unexpected_models}")
    template_ordinals = {
        model_id: tuple(template["ord"] for template in models[str(model_id)]["tmpls"])
        for model_id in sorted(note_model_ids)
    }
    invalid_templates = {
        model_id: ordinals
        for model_id, ordinals in template_ordinals.items()
        if ordinals != EXPECTED_ORDINALS[model_id]
    }
    if invalid_templates:
        raise PackageValidationError(f"fixed template ordinals changed: {invalid_templates}")
    deck_ids = {
        value["name"]: int(key)
        for key, value in decks.items()
        if value["name"] != "Default"
    }
    if source is not None:
        expected_deck_ids = {PARENT_DECK: class_deck_id(PARENT_DECK)}
        expected_tags = {}
        for record in source.classes:
            if not record.approved:
                continue
            name = class_deck_name(record.date)
            expected_deck_ids[name] = class_deck_id(name)
            for note in record.notes:
                expected_tags[note_guid(note)] = {
                    f"Class::{note.date}",
                    f"Type::{note.type.title()}",
                }
        if deck_ids != expected_deck_ids:
            raise PackageValidationError("deterministic deck IDs or deck set changed")
        for guid, _, tags in note_rows:
            required = expected_tags.get(guid)
            if required is None or not required <= set(tags.split()):
                raise PackageValidationError(f"required tags missing for note {guid}")
    mapped_names = set(media_map.values())
    referenced_names = set()
    for _, fields, _ in note_rows:
        referenced_names.update(re.findall(r"\[sound:([^\]]+)\]", fields))
        referenced_names.update(re.findall(r'<img src="([^"]+)">', fields))
    asset_names = {packaged for _, packaged in ASSETS.values()}
    if not asset_names <= mapped_names:
        raise PackageValidationError(
            f"required offline assets missing from media map: {sorted(asset_names - mapped_names)}"
        )
    if referenced_names != mapped_names - asset_names:
        raise PackageValidationError(
            f"media reference mismatch: fields={sorted(referenced_names)}, "
            f"note-media={sorted(mapped_names - asset_names)}"
        )
    deck_names = sorted(deck_ids)
    return {
        "integrity": integrity,
        "notes": notes,
        "cards": cards,
        "unique_guids": unique_guids,
        "decks": deck_names,
        "media": len(media_map),
        "model_ids": MODEL_IDS,
        "template_ordinals": {str(key): list(value) for key, value in template_ordinals.items()},
        "deck_ids": deck_ids,
        "tags_valid": True,
        "media_references_valid": True,
    }


def _check_source(source: ClassSource, media_root: Path) -> dict[str, Any]:
    if not media_root.is_dir():
        raise SourceValidationError(f"media: directory not found: {media_root}")
    for class_index, record in enumerate(source.classes):
        if not record.approved:
            continue
        for note_index, note in enumerate(record.notes):
            for role in ("image", "audio"):
                value = getattr(note, role)
                if value is None:
                    continue
                if isinstance(value, MediaRef):
                    if value.confidence != "approved":
                        continue
                    local_name = value.local_name or value.source_name
                else:
                    local_name = value
                candidate = (media_root / local_name).resolve()
                try:
                    candidate.relative_to(media_root.resolve())
                except ValueError as exc:
                    raise SourceValidationError(
                        f"classes[{class_index}].notes[{note_index}].{role}: path escapes media directory"
                    ) from exc
                if not candidate.is_file():
                    raise SourceValidationError(
                        f"classes[{class_index}].notes[{note_index}].{role}: "
                        f"file not found: {local_name}"
                    )
    approved = [record for record in source.classes if record.approved]
    expected_decks = [class_deck_name(record.date) for record in approved]
    return {
        "classes": len(source.classes),
        "approved_classes": len(approved),
        "notes": sum(len(record.notes) for record in approved),
        "expected_decks": expected_decks,
        "media_root": str(media_root),
    }


def _report_dict(report: BuildReport, validation: dict[str, Any], merge: Any) -> dict[str, Any]:
    value = asdict(report)
    value["media"] = list(report.media)
    value["warnings"] = list(report.warnings)
    value["validation"] = validation
    value["merge"] = {
        "new_classes": list(merge.new_classes),
        "changed_classes": list(merge.changed_classes),
        "missing_classes": list(merge.missing_classes),
        "unchanged_classes": list(merge.unchanged_classes),
    }
    return value


def _build(arguments: argparse.Namespace) -> int:
    source = _load_source(Path(arguments.source))
    media_root = Path(arguments.media)
    state = Path(arguments.state)
    output = Path(arguments.out)
    previous = _load_manifest(state / "manifest.json")
    merged = merge_manifest(previous, source)
    _check_source(merged.source, media_root)

    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, candidate_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".apkg", dir=output.parent)
    os.close(descriptor)
    candidate = Path(candidate_name)
    try:
        report = build_package(merged.source, media_root, candidate)
        validation = inspect_package(candidate, report, merged.source)
        expected_decks = {class_deck_name(record.date) for record in merged.source.classes if record.approved}
        actual_decks = set(validation["decks"])
        absent = sorted(expected_decks - actual_decks)
        if absent:
            raise PackageValidationError(f"approved class decks missing: {absent}")
        manifest = ClassManifest.from_source(merged.source)
        _atomic_json(state / "manifest.json", manifest.to_dict())
        _atomic_json(state / "build-report.json", _report_dict(report, validation, merged))
        os.replace(candidate, output)
    finally:
        if candidate.exists():
            candidate.unlink()

    print(f"Built {output}: {report.notes} notes, {report.cards} cards, {report.decks} decks")
    if report.warnings:
        print(f"Warnings: {len(report.warnings)} (see {state / 'build-report.json'})")
    return 0


def _check(arguments: argparse.Namespace) -> int:
    source = _load_source(Path(arguments.source))
    result = _check_source(source, Path(arguments.media))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _transcribe(arguments: argparse.Namespace) -> int:
    source = Path(arguments.source)
    segments = transcribe_recording(
        source,
        arguments.recording_id,
        arguments.model,
        FasterWhisperTranscriber(),
    )
    clips = Path(arguments.clips)
    clip_paths = []
    for segment in segments:
        clip = clips / f"{segment.segment_id.replace(':', '-')}.mp3"
        export_segment(source, segment, clip)
        clip_paths.append(clip)
    value = recording_review_dict(
        arguments.recording_id,
        source,
        arguments.model,
        segments,
        tuple(clip_paths),
    )
    _atomic_json(Path(arguments.out), value)
    print(f"Transcribed {source}: {len(segments)} review segments")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build an incremental Chinese Classes Anki deck")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="validate reviewed source JSON")
    check.add_argument("--source", required=True)
    check.add_argument("--media", required=True)
    build = commands.add_parser("build", help="build and validate an APKG")
    build.add_argument("--source", required=True)
    build.add_argument("--media", required=True)
    build.add_argument("--state", required=True)
    build.add_argument("--out", required=True)
    transcribe = commands.add_parser("transcribe", help="draft sentence-level listening segments")
    transcribe.add_argument("--source", required=True)
    transcribe.add_argument("--recording-id", required=True)
    transcribe.add_argument("--model", required=True)
    transcribe.add_argument("--out", required=True)
    transcribe.add_argument("--clips", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        if arguments.command == "check":
            return _check(arguments)
        if arguments.command == "transcribe":
            return _transcribe(arguments)
        return _build(arguments)
    except (AudioError, SourceValidationError, PackageValidationError, TranscriptionError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
