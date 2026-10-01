from class_deck.template_bundle import load_template_bundle
from class_deck.templates import MODEL_IDS, ClassDeckModel, build_models


def test_models_preserve_released_ids_fields_and_append_only_ordinals():
    models = build_models()

    assert {name: model.model_id for name, model in models.items()} == MODEL_IDS
    assert [field["name"] for field in models["vocabulary"].fields] == [
        "Chinese", "Traditional", "Pinyin", "Meaning", "Example",
        "ExampleTranslation", "Image", "Audio", "ClassDate", "SourceRef",
        "Zhuyin", "PartOfSpeech", "Definitions", "Breakdown", "Radical",
        "HskLevel", "Frequency",
    ]
    assert [field["name"] for field in models["sentence"].fields] == [
        "Chinese", "Pinyin", "Meaning", "Answer", "Explanation", "Audio", "ClassDate", "SourceRef"
    ]
    assert [field["name"] for field in models["listening"].fields] == [
        "Chinese", "Pinyin", "Meaning", "Audio", "ClassDate", "SourceRef"
    ]
    assert [[template["name"], template["ord"]] for template in models["vocabulary"].templates] == [
        ["Recognize", 0], ["Produce", 1], ["Listen", 2], ["Writing", 3]
    ]
    assert [[template["name"], template["ord"]] for template in models["sentence"].templates] == [
        ["Produce", 0], ["Listen", 1]
    ]
    assert [[template["name"], template["ord"]] for template in models["listening"].templates] == [["Listen", 0]]


def test_explicit_requirements_make_writing_unconditional_and_listening_audio_only():
    models = build_models()

    assert all(isinstance(model, ClassDeckModel) for model in models.values())
    assert models["vocabulary"]._req == [
        [0, "all", [0]], [1, "all", [0]], [2, "all", [7]], [3, "all", [0]]
    ]
    assert models["sentence"]._req == [[0, "all", [0]], [1, "all", [5]]]
    assert models["listening"]._req == [[0, "all", [3]]]


def test_models_consume_the_validated_bundle_contract():
    bundle = load_template_bundle()
    models = build_models(bundle)

    for name, definition in bundle.models.items():
        assert models[name].css == definition.css
        assert [template["qfmt"] for template in models[name].templates] == [
            template.qfmt for template in definition.templates
        ]
