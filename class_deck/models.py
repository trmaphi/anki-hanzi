from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type
from typing import Any, ClassVar, Mapping


class SourceValidationError(ValueError):
    """A reviewed source value is invalid at a precise JSON-style path."""


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SourceValidationError(f"{path}: expected an object")
    return value


def _list(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        raise SourceValidationError(f"{path}: expected an array")
    return value


def _text(value: Any, path: str, *, required: bool = False) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        raise SourceValidationError(f"{path}: expected non-empty text")
    return value.strip()


def _iso_date(value: Any, path: str) -> str:
    text = _text(value, path, required=True)
    try:
        parsed = date_type.fromisoformat(text)
    except ValueError as exc:
        raise SourceValidationError(f"{path}: expected an ISO date (YYYY-MM-DD)") from exc
    if parsed.isoformat() != text:
        raise SourceValidationError(f"{path}: expected an ISO date (YYYY-MM-DD)")
    return text


@dataclass(frozen=True)
class MediaRef:
    file_id: str
    source_name: str
    local_name: str = ""
    confidence: str = "approved"

    @classmethod
    def from_value(cls, value: Any, path: str) -> MediaRef | None:
        if value in (None, ""):
            return None
        if isinstance(value, str):
            return cls(file_id="", source_name=value, local_name=value)
        raw = _mapping(value, path)
        return cls(
            file_id=_text(raw.get("file_id"), f"{path}.file_id"),
            source_name=_text(raw.get("source_name"), f"{path}.source_name", required=True),
            local_name=_text(raw.get("local_name"), f"{path}.local_name"),
            confidence=_text(raw.get("confidence", "approved"), f"{path}.confidence", required=True),
        )

    def to_value(self) -> str | dict[str, str]:
        if not self.file_id and self.local_name == self.source_name and self.confidence == "approved":
            return self.source_name
        result = {"source_name": self.source_name}
        if self.file_id:
            result["file_id"] = self.file_id
        if self.local_name:
            result["local_name"] = self.local_name
        if self.confidence != "approved":
            result["confidence"] = self.confidence
        return result


@dataclass(frozen=True)
class SourceFile:
    id: str
    name: str
    mime_type: str
    modified_time: str = ""
    sha256: str = ""

    @classmethod
    def from_dict(cls, value: Any, path: str) -> SourceFile:
        raw = _mapping(value, path)
        return cls(
            id=_text(raw.get("id"), f"{path}.id", required=True),
            name=_text(raw.get("name"), f"{path}.name", required=True),
            mime_type=_text(raw.get("mime_type"), f"{path}.mime_type", required=True),
            modified_time=_text(raw.get("modified_time"), f"{path}.modified_time"),
            sha256=_text(raw.get("sha256"), f"{path}.sha256"),
        )

    def to_dict(self) -> dict[str, str]:
        result = {"id": self.id, "name": self.name, "mime_type": self.mime_type}
        if self.modified_time:
            result["modified_time"] = self.modified_time
        if self.sha256:
            result["sha256"] = self.sha256
        return result


@dataclass(frozen=True)
class BaseNote:
    date: str
    type: str
    chinese: str
    pinyin: str = ""
    meaning: str = ""
    source_ref: str = ""
    image: MediaRef | str | None = None
    audio: MediaRef | str | None = None
    item_id: str = ""
    identity_seed: str = ""

    note_type: ClassVar[str]

    @property
    def primary_chinese(self) -> str:
        return self.chinese

    def _base_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"type": self.type, "chinese": self.chinese}
        for name in ("pinyin", "meaning", "source_ref", "item_id", "identity_seed"):
            value = getattr(self, name)
            if value:
                result[name] = value
        for name in ("image", "audio"):
            value = getattr(self, name)
            if isinstance(value, MediaRef):
                result[name] = value.to_value()
            elif value:
                result[name] = value
        return result


@dataclass(frozen=True)
class VocabularyNote(BaseNote):
    traditional: str = ""
    example: str = ""
    example_translation: str = ""

    note_type: ClassVar[str] = "vocabulary"

    def to_dict(self) -> dict[str, Any]:
        result = self._base_dict()
        for name in ("traditional", "example", "example_translation"):
            value = getattr(self, name)
            if value:
                result[name] = value
        return result


@dataclass(frozen=True)
class SentenceNote(BaseNote):
    answer: str = ""
    explanation: str = ""

    note_type: ClassVar[str] = "sentence"

    def to_dict(self) -> dict[str, Any]:
        result = self._base_dict()
        for name in ("answer", "explanation"):
            value = getattr(self, name)
            if value:
                result[name] = value
        return result


@dataclass(frozen=True)
class ListeningNote(BaseNote):
    recording_id: str = ""
    segment_id: str = ""

    note_type: ClassVar[str] = "listening"

    def to_dict(self) -> dict[str, Any]:
        result = self._base_dict()
        for name in ("recording_id", "segment_id"):
            value = getattr(self, name)
            if value:
                result[name] = value
        return result


Note = VocabularyNote | SentenceNote | ListeningNote


