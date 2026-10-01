# Unified Full-Feature Chinese Class Deck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing Python class-deck generator so one cumulative `Chinese-Classes.apkg` delivers the complete offline xiehanzi vocabulary experience, Vietnamese-to-Chinese sentence practice, and reviewed sentence-level listening while preserving every released note and card identity.

**Architecture:** The existing pure TypeScript card compiler remains the source of truth for card HTML/CSS and emits one deterministic, versioned JSON template bundle with namespaced media references. Python validates and consumes that bundle, enriches reviewed notes, transcribes and segments approved audio, packages all offline assets, and performs SQLite-level compatibility checks against the released APKG before replacing any distributable artifact.

**Tech Stack:** TypeScript/Node 18+, existing `deckTemplate.ts`/`noteFields.ts`/dictionary modules, Python 3.11+, `genanki==0.13.1`, `pypinyin`, `faster-whisper`, ffmpeg/ffprobe, Pillow, PyMuPDF, pytest, Vitest, SQLite APKG inspection.

**Spec:** `docs/superpowers/specs/2026-10-01-unified-class-deck-design.md`

## Global Constraints

- Keep the parent/child hierarchy exactly `Chinese Classes::YYYY-MM-DD`; all categories for one lesson share that dated deck.
- Preserve model IDs `1956836792`, `1740209695`, and `1680100180`.
- Preserve all released field ordinals; append vocabulary fields `Zhuyin, PartOfSpeech, Definitions, Breakdown, Radical, HskLevel, Frequency` at ordinals 10–16 and append any sentence/listening fields after their released fields.
- Preserve vocabulary template ordinals `0 Recognize`, `1 Produce`, `2 Listen`; add `3 Writing`. Preserve sentence `0 Produce`, `1 Listen` and listening `0 Listen`.
- Reproduce all 320 released GUIDs and 581 released cards before permitting a migration build.
- New identity fields must be independent of editable Chinese, Vietnamese, pinyin, transcript text, and clip boundaries while retaining exact legacy GUIDs through an explicit migration seed.
- Generate Writing cards for every vocabulary note; when stroke data is absent, hide/disable only the writer and leave a readable text card.
- Listen templates require approved audio through explicit Anki `req`; never create a blank front.
- Prefix every engine asset with `cdx1-` and parameterize template URLs; never reuse bare xiehanzi media names.
- Package `_anki-tts.js` locally; remove the dead `_press.mp3` call; use one consistent `draw-size` default of 250 and `stroke-size` default within the declared 2–50 range.
- Preserve reviewed teacher values over inferred enrichment and record auto-filled fields.
- Keep `.class-deck/`, `output/class-decks/`, source media, credentials, manifests, and generated APKGs out of Git.
- Target APKG size is at most 60 MiB; stop for an explicit decision if the staged artifact exceeds 75 MiB.
- Do not change existing HSK/radical deck identities or generated outputs.

## Review Focus

- Legacy identity migration: all 320 shipped GUIDs and 581 card rows must be reproduced exactly before any new template/card is added; Task 4 tests this.
- Conditional cards: absent or unapproved audio must suppress ordinals 1/2 as applicable without blank fronts, while Writing always exists; Tasks 3 and 8 test this.
- Offline safety: dictionary/example text containing HTML, punctuation, Traditional text, or no match must render escaped, bounded, intact results without network access; Task 7 tests this.
- Cross-deck media safety: every engine asset must use the stable `cdx1-` namespace and every archive reference must resolve; Tasks 1 and 8 test this.
- Mobile-scale payloads: dictionary/example lookup must be indexed and paginated, and package size must remain below the 75 MiB stop threshold; Tasks 7 and 10 test this.

---

### Task 1: Deterministic TypeScript template-bundle exporter

