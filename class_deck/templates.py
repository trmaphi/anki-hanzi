from __future__ import annotations

from typing import Mapping

import genanki

from .template_bundle import ModelDeclaration, TemplateBundle, load_template_bundle, validate_model_contract


MODEL_IDS = {
    "vocabulary": 1956836792,
    "sentence": 1740209695,
    "listening": 1680100180,
}

MODEL_NAMES = {
    "vocabulary": "Chinese Classes - Vocabulary",
    "sentence": "Chinese Classes - Sentence Pattern",
    "listening": "Chinese Classes - Listening",
}

MODEL_DECLARATIONS: Mapping[str, ModelDeclaration] = {
    "vocabulary": ModelDeclaration(
        fields=(
            "Chinese", "Traditional", "Pinyin", "Meaning", "Example", "ExampleTranslation",
            "Image", "Audio", "ClassDate", "SourceRef", "Zhuyin", "PartOfSpeech",
            "Definitions", "Breakdown", "Radical", "HskLevel", "Frequency",
        ),
        templates=((0, "Recognize"), (1, "Produce"), (2, "Listen"), (3, "Writing")),
        field_roles={
            "Simplified": "Chinese",
            "Traditional": "Traditional",
            "Pinyin": "Pinyin",
            "SimpleMeaning": "Meaning",
            "Examples": ("Example", "ExampleTranslation"),
            "Audio": "Audio",
        },
    ),
    "sentence": ModelDeclaration(
        fields=("Chinese", "Pinyin", "Meaning", "Answer", "Explanation", "Audio", "ClassDate", "SourceRef"),
        templates=((0, "Produce"), (1, "Listen")),
        field_roles={"Simplified": "Chinese", "Pinyin": "Pinyin", "SimpleMeaning": "Meaning", "Audio": "Audio"},
    ),
    "listening": ModelDeclaration(
        fields=("Chinese", "Pinyin", "Meaning", "Audio", "ClassDate", "SourceRef"),
        templates=((0, "Listen"),),
        field_roles={"Simplified": "Chinese", "Pinyin": "Pinyin", "Audio": "Audio"},
    ),
}


class ClassDeckModel(genanki.Model):
    """A genanki model whose card requirements are part of the reviewed bundle."""

    def __init__(self, *args, req: tuple[tuple[int, str, tuple[int, ...]], ...], **kwargs):
        self._explicit_req = [
            [template_ord, mode, list(field_ords)]
            for template_ord, mode, field_ords in req
        ]
        super().__init__(*args, **kwargs)

    @property
    def _req(self) -> list[list[object]]:
        return self._explicit_req


def build_models(bundle: TemplateBundle | None = None) -> dict[str, genanki.Model]:
    bundle = bundle or load_template_bundle()
    validate_model_contract(bundle, MODEL_DECLARATIONS)
    models: dict[str, genanki.Model] = {}
    for model_name, definition in bundle.models.items():
        models[model_name] = ClassDeckModel(
            MODEL_IDS[model_name],
            MODEL_NAMES[model_name],
            fields=[{"name": field} for field in definition.fields],
            templates=[
                {
                    "name": template.name,
                    "ord": template.ord,
                    "qfmt": template.qfmt,
                    "afmt": template.afmt,
                }
                for template in definition.templates
            ],
            css=definition.css,
            req=tuple(template.req for template in definition.templates),
        )
    return models


__all__ = ["ClassDeckModel", "MODEL_DECLARATIONS", "MODEL_IDS", "build_models"]
