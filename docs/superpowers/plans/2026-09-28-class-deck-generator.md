# Incremental Chinese Class Deck Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deliver one incrementally upgradable `Chinese Classes.apkg` whose dated subdecks preserve existing Anki progress when later class material is added.

**Architecture:** A standalone Python package handles source validation, deterministic identities, media/PDF preparation, manifest merging, and Anki package construction. It consumes a reviewed JSON intermediate format so uncertain OCR or audio matches cannot silently become cards. Google Drive remains an authenticated ingestion source; private class files, manifests, and generated packages remain outside Git.

**Tech Stack:** Python 3.11+, `genanki`, `pypinyin`, Pillow, PyMuPDF, pytest, and existing repository card assets where reusable.

**Spec:** `docs/superpowers/specs/2026-09-28-class-deck-generator-design.md`

## Global Constraints

- The output parent deck is exactly `Chinese Classes`; each child deck is `Chinese Classes::YYYY-MM-DD`.
- Existing deck IDs, model IDs, note GUIDs, and card-template ordinals remain stable across rebuilds.
- Correcting a meaning, pinyin, example, image, or audio file does not change note identity.
- Missing source material is reported and never causes automatic deletion from Anki.
- Only confidently matched audio receives a listening card; unmatched audio remains in the report.
- All packaged media works offline.
- Google credentials, authenticated URLs, source class files, manifests, and generated packages are never committed.
- Existing JavaScript HSK deck exports and identities remain unchanged.

## Review Focus

- The same Chinese expression taught on two dates creates two distinct notes in the correct dated subdecks; Task 1 tests this.
- Corrected pinyin, meaning, or media retains the previous GUID; Task 1 tests this.
- Missing or ambiguous audio omits the listening card and appears in the report; Task 3 tests this.
- A disappeared source folder retains previously approved notes and is reported rather than deleted; Task 2 tests this.
- Unicode, spaces, and duplicate media basenames normalize without collisions and resolve inside the APKG; Task 3 tests this.

---

### Task 1: Python package, reviewed source schema, and deterministic identities

**Files:**
- Create: `class_deck/__init__.py`
- Create: `class_deck/models.py`
- Create: `class_deck/identity.py`
- Create: `tests/class_deck/test_models.py`
- Create: `tests/class_deck/test_identity.py`
- Create: `requirements-class-deck.txt`

**Interfaces:**
- Consumes: reviewed JSON dictionaries.
- Produces: `ClassSource.from_dict(value)`, `ClassSource.to_dict()`, `class_deck_name(date)`, `class_deck_id(name)`, `note_key(note)`, `note_guid(note)`, and `media_name(note_key, role, source_name)`.

- [ ] **Step 1: Write failing source and identity tests**

Add tests named `test_valid_reviewed_source_round_trip`, `test_invalid_date_reports_json_path`, `test_missing_primary_chinese_is_rejected`, `test_mutable_fields_do_not_change_guid`, `test_date_and_note_type_change_guid`, and `test_media_names_are_unicode_safe_and_collision_resistant`. Assert exact parent/subdeck names and deterministic results across repeated calls.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `python -m pytest tests/class_deck/test_models.py tests/class_deck/test_identity.py -q`

Expected: FAIL because the `class_deck` package does not exist.

- [ ] **Step 3: Implement typed immutable source models**

Use frozen dataclasses for `ClassSource`, `ClassRecord`, `VocabularyNote`, `SentenceNote`, `ListeningNote`, `MediaRef`, and `SourceFile`. Validation errors include a JSON path such as `classes[0].notes[2].chinese`. Note types accept mutable learning fields but require `date`, `type`, and normalized primary Chinese identity fields.

- [ ] **Step 4: Implement deterministic identity helpers**

Generate numeric deck/model IDs inside Anki's valid signed 31-bit range using fixed namespaces. Generate a deterministic 14-character base-36 note GUID from `date:type:normalized-primary-Chinese`; never include pinyin, translation, examples, or media.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest tests/class_deck/test_models.py tests/class_deck/test_identity.py -q`

Expected: all tests PASS.

```bash
git add class_deck tests/class_deck requirements-class-deck.txt
git commit -m "feat: define Python class deck source model"
```

### Task 2: Incremental manifest and non-destructive merge

**Files:**
- Create: `class_deck/manifest.py`
- Create: `tests/class_deck/test_manifest.py`