**Files:**
- Create: `src/lib/classDeckBundle.ts`
- Create: `src/lib/classDeckBundle.test.ts`
- Create: `scripts/export-class-deck-bundle.mjs`
- Create: `class_deck/assets/class-deck-bundle.v1.json`
- Modify: `src/lib/deckTemplate.ts`
- Modify: `src/lib/dict/contants.ts`
- Modify: `package.json`

**Interfaces:**
- Consumes: `buildNoteTemplates`, `DECK_CSS`, tone palettes, card themes, field renderer constants, and existing xiehanzi card runtime.
- Produces: `buildClassDeckBundle(): ClassDeckBundleV1` containing `version`, ordered model/field-role maps, qfmt/afmt per fixed ordinal, CSS, tone palettes, writer controls, `SIDEBAR_SECTIONS`, `defaultOff`, explicit `req`, and logical-to-namespaced media mappings.
- Produces: `npm run build:class-deck-bundle` with byte-stable JSON output.

- [ ] **Step 1: Write failing bundle-contract tests**

Add tests named `emits_append_only_models_and_ordinals`, `namespaces_every_media_reference`, `keeps_writer_vocabulary_only`, `uses_local_anki_tts_without_press_sound`, `aligns_writer_control_defaults`, `renders_vietnamese_production_and_audio_only_listening`, and `regeneration_is_byte_stable`. Assert exact `cdx1-` media names and fixed template ordinals.

- [ ] **Step 2: Run the focused test and verify failure**

Run: `npx vitest run src/lib/classDeckBundle.test.ts`

Expected: FAIL because `classDeckBundle.ts` and the exported fixture do not exist.

- [ ] **Step 3: Implement the versioned bundle compiler**

Add `buildClassDeckBundle(): ClassDeckBundleV1` without importing genanki-js, sql.js runtime state, or SvelteKit. Parameterize all engine asset URLs, remove `_press.mp3`, point TTS to `cdx1-anki-tts.js`, and use `draw-size=250`, `stroke-size<=50` consistently.

- [ ] **Step 4: Implement deterministic export and generate the fixture**

Run: `npm run build:class-deck-bundle`

Expected: creates `class_deck/assets/class-deck-bundle.v1.json`; a second run makes no diff.

- [ ] **Step 5: Run tests and commit**

Run: `npx vitest run src/lib/classDeckBundle.test.ts`

Expected: PASS.

```bash
git add src/lib/classDeckBundle.ts src/lib/classDeckBundle.test.ts src/lib/deckTemplate.ts src/lib/dict/contants.ts scripts/export-class-deck-bundle.mjs class_deck/assets/class-deck-bundle.v1.json package.json
git commit -m "feat: export unified class deck template bundle"
```

### Task 2: Python bundle loader and schema validator

**Files:**
- Create: `class_deck/template_bundle.py`
- Create: `tests/class_deck/test_template_bundle.py`
- Modify: `class_deck/__init__.py`

**Interfaces:**
- Consumes: `class_deck/assets/class-deck-bundle.v1.json`.
- Produces: `load_template_bundle(path: Path | None = None) -> TemplateBundle` and `validate_model_contract(bundle: TemplateBundle, declarations: Mapping[str, ModelDeclaration]) -> None`.

- [ ] **Step 1: Write failing loader tests**

Add `test_loads_v1_bundle`, `test_rejects_missing_or_unknown_version`, `test_rejects_field_role_mismatch`, `test_rejects_duplicate_or_changed_ordinals`, and `test_rejects_unmapped_media_reference` with JSON-path-style errors.

- [ ] **Step 2: Run the focused test and verify failure**

Run: `.venv/bin/python -m pytest tests/class_deck/test_template_bundle.py -q`

Expected: FAIL because `class_deck.template_bundle` does not exist.

- [ ] **Step 3: Implement immutable bundle types and strict validation**

