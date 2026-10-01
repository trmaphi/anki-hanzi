from __future__ import annotations

import json
from pathlib import Path

import pytest

from class_deck.template_bundle import (
    BundleValidationError,
    ModelDeclaration,
    load_template_bundle,
    validate_model_contract,
)


BUNDLE_PATH = Path(__file__).parents[2] / "class_deck/assets/class-deck-bundle.v1.json"


def _bundle_data() -> dict:
    return json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))


def _write_bundle(tmp_path: Path, data: dict) -> Path:
    path = tmp_path / "bundle.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _declarations() -> dict[str, ModelDeclaration]:
    return {
        "vocabulary": ModelDeclaration(
            fields=(
                "Chinese", "Traditional", "Pinyin", "Meaning", "Example",
                "ExampleTranslation", "Image", "Audio", "ClassDate", "SourceRef",
                "Zhuyin", "PartOfSpeech", "Definitions", "Breakdown", "Radical",
                "HskLevel", "Frequency",
            ),
            templates=((0, "Recognize"), (1, "Produce"), (2, "Listen"), (3, "Writing")),
            field_roles={"Simplified": "Chinese", "Audio": "Audio"},
        ),
        "sentence": ModelDeclaration(
            fields=("Chinese", "Pinyin", "Meaning", "Answer", "Explanation", "Audio", "ClassDate", "SourceRef"),
            templates=((0, "Produce"), (1, "Listen")),
            field_roles={"Simplified": "Chinese", "Audio": "Audio"},
        ),
        "listening": ModelDeclaration(
            fields=("Chinese", "Pinyin", "Meaning", "Audio", "ClassDate", "SourceRef"),
            templates=((0, "Listen"),),
            field_roles={"Simplified": "Chinese", "Audio": "Audio"},
        ),
    }


def test_loads_v1_bundle():
    bundle = load_template_bundle()

    assert bundle.version == 1
    assert bundle.engine == "xiehanzi-class-deck-v1"
    assert bundle.models["vocabulary"].fields[10:] == (
        "Zhuyin", "PartOfSpeech", "Definitions", "Breakdown", "Radical", "HskLevel", "Frequency"
    )
    assert tuple(template.ord for template in bundle.models["vocabulary"].templates) == (0, 1, 2, 3)
    assert bundle.media["ankiTts"] == "cdx1-anki-tts.js"
    validate_model_contract(bundle, _declarations())


@pytest.mark.parametrize("version", [None, 2])
def test_rejects_missing_or_unknown_version(tmp_path: Path, version: int | None):
    data = _bundle_data()
    if version is None:
        del data["version"]
    else:
        data["version"] = version

    with pytest.raises(BundleValidationError, match=r"^\$\.version:"):
        load_template_bundle(_write_bundle(tmp_path, data))


def test_rejects_field_role_mismatch(tmp_path: Path):
    data = _bundle_data()
    data["models"]["vocabulary"]["fieldRoles"]["Simplified"] = "NotAField"

    with pytest.raises(BundleValidationError, match=r"\$\.models\.vocabulary\.fieldRoles\.Simplified"):
        load_template_bundle(_write_bundle(tmp_path, data))


@pytest.mark.parametrize(
    ("mutation", "error_path"),
    [
        (lambda data: data["models"]["vocabulary"]["fields"].__setitem__(1, "Chinese"), r"\$\.models\.vocabulary\.fields\[1\]"),
        (lambda data: data["models"]["vocabulary"]["templates"][1].__setitem__("ord", 0), r"\$\.models\.vocabulary\.templates\[1\]\.ord"),
    ],
)
def test_rejects_duplicate_or_changed_ordinals(tmp_path: Path, mutation, error_path: str):
    data = _bundle_data()
    mutation(data)

    with pytest.raises(BundleValidationError, match=error_path):
        load_template_bundle(_write_bundle(tmp_path, data))


def test_rejects_unmapped_media_reference(tmp_path: Path):
    data = _bundle_data()
    data["models"]["listening"]["templates"][0]["qfmt"] += '<script src="cdx1-missing.js"></script>'

    with pytest.raises(BundleValidationError, match=r"\$\.models\.listening\.templates\[0\]\.qfmt"):
        load_template_bundle(_write_bundle(tmp_path, data))


def test_contract_mismatch_reports_precise_path():
    declarations = _declarations()
    declarations["sentence"] = ModelDeclaration(
        fields=declarations["sentence"].fields,
        templates=((0, "Produce"), (1, "Changed")),
        field_roles=declarations["sentence"].field_roles,
    )

    with pytest.raises(BundleValidationError, match=r"\$\.models\.sentence\.templates\[1\]\.name"):
        validate_model_contract(load_template_bundle(), declarations)
