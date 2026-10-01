from __future__ import annotations

import json
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Mapping

from pypinyin import Style, lazy_pinyin

from .models import Note, VocabularyNote


VOCABULARY_METADATA = (
    "traditional",
    "part_of_speech",
    "definitions",
    "breakdown",
    "radical",
    "hsk_level",
    "frequency",
)


@dataclass(frozen=True)
class LexiconEntry:
    traditional: str = ""
    part_of_speech: str = ""
    definitions: str = ""
    breakdown: str = ""
    radical: str = ""
    hsk_level: str = ""
    frequency: str = ""


@dataclass(frozen=True)
class EnrichmentAssets:
    entries: Mapping[str, LexiconEntry]

    @classmethod
    def from_cedict_archive(cls, archive: Path) -> EnrichmentAssets:
        with zipfile.ZipFile(archive) as package, tempfile.TemporaryDirectory(prefix="class-deck-cedict-") as directory:
            members = [name for name in package.namelist() if name.endswith(".db")]
            if len(members) != 1:
                raise ValueError(f"{archive}: expected exactly one .db member")
            database_path = Path(directory) / "cedict.db"
            database_path.write_bytes(package.read(members[0]))
            with sqlite3.connect(database_path) as database:
                character_rows = {
                    row[0]: row[1:]
                    for row in database.execute("select character, decomposition, radical from character")
                }
                entries: dict[str, LexiconEntry] = {}
                rows = database.execute(
                    "select c.word, c.traditional, c.definitions, c.dominant_PoS, c.rank, w.level "
                    "from cedict c left join word_levels w on w.word=c.word"
                )
                for word, traditional, definitions_json, pos, rank, level in rows:
                    definitions = ""
                    if definitions_json:
                        parsed = json.loads(definitions_json)
                        definitions = "; ".join(dict.fromkeys(value.strip(" ;") for value in parsed.values() if value.strip(" ;")))
                    decompositions = []
                    radicals = []
                    for character in word:
                        decomposition, radical = character_rows.get(character, ("", ""))
                        if decomposition and decomposition != "？":
                            decompositions.append(f"{character}: {decomposition}")
                        if radical:
                            radicals.append(f"{character}: {str(radical).strip(chr(34))}")
                    entries[word] = LexiconEntry(
                        traditional=traditional or "",
                        part_of_speech=pos or "",
                        definitions=definitions,
                        breakdown="; ".join(decompositions),
                        radical="; ".join(radicals),
                        hsk_level=level or "",
                        frequency=str(rank) if rank is not None else "",
                    )
        return cls(entries=entries)


@dataclass(frozen=True)
class EnrichmentResult:
    note: Note
    autofilled_fields: tuple[str, ...]
    unresolved_fields: tuple[str, ...]


def _romanization(text: str, style: Style) -> str:
    return " ".join(lazy_pinyin(text, style=style, neutral_tone_with_five=False)).strip()


def enrich_note(note: Note, assets: EnrichmentAssets) -> EnrichmentResult:
    updates: dict[str, str] = {}
    autofilled: list[str] = []
    unresolved: list[str] = []
    if not note.pinyin:
        updates["pinyin"] = _romanization(note.chinese, Style.TONE)
        autofilled.append("pinyin")
    if isinstance(note, VocabularyNote):
        if not note.zhuyin:
            updates["zhuyin"] = _romanization(note.chinese, Style.BOPOMOFO)
            autofilled.append("zhuyin")
        entry = assets.entries.get(note.chinese)
        for field in VOCABULARY_METADATA:
            if getattr(note, field):
                continue
            value = getattr(entry, field, "") if entry else ""
            if value:
                updates[field] = value
                autofilled.append(field)
            else:
                unresolved.append(field)
    return EnrichmentResult(
        note=replace(note, **updates),
        autofilled_fields=tuple(autofilled),
        unresolved_fields=tuple(unresolved),
    )
