# Chinese class Anki deck generator

This generator produces one importable `Chinese-Classes.apkg` containing the parent deck **Chinese Classes** and one subdeck for every approved class date. Its stable deck IDs, note GUIDs, model IDs, and card-template order let a later package add classes or correct reviewed content without resetting existing Anki scheduling progress.

The unified package contains the complete vocabulary experience (Recognition, Production, Listening when approved audio exists, and Writing), sentence-pattern cards, and audio-first listening cards. Vocabulary cards bundle the xiehanzi writer, tone colours, traditional characters, pinyin, Zhuyin, definitions, character breakdowns, radicals, HSK/frequency metadata, an offline dictionary, and an expandable offline example corpus. Sentence and listening cards deliberately do not expose the writer, dictionary, or example controls.

## Daily study strategy

Study the parent **Chinese Classes** deck so Anki mixes all dated lessons according to need. Within each class, new cards are positioned vocabulary first, sentence patterns second, and listening last. Vocabulary includes both Chinese-to-meaning and meaning-to-Chinese production. Say every answer aloud before revealing it. Sentence cards train active use rather than isolated recognition. Keep new cards modest (about 10–20 per day) and complete reviews before adding more.

The dated subdecks are useful for a short lesson preview or catch-up session. They are not separate learning tracks: normal daily study should return to the parent deck.

## Build the reviewed deck

Create the Python environment once and install the generator dependencies:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-class-deck.txt
```

The source workflow is deliberately review-first:

1. Fetch the authenticated Drive folder inventory and materialize its class files under `.class-deck/current/media/`.
2. Prepare PDF pages and image contact sheets with `class_deck.ingest` and `class_deck.review`.
3. Verify Chinese, tone-marked pinyin, English, examples, and media matches in `.class-deck/current/reviewed-source.json`. Do not approve OCR guesses.
4. Transcribe every class recording into persistent `recording_id` + `segment_id` drafts. Review the Chinese against the recording, regenerate pinyin after corrections, and approve only complete dialogue/sentence clips. Pronunciation and isolated-word drills remain visible in the review data but are excluded from sentence-level listening cards. Listening cards contain no English or Vietnamese: the front is audio only, and the back contains the Chinese transcript, pinyin, and replay controls.
5. Validate and build to a staging path:

```bash
.venv/bin/python -m class_deck.cli check \
  --source .class-deck/current/reviewed-source.json \
  --media .class-deck/current/media

.venv/bin/python -m class_deck.cli build \
  --source .class-deck/current/reviewed-source.json \
  --media .class-deck/current/media \
  --state .class-deck/current/state \
  --out output/class-decks/Chinese-Classes.staging.apkg \
  --baseline output/class-decks/Chinese-Classes.apkg
