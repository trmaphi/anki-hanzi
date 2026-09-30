# Incremental Chinese Class Deck Generator

## Purpose

Generate an importable Anki package from the user's dated Google Drive class folders. Each subsequent export must add newly available classes while preserving the scheduling and review history of notes imported from earlier exports.

## User outcome

The user imports one master `.apkg` package into Anki. The package contains a parent deck named `Chinese Classes` and one subdeck per class date. When a new class is added to the source folder, regenerating and importing the package updates existing notes and adds the new dated subdeck without duplicating existing cards or resetting their progress.

## Source organization

The source is a Google Drive folder whose direct children are class folders named as ISO dates, such as `2026-09-22`. Class folders may contain:

- vocabulary and lesson images;
- MP3 recordings;
- PDF course material; and
- files whose names do not describe their educational content.

The class date is the authoritative source identifier. Files are retained as source evidence, but a screenshot is not automatically one flashcard.

## Output structure

The generated package uses this deck hierarchy:

```text
Chinese Classes
├── 2026-07-20
├── 2026-07-24
└── 2026-09-22
```

All notes receive a tag in the form `Class::YYYY-MM-DD`. Additional tags identify the learning role, such as `Type::Vocabulary`, `Type::Sentence`, or `Type::Listening`.

The deliverables are:

- one versioned master `.apkg` file;
- a machine-readable manifest recording source identity and generated-note identity;
- an extraction file that can be reviewed and corrected before packaging; and
- a repeatable generator command documented in the repository.

## Note types and cards

### Vocabulary note

Fields:

- stable source key;
- simplified Chinese;
- traditional Chinese when available;
- tone-marked pinyin;
- concise English meaning;
- example sentence;
- example translation;
- image;
- word audio;
- class date; and
- source reference.

Cards:

1. Chinese recognition: Chinese to pronunciation and meaning.
2. Active production: meaning or image to spoken Chinese.
3. Listening: audio to Chinese, pronunciation, and meaning, only when suitable audio is available.

### Sentence-pattern note

Fields:

- stable source key;
- Chinese prompt or sentence;
- pinyin;
- English cue;
- answer or model response;
- explanation;
- audio;
- class date; and
- source reference.

Cards test active sentence production and, when audio exists, listening comprehension. A pattern such as `你觉得……怎么样？` is represented with useful completed examples rather than a grammar explanation alone.

### Listening note

Listening notes are used only when an MP3 can be associated confidently with a transcript. The front contains audio only; the back contains the transcript, pinyin, translation, and source date. Unmatched recordings remain listed in the extraction report and are not converted into speculative cards.

## Stable identity and progress preservation

The generator assigns deterministic identifiers to every persistent object:

- the parent deck has a fixed deck ID;
- a dated subdeck ID is derived deterministically from its ISO date;
- note-model IDs are fixed constants;
- each note GUID is derived from the class date, note type, and normalized primary Chinese content; and
- card-template ordinals remain stable across releases.

Re-exporting unchanged content therefore produces the same identity. Importing a later package updates matching notes and adds new notes while Anki retains card scheduling and review history.

Changing a meaning, pinyin value, example, image, or audio file does not change note identity. Moving a note to another date or changing its primary Chinese expression is treated as a new identity. Generated imports do not delete older notes automatically; removals are reported so the user can decide whether to suspend or delete them.

## Extraction and review

Content extraction is deliberately separated from packaging:

1. Discover dated class folders and inventory their files.
2. Extract candidate vocabulary, sentences, and media associations.
3. Normalize Chinese, pinyin, meanings, and source references.
4. Validate required fields and flag uncertain or duplicate candidates.
5. Write a reviewable extraction artifact.
6. Package only approved, valid entries.

This separation prevents OCR mistakes or ambiguous audio associations from silently entering the deck. Automated extraction may propose content, but uncertainty is preserved explicitly rather than guessed away.

## Incremental updates

The manifest stores, for each class, the Drive folder ID, source file IDs, source modification times, content hashes where available, and generated stable keys. A subsequent run compares current Drive metadata with the manifest:

- unchanged classes reuse their reviewed extraction data;
- new classes are extracted and added;
- changed classes are re-extracted and presented for review; and
- missing source material is reported but does not trigger destructive removal.

The resulting master package includes all approved classes so it can be imported as the next version of the same deck.

## Media handling

Images are cropped or associated with individual notes when a reliable mapping exists. Full lesson screenshots may be retained as source context on the back, but they are not used as the sole prompt for a large collection of answers.

Audio is copied into the Anki package under deterministic filenames. Class recordings take precedence over generated pronunciation. Existing repository pronunciation sources may be used for isolated vocabulary when class audio is unavailable, but generated or dictionary audio must be labeled separately from teacher-provided audio in extraction metadata.

All packaged media must work offline after import.

## Repository integration

The implementation will reuse the repository's existing `genanki-js`, dictionary, pinyin, note-field, and media-generation capabilities where they fit. Class-specific extraction, manifest management, and note models will be isolated from the existing HSK deck generator so the established exported decks and browser workflow do not change.

The generator will have a non-interactive entry point suitable for repeatable local execution. Credentials and authenticated Drive URLs will not be committed. Downloaded source material and generated packages will live in ignored working/output directories unless the user explicitly chooses otherwise.

## Validation and testing

Automated tests will verify:

- deterministic deck IDs and note GUIDs;
- stable identities across field and media updates;
- distinct identities across class dates and note types;
- expected parent/subdeck hierarchy;
- correct tags and card-template counts;
- media references resolve inside the package;
- the generated `.apkg` contains a readable Anki SQLite collection; and
- a fixture representing a second class update adds notes without changing existing GUIDs.

The final package will be inspected by opening its embedded collection database and checking note, card, deck, tag, and media counts. A small rendered sample from each note type will also be reviewed for legibility.

## Non-goals

- Automatically deleting notes from the user's Anki collection.
- Guessing transcripts for audio that cannot be matched confidently.
- Converting every screenshot or PDF page into a card.
- Synchronizing directly with AnkiWeb.
- Changing the repository's existing HSK deck identities or export behavior.

## Success criteria

The work is complete when:

1. the current dated class folders can be converted into a single importable master package;
2. the package contains dated subdecks and the agreed vocabulary, sentence, and listening card types;
3. regenerating from an added class produces an updated package with stable existing identities;
4. automated round-trip tests pass; and
5. the user can follow a documented command to repeat the process for future classes.