Parse only bundle version `1`; require exact ordered fields/templates, explicit `req`, and complete namespaced media mappings. Do not silently default missing contract data.

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/class_deck/test_template_bundle.py -q`

Expected: PASS.

```bash
git add class_deck/template_bundle.py class_deck/__init__.py tests/class_deck/test_template_bundle.py
git commit -m "feat: validate class deck template bundles"
```

### Task 3: Append-only Anki models and explicit template requirements

**Files:**
- Modify: `class_deck/templates.py`
- Modify: `tests/class_deck/test_package.py`
- Create: `tests/class_deck/test_templates.py`

**Interfaces:**
- Consumes: `TemplateBundle` from Task 2.
- Produces: `build_models(bundle: TemplateBundle | None = None) -> dict[str, genanki.Model]` with fixed field/template ordinals and explicit `_req` values.

- [ ] **Step 1: Write failing ordinal and conditionality tests**

Assert the exact released fields at their original ordinals, appended vocabulary fields at 10–16, exact template names/ordinals 0–3/0–1/0, Writing always generated, and Listen templates dependent only on the released `Audio` field.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `.venv/bin/python -m pytest tests/class_deck/test_templates.py tests/class_deck/test_package.py -q`

Expected: FAIL because the handwritten models lack appended fields, Writing, and explicit requirements.

- [ ] **Step 3: Implement bundle-backed models with explicit `req`**

Subclass `genanki.Model` as `ClassDeckModel` and override `_req` from validated bundle data. Preserve existing numeric model IDs and append-only fields/templates.

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/class_deck/test_templates.py tests/class_deck/test_package.py -q`

Expected: PASS with actual card ordinals read from the generated collection.

```bash
git add class_deck/templates.py tests/class_deck/test_templates.py tests/class_deck/test_package.py
git commit -m "feat: add full-feature append-only Anki models"
```

### Task 4: Persistent identities and released-package migration proof

**Files:**
- Modify: `class_deck/models.py`
- Modify: `class_deck/identity.py`
- Modify: `class_deck/manifest.py`
- Modify: `tests/class_deck/test_models.py`
- Modify: `tests/class_deck/test_identity.py`
- Modify: `tests/class_deck/test_manifest.py`
- Create: `tests/class_deck/test_migration.py`
- Modify locally, do not commit: `.class-deck/current/reviewed-source.json`

**Interfaces:**
- Produces: `BaseNote.item_id: str`, `BaseNote.identity_seed: str`, `ListeningNote.recording_id: str`, `ListeningNote.segment_id: str`, and `note_key(note: BaseNote) -> str`.
- Preserves: the exact legacy key through `identity_seed` for migrated notes; new notes key on persistent source/item or recording/segment identities.

- [ ] **Step 1: Write failing identity and migration tests**

Add tests for required persistent IDs, duplicate `item_id`/`recording_id+segment_id` rejection, mutable text/boundary independence, and exact GUID recovery from all 320 note rows in the shipped APKG. Assert the released package contains 581 pre-migration card rows before proceeding.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `.venv/bin/python -m pytest tests/class_deck/test_models.py tests/class_deck/test_identity.py tests/class_deck/test_manifest.py tests/class_deck/test_migration.py -q`

Expected: FAIL because the schema still keys identity on normalized Chinese.

- [ ] **Step 3: Implement persistent IDs and legacy migration seeds**

Require persistent IDs for new schema records, preserve JSON-path validation, and keep the old key only as an explicit `identity_seed` on migrated notes. Extend manifest merge without changing approved-note retention behavior.

- [ ] **Step 4: Migrate the ignored reviewed source and prove exact compatibility**

Run the migration into a temporary file first, compare every computed GUID against `output/class-decks/Chinese-Classes.apkg`, then atomically replace the ignored reviewed source only when all 320 match.

Expected: 320/320 GUIDs match and the baseline package still has exactly 581 cards; otherwise stop.

- [ ] **Step 5: Run tests and commit reusable code only**

