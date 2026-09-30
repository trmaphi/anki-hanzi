import json
import sqlite3
import zipfile
from pathlib import Path

import class_deck.cli as cli
from class_deck.cli import main
from class_deck.identity import class_deck_id, class_deck_name
from class_deck.package import MODEL_IDS


FIXTURES = Path(__file__).parent / "fixtures"


def run_build(tmp_path, source=FIXTURES / "source.json", output=None):
    output = output or tmp_path / "Chinese-Classes.apkg"
    state = tmp_path / "state"
    exit_code = main([
        "build",
        "--source", str(source),
        "--media", str(FIXTURES / "media"),
        "--state", str(state),
        "--out", str(output),
    ])
    return exit_code, output, state


def inspect_ids(package, tmp_path):
    with zipfile.ZipFile(package) as archive:
        collection_name = next(name for name in archive.namelist() if name.startswith("collection.anki"))
        database_path = tmp_path / f"{package.stem}.anki2"
        database_path.write_bytes(archive.read(collection_name))
    with sqlite3.connect(database_path) as database:
        notes = dict(database.execute("select guid, mid from notes"))
        models = json.loads(database.execute("select models from col").fetchone()[0])
        decks = json.loads(database.execute("select decks from col").fetchone()[0])
        ordinals = {
            int(model_id): tuple(template["ord"] for template in model["tmpls"])
            for model_id, model in models.items()
            if int(model_id) in MODEL_IDS.values()
        }
        deck_ids = {value["name"]: int(key) for key, value in decks.items() if value["name"] != "Default"}
    return notes, ordinals, deck_ids


def test_check_reports_validation_paths(tmp_path, capsys):
    source = tmp_path / "bad.json"
    source.write_text(json.dumps({
        "version": 1,
        "classes": [{"date": "not-a-date", "folder_id": "folder", "notes": []}],
    }))

    exit_code = main(["check", "--source", str(source), "--media", str(tmp_path)])

    assert exit_code == 2
    assert "classes[0].date" in capsys.readouterr().err


def test_check_reports_missing_media_with_note_path(tmp_path, capsys):
    source = json.loads((FIXTURES / "source.json").read_text())
    missing_media = tmp_path / "empty-media"
    missing_media.mkdir()
    reviewed = tmp_path / "reviewed.json"
    reviewed.write_text(json.dumps(source, ensure_ascii=False))

    exit_code = main(["check", "--source", str(reviewed), "--media", str(missing_media)])

    assert exit_code == 2
    error = capsys.readouterr().err
    assert "classes[0].notes[0].image" in error
    assert "a/Bài học 1.JPG" in error


def test_build_writes_package_manifest_and_report(tmp_path):
    exit_code, output, state = run_build(tmp_path)

    assert exit_code == 0
    assert output.is_file()
    manifest = json.loads((state / "manifest.json").read_text())
    report = json.loads((state / "build-report.json").read_text())
    assert manifest["manifest_version"] == 1
    assert report["notes"] == 5
    assert report["cards"] == 9
    assert report["validation"]["integrity"] == "ok"
    assert report["output_sha256"]


def test_failed_build_does_not_replace_previous_package(tmp_path):
    output = tmp_path / "Chinese-Classes.apkg"
    output.write_bytes(b"previous package")
    bad_source = tmp_path / "bad.json"
    bad_source.write_text("not json")

    exit_code, _, state = run_build(tmp_path, bad_source, output)

    assert exit_code == 2
    assert output.read_bytes() == b"previous package"
    assert not (state / "manifest.json").exists()


def test_failed_state_write_does_not_replace_previous_package(tmp_path, monkeypatch):
    output = tmp_path / "Chinese-Classes.apkg"
    output.write_bytes(b"previous package")

    def fail_state_write(path, value):
        raise OSError("state is read-only")

    monkeypatch.setattr(cli, "_atomic_json", fail_state_write)
    exit_code, _, _ = run_build(tmp_path, output=output)

    assert exit_code == 2
    assert output.read_bytes() == b"previous package"


def test_build_accepts_unused_listening_model(tmp_path):
    source = json.loads((FIXTURES / "source.json").read_text())
    for class_record in source["classes"]:
        class_record["notes"] = [
            note for note in class_record["notes"] if note["type"] != "listening"
        ]
    reviewed = tmp_path / "no-listening.json"
    reviewed.write_text(json.dumps(source, ensure_ascii=False))

    exit_code, output, _ = run_build(tmp_path, reviewed)

    assert exit_code == 0
    _, ordinals, _ = inspect_ids(output, tmp_path)
    assert MODEL_IDS["listening"] not in ordinals


def test_build_report_records_progress_preservation_invariants(tmp_path):
    exit_code, _, state = run_build(tmp_path)

    assert exit_code == 0
    validation = json.loads((state / "build-report.json").read_text())["validation"]
    assert validation["template_ordinals"] == {
        str(MODEL_IDS["vocabulary"]): [0, 1, 2],
        str(MODEL_IDS["sentence"]): [0, 1],
        str(MODEL_IDS["listening"]): [0],
    }
    assert validation["deck_ids"]["Chinese Classes"] == class_deck_id("Chinese Classes")
    assert validation["tags_valid"] is True
    assert validation["media_references_valid"] is True


def test_second_build_adds_class_without_changing_existing_ids(tmp_path):
    first_code, first_package, state = run_build(tmp_path)
    first_ids = inspect_ids(first_package, tmp_path)
    source = json.loads((FIXTURES / "source.json").read_text())
    source["classes"].append({
        "date": "2026-10-01",
        "folder_id": "folder-october",
        "approved": True,
        "source_files": [],
        "notes": [{
            "type": "vocabulary",
            "chinese": "秋天",
            "pinyin": "qiūtiān",
            "meaning": "autumn",
        }],
        "issues": {},
    })
    updated_source = tmp_path / "updated.json"
    updated_source.write_text(json.dumps(source, ensure_ascii=False))
    second_package = tmp_path / "Chinese-Classes-updated.apkg"

    second_code, _, _ = run_build(tmp_path, updated_source, second_package)
    second_ids = inspect_ids(second_package, tmp_path)

    assert first_code == second_code == 0
    first_notes, first_ordinals, first_decks = first_ids
    second_notes, second_ordinals, second_decks = second_ids
    assert first_notes.items() <= second_notes.items()
    assert first_ordinals == second_ordinals
    assert first_decks.items() <= second_decks.items()
    added_name = class_deck_name("2026-10-01")
    assert second_decks[added_name] == class_deck_id(added_name)
    assert json.loads((state / "build-report.json").read_text())["merge"]["new_classes"] == ["2026-10-01"]
