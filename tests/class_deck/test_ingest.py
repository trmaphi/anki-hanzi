from pathlib import Path

import fitz
from PIL import Image

from class_deck.ingest import prepare_inventory
from class_deck.review import prepare_review


def raw_inventory():
    return {
        "root_id": "drive-root",
        "items": [
            {
                "id": "folder-22",
                "title": "2026-09-22",
                "mime_type": "application/vnd.google-apps.folder",
                "modified_time": "2026-09-23T03:08:52Z",
                "children": [
                    {
                        "id": "image-1",
                        "title": "lesson.jpg",
                        "mime_type": "image/jpeg",
                        "size": "1234",
                        "modified_time": "2026-09-23T03:22:24Z",
                        "url": "https://drive.google.com/file/d/image-1/view",
                        "local_path": "2026-09-22/lesson.jpg",
                    },
                    {
                        "id": "pdf-1",
                        "title": "lesson.pdf",
                        "mime_type": "application/pdf",
                        "size": 4321,
                        "modified_time": "2026-09-23T03:24:00Z",
                        "url": "https://drive.google.com/file/d/pdf-1/view",
                        "local_path": "2026-09-22/lesson.pdf",
                    },
                    {
                        "id": "audio-1",
                        "title": "01-1.mp3",
                        "mime_type": "audio/mpeg",
                        "size": 555,
                        "modified_time": "2026-09-23T03:25:00Z",
                        "url": "https://drive.google.com/file/d/audio-1/view",
                        "local_path": "2026-09-22/01-1.mp3",
                    },
                ],
            },
            {
                "id": "misc-folder",
                "title": "Teacher notes",
                "mime_type": "application/vnd.google-apps.folder",
                "children": [],
            },
            {
                "id": "loose-file",
                "title": "readme.txt",
                "mime_type": "text/plain",
            },
        ],
    }


def materialize_fixture_media(root: Path):
    class_dir = root / "2026-09-22"
    class_dir.mkdir(parents=True)
    Image.new("RGB", (120, 80), "pink").save(class_dir / "lesson.jpg")
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Class PDF text")
    document.save(class_dir / "lesson.pdf")
    (class_dir / "01-1.mp3").write_bytes(b"fixture audio")


def test_accepts_only_iso_dated_class_folders():
    inventory = prepare_inventory(raw_inventory())

    assert [item.date for item in inventory.classes] == ["2026-09-22"]
    assert [item.title for item in inventory.unassigned] == ["Teacher notes", "readme.txt"]


def test_preserves_drive_file_identity():
    inventory = prepare_inventory(raw_inventory())
    image = inventory.classes[0].files[0]

    assert image.id == "image-1"
    assert image.name == "lesson.jpg"
    assert image.modified_time == "2026-09-23T03:22:24Z"
    assert image.url == "https://drive.google.com/file/d/image-1/view"
    assert image.local_path == "2026-09-22/lesson.jpg"


def test_extracts_pdf_text_and_renders_pages(tmp_path):
    materialize_fixture_media(tmp_path)
    draft = prepare_review(prepare_inventory(raw_inventory()), tmp_path)
    class_draft = draft.classes[0]

    assert class_draft.pdfs[0].text == "Class PDF text"
    assert len(class_draft.pdfs[0].pages) == 1
    assert (tmp_path / class_draft.pdfs[0].pages[0]).is_file()


def test_images_become_review_candidates_not_automatic_notes(tmp_path):
    materialize_fixture_media(tmp_path)
    draft = prepare_review(prepare_inventory(raw_inventory()), tmp_path)
    source = draft.to_source_dict()

    assert source["classes"][0]["notes"] == []
    assert source["classes"][0]["approved"] is False
    assert source["classes"][0]["issues"]["image_candidates"] == [
        {
            "file_id": "image-1",
            "local_path": "2026-09-22/lesson.jpg",
            "source_name": "lesson.jpg",
        }
    ]
    assert (tmp_path / draft.classes[0].contact_sheet).is_file()


def test_unmatched_audio_remains_an_issue(tmp_path):
    materialize_fixture_media(tmp_path)
    draft = prepare_review(prepare_inventory(raw_inventory()), tmp_path)
    source = draft.to_source_dict()

    assert source["classes"][0]["issues"]["unmatched_audio"] == [
        {
            "file_id": "audio-1",
            "local_path": "2026-09-22/01-1.mp3",
            "source_name": "01-1.mp3",
        }
    ]
