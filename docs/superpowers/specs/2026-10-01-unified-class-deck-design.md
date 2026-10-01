# Unified Full-Feature Class Deck Design

## Goal

Produce one cumulative `Chinese-Classes.apkg` that combines every approved class with the complete applicable Anki xiehanzi experience. Each subsequent build updates existing notes in place, adds new class material, and preserves Anki scheduling.

There are no free and premium editions. Every supported feature ships in the same deck from the first release.

## Deck organization

The existing per-class hierarchy remains authoritative:

```text
Chinese Classes
├── YYYY-MM-DD
├── YYYY-MM-DD
└── YYYY-MM-DD
```

All cards for a class live directly in that class's dated deck. New cards are inserted in this pedagogical order:

1. vocabulary;
2. sentence patterns;
3. listening.

Anki may mix cards after they enter learning or review according to their individual schedules.

## Vocabulary cards

Every approved vocabulary item produces three independently scheduled cards:

1. **Recognition:** Chinese to Vietnamese.
2. **Production:** Vietnamese to Chinese.
3. **Writing:** recall and draw the Chinese word stroke by stroke.

Vocabulary cards provide the applicable advanced Anki xiehanzi features:

- simplified and traditional forms;
- tone-marked pinyin and Zhuyin;
- tone-colored characters, pinyin, and strokes;
- pronunciation audio when available;
- definitions, part of speech, radical, character breakdown, HSK band, frequency, and reviewed examples when data is available;
- Hanzi Writer animation and interactive practice;
- replay, reveal, outline, hint, character-size, and stroke-width controls;
- night mode and per-side field visibility;
- redesigned full-feature layout;
- searchable offline dictionary;
- expandable offline example-sentence corpus;
- offline fonts, scripts, stroke data, dictionary data, examples, images, and audio.

Writing remains exclusive to vocabulary. Missing stroke data yields a functional text card without a broken drawing area.

## Sentence-pattern cards

Every reviewed sentence pattern produces:

1. the recognition or exercise card appropriate to the teacher's source;
2. a Vietnamese-to-Chinese production card.

The answer displays the reviewed Chinese, pinyin, explanation where supplied, and audio where available. Sentence-pattern cards never contain stroke-writing, offline-dictionary, or expandable-example controls.

## Listening cards

Every class recording is transcribed, manually reviewed, and divided into individual sentence clips. Each approved segment produces one listening card:

- front: only the sentence audio;
- back: replay controls, corrected Chinese transcript, and pinyin.

Listening cards contain no Vietnamese or English translation and no stroke-writing controls. Uncertain transcripts remain in the review report and do not enter the released deck.

## Source and review pipeline

For every dated class, the pipeline:

1. imports Drive and Zalo evidence into the dated class record;
2. extracts vocabulary, Vietnamese meanings, and sentence patterns;
3. transcribes every recording and divides it into persistent sentence segments;
4. generates pinyin for vocabulary, patterns, and listening transcripts;
5. presents extracted text, Vietnamese prompts, audio clips, boundaries, transcripts, pinyin, and uncertainties for human review;
6. builds notes only from approved material;
7. packages the cumulative `.apkg` with all offline assets.

Teacher corrections and approved Zalo evidence override automated extraction. Automated transcription and enrichment are drafts, not final authority.

## Stable identity and progress preservation

Mutable learning content must never define identity:

- vocabulary and sentence notes use class date, source identity, content category, and a persistent item ID;
- listening notes use original recording identity and a persistent segment ID;
- GUIDs never depend on Chinese, Vietnamese, pinyin, transcript wording, or clip boundaries;
- released deck IDs, model IDs, field ordinals, and template ordinals remain stable;
- corrections update existing notes;
- new class items create new notes and cards;
- importing the unified package repeatedly is idempotent.

The migration from the existing simplified deck must preserve all current GUIDs and card ordinals. The new Writing template is added at a previously unused stable ordinal so existing Recognition, Production, and conditional audio cards retain their scheduling.

The build reports removed, merged, or unmatched items instead of silently deleting already-imported Anki cards.

## Component boundaries

- **Source normalization:** converts Drive/Zalo evidence into dated persistent items.
- **Language enrichment:** supplies traditional forms, pinyin, Zhuyin, dictionary metadata, and examples while preserving reviewed values.
- **Audio processing:** transcribes, segments, exports clips, and records confidence/review status.
- **Review data:** stores human approval and corrections independently of identity.
- **Template bundle:** exports the existing TypeScript Anki xiehanzi engine into one versioned bundle for the Python generator.
- **Offline assets:** builds collision-safe writer, dictionary, example, font, image, and audio media.
- **Package builder:** assigns dated decks, card positions, models, GUIDs, and media.
- **Compatibility validation:** inspects schemas, templates, media, ordering, identities, and seeded upgrade behavior before release.

## Failure behavior

- Missing stroke data suppresses only the writer component.
- Missing audio suppresses audio-dependent cards instead of creating blank fronts.
- Unapproved listening segments cannot enter the package.
- Unmatched recordings remain visible in the review report.
- Duplicate item or segment IDs fail validation.
- Missing bundled media, blank generated fronts, template-field mismatches, and duplicate identities fail the build.
- Changes to released GUIDs, model IDs, field ordinals, or template ordinals fail compatibility validation unless an explicit migration is supplied.
- Dictionary searches and example rendering escape untrusted text and return an intact empty state when no match exists.

## Acceptance criteria

The unified deck is complete when:

- each approved class remains one dated deck containing all relevant card categories;
- new-card insertion order is vocabulary, sentence patterns, listening;
- vocabulary provides Recognition, Vietnamese-to-Chinese Production, and independent Writing cards;
- full vocabulary drawing, layout, offline dictionary, and expandable examples work without a network connection;
- sentence patterns include Vietnamese-to-Chinese cards and never show writer controls;
- every approved recording segment produces an audio-only front and transcript/pinyin/replay back;
- all current simplified-deck reviews survive an import of the unified package;
- importing the same unified package twice creates no duplicate notes or cards;
- automated tests cover schema, conditional cards, offline media, sanitization, ordering, GUID stability, model/template identity, segment identity, and APKG integrity;
- manual smoke tests cover Anki Desktop, AnkiDroid, and AnkiMobile, with any platform limitation documented.

Users must back up their collection with scheduling information before the first migration import.
