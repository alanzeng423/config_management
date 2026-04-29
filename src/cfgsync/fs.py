from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Iterable

from .models import Manifest


DEFAULT_VAULT = Path.home() / ".local" / "share" / "cfgsync"
MANIFEST_NAME = "manifest.json"
ITEMS_DIR = "items"


def manifest_path(vault: Path) -> Path:
    return vault / MANIFEST_NAME


def items_path(vault: Path) -> Path:
    return vault / ITEMS_DIR


def item_path(vault: Path, name: str) -> Path:
    return items_path(vault) / name


def ensure_vault(vault: Path) -> None:
    vault.mkdir(parents=True, exist_ok=True)
    items_path(vault).mkdir(parents=True, exist_ok=True)
    path = manifest_path(vault)
    if not path.exists():
        write_manifest(vault, Manifest())


def read_manifest(vault: Path) -> Manifest:
    ensure_vault(vault)
    with manifest_path(vault).open("r", encoding="utf-8") as handle:
        return Manifest.from_dict(json.load(handle))


def write_manifest(vault: Path, manifest: Manifest) -> None:
    vault.mkdir(parents=True, exist_ok=True)
    items_path(vault).mkdir(parents=True, exist_ok=True)
    tmp = manifest_path(vault).with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(manifest.to_dict(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(manifest_path(vault))


def path_kind(path: Path) -> str:
    if path.is_symlink():
        return "symlink"
    if path.is_file():
        return "file"
    if path.is_dir():
        return "directory"
    raise FileNotFoundError(path)


def copy_into_vault(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        remove_path(dst)
    if src.is_symlink():
        target = os.readlink(src)
        dst.symlink_to(target)
    elif src.is_dir():
        ignore = shutil.ignore_patterns(".git", ".DS_Store", "__pycache__")
        shutil.copytree(src, dst, symlinks=True, ignore=ignore)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst, follow_symlinks=False)


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def iter_files(root: Path) -> Iterable[Path]:
    if root.is_symlink() or root.is_file():
        yield root
        return
    for path in sorted(root.rglob("*")):
        if path.is_file() or path.is_symlink():
            yield path


def checksum_path(path: Path) -> str:
    digest = hashlib.sha256()
    if path.is_symlink():
        digest.update(b"symlink\0")
        digest.update(os.readlink(path).encode("utf-8"))
        return digest.hexdigest()
    if path.is_file():
        digest.update(b"file\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    if path.is_dir():
        digest.update(b"directory\0")
        for child in iter_files(path):
            rel = child.relative_to(path).as_posix()
            digest.update(rel.encode("utf-8"))
            digest.update(b"\0")
            digest.update(checksum_path(child).encode("ascii"))
            digest.update(b"\0")
        return digest.hexdigest()
    return "missing"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