Run: `.venv/bin/python -m pytest tests/class_deck/test_models.py tests/class_deck/test_identity.py tests/class_deck/test_manifest.py tests/class_deck/test_migration.py -q`

Expected: PASS.

```bash
git add class_deck/models.py class_deck/identity.py class_deck/manifest.py tests/class_deck/test_models.py tests/class_deck/test_identity.py tests/class_deck/test_manifest.py tests/class_deck/test_migration.py
git commit -m "feat: migrate class notes to persistent identities"
```

### Task 5: Reviewed language enrichment

**Files:**
- Create: `class_deck/enrichment.py`
- Modify: `class_deck/models.py`
- Modify: `class_deck/review.py`
- Create: `tests/class_deck/test_enrichment.py`
- Modify: `tests/class_deck/test_models.py`

**Interfaces:**
- Produces: `enrich_note(note: Note, assets: EnrichmentAssets) -> EnrichmentResult` and `EnrichmentResult(note, autofilled_fields, unresolved_fields)`.
- Supplies: traditional, pinyin, Zhuyin, POS, definitions, radical, breakdown, HSK level, frequency while never overwriting non-empty reviewed values.

- [ ] **Step 1: Write failing enrichment tests**

Add `test_preserves_every_reviewed_value`, `test_fills_only_blank_supported_fields`, `test_generates_pinyin_and_zhuyin`, `test_records_autofilled_and_unresolved_fields`, and `test_sentence_and_listening_scope_excludes_vocabulary_metadata`.

- [ ] **Step 2: Run the focused test and verify failure**

Run: `.venv/bin/python -m pytest tests/class_deck/test_enrichment.py tests/class_deck/test_models.py -q`

Expected: FAIL because the enrichment adapter and appended model fields do not exist.

- [ ] **Step 3: Implement enrichment adapters over committed data**

Use `pypinyin` and existing repository dictionaries. Preserve teacher content, record provenance, leave unsupported values blank, and escape only at render time rather than mutating reviewed text.

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/class_deck/test_enrichment.py tests/class_deck/test_models.py -q`

Expected: PASS.

```bash
git add class_deck/enrichment.py class_deck/models.py class_deck/review.py tests/class_deck/test_enrichment.py tests/class_deck/test_models.py
git commit -m "feat: enrich reviewed Chinese class notes"
```

### Task 6: Sentence-level transcription, segmentation, and review

**Files:**
- Create: `class_deck/audio.py`
- Create: `class_deck/transcribe.py`
- Modify: `class_deck/review.py`
- Modify: `class_deck/cli.py`
- Modify: `requirements-class-deck.txt`
- Create: `tests/class_deck/test_audio.py`
- Create: `tests/class_deck/test_transcribe.py`
- Modify: `tests/class_deck/test_cli.py`

**Interfaces:**
- Produces: `AudioSegment(segment_id: str, start_ms: int, end_ms: int, chinese: str, pinyin: str, confidence: float, approved: bool)`.
- Produces: `transcribe_recording(source: Path, recording_id: str, model_name: str, transcriber: Transcriber) -> tuple[AudioSegment, ...]`.
- Produces: `export_segment(source: Path, segment: AudioSegment, target: Path) -> Path` and CLI command `transcribe`.

- [ ] **Step 1: Write failing tests with injected ASR/ffmpeg runners**

Cover deterministic segment IDs, sentence splitting, pinyin, unchanged IDs after transcript/boundary correction, invalid/overlapping boundaries, missing ffmpeg/model errors, unapproved exclusion, and unmatched recording retention.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `.venv/bin/python -m pytest tests/class_deck/test_audio.py tests/class_deck/test_transcribe.py tests/class_deck/test_cli.py -q`

Expected: FAIL because transcription support does not exist.

- [ ] **Step 3: Add and install the pinned ASR dependency**

Add a pinned `faster-whisper` release compatible with the current Python runtime; keep model selection explicit through `--model`. Do not download a model during unit tests.

- [ ] **Step 4: Implement transcription, clip export, and review records**

Use ffprobe/ffmpeg for validated time ranges, `faster-whisper` for Mandarin draft text, `pypinyin` for pinyin, and `approved: false` by default. Review output includes source ID, clip path, boundaries, confidence, transcript, pinyin, and uncertainty.

- [ ] **Step 5: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/class_deck/test_audio.py tests/class_deck/test_transcribe.py tests/class_deck/test_cli.py -q`

