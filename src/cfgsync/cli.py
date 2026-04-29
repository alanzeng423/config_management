from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from . import core
from .fs import DEFAULT_VAULT
from .models import RemoteConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cfgsync")
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT, help=f"vault path (default: {DEFAULT_VAULT})")
    parser.add_argument("--version", action="version", version=f"cfgsync {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="initialize a config vault")

    add_cmd = sub.add_parser("add", help="copy a source config into the vault")
    add_cmd.add_argument("name")
    add_cmd.add_argument("path", type=Path)

    remove_cmd = sub.add_parser("remove", help="remove an item from the manifest")
    remove_cmd.add_argument("name")
    remove_cmd.add_argument("--delete-copy", action="store_true")

    sub.add_parser("list", help="list tracked configs")
    sub.add_parser("status", help="compare source paths with vaulted copies")

    diff_cmd = sub.add_parser("diff", help="show file diff between vault and source")
    diff_cmd.add_argument("name")

    refresh_cmd = sub.add_parser("refresh", help="copy source changes into the vault")
    refresh_cmd.add_argument("name", nargs="?")

    install_cmd = sub.add_parser("install", help="symlink vaulted configs back to source paths")
    install_cmd.add_argument("--dry-run", action="store_true")
    install_cmd.add_argument("--no-backup", action="store_true")

    remote_cmd = sub.add_parser("remote", help="configure remote sync")
    remote_sub = remote_cmd.add_subparsers(dest="remote_command", required=True)
    set_cmd = remote_sub.add_parser("set", help="set remote storage")
    set_cmd.add_argument("provider", choices=["r2", "s3"])
    set_cmd.add_argument("--bucket", required=True)
    set_cmd.add_argument("--prefix", default="")
    set_cmd.add_argument("--endpoint-url", default="")
    set_cmd.add_argument("--region", default="auto")

    push_cmd = sub.add_parser("push", help="upload the vault to remote storage")
    push_cmd.add_argument("--dry-run", action="store_true")
    pull_cmd = sub.add_parser("pull", help="download the vault from remote storage")
    pull_cmd.add_argument("--dry-run", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    vault = args.vault.expanduser()
    try:
        if args.command == "init":
            print(f"initialized {core.init(vault)}")
        elif args.command == "add":
            item = core.add(vault, args.name, args.path)
            print(f"added {item.name}: {item.source}")
        elif args.command == "remove":
            core.remove(vault, args.name, delete_copy=args.delete_copy)
            print(f"removed {args.name}")
        elif args.command == "list":
            for item in core.list_items(vault):
                print(f"{item.name}\t{item.kind}\t{item.source}")
        elif args.command == "status":
            rows = core.status(vault)
            for row in rows:
                print(f"{row.state}\t{row.name}\t{row.source}")
            return 1 if any(row.state == "changed" for row in rows) else 0
        elif args.command == "diff":
            print(core.diff(vault, args.name), end="")
        elif args.command == "refresh":
            for item in core.refresh(vault, args.name):
                print(f"refreshed {item.name}")
        elif args.command == "install":
            for action in core.install(vault, dry_run=args.dry_run, backup=not args.no_backup):
                print(action)
        elif args.command == "remote" and args.remote_command == "set":
            remote = RemoteConfig(
                provider=args.provider,
                bucket=args.bucket,
                prefix=args.prefix,
                endpoint_url=args.endpoint_url,
                region=args.region,
            )
            core.set_remote(vault, remote)
            print(f"remote set: {args.provider} bucket={args.bucket} prefix={args.prefix}")
        elif args.command == "push":
            for action in core.push(vault, dry_run=args.dry_run):
                print(action)
        elif args.command == "pull":
            for action in core.pull(vault, dry_run=args.dry_run):
                print(action)
        else:
            parser.error("unknown command")
    except Exception as exc:
        print(f"cfgsync: error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
