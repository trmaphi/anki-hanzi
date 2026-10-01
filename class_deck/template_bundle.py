from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


DEFAULT_BUNDLE_PATH = Path(__file__).with_name("assets") / "class-deck-bundle.v1.json"
SUPPORTED_VERSION = 1
EXPECTED_MODELS = ("vocabulary", "sentence", "listening")
REQUIRED_MEDIA = (
    "ankiPersistence",
    "ankiTts",
    "hanziWriter",
    "hanziWriterData",
    "cedict",
    "sentences",
    "sqlWasm",
)
MEDIA_REFERENCE = re.compile(r"(?<![\w.-])(cdx1-[A-Za-z0-9_.-]+)")


class BundleValidationError(ValueError):
    """A template bundle value is invalid at a precise JSON-style path."""


@dataclass(frozen=True)
class TemplateDefinition:
    ord: int
    name: str
    qfmt: str
    afmt: str
    req: tuple[int, str, tuple[int, ...]]
    sidebar_sections: Mapping[str, Any]
    default_off: Mapping[str, Any]


@dataclass(frozen=True)
class ModelDefinition:
    fields: tuple[str, ...]
    field_roles: Mapping[str, str | tuple[str, ...]]
    templates: tuple[TemplateDefinition, ...]
    css: str


@dataclass(frozen=True)
class TemplateBundle:
    version: int
    engine: str
    models: Mapping[str, ModelDefinition]
    media: Mapping[str, str]
    tone_palettes: tuple[Mapping[str, Any], ...]
    writer_controls: Mapping[str, Any]


@dataclass(frozen=True)
class ModelDeclaration:
    fields: tuple[str, ...]
    templates: tuple[tuple[int, str], ...]
    field_roles: Mapping[str, str | tuple[str, ...]]


def _fail(path: str, message: str) -> None:
    raise BundleValidationError(f"{path}: {message}")


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        _fail(path, "expected an object")
    return value