Expected: PASS.

```bash
git add class_deck/audio.py class_deck/transcribe.py class_deck/review.py class_deck/cli.py requirements-class-deck.txt tests/class_deck/test_audio.py tests/class_deck/test_transcribe.py tests/class_deck/test_cli.py
git commit -m "feat: transcribe class recordings into reviewable clips"
```

### Task 7: Namespaced offline writer, dictionary, and example assets

**Files:**
- Create: `class_deck/assets.py`
- Create: `scripts/build-class-deck-assets.mjs`
- Create: `src/lib/classDeckOffline.ts`
- Create: `src/lib/classDeckOffline.test.ts`
- Modify: `class_deck/package.py`
- Create: `tests/class_deck/test_assets.py`
- Modify: `tests/class_deck/test_package.py`

**Interfaces:**
- Produces: `build_asset_manifest(repo_root: Path) -> AssetManifest` mapping logical bundle names to `cdx1-*` media files.
- Produces card runtime functions `searchDictionary(query, limit)` and `loadExamplePage(word, offset, limit)` backed only by bundled data.
- Consumes: `_hanzi-writer.min.js` (36,584 B), `hanzi-writer-data.json` (32,330,525 B), `_anki-tts.js` (23,920 B), `cedict.db.zip` (10,139,477 B), `hsk_sentences.db.zip` (8,459,361 B), `sql-wasm.wasm` (655,300 B), and `_anki-persistence.js` (2,272 B).

- [ ] **Step 1: Write failing asset and browser-runtime tests**

Assert exact namespaced media, deterministic manifest hashes, required dictionary index initialization, Simplified/Traditional/pinyin lookup, punctuation normalization, escaped HTML, no-result empty state, bounded results, paginated `Load more`, and no `http://`/`https://` runtime dependencies.

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `npx vitest run src/lib/classDeckOffline.test.ts`

Run: `.venv/bin/python -m pytest tests/class_deck/test_assets.py tests/class_deck/test_package.py -q`

Expected: FAIL because namespaced offline assets and runtimes do not exist.

- [ ] **Step 3: Implement deterministic asset staging and runtime**

Copy complete shared datasets under stable `cdx1-` names, initialize `idx_cedict_simplified`, use the existing token/substring strategy for sentences, escape all display text, paginate results, and expose intact empty states.

- [ ] **Step 4: Enforce size budget and reference closure**

Compute staged raw and compressed sizes. Expected raw engine/database payload is about 51.8 MB; the APKG target is <=60 MiB. Fail above 75 MiB pending explicit approval.

- [ ] **Step 5: Run tests and commit**

Run: `npx vitest run src/lib/classDeckOffline.test.ts`

Run: `.venv/bin/python -m pytest tests/class_deck/test_assets.py tests/class_deck/test_package.py -q`

Expected: PASS.

```bash
git add class_deck/assets.py class_deck/package.py scripts/build-class-deck-assets.mjs src/lib/classDeckOffline.ts src/lib/classDeckOffline.test.ts tests/class_deck/test_assets.py tests/class_deck/test_package.py
git commit -m "feat: bundle namespaced offline study assets"
```

### Task 8: Full note fields, card ordering, and package validation

**Files:**
- Modify: `class_deck/package.py`
- Modify: `class_deck/cli.py`
- Modify: `tests/class_deck/test_package.py`
- Modify: `tests/class_deck/test_cli.py`
- Create: `tests/class_deck/test_ordering.py`

