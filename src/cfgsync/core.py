from __future__ import annotations

import difflib
import shutil
from dataclasses import dataclass
from pathlib import Path

from .fs import (
    checksum_path,
    copy_into_vault,
    ensure_vault,
    item_path,
    path_kind,
    read_manifest,
    remove_path,
    write_manifest,
)
from .models import ConfigItem, Manifest, RemoteConfig
from .s3_backend import S3Backend


@dataclass(slots=True)
class StatusRow:
    name: str
    state: str
    source: str
    vault_checksum: str
    source_checksum: str


def init(vault: Path) -> Path:
    ensure_vault(vault)
    return vault


def add(vault: Path, name: str, source: Path) -> ConfigItem:
    manifest = read_manifest(vault)
    source = source.expanduser().resolve()
    if not source.exists() and not source.is_symlink():
        raise FileNotFoundError(source)
    kind = path_kind(source)
    dst = item_path(vault, name)
    copy_into_vault(source, dst)
    item = ConfigItem(
        name=name,
        source=str(source),
        kind=kind,
        checksum=checksum_path(dst),
    )
    manifest.items[name] = item
    write_manifest(vault, manifest)
    return item


def remove(vault: Path, name: str, delete_copy: bool = False) -> None:
    manifest = read_manifest(vault)
    if name not in manifest.items:
        raise KeyError(name)
    del manifest.items[name]
    if delete_copy:
        path = item_path(vault, name)
        if path.exists() or path.is_symlink():
            remove_path(path)
    write_manifest(vault, manifest)


def list_items(vault: Path) -> list[ConfigItem]:
    manifest = read_manifest(vault)
    return [manifest.items[name] for name in sorted(manifest.items)]


def status(vault: Path) -> list[StatusRow]:
    manifest = read_manifest(vault)
    rows: list[StatusRow] = []
    for name in sorted(manifest.items):
        item = manifest.items[name]
        vault_file = item_path(vault, name)
        source = item.source_path
        vault_checksum = checksum_path(vault_file) if vault_file.exists() or vault_file.is_symlink() else "missing"
        source_checksum = checksum_path(source) if source.exists() or source.is_symlink() else "missing"
        if vault_checksum == "missing":
            state = "vault-missing"
        elif source_checksum == "missing":
            state = "source-missing"
        elif vault_checksum == source_checksum:
            state = "clean"
        else:
            state = "changed"
        rows.append(StatusRow(name, state, item.source, vault_checksum, source_checksum))
    return rows


def diff(vault: Path, name: str) -> str:
    manifest = read_manifest(vault)
    if name not in manifest.items:
        raise KeyError(name)
    item = manifest.items[name]
    src = item.source_path
    vaulted = item_path(vault, name)
    if item.kind != "file":
        raise ValueError("diff currently supports file items only")
    if not src.exists() or not vaulted.exists():
        raise FileNotFoundError(name)
    left = vaulted.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    right = src.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            left,
            right,
            fromfile=f"vault/{name}",
            tofile=item.source,
        )
    )


def refresh(vault: Path, name: str | None = None) -> list[ConfigItem]:
    manifest = read_manifest(vault)
    names = [name] if name else sorted(manifest.items)
    refreshed: list[ConfigItem] = []
    for item_name in names:
        if item_name not in manifest.items:
            raise KeyError(item_name)
        item = manifest.items[item_name]
        source = item.source_path
        if not source.exists() and not source.is_symlink():
            raise FileNotFoundError(source)
        copy_into_vault(source, item_path(vault, item_name))
        item.checksum = checksum_path(item_path(vault, item_name))
        refreshed.append(item)
    write_manifest(vault, manifest)
    return refreshed


def install(vault: Path, dry_run: bool = False, backup: bool = True) -> list[str]:
    manifest = read_manifest(vault)
    actions: list[str] = []
    for name in sorted(manifest.items):
        item = manifest.items[name]
        src = item_path(vault, name)
        target = item.source_path
        if not src.exists() and not src.is_symlink():
            raise FileNotFoundError(src)
        if target.is_symlink() and target.resolve() == src.resolve():
            actions.append(f"{name}: already linked")
            continue
        backup_path = target.with_name(target.name + ".cfgsync.bak")
        actions.append(f"{name}: link {target} -> {src}")
        if dry_run:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() or target.is_symlink():
            if backup:
                if backup_path.exists() or backup_path.is_symlink():
                    remove_path(backup_path)
                shutil.move(str(target), str(backup_path))
            else:
                remove_path(target)
        target.symlink_to(src, target_is_directory=src.is_dir())
    return actions


def set_remote(vault: Path, remote: RemoteConfig) -> RemoteConfig:
    manifest = read_manifest(vault)
    manifest.remote = remote
    write_manifest(vault, manifest)
    return remote


def push(vault: Path, dry_run: bool = False) -> list[str]:
    manifest = read_manifest(vault)
    return S3Backend(manifest.remote).upload_vault(vault, dry_run=dry_run)


def pull(vault: Path, dry_run: bool = False) -> list[str]:
    manifest = read_manifest(vault)
    actions = S3Backend(manifest.remote).download_vault(vault, dry_run=dry_run)
    if not dry_run:
        pulled = read_manifest(vault)
        write_manifest(vault, Manifest(items=pulled.items, remote=manifest.remote))
    return actions
