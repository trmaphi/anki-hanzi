from pathlib import Path

import pytest

from class_deck.assets import AssetError, build_asset_manifest, stage_assets


ROOT = Path(__file__).parents[2]


def test_manifest_has_exact_namespaced_assets_and_stable_hashes(tmp_path):
    first = build_asset_manifest(ROOT)
    second = build_asset_manifest(ROOT)

    assert first == second
    assert set(first.files) == {
        "ankiPersistence", "ankiTts", "hanziWriter", "hanziWriterData",
        "cedict", "sentences", "sqlWasm", "offlineRuntime",
    }
    assert all(item.packaged_name.startswith("cdx1-") for item in first.files.values())
    assert all(len(item.sha256) == 64 for item in first.files.values())
    staged = stage_assets(first, tmp_path / "media")
    assert {item.name for item in staged} == {item.packaged_name for item in first.files.values()}


def test_manifest_enforces_hard_size_budget():
    with pytest.raises(AssetError, match="75 MiB"):
        build_asset_manifest(ROOT, hard_limit_bytes=1)


def test_runtime_has_no_network_dependencies():
    manifest = build_asset_manifest(ROOT)
    runtime = manifest.files["offlineRuntime"].source.read_text(encoding="utf-8")

    assert "http://" not in runtime
    assert "https://" not in runtime
    assert "idx_cedict_simplified" in runtime
