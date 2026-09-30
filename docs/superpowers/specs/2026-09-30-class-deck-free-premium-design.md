# Class Deck Free and Premium Upgrade Design

## Goal

Upgrade the incremental Chinese class deck generator so every dated class deck contains the relevant vocabulary, sentence-pattern, Vietnamese-to-Chinese, and listening cards while preserving existing Anki scheduling. Vocabulary cards receive the writing features from Anki xiehanzi; listening and sentence-pattern cards remain focused on their own learning tasks.

## User outcome

After each class, the learner imports one updated `.apkg`. Existing cards retain their review history, corrected material updates in place, and new material appears under the new class date. New cards in a class are introduced in the pedagogical order vocabulary, sentence patterns, then listening.

## Deck organization and ordering

The existing per-class hierarchy remains authoritative:

```text
Chinese Classes
├── YYYY-MM-DD
├── YYYY-MM-DD
└── YYYY-MM-DD
```

All card categories for a class live directly in that class's dated deck. The generator assigns deterministic new-card positions in this order:

1. vocabulary cards;
2. sentence-pattern cards;
3. listening cards.

Anki may mix cards after they enter learning or review according to their individual schedules. The generator does not attempt to override Anki's scheduler.

## Stage 1: Free-deck parity

### Vocabulary

Each vocabulary note produces:

- a Chinese-to-Vietnamese recognition card;
- a Vietnamese-to-Chinese production card.

Vocabulary cards reuse the free Anki xiehanzi capabilities applicable to the supplied class word:

- simplified and traditional forms;
- tone-marked pinyin and Zhuyin;
- tone-colored characters, pinyin, and strokes;
- pronunciation audio when available;
- definitions, part of speech, radical, character breakdown, HSK band, frequency, and reviewed examples when data is available;
- Hanzi Writer stroke animation and practice grid;
- night mode, adjustable character and stroke sizes, hints, replay, and field visibility controls;
- external lookup links and load status where supported by the existing free template;
- bundled fonts, scripts, stroke data, images, and audio for offline study.

Stroke writing is enabled only for vocabulary notes. A character without stroke data must fall back to an intact text card without presenting a broken drawing area.

### Sentence patterns

Each reviewed sentence pattern produces:

- the existing prompt or recognition card appropriate to the source exercise;
- a Vietnamese-to-Chinese production card.

The answer side displays the reviewed Chinese answer, pinyin, explanation where supplied, and audio where available. Sentence-pattern cards do not include stroke-writing practice.

### Listening

Every class recording is transcribed, manually reviewed, and split into sentence-level clips. Each approved segment produces one listening card:

- front: only the segment audio;
- back: replay controls, corrected Chinese transcript, and pinyin.

Listening cards contain neither Vietnamese/English translation nor stroke-writing practice. Long recordings are never used as a single review card when sentence segmentation is possible.

The review workflow exposes segment audio, boundaries, transcript, pinyin, and uncertainty. Uncertain segments remain flagged and are excluded from the final deck until approved.

## Stage 2: Premium upgrade

Premium extends the same dated class decks rather than creating a parallel deck tree. It adds:

- independent vocabulary Recognition and Writing cards with separate scheduling;
- the premium redesigned card layout;
- an offline searchable dictionary accessible within vocabulary cards;
- the expandable full example-sentence corpus with a `Load more` interaction.

Premium features do not add stroke writing to sentence-pattern or listening cards. Upgrading must not replace or renumber existing free cards. New premium cards use new stable card-template identities so Anki adds them while retaining the scheduling of free cards.

## Source and review pipeline

For every dated class, the pipeline:

1. imports Drive and Zalo materials into the dated class record;
2. extracts vocabulary, Vietnamese meanings, and sentence patterns;
3. transcribes all recordings and divides them into persistent sentence segments;
4. generates pinyin for vocabulary, patterns, and listening transcripts;
5. produces a human review report containing extracted text, Vietnamese-to-Chinese prompts, audio clips, segment boundaries, transcripts, pinyin, and unresolved issues;
6. builds notes only from approved material;
7. packages the selected free or premium edition into the cumulative `.apkg`.

Automated output is evidence for review, not authority over teacher-provided material. Teacher corrections and approved Zalo evidence override automated extraction.

## Stable identity and upgrades

The identity scheme must preserve progress independently of editable learning content:

- vocabulary and sentence notes derive identity from the class date, source identity, content category, and persistent item ID;
- listening notes derive identity from the original recording identity plus a persistent segment ID;
- note GUIDs never depend on Chinese, Vietnamese, pinyin, transcript wording, or mutable audio boundaries;
- model IDs and existing template ordinals remain stable after release;
- corrected text, pinyin, metadata, media, or segment timing updates the existing note;
- newly introduced premium templates add cards without replacing free cards.

The build reports removed, merged, or unmatched source items. It does not silently delete already-imported Anki cards because package imports do not provide a reliable progress-safe deletion mechanism.

## Component boundaries

The implementation should keep these responsibilities separate:

- **Source normalization:** converts Drive/Zalo evidence into dated, persistent source items.
- **Language enrichment:** supplies traditional forms, pinyin, Zhuyin, dictionary metadata, and examples without deciding card layout.
- **Audio processing:** transcribes, segments, exports clips, and records confidence/review state.
- **Review data:** stores approvals and corrections without changing persistent identities.
- **Edition templates:** adapts the repository's existing free and premium Anki xiehanzi templates to class notes.
- **Package builder:** assigns decks, ordering, models, GUIDs, and offline media.
- **Validation:** inspects schemas, templates, media references, ordering, identities, and upgrade behavior before an `.apkg` is published.

## Failure behavior

- Missing or unsupported stroke data yields a functional text card.
- Missing audio suppresses audio-dependent cards rather than producing blank fronts.
- An unapproved or uncertain transcript cannot enter the final deck.
- Unmatched recordings remain visible in the review report.
- Duplicate segments or source items are detected before packaging.
- Missing bundled media, template field mismatches, and duplicate model/card identities fail the build.
- A package upgrade that changes an existing GUID, model ID, or template ordinal without an explicit migration fails compatibility validation.

## Verification and acceptance criteria

Stage 1 is complete when:

- every dated class remains a single deck containing all its card categories;
- deterministic new-card ordering is vocabulary, patterns, listening;
- vocabulary cards provide the applicable free writing and display features offline;
- vocabulary and sentence patterns both provide Vietnamese-to-Chinese cards;
- every approved recording segment produces an audio-front, transcript-and-pinyin-back listening card;
- sentence-pattern and listening cards contain no writing grid;
- importing a corrected build retains scheduling for existing cards;
- automated tests cover template fields, conditional cards, bundled media, stable GUIDs, stable model/template identities, segment identity, and package integrity.

Stage 2 is complete when:

- the same collection can be upgraded with premium vocabulary cards without losing free-card scheduling;
- Recognition and Writing cards schedule independently;
- the redesigned layout, offline dictionary, and expandable example corpus work without a network connection;
- the premium edition does not change sentence-pattern or listening scope;
- free-to-premium import compatibility is verified against a seeded Anki collection.

Manual acceptance testing must cover current Anki Desktop, AnkiDroid, and AnkiMobile card rendering and interaction. Collection backups remain required before testing imports.
