from class_deck.identity import note_guid, note_key
from class_deck.manifest import ClassManifest, merge_manifest, migrate_source_identities
from class_deck.models import ClassSource


def source_for(date="2026-09-22", *, folder="folder-22", modified="2026-09-23T03:22:24Z"):
    return {
        "version": 1,
        "deck_name": "Chinese Classes",
        "classes": [
            {
                "date": date,
                "folder_id": folder,
                "approved": True,
                "source_files": [
                    {
                        "id": f"file-{date}",
                        "name": "lesson.jpg",
                        "mime_type": "image/jpeg",
                        "modified_time": modified,
                        "sha256": "a" * 64,
                    }
                ],
                "notes": [
                    {
                        "type": "vocabulary",
                        "chinese": "感冒" if date == "2026-09-22" else "发烧",
                        "pinyin": "gǎnmào" if date == "2026-09-22" else "fāshāo",
                        "meaning": "common cold" if date == "2026-09-22" else "fever",
                    }
                ],
                "issues": {},
            }
        ],
    }


def parsed(raw):
    return ClassSource.from_dict(raw)


def test_first_import_marks_all_classes_new():
    result = merge_manifest(None, parsed(source_for()))

    assert result.new_classes == ("2026-09-22",)
    assert result.changed_classes == ()
    assert result.missing_classes == ()
    assert result.unchanged_classes == ()
    assert result.source.classes[0].approved is True


def test_unchanged_class_reuses_reviewed_content():
    original = parsed(source_for())
    previous = ClassManifest.from_source(original)
    rediscovered = source_for()
    rediscovered["classes"][0]["approved"] = False
    rediscovered["classes"][0]["notes"] = []

    result = merge_manifest(previous, parsed(rediscovered))

    assert result.unchanged_classes == ("2026-09-22",)
    assert result.source.classes[0].approved is True
    assert result.source.classes[0].notes[0].chinese == "感冒"


def test_approved_review_correction_replaces_content_when_files_are_unchanged():
    original = parsed(source_for())
    previous = ClassManifest.from_source(original)
    corrected = source_for()
    corrected["classes"][0]["notes"][0]["meaning"] = "to catch a cold; common cold"

    result = merge_manifest(previous, parsed(corrected))

    assert result.changed_classes == ("2026-09-22",)
    assert result.unchanged_classes == ()
    assert result.source.classes[0].notes[0].meaning == "to catch a cold; common cold"
    assert note_guid(result.source.classes[0].notes[0]) == note_guid(original.classes[0].notes[0])


def test_added_class_preserves_old_keys_and_guids():
    original = parsed(source_for())
    previous = ClassManifest.from_source(original)
    updated = source_for()
    updated["classes"].extend(source_for("2026-09-29", folder="folder-29")["classes"])

    result = merge_manifest(previous, parsed(updated))

    before = original.classes[0].notes[0]
    after = next(item for item in result.source.classes if item.date == "2026-09-22").notes[0]
    assert note_key(after) == note_key(before)
    assert note_guid(after) == note_guid(before)
    assert result.new_classes == ("2026-09-29",)


def test_changed_files_require_re_review():
    original = parsed(source_for())
    previous = ClassManifest.from_source(original)
    changed = source_for(modified="2026-09-29T09:00:00Z")
    changed["classes"][0]["approved"] = False
    changed["classes"][0]["notes"] = []

    result = merge_manifest(previous, parsed(changed))

    assert result.changed_classes == ("2026-09-22",)
    assert result.source.classes[0].notes[0].chinese == "感冒"
    assert result.source.classes[0].approved is True


def test_missing_class_is_retained_and_reported():
    two_classes = source_for()
    two_classes["classes"].extend(source_for("2026-09-29", folder="folder-29")["classes"])
    previous_source = parsed(two_classes)
    previous = ClassManifest.from_source(previous_source)

    result = merge_manifest(previous, parsed(source_for("2026-09-29", folder="folder-29")))

    assert result.missing_classes == ("2026-09-22",)
    assert [item.date for item in result.source.classes] == ["2026-09-22", "2026-09-29"]
    before_keys = {note_key(note) for item in previous_source.classes for note in item.notes}
    after_keys = {note_key(note) for item in result.source.classes for note in item.notes}
    assert after_keys == before_keys


def test_manifest_serializes_reviewed_content_and_note_keys():
    source = parsed(source_for())
    manifest = ClassManifest.from_source(source)
    raw = manifest.to_dict()

    assert raw["manifest_version"] == 1
    assert raw["classes"][0]["note_keys"] == ["2026-09-22:vocabulary:感冒"]
    assert ClassManifest.from_dict(raw).to_dict() == raw


def test_migration_assigns_content_independent_ids_and_legacy_seeds():
    legacy = parsed(source_for())
    migrated = migrate_source_identities(legacy)
    note = migrated.classes[0].notes[0]

    assert migrated.version == 2
    assert note.item_id == "folder-22:vocabulary:0001"
    assert note.identity_seed == "2026-09-22:vocabulary:感冒"
    assert note_guid(note) == note_guid(legacy.classes[0].notes[0])
