# Chinese class Anki deck generator

This generator produces one importable `Chinese-Classes.apkg` containing the parent deck **Chinese Classes** and one subdeck for every approved class date. Its stable deck IDs, note GUIDs, model IDs, and card-template order let a later package add classes or correct reviewed content without resetting existing Anki scheduling progress.

## Daily study strategy

Study the parent **Chinese Classes** deck so Anki mixes all dated lessons according to need. For each new word, first recall the English meaning from Chinese, then produce the Chinese from English. Say every answer aloud before revealing it. Sentence cards train active use rather than isolated recognition. Keep new cards modest (about 10–20 per day) and complete reviews before adding more.

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
3. Verify Chinese, tone-marked pinyin, English, examples, and media matches in `.class-deck/current/reviewed-source.json`. Do not approve OCR guesses. Attach audio only when its transcript is established; leave exercise recordings under `issues.unmatched_audio` otherwise.
4. Validate and build:

```bash
.venv/bin/python -m class_deck.cli check \
  --source .class-deck/current/reviewed-source.json \
  --media .class-deck/current/media

.venv/bin/python -m class_deck.cli build \
  --source .class-deck/current/reviewed-source.json \
  --media .class-deck/current/media \
  --state .class-deck/current/state \
  --out output/class-decks/Chinese-Classes.apkg
```

Inspect `.class-deck/current/state/build-report.json` before importing. Warnings identify missing or ambiguous media that were safely omitted.

## Add a later class without losing progress

Keep `.class-deck/current/state/manifest.json`. Add the new dated folder to the inventory, review its notes, then run the same build command. The new class becomes `Chinese Classes::YYYY-MM-DD`; existing identities remain unchanged.

Back up the Anki profile before the first import. Import the replacement APKG into the same profile with note updates enabled. Anki will add new notes and update matching notes while retaining their review history. This workflow never automatically deletes old notes: if a source folder disappears, its previously approved content remains in the manifest and the build report marks the class as missing. Delete obsolete notes manually only after confirming that is intentional.

The `.class-deck/` working data and generated `output/class-decks/` package are private local artifacts and are excluded from Git.