**Interfaces:**
- Consumes: `merge_manifest(previous: ClassManifest | None, incoming: ClassSource) -> MergeResult`.
- Produces: `MergeResult(source, new_classes, changed_classes, missing_classes, unchanged_classes)` and serializable `ClassManifest` records containing folder/file IDs, modification times, hashes when available, approval state, note keys, and reviewed content.

- [ ] **Step 1: Write failing incremental merge tests**

Add `test_first_import_marks_all_classes_new`, `test_unchanged_class_reuses_reviewed_content`, `test_added_class_preserves_old_keys_and_guids`, `test_changed_files_require_re_review`, and `test_missing_class_is_retained_and_reported`. The final test must prove no approved note disappears from the merged source.

- [ ] **Step 2: Run the test and verify failure**

Run: `python -m pytest tests/class_deck/test_manifest.py -q`

Expected: FAIL because `class_deck.manifest` does not exist.

- [ ] **Step 3: Implement the manifest merge**

Compare Drive folder ID, file ID, modified timestamp, and available content hash. Reuse approved unchanged content; mark new/changed classes for review; retain missing approved classes; and return deterministic status lists sorted by ISO date.

- [ ] **Step 4: Run tests and commit**

Run: `python -m pytest tests/class_deck/test_manifest.py -q`

Expected: all tests PASS.

```bash
git add class_deck/manifest.py tests/class_deck/test_manifest.py
git commit -m "feat: preserve reviewed classes across incremental builds"
```

### Task 3: Anki models, templates, and offline APKG builder

**Files:**
- Create: `class_deck/templates.py`
- Create: `class_deck/package.py`
- Create: `tests/class_deck/test_package.py`
- Create: `tests/class_deck/fixtures/source.json`
- Create: `tests/class_deck/fixtures/media/`

**Interfaces:**
- Consumes: `build_package(source: ClassSource, media_root: Path, output: Path) -> BuildReport`.
- Produces: `BuildReport(notes, cards, decks, media, warnings, output_sha256)` and fixed exported `MODEL_IDS`/template ordinals.

- [ ] **Step 1: Write failing APKG round-trip tests**

Add `test_builds_parent_and_dated_subdecks`, `test_vocabulary_has_recognition_production_and_conditional_listening`, `test_sentence_and_listening_models_have_fixed_ordinals`, `test_ambiguous_audio_is_warning_not_card`, `test_media_names_resolve_without_collisions`, and `test_collection_database_round_trip`. Open the produced ZIP and SQLite collection to assert exact deck names, GUID uniqueness, tags, model IDs, card counts, and media mappings.

- [ ] **Step 2: Run the test and verify failure**

Run: `python -m pytest tests/class_deck/test_package.py -q`

Expected: FAIL because package construction does not exist.

- [ ] **Step 3: Implement card templates**

Define fixed models for vocabulary, sentence pattern, and listening notes. Vocabulary creates recognition and production cards plus listening only with approved matched audio. Sentence patterns create active production plus optional listening. Listening notes create one audio-first card. Templates show Chinese, tone-marked pinyin, meaning/translation, example, date, and available image/audio with mobile-friendly CSS.

- [ ] **Step 4: Implement package and media construction**

Create the parent and deterministic dated decks with `genanki`; add notes with Task 1 GUIDs and `Class::YYYY-MM-DD`/`Type::*` tags. Copy approved media under deterministic names, warn on missing or ambiguous inputs, write atomically to the requested `.apkg`, and compute its SHA-256.

- [ ] **Step 5: Run tests and commit**

Run: `python -m pytest tests/class_deck/test_package.py -q`

Expected: all tests PASS.

```bash
git add class_deck/templates.py class_deck/package.py tests/class_deck/test_package.py tests/class_deck/fixtures
git commit -m "feat: generate offline multimedia class decks"
```

### Task 4: Drive inventory preparation and reviewed extraction workflow

**Files:**
- Create: `class_deck/ingest.py`
- Create: `class_deck/review.py`
- Create: `tests/class_deck/test_ingest.py`
- Create locally, ignored: `.class-deck/current/inventory.json`
- Create locally, ignored: `.class-deck/current/reviewed-source.json`
- Create locally, ignored: `.class-deck/current/media/`

**Interfaces:**
- Consumes: connector-produced Drive metadata JSON plus materialized media files.
- Produces: `prepare_inventory(raw) -> Inventory`, `prepare_review(inventory, media_root) -> ReviewDraft`, rendered PDF pages/contact sheets, and a review JSON accepted by `ClassSource.from_dict`.