def _array(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(path, "expected an array")
    return value


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(path, "expected non-empty text")
    return value


def _integer(value: Any, path: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        _fail(path, "expected an integer")
    return value


def _frozen_object(value: Any, path: str) -> Mapping[str, Any]:
    raw = _object(value, path)
    return MappingProxyType({key: _freeze(item, f"{path}.{key}") for key, item in raw.items()})


def _freeze(value: Any, path: str) -> Any:
    if isinstance(value, dict):
        return _frozen_object(value, path)
    if isinstance(value, list):
        return tuple(_freeze(item, f"{path}[{index}]") for index, item in enumerate(value))
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    _fail(path, "unsupported JSON value")


def _unique_texts(value: Any, path: str) -> tuple[str, ...]:
    result: list[str] = []
    for index, item in enumerate(_array(value, path)):
        text = _text(item, f"{path}[{index}]")
        if text in result:
            _fail(f"{path}[{index}]", f"duplicate value {text!r}")
        result.append(text)
    if not result:
        _fail(path, "expected at least one value")
    return tuple(result)


def _parse_req(value: Any, path: str, *, template_ord: int, field_count: int) -> tuple[int, str, tuple[int, ...]]:
    raw = _array(value, path)
    if len(raw) != 3:
        _fail(path, "expected [template ordinal, mode, field ordinals]")
    req_ord = _integer(raw[0], f"{path}[0]")
    if req_ord != template_ord:
        _fail(f"{path}[0]", f"expected template ordinal {template_ord}")
    mode = _text(raw[1], f"{path}[1]")
    if mode not in {"all", "any", "none"}:
        _fail(f"{path}[1]", "expected all, any, or none")
    field_ords = tuple(_integer(item, f"{path}[2][{index}]") for index, item in enumerate(_array(raw[2], f"{path}[2]")))
    if not field_ords:
        _fail(f"{path}[2]", "expected at least one field ordinal")
    for index, field_ord in enumerate(field_ords):
        if not 0 <= field_ord < field_count:
            _fail(f"{path}[2][{index}]", f"field ordinal {field_ord} is out of range")
    return (req_ord, mode, field_ords)


def _parse_field_roles(value: Any, path: str, fields: tuple[str, ...]) -> Mapping[str, str | tuple[str, ...]]:
    raw = _object(value, path)
    roles: dict[str, str | tuple[str, ...]] = {}
    for role, target in raw.items():
        role_path = f"{path}.{role}"
        _text(role, role_path)
        targets = (_text(target, role_path),) if isinstance(target, str) else _unique_texts(target, role_path)
        for field in targets:
            if field not in fields:
                _fail(role_path, f"references unknown field {field!r}")
        roles[role] = targets[0] if isinstance(target, str) else targets
    if not roles:
        _fail(path, "expected at least one role")
    return MappingProxyType(roles)


def _parse_models(value: Any) -> Mapping[str, ModelDefinition]:
    raw = _object(value, "$.models")
    if tuple(raw) != EXPECTED_MODELS:
        _fail("$.models", f"expected models in order {EXPECTED_MODELS!r}")
    models: dict[str, ModelDefinition] = {}
    for model_name, model_value in raw.items():
        path = f"$.models.{model_name}"
        model = _object(model_value, path)
        fields = _unique_texts(model.get("fields"), f"{path}.fields")
        field_roles = _parse_field_roles(model.get("fieldRoles"), f"{path}.fieldRoles", fields)
        templates: list[TemplateDefinition] = []
        seen_names: set[str] = set()
        for index, template_value in enumerate(_array(model.get("templates"), f"{path}.templates")):
            template_path = f"{path}.templates[{index}]"
            template = _object(template_value, template_path)
            template_ord = _integer(template.get("ord"), f"{template_path}.ord")
            if template_ord != index:
                _fail(f"{template_path}.ord", f"expected append-only ordinal {index}")
            name = _text(template.get("name"), f"{template_path}.name")
            if name in seen_names:
                _fail(f"{template_path}.name", f"duplicate template name {name!r}")
            seen_names.add(name)
            templates.append(
                TemplateDefinition(
                    ord=template_ord,
                    name=name,
                    qfmt=_text(template.get("qfmt"), f"{template_path}.qfmt"),
                    afmt=_text(template.get("afmt"), f"{template_path}.afmt"),
                    req=_parse_req(template.get("req"), f"{template_path}.req", template_ord=template_ord, field_count=len(fields)),
                    sidebar_sections=_frozen_object(template.get("sidebarSections"), f"{template_path}.sidebarSections"),
                    default_off=_frozen_object(template.get("defaultOff"), f"{template_path}.defaultOff"),
                )
            )
        if not templates:
            _fail(f"{path}.templates", "expected at least one template")
        models[model_name] = ModelDefinition(
            fields=fields,
            field_roles=field_roles,
            templates=tuple(templates),
            css=_text(model.get("css"), f"{path}.css"),
        )
    return MappingProxyType(models)


def _parse_media(value: Any) -> Mapping[str, str]:
    raw = _object(value, "$.media")
    if tuple(raw) != REQUIRED_MEDIA:
        _fail("$.media", f"expected media keys in order {REQUIRED_MEDIA!r}")
    media: dict[str, str] = {}
    for key, value in raw.items():
        filename = _text(value, f"$.media.{key}")
        if not filename.startswith("cdx1-") or "/" in filename or "\\" in filename:
            _fail(f"$.media.{key}", "expected a namespaced cdx1-* basename")
        if filename in media.values():
            _fail(f"$.media.{key}", f"duplicate packaged filename {filename!r}")
        media[key] = filename
    return MappingProxyType(media)


def _validate_media_references(bundle: TemplateBundle) -> None:
    mapped = set(bundle.media.values())
    for model_name, model in bundle.models.items():
        values = [(f"$.models.{model_name}.css", model.css)]
        for index, template in enumerate(model.templates):
            base = f"$.models.{model_name}.templates[{index}]"
            values.extend(((f"{base}.qfmt", template.qfmt), (f"{base}.afmt", template.afmt)))
        for path, text in values:
            for reference in MEDIA_REFERENCE.findall(text):
                if reference not in mapped:
                    _fail(path, f"references unmapped media {reference!r}")


def load_template_bundle(path: Path | None = None) -> TemplateBundle:
    source_path = path or DEFAULT_BUNDLE_PATH
    try:
        raw_value = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleValidationError(f"$: cannot load {source_path}: {exc}") from exc
    raw = _object(raw_value, "$")
    version = raw.get("version")
    if version != SUPPORTED_VERSION or isinstance(version, bool):
        _fail("$.version", f"expected supported version {SUPPORTED_VERSION}")
    bundle = TemplateBundle(
        version=version,
        engine=_text(raw.get("engine"), "$.engine"),
        models=_parse_models(raw.get("models")),
        media=_parse_media(raw.get("media")),
        tone_palettes=tuple(
            _frozen_object(item, f"$.tonePalettes[{index}]")
            for index, item in enumerate(_array(raw.get("tonePalettes"), "$.tonePalettes"))
        ),
        writer_controls=_frozen_object(raw.get("writerControls"), "$.writerControls"),
    )
    _validate_media_references(bundle)
    return bundle


def validate_model_contract(bundle: TemplateBundle, declarations: Mapping[str, ModelDeclaration]) -> None:
    if tuple(declarations) != tuple(bundle.models):
        _fail("$.models", f"declarations must match bundle models in order {tuple(bundle.models)!r}")
    for model_name, declaration in declarations.items():
        model = bundle.models[model_name]
        path = f"$.models.{model_name}"
        for index, (actual, expected) in enumerate(zip(model.fields, declaration.fields, strict=False)):
            if actual != expected:
                _fail(f"{path}.fields[{index}]", f"expected {expected!r}, found {actual!r}")
        if len(model.fields) != len(declaration.fields):
            _fail(f"{path}.fields", f"expected {len(declaration.fields)} fields, found {len(model.fields)}")
        actual_templates = tuple((template.ord, template.name) for template in model.templates)
        for index, (actual, expected) in enumerate(zip(actual_templates, declaration.templates, strict=False)):
            if actual[0] != expected[0]:
                _fail(f"{path}.templates[{index}].ord", f"expected {expected[0]}, found {actual[0]}")
            if actual[1] != expected[1]:
                _fail(f"{path}.templates[{index}].name", f"expected {expected[1]!r}, found {actual[1]!r}")
        if len(actual_templates) != len(declaration.templates):
            _fail(f"{path}.templates", f"expected {len(declaration.templates)} templates, found {len(actual_templates)}")
        for role, expected in declaration.field_roles.items():
            actual = model.field_roles.get(role)
            if actual != expected:
                _fail(f"{path}.fieldRoles.{role}", f"expected {expected!r}, found {actual!r}")
