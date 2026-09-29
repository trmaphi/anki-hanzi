from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type
from typing import Any, Mapping


FOLDER_MIME = "application/vnd.google-apps.folder"


@dataclass(frozen=True)
class DriveItem:
    id: str
    title: str
    mime_type: str
    size: int | None = None
    modified_time: str = ""
    url: str = ""
    local_path: str = ""

    @property
    def name(self) -> str:
        return self.title


@dataclass(frozen=True)
class ClassInventory:
    date: str
    folder_id: str
    modified_time: str
    files: tuple[DriveItem, ...]


@dataclass(frozen=True)
class Inventory:
    root_id: str
    classes: tuple[ClassInventory, ...]
    unassigned: tuple[DriveItem, ...]


def _item(value: Mapping[str, Any]) -> DriveItem:
    size = value.get("size")
    try:
        parsed_size = int(size) if size not in (None, "") else None
    except (TypeError, ValueError):
        parsed_size = None
    return DriveItem(
        id=str(value.get("id", "")),
        title=str(value.get("title", value.get("name", ""))),
        mime_type=str(value.get("mime_type", "")),
        size=parsed_size,
        modified_time=str(value.get("modified_time", "")),
        url=str(value.get("url", "")),
        local_path=str(value.get("local_path", "")),
    )


def _class_date(title: str) -> str | None:
    try:
        parsed = date_type.fromisoformat(title)
    except ValueError:
        return None
    return title if parsed.isoformat() == title else None


def prepare_inventory(raw: Mapping[str, Any]) -> Inventory:
    classes: list[ClassInventory] = []
    unassigned: list[DriveItem] = []
    for value in raw.get("items", []):
        item = _item(value)
        class_date = _class_date(item.title) if item.mime_type == FOLDER_MIME else None
        if not class_date:
            unassigned.append(item)
            continue
        children = tuple(_item(child) for child in value.get("children", []))
        classes.append(
            ClassInventory(
                date=class_date,
                folder_id=item.id,
                modified_time=item.modified_time,
                files=children,
            )
        )
    return Inventory(
        root_id=str(raw.get("root_id", "")),
        classes=tuple(sorted(classes, key=lambda item: item.date)),
        unassigned=tuple(unassigned),
    )
