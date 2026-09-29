from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz
from PIL import Image, ImageOps, ImageDraw

from .ingest import ClassInventory, DriveItem, Inventory


IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
AUDIO_MIMES = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/mp4"}


@dataclass(frozen=True)
class PdfDraft:
    file_id: str
    source_name: str
    text: str
    pages: tuple[str, ...]


@dataclass(frozen=True)
class ClassReviewDraft:
    inventory: ClassInventory
    pdfs: tuple[PdfDraft, ...]
    images: tuple[dict[str, str], ...]
    audio: tuple[dict[str, str], ...]
    missing_files: tuple[str, ...]
    contact_sheet: str


@dataclass(frozen=True)
class ReviewDraft:
    inventory: Inventory
    classes: tuple[ClassReviewDraft, ...]

    def to_source_dict(self) -> dict[str, Any]:
        records = []
        for draft in self.classes:
            source_files = []
            for item in draft.inventory.files:
                raw: dict[str, Any] = {
                    "id": item.id,
                    "name": item.title,
                    "mime_type": item.mime_type,
                }
                if item.modified_time:
                    raw["modified_time"] = item.modified_time
                source_files.append(raw)
            issues: dict[str, Any] = {
                "image_candidates": list(draft.images),
                "unmatched_audio": list(draft.audio),
                "pdf_candidates": [
                    {
                        "file_id": item.file_id,
                        "source_name": item.source_name,
                        "pages": list(item.pages),
                        "text": item.text,
                    }
                    for item in draft.pdfs
                ],
            }
            if draft.missing_files:
                issues["missing_files"] = list(draft.missing_files)
            records.append(
                {
                    "date": draft.inventory.date,
                    "folder_id": draft.inventory.folder_id,
                    "approved": False,
                    "source_files": source_files,
                    "notes": [],
                    "issues": issues,
                }
            )
        return {"version": 1, "deck_name": "Chinese Classes", "classes": records}


def _safe_media_path(media_root: Path, local_path: str) -> Path | None:
    if not local_path:
        return None
    candidate = (media_root / local_path).resolve()
    try:
        candidate.relative_to(media_root.resolve())
    except ValueError:
        return None
    return candidate


def _reference(item: DriveItem) -> dict[str, str]:
    return {"file_id": item.id, "local_path": item.local_path, "source_name": item.title}


def _render_pdf(item: DriveItem, source: Path, review_dir: Path, media_root: Path) -> PdfDraft:
    pages: list[str] = []
    texts: list[str] = []
    with fitz.open(source) as document:
        for index, page in enumerate(document):
            texts.append(page.get_text("text").strip())
            target = review_dir / f"{item.id}-page-{index + 1}.png"
            page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(target)
            pages.append(target.relative_to(media_root).as_posix())
    return PdfDraft(item.id, item.title, "\n\n".join(filter(None, texts)), tuple(pages))


def _contact_sheet(images: list[tuple[DriveItem, Path]], target: Path) -> None:
    width = 800
    tile_height = 260
    canvas = Image.new("RGB", (width, max(tile_height, tile_height * len(images))), "white")
    draw = ImageDraw.Draw(canvas)
    for index, (item, path) in enumerate(images):
        top = index * tile_height
        with Image.open(path) as original:
            preview = ImageOps.contain(original.convert("RGB"), (width - 40, tile_height - 45))
        left = (width - preview.width) // 2
        canvas.paste(preview, (left, top + 25))
        draw.text((12, top + 6), f"{item.id} · {item.title}", fill="black")
    canvas.save(target, format="JPEG", quality=88)


def prepare_review(inventory: Inventory, media_root: Path) -> ReviewDraft:
    media_root = Path(media_root)
    drafts: list[ClassReviewDraft] = []
    for class_record in inventory.classes:
        review_dir = media_root / "_review" / class_record.date
        review_dir.mkdir(parents=True, exist_ok=True)
        pdfs: list[PdfDraft] = []
        images: list[dict[str, str]] = []
        image_paths: list[tuple[DriveItem, Path]] = []
        audio: list[dict[str, str]] = []
        missing: list[str] = []
        for item in class_record.files:
            local = _safe_media_path(media_root, item.local_path)
            if local is None or not local.is_file():
                missing.append(item.id)
                continue
            if item.mime_type == "application/pdf":
                pdfs.append(_render_pdf(item, local, review_dir, media_root))
            elif item.mime_type in IMAGE_MIMES:
                images.append(_reference(item))
                image_paths.append((item, local))
            elif item.mime_type in AUDIO_MIMES:
                audio.append(_reference(item))
        contact_sheet = ""
        if image_paths:
            target = review_dir / "contact-sheet.jpg"
            _contact_sheet(image_paths, target)
            contact_sheet = target.relative_to(media_root).as_posix()
        drafts.append(
            ClassReviewDraft(
                inventory=class_record,
                pdfs=tuple(pdfs),
                images=tuple(images),
                audio=tuple(audio),
                missing_files=tuple(missing),
                contact_sheet=contact_sheet,
            )
        )
    return ReviewDraft(inventory=inventory, classes=tuple(drafts))