**Interfaces:**
- Produces: `ordered_notes(record: ClassRecord) -> tuple[Note, ...]` ordered vocabulary, sentence, listening with persistent source order inside each category.
- Produces: exact bundle-aligned field arrays and `inspect_package(...)` checks for schemas, ordinals, requirements, media closure, blank fronts, identities, and due/order values.

- [ ] **Step 1: Write failing APKG inspection tests**

Read the generated SQLite collection and assert full fields, 4/2/1 templates, explicit `req`, Writing presence, conditional audio absence, vocabulary→sentence→listening new-card order, exact dated deck assignment, unique GUIDs, collision-safe media, and zero unresolved media references.

- [ ] **Step 2: Run focused tests and verify failure**

Run: `.venv/bin/python -m pytest tests/class_deck/test_package.py tests/class_deck/test_cli.py tests/class_deck/test_ordering.py -q`

Expected: FAIL against the simplified package builder.

- [ ] **Step 3: Implement full packaging and actual card counting**

Build field values by bundle roles, order note insertion deterministically, use generated SQLite card rows for `BuildReport.cards`, and fail atomically on blank fronts, missing assets, invalid field/template references, duplicate IDs, or ordering drift.

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/class_deck/test_package.py tests/class_deck/test_cli.py tests/class_deck/test_ordering.py -q`

Expected: PASS.

```bash
git add class_deck/package.py class_deck/cli.py tests/class_deck/test_package.py tests/class_deck/test_cli.py tests/class_deck/test_ordering.py
git commit -m "feat: package ordered full-feature class decks"
```

### Task 9: Idempotence, incremental updates, and scheduling-preserving upgrade

**Files:**
- Create: `class_deck/compatibility.py`
- Create: `tests/class_deck/test_upgrade.py`
- Modify: `class_deck/cli.py`
- Modify: `tests/class_deck/test_cli.py`

**Interfaces:**
- Produces: `compare_collections(before: Path, after: Path) -> CompatibilityReport` covering decks, models, fields, templates, notes, cards, and scheduling columns.
- Produces: CLI validation that blocks incompatible migration output before artifact replacement.

- [ ] **Step 1: Write failing upgrade tests**

Seed scheduling data into a copy of the released 320-note/581-card collection, apply the unified package, and assert every released note/card identity plus due, interval, ease, reps, and lapses is retained; only ordinal-3 Writing cards are New. Import the same package twice and assert zero duplicates. Build a synthetic later class and assert only its deck/notes/cards are added.

- [ ] **Step 2: Run the focused test and verify failure**

Run: `.venv/bin/python -m pytest tests/class_deck/test_upgrade.py tests/class_deck/test_cli.py -q`

Expected: FAIL because collection compatibility comparison does not exist.

- [ ] **Step 3: Implement collection comparison and CLI gate**

Compare authoritative SQLite rows and fail on any released GUID, model ID, field ordinal, template ordinal, deck ID, or scheduling regression. Report expected new Writing cards separately.

- [ ] **Step 4: Run tests and commit**

Run: `.venv/bin/python -m pytest tests/class_deck/test_upgrade.py tests/class_deck/test_cli.py -q`

Expected: PASS for idempotence, migration, and synthetic-class scenarios.

```bash
git add class_deck/compatibility.py class_deck/cli.py tests/class_deck/test_upgrade.py tests/class_deck/test_cli.py
git commit -m "test: prove progress-safe unified deck upgrades"
```

### Task 10: Process private recordings, build the release candidate, and document deployment

**Files:**
- Modify locally, do not commit: `.class-deck/current/reviewed-source.json`
- Create locally, do not commit: `.class-deck/current/media/<dated sentence clips>`
- Modify locally, do not commit: `.class-deck/current/state/manifest.json`
- Modify locally, do not commit: `.class-deck/current/state/build-report.json`
- Create locally, do not commit: `output/class-decks/Chinese-Classes.apkg`
- Modify: `docs/class-deck-generator.md`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: all 14 present class recordings and all approved reviewed source material.
- Produces: one staged unified APKG, SHA-256, size/count metadata, engine-bundle version, compatibility report, and teacher-facing release instructions.

- [ ] **Step 1: Transcribe all recordings and generate review clips**

Run the new `transcribe` command for all unmatched recordings. Review every sentence against audio, correct Chinese, regenerate pinyin, approve confident segments, and leave uncertain segments explicitly unresolved and excluded.

- [ ] **Step 2: Validate the reviewed source**

Run: `.venv/bin/python -m class_deck.cli check --source .class-deck/current/reviewed-source.json --media .class-deck/current/media`

Expected: exit 0; no duplicate IDs; every included listening segment is approved and has resolvable audio.

- [ ] **Step 3: Build to staging and run real-package inspection**

Run: `.venv/bin/python -m class_deck.cli build --source .class-deck/current/reviewed-source.json --media .class-deck/current/media --state .class-deck/current/state --out output/class-decks/Chinese-Classes.staging.apkg`

Expected: exact dated deck set/IDs; full model fields/templates; unique GUIDs; required new-card order; all media references resolve; APKG <=60 MiB target and never >75 MiB without approval.

- [ ] **Step 4: Run all automated verification gates**

Run: `.venv/bin/python -m pytest tests/class_deck -q`

Run: `npm test`

Run: `npm run check`

Run: `npm run build`

Expected: every command exits 0; existing HSK/radical outputs and identities remain unchanged.

- [ ] **Step 5: Promote the staged artifact and record release metadata**

Only after Tasks 1–4 pass, atomically replace `output/class-decks/Chinese-Classes.apkg`; record SHA-256, size, note/card/deck counts, bundle version, warnings, and compatibility results in the ignored build report.

- [ ] **Step 6: Update documentation and ignored paths**

Document backup-with-scheduling preflight, first migration import, repeated updates, new Writing cards, offline payload/size, transcription review, manual deletion of superseded notes, and real-client verification steps/limitations. Keep all private/generated artifacts ignored.

- [ ] **Step 7: Run documentation checks and commit**

Run: `git status --short --ignored`

Expected: no private source, manifest, media, credentials, or APKG is staged.

```bash
git add docs/class-deck-generator.md .gitignore
git commit -m "docs: release unified full-feature class deck"
```

### Task 11: Real-client post-deployment verification

**Files:**
- Modify: `docs/class-deck-generator.md`

**Interfaces:**
- Consumes: staged/released APKG and disposable profiles on Anki Desktop, AnkiDroid, and AnkiMobile.
- Produces: a documented platform matrix with observed behavior and every limitation.

- [ ] **Step 1: Verify migration and idempotence on each client**

Back up, import over the old deck with note updates enabled, confirm released scheduling survives and Writing is New, then import the same package again and confirm zero new notes/cards.

- [ ] **Step 2: Verify vocabulary offline on each client**

In airplane mode test tone colors, pinyin, Zhuyin, traditional, writer animation/quiz, replay/reveal/outline/hint, sizes, night mode, field visibility, dictionary search/empty state, expandable examples, and available audio.

- [ ] **Step 3: Verify degraded and non-vocabulary behavior**

Confirm missing stroke data leaves readable text, missing audio never creates blank fronts, sentence cards expose no writer/dictionary/examples, listening fronts are audio-only and backs show Chinese/pinyin/replay without translation, and new-card order is vocabulary→sentence→listening.

- [ ] **Step 4: Document observed platform limitations and commit**

If a required feature fails on a client, stop release and document the exact WebView/sql.js/media limitation before choosing a fix. Do not substitute fixture results for this manual evidence.

```bash
git add docs/class-deck-generator.md
git commit -m "docs: record unified deck client verification"
```
