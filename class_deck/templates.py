from __future__ import annotations

import genanki


MODEL_IDS = {
    "vocabulary": 1956836792,
    "sentence": 1740209695,
    "listening": 1680100180,
}


CSS = """
.card {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  text-align: center;
  color: #202124;
  background: #fffafc;
  padding: 20px;
}
.hanzi { font-size: 48px; line-height: 1.3; margin: 12px 0; }
.pinyin { font-size: 24px; color: #8e4b63; margin: 8px 0; }
.meaning, .answer { font-size: 22px; margin: 12px 0; }
.example, .meta { font-size: 16px; color: #5f6368; margin-top: 12px; }
img { max-width: 100%; max-height: 320px; border-radius: 12px; }
.prompt { font-size: 21px; margin: 16px 0; }
hr { border: 0; border-top: 1px solid #ead7df; margin: 18px 0; }
.nightMode .card { color: #f4edf0; background: #211a1d; }
.nightMode .pinyin { color: #f3a9c3; }
.nightMode .example, .nightMode .meta { color: #c9b9bf; }
"""


BACK_COMMON = """
<hr>
<div class="hanzi">{{Chinese}}</div>
{{#Pinyin}}<div class="pinyin">{{Pinyin}}</div>{{/Pinyin}}
{{#Meaning}}<div class="meaning">{{Meaning}}</div>{{/Meaning}}
{{#Image}}<div>{{Image}}</div>{{/Image}}
{{#Example}}<div class="example">{{Example}}</div>{{/Example}}
{{#ExampleTranslation}}<div class="example">{{ExampleTranslation}}</div>{{/ExampleTranslation}}
{{#Answer}}<div class="answer">{{Answer}}</div>{{/Answer}}
{{#Explanation}}<div class="example">{{Explanation}}</div>{{/Explanation}}
{{#Audio}}<div>{{Audio}}</div>{{/Audio}}
<div class="meta">Class {{ClassDate}}</div>
"""


def _fields(*names: str) -> list[dict[str, str]]:
    return [{"name": name} for name in names]


def build_models() -> dict[str, genanki.Model]:
    vocabulary = genanki.Model(
        MODEL_IDS["vocabulary"],
        "Chinese Classes - Vocabulary",
        fields=_fields(
            "Chinese",
            "Traditional",
            "Pinyin",
            "Meaning",
            "Example",
            "ExampleTranslation",
            "Image",
            "Audio",
            "ClassDate",
            "SourceRef",
        ),
        templates=[
            {
                "name": "Recognize",
                "qfmt": '<div class="hanzi">{{Chinese}}</div>{{#Audio}}<div>{{Audio}}</div>{{/Audio}}',
                "afmt": "{{FrontSide}}" + BACK_COMMON,
            },
            {
                "name": "Produce",
                "qfmt": '<div class="prompt">{{Meaning}}</div>{{#Image}}<div>{{Image}}</div>{{/Image}}',
                "afmt": "{{FrontSide}}" + BACK_COMMON,
            },
            {
                "name": "Listen",
                "qfmt": "{{#Audio}}<div>{{Audio}}</div>{{/Audio}}",
                "afmt": "{{FrontSide}}" + BACK_COMMON,
            },
        ],
        css=CSS,
    )
    sentence = genanki.Model(
        MODEL_IDS["sentence"],
        "Chinese Classes - Sentence Pattern",
        fields=_fields(
            "Chinese", "Pinyin", "Meaning", "Answer", "Explanation", "Audio", "ClassDate", "SourceRef"
        ),
        templates=[
            {
                "name": "Produce",
                "qfmt": '<div class="prompt">{{Meaning}}</div>',
                "afmt": "{{FrontSide}}" + BACK_COMMON,
            },
            {
                "name": "Listen",
                "qfmt": "{{#Audio}}<div>{{Audio}}</div>{{/Audio}}",
                "afmt": "{{FrontSide}}" + BACK_COMMON,
            },
        ],
        css=CSS,
    )
    listening = genanki.Model(
        MODEL_IDS["listening"],
        "Chinese Classes - Listening",
        fields=_fields("Chinese", "Pinyin", "Meaning", "Audio", "ClassDate", "SourceRef"),
        templates=[
            {
                "name": "Listen",
                "qfmt": "{{#Audio}}<div>{{Audio}}</div>{{/Audio}}",
                "afmt": "{{FrontSide}}" + BACK_COMMON,
            }
        ],
        css=CSS,
    )
    return {"vocabulary": vocabulary, "sentence": sentence, "listening": listening}
