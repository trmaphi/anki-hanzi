from __future__ import annotations

import hashlib
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


MIB = 1024 * 1024
DEFAULT_HARD_LIMIT = 75 * MIB


class AssetError(RuntimeError):
    """A required offline study asset is absent or exceeds the release budget."""


@dataclass(frozen=True)
class AssetFile:
    logical_name: str
    source: Path
    packaged_name: str
    size: int
    sha256: str


@dataclass(frozen=True)
class AssetManifest:
    files: Mapping[str, AssetFile]
    total_bytes: int


ASSETS = {
    "ankiPersistence": ("static/data/_anki-persistence.js", "cdx1-anki-persistence.js"),
    "ankiTts": ("static/data/_anki-tts.js", "cdx1-anki-tts.js"),
    "hanziWriter": ("static/data/_hanzi-writer.min.js", "cdx1-hanzi-writer.min.js"),
    "hanziWriterData": ("static/data/hanzi-writer-data.json", "cdx1-hanzi-writer-data.json"),
    "cedict": ("static/data/cedict.db.zip", "cdx1-cedict.db.zip"),
    "sentences": ("static/data/hsk_sentences.db.zip", "cdx1-hsk-sentences.db.zip"),
    "sqlWasm": ("static/data/sql-wasm.wasm", "cdx1-sql-wasm.wasm"),
    "offlineRuntime": (".class-deck/generated/cdx1-offline-runtime.js", "cdx1-offline-runtime.js"),
}


def _ensure_runtime(repo_root: Path) -> None:
    source = repo_root / "src/lib/classDeckOffline.ts"
    target = repo_root / ASSETS["offlineRuntime"][0]
    if target.is_file() and target.stat().st_mtime_ns >= source.stat().st_mtime_ns:
        return
    try:
        subprocess.run(
            ["node", "scripts/build-class-deck-assets.mjs", str(target)],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise AssetError(f"cannot build offline runtime: {detail.strip()}") from exc


def build_asset_manifest(repo_root: Path, *, hard_limit_bytes: int = DEFAULT_HARD_LIMIT) -> AssetManifest:
    repo_root = Path(repo_root).resolve()
    _ensure_runtime(repo_root)
    files: dict[str, AssetFile] = {}
    packaged_names: set[str] = set()
    for logical_name, (relative, packaged_name) in ASSETS.items():
        source = repo_root / relative
        if not source.is_file():
            raise AssetError(f"required offline asset missing: {source}")
        if not packaged_name.startswith("cdx1-") or packaged_name in packaged_names:
            raise AssetError(f"invalid or duplicate packaged asset name: {packaged_name}")
        packaged_names.add(packaged_name)
        data = source.read_bytes()
        files[logical_name] = AssetFile(
            logical_name=logical_name,
            source=source,
            packaged_name=packaged_name,
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )
    total = sum(item.size for item in files.values())
    if total > hard_limit_bytes:
        raise AssetError(
            f"offline assets total {total / MIB:.1f} MiB, exceeding the 75 MiB hard release limit"
        )
    return AssetManifest(files=MappingProxyType(files), total_bytes=total)


def stage_assets(manifest: AssetManifest, target_dir: Path) -> tuple[Path, ...]:
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    staged = []
    for logical_name in ASSETS:
        item = manifest.files[logical_name]
        target = target_dir / item.packaged_name
        shutil.copyfile(item.source, target)
        if hashlib.sha256(target.read_bytes()).hexdigest() != item.sha256:
            raise AssetError(f"staged asset hash mismatch: {target}")
        staged.append(target)
    return tuple(staged)