def _note(value: Any, date: str, path: str, *, version: int) -> Note:
    raw = _mapping(value, path)
    note_type = _text(raw.get("type"), f"{path}.type", required=True)
    chinese = _text(raw.get("chinese"), f"{path}.chinese", required=True)
    common: dict[str, Any] = {
        "date": date,
        "type": note_type,
        "chinese": chinese,
        "pinyin": _text(raw.get("pinyin"), f"{path}.pinyin"),
        "meaning": _text(raw.get("meaning"), f"{path}.meaning"),
        "source_ref": _text(raw.get("source_ref"), f"{path}.source_ref"),
        "image": MediaRef.from_value(raw.get("image"), f"{path}.image"),
        "audio": MediaRef.from_value(raw.get("audio"), f"{path}.audio"),
        "item_id": _text(raw.get("item_id"), f"{path}.item_id", required=version == 2 and note_type != "listening"),
        "identity_seed": _text(raw.get("identity_seed"), f"{path}.identity_seed"),
    }
    if note_type == "vocabulary":
        return VocabularyNote(
            **common,
            traditional=_text(raw.get("traditional"), f"{path}.traditional"),
            example=_text(raw.get("example"), f"{path}.example"),
            example_translation=_text(raw.get("example_translation"), f"{path}.example_translation"),
        )
    if note_type == "sentence":
        return SentenceNote(
            **common,
            answer=_text(raw.get("answer"), f"{path}.answer"),
            explanation=_text(raw.get("explanation"), f"{path}.explanation"),
        )
    if note_type == "listening":
        common["item_id"] = _text(raw.get("item_id"), f"{path}.item_id")
        return ListeningNote(
            **common,
            recording_id=_text(raw.get("recording_id"), f"{path}.recording_id", required=version == 2),
            segment_id=_text(raw.get("segment_id"), f"{path}.segment_id", required=version == 2),
        )
    raise SourceValidationError(f"{path}.type: expected vocabulary, sentence, or listening")


@dataclass(frozen=True)
class ClassRecord:
    date: str
    folder_id: str
    approved: bool
    source_files: tuple[SourceFile, ...]
    notes: tuple[Note, ...]
    issues: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: Any, path: str, *, version: int = 1) -> ClassRecord:
        raw = _mapping(value, path)
        class_date = _iso_date(raw.get("date"), f"{path}.date")
        source_files = tuple(
            SourceFile.from_dict(item, f"{path}.source_files[{index}]")
            for index, item in enumerate(_list(raw.get("source_files", []), f"{path}.source_files"))
        )
        notes = tuple(
            _note(item, class_date, f"{path}.notes[{index}]", version=version)
            for index, item in enumerate(_list(raw.get("notes", []), f"{path}.notes"))
        )
        issues = raw.get("issues", {})
        if not isinstance(issues, Mapping):
            raise SourceValidationError(f"{path}.issues: expected an object")
        approved = raw.get("approved", False)
        if not isinstance(approved, bool):
            raise SourceValidationError(f"{path}.approved: expected true or false")
        return cls(
            date=class_date,
            folder_id=_text(raw.get("folder_id"), f"{path}.folder_id", required=True),
            approved=approved,
            source_files=source_files,
            notes=notes,
            issues=dict(issues),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "folder_id": self.folder_id,
            "approved": self.approved,
            "source_files": [item.to_dict() for item in self.source_files],
            "notes": [item.to_dict() for item in self.notes],
            "issues": dict(self.issues),
        }


@dataclass(frozen=True)
class ClassSource:
    version: int
    deck_name: str
    classes: tuple[ClassRecord, ...]

    @classmethod
    def from_dict(cls, value: Any) -> ClassSource:
        raw = _mapping(value, "$" )
        version = raw.get("version")
        if version not in (1, 2):
            raise SourceValidationError("version: expected 1 or 2")
        deck_name = _text(raw.get("deck_name", "Chinese Classes"), "deck_name", required=True)
        if deck_name != "Chinese Classes":
            raise SourceValidationError("deck_name: expected 'Chinese Classes'")
        classes = tuple(
            ClassRecord.from_dict(item, f"classes[{index}]", version=version)
            for index, item in enumerate(_list(raw.get("classes"), "classes"))
        )
        dates = [item.date for item in classes]
        if len(dates) != len(set(dates)):
            raise SourceValidationError("classes: duplicate class date")
        if version == 2:
            item_ids: set[str] = set()
            segment_ids: set[tuple[str, str]] = set()
            for record in classes:
                for note in record.notes:
                    if isinstance(note, ListeningNote):
                        segment_key = (note.recording_id, note.segment_id)
                        if segment_key in segment_ids:
                            raise SourceValidationError("classes: duplicate recording_id/segment_id")
                        segment_ids.add(segment_key)
                    else:
                        if note.item_id in item_ids:
                            raise SourceValidationError(f"classes: duplicate item_id {note.item_id!r}")
                        item_ids.add(note.item_id)
        return cls(version=version, deck_name=deck_name, classes=classes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "deck_name": self.deck_name,
            "classes": [item.to_dict() for item in self.classes],
        }
