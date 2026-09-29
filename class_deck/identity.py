from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import PurePath

from .models import BaseNote


PARENT_DECK = "Chinese Classes"


def _digest(namespace: str, value: str) -> bytes:
    return hashlib.sha256(f"class-deck:{namespace}:{value}".encode("utf-8")).digest()


def _base36(value: int) -> str:
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    result = ""
    while value:
        value, remainder = divmod(value, 36)
        result = alphabet[remainder] + result
    return result or "0"


def normalize_chinese(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", value)).strip()


def class_deck_name(date: str) -> str:
    return f"{PARENT_DECK}::{date}"


def class_deck_id(name: str) -> int:
    value = int.from_bytes(_digest("deck", name)[:8], "big")
    return 2**30 + value % 2**30


def model_id(note_type: str) -> int:
    value = int.from_bytes(_digest("model", note_type)[:8], "big")
    return 2**30 + value % 2**30


def note_key(note: BaseNote) -> str:
    return f"{note.date}:{note.type}:{normalize_chinese(note.primary_chinese)}"


def note_guid(note: BaseNote) -> str:
    value = int.from_bytes(_digest("note", note_key(note))[:11], "big")
    return _base36(value).rjust(14, "0")[-14:]


def media_name(key: str, role: str, source_name: str) -> str:
    suffix = PurePath(source_name).suffix.lower()
    suffix = suffix if re.fullmatch(r"\.[a-z0-9]{1,8}", suffix) else ""
    safe_role = re.sub(r"[^a-z0-9]+", "-", role.lower()).strip("-") or "media"
    token = hashlib.sha256(f"{key}:{role}:{source_name}".encode("utf-8")).hexdigest()[:16]
    return f"class-{safe_role}-{token}{suffix}"
