from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .identity import note_key
from .models import ClassRecord, ClassSource, SourceValidationError


def _source_fingerprint(record: ClassRecord) -> tuple[Any, ...]:
    files = tuple(
        sorted(
            (item.id, item.modified_time, item.sha256)
            for item in record.source_files
        )
    )
    return record.folder_id, files


@dataclass(frozen=True)
class ClassManifest:
    source: ClassSource
    manifest_version: int = 1

    @classmethod
    def from_source(cls, source: ClassSource) -> ClassManifest:
        return cls(source=source)

    @classmethod
    def from_dict(cls, value: Any) -> ClassManifest:
        if not isinstance(value, Mapping):
            raise SourceValidationError("manifest: expected an object")
        if value.get("manifest_version") != 1:
            raise SourceValidationError("manifest_version: expected 1")
        classes = []
        for index, item in enumerate(value.get("classes", [])):
            if not isinstance(item, Mapping):
                raise SourceValidationError(f"classes[{index}]: expected an object")
            record = {key: val for key, val in item.items() if key != "note_keys"}
            classes.append(record)
        return cls.from_source(
            ClassSource.from_dict(
                {
                    "version": value.get("source_version", 1),
                    "deck_name": value.get("deck_name", "Chinese Classes"),
                    "classes": classes,
                }
            )
        )

    def to_dict(self) -> dict[str, Any]:
        classes = []
        for record in self.source.classes:
            raw = record.to_dict()
            raw["note_keys"] = [note_key(note) for note in record.notes]
            classes.append(raw)
        return {
            "manifest_version": self.manifest_version,
            "source_version": self.source.version,
            "deck_name": self.source.deck_name,
            "classes": classes,
        }


@dataclass(frozen=True)
class MergeResult:
    source: ClassSource
    new_classes: tuple[str, ...]
    changed_classes: tuple[str, ...]
    missing_classes: tuple[str, ...]
    unchanged_classes: tuple[str, ...]


def merge_manifest(previous: ClassManifest | None, incoming: ClassSource) -> MergeResult:
    if previous is None:
        ordered = tuple(sorted(incoming.classes, key=lambda item: item.date))
        return MergeResult(
            source=ClassSource(incoming.version, incoming.deck_name, ordered),
            new_classes=tuple(item.date for item in ordered),
            changed_classes=(),
            missing_classes=(),
            unchanged_classes=(),
        )

    old_by_date = {item.date: item for item in previous.source.classes}
    new_by_date = {item.date: item for item in incoming.classes}
    merged: dict[str, ClassRecord] = {}
    new_dates: list[str] = []
    changed_dates: list[str] = []
    unchanged_dates: list[str] = []

    for class_date, discovered in new_by_date.items():
        old = old_by_date.get(class_date)
        if old is None:
            new_dates.append(class_date)
            merged[class_date] = discovered
            continue
        if _source_fingerprint(old) == _source_fingerprint(discovered):
            unchanged_dates.append(class_date)
            merged[class_date] = old
            continue
        changed_dates.append(class_date)
        merged[class_date] = discovered if discovered.approved else old

    missing_dates = sorted(set(old_by_date) - set(new_by_date))
    for class_date in missing_dates:
        merged[class_date] = old_by_date[class_date]

    ordered = tuple(merged[class_date] for class_date in sorted(merged))
    return MergeResult(
        source=ClassSource(incoming.version, incoming.deck_name, ordered),
        new_classes=tuple(sorted(new_dates)),
        changed_classes=tuple(sorted(changed_dates)),
        missing_classes=tuple(missing_dates),
        unchanged_classes=tuple(sorted(unchanged_dates)),
    )