```

Inspect `.class-deck/current/state/build-report.json` before promoting the staged file. Warnings identify missing or ambiguous media that were safely omitted. The compatibility section must report every released note and card as preserved and must report zero removals.

The offline payload is intentionally large because it includes collision-safe, `cdx1-`-namespaced stroke, dictionary, example, SQL/Wasm, persistence, and speech assets. Release builds target at most 60 MiB and must stop above 75 MiB unless that limit is explicitly reconsidered. A missing stroke-data entry hides only the drawing component; the Writing card remains a readable text card.

## Add a later class without losing progress

Keep `.class-deck/current/state/manifest.json`. Add the new dated folder to the inventory, review its notes, then run the same build command. The new class becomes `Chinese Classes::YYYY-MM-DD`; existing identities remain unchanged.

**Before the first migration import, back up the complete Anki profile and include scheduling information.** This upgrade requires Anki 23.10 or newer. In **File → Import**, expand **Updates**, enable **Merge note types**, and leave **Import any learning progress** and **Import any deck presets** disabled. Keep **Update notes** and **Update note types** set to **If newer**, then import the replacement APKG into the same profile. Anki will merge the extended vocabulary note type, update the 320 released notes in place, retain the existing Recognition/Production/Listening scheduling rows, and add Writing as New. Persistent item and segment identities mean later wording, pinyin, or transcript corrections update those notes without resetting progress.

Do not accept the default import settings for this first upgrade. Without **Merge note types**, Anki treats the extended vocabulary schema as a separate `Chinese Classes - Vocabulary+` note type: the listening notes are added, but the 261 Writing cards are not attached to the existing vocabulary notes. A disposable Desktop test produced 358 notes but only 619 cards in that incorrect state, instead of the expected 358 notes and 880 cards.

Importing an identical package again must add zero notes and zero cards. This workflow never automatically deletes old notes: if a source folder disappears, its previously approved content remains in the manifest and the build report marks the class as missing. Delete superseded notes manually only after confirming that is intentional.

## Release candidate metadata

The 2026-10-01 staged candidate uses engine bundle `xiehanzi-class-deck-v1` (schema 1):

- SHA-256: `84b4e2f133c345090d25c5283f6b6e89008a905f43d0991ad6de243879332341`
- Size: 54,199,207 bytes (51.69 MiB)
- Collection: 358 notes, 880 cards, 24 decks, 47 media files
- Upgrade result: 320 notes and 581 cards preserved; 38 listening notes and 261 Writing cards added; 0 notes/cards removed; 0 build warnings
- Recording review: all 14 recordings transcribed; 38 sentence/turn clips from 7 dialogue recordings approved; 7 pronunciation/isolated-word recordings retained as unresolved review material and excluded

The package itself, source recordings, transcript drafts, manifests, and build reports are private/generated artifacts and remain outside Git.

## Required client smoke test

Before distributing to teachers, use disposable profiles that already contain the old package and record results for Anki Desktop, AnkiDroid, and AnkiMobile:

1. Back up, expand **Updates**, enable **Merge note types**, leave learning progress and deck presets disabled, confirm old due dates/intervals/reps remain and Writing is New, then import the same package again and confirm zero additions.
2. With networking disabled, verify vocabulary tone colours, pinyin, Zhuyin, traditional form, writer animation/practice and controls, night mode, field visibility, replay, offline dictionary (including an empty search), and expandable examples.
3. Verify a word without stroke data remains readable; missing audio never produces a blank front; sentence cards have no vocabulary-only controls; listening fronts are audio-only and backs contain Chinese, pinyin, and replay without translation.
4. Confirm new-card order is vocabulary, sentence patterns, then listening within each dated deck.

Automated APKG/SQLite checks are not substitutes for these client tests. In particular, record any AnkiMobile or AnkiDroid WebView limitation involving JavaScript, SQL/Wasm loading, media size, or sync before release rather than silently removing the affected feature.

### Observed client status (2026-10-01)

| Client | Migration/import | Repeated import | Offline feature smoke test | Status |
| --- | --- | --- | --- | --- |
| Anki Desktop (macOS) | Verified the 320-note baseline → unified migration with **Merge note types** enabled: 358 notes and 880 cards, including all 261 Writing cards on the original vocabulary note type. A reviewed baseline card retained its exact card ID, due value, 5-day interval, ease, review count, and lapse count after re-import. The default import was also tested and is documented as invalid (358 notes/619 cards plus `Chinese Classes - Vocabulary+`). | A second unified import showed all 358 entries as `Skipped`, kept the collection at 358 notes/880 cards, and preserved the reviewed card's scheduling row | Vocabulary answer rendered simplified text, pinyin, meaning, expandable definitions/examples, replay/menu controls, and the writing panel. Remaining sentence, listening, offline/degraded-stroke, missing-audio, night-mode, and interactive-control cases are not yet complete. | Partial |
| AnkiDroid | No Android device/client was available in this environment | Not run | Not run | Unverified |
| AnkiMobile | No iOS device/client was available in this environment | Not run | Not run | Unverified |

The artifact is therefore structurally verified and importable on Anki Desktop, but it is **not yet cleared as fully post-deployment verified on all three clients**. Complete the remaining matrix before broad teacher distribution.

The `.class-deck/` working data and generated `output/class-decks/` package are private local artifacts and are excluded from Git.