- [ ] **Step 1: Write failing ingestion tests**

Add `test_accepts_only_iso_dated_class_folders`, `test_preserves_drive_file_identity`, `test_extracts_pdf_text_and_renders_pages`, `test_images_become_review_candidates_not_automatic_notes`, and `test_unmatched_audio_remains_an_issue`.

- [ ] **Step 2: Run the test and verify failure**

Run: `python -m pytest tests/class_deck/test_ingest.py -q`

Expected: FAIL because ingestion helpers do not exist.

- [ ] **Step 3: Implement inventory and review preparation**

Normalize connector metadata, route non-date folders to `unassigned`, extract embedded PDF text with PyMuPDF, render PDF pages and image contact sheets, and create candidate records carrying exact source references. Do not automatically approve OCR/image text or infer audio transcripts.

- [ ] **Step 4: Ingest and review the current Drive folder**

Inventory every dated folder and file. Inspect the prepared pages/images, transcribe vocabulary and useful sentence patterns, verify pinyin/English, and associate MP3 only when lesson context establishes the transcript. Store unresolved readings/translations and unmatched audio under `issues`, not approved notes.

- [ ] **Step 5: Run tests and commit reusable ingestion code**

Run: `python -m pytest tests/class_deck/test_ingest.py -q`

Expected: all tests PASS.

```bash
git add class_deck/ingest.py class_deck/review.py tests/class_deck/test_ingest.py
git commit -m "feat: prepare class media for reviewed extraction"
```

Do not commit `.class-deck/` contents.

### Task 5: CLI, verification, current deck build, and update documentation

**Files:**
- Create: `class_deck/cli.py`
- Create: `tests/class_deck/test_cli.py`
- Create: `docs/class-deck-generator.md`
- Modify: `.gitignore`
- Create locally, ignored: `output/class-decks/Chinese-Classes.apkg`

**Interfaces:**
- Consumes: `python -m class_deck.cli build --source <json> --media <dir> --state <dir> --out <apkg>` and `python -m class_deck.cli check ...`.
- Produces: APKG, state `manifest.json`, `build-report.json`, and exit status `0` only after validation and round-trip inspection succeed.

- [ ] **Step 1: Write failing CLI tests**

Add `test_check_reports_validation_paths`, `test_build_writes_package_manifest_and_report`, `test_failed_build_does_not_replace_previous_package`, and `test_second_build_adds_class_without_changing_existing_ids`.

- [ ] **Step 2: Run the test and verify failure**

Run: `python -m pytest tests/class_deck/test_cli.py -q`

Expected: FAIL because the CLI does not exist.

- [ ] **Step 3: Implement check/build commands and ignored paths**

The CLI validates source/media, merges state, builds to a temporary path, inspects the ZIP/SQLite/media map, then atomically replaces the requested output. Write counts, stable IDs, warnings, and hashes to the report. Ignore `.class-deck/`, `output/class-decks/`, Python caches, and the local virtual environment without modifying existing JavaScript build behavior.

- [ ] **Step 4: Build and inspect the current master deck**

Run: `python -m class_deck.cli build --source .class-deck/current/reviewed-source.json --media .class-deck/current/media --state .class-deck/current/state --out output/class-decks/Chinese-Classes.apkg`

Expected: exit `0`; every approved dated class is present; note/card counts match reviewed source; all media references resolve; no GUID duplicates exist.

- [ ] **Step 5: Prove progress-preserving update behavior**

Build a temporary source containing one synthetic later class and compare both collection databases. All original GUIDs, model IDs, template ordinals, and deck IDs remain unchanged; only the synthetic deck/notes are added.

- [ ] **Step 6: Document future class updates**

Explain the authenticated Drive ingestion/review step, CLI commands, warning review, Anki backup, and importing the replacement package. State explicitly that import adds/updates notes but never automatically deletes old notes.

- [ ] **Step 7: Run full verification and commit**

Run: `python -m pytest tests/class_deck -q`

Run: `npm test`

Run: `npm run check`

Run: `npm run build`

Expected: all commands exit `0`.

```bash
git add class_deck tests/class_deck requirements-class-deck.txt docs/class-deck-generator.md .gitignore
git commit -m "feat: deliver incremental Chinese class deck generator"
```

Do not commit private Drive sources, manifests, media, or generated `.apkg` files.
