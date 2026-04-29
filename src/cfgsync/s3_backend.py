from __future__ import annotations

import os
from pathlib import Path

from .models import RemoteConfig


class S3Backend:
    def __init__(self, remote: RemoteConfig) -> None:
        self.remote = remote
        if remote.provider not in {"r2", "s3"}:
            raise ValueError("remote provider must be 'r2' or 's3'")
        if not remote.bucket:
            raise ValueError("remote bucket is required")

    def _client(self):
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("Install R2/S3 support with: python3 -m pip install 'cfgsync[s3]'") from exc
        return boto3.client(
            "s3",
            endpoint_url=self.remote.endpoint_url or None,
            region_name=self.remote.region or "auto",
            aws_access_key_id=self.remote.access_key_id or os.getenv("R2_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=self.remote.secret_access_key or os.getenv("R2_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    def _key(self, rel: str) -> str:
        prefix = self.remote.prefix.strip("/")
        return f"{prefix}/{rel}" if prefix else rel

    def upload_vault(self, vault: Path, dry_run: bool = False) -> list[str]:
        actions: list[str] = []
        client = None if dry_run else self._client()
        for path in sorted(vault.rglob("*")):
            if path.is_dir():
                continue
            rel = path.relative_to(vault).as_posix()
            key = self._key(rel)
            actions.append(f"upload s3://{self.remote.bucket}/{key}")
            if not dry_run:
                client.upload_file(str(path), self.remote.bucket, key)
        return actions

    def download_vault(self, vault: Path, dry_run: bool = False) -> list[str]:
        actions: list[str] = []
        client = None if dry_run else self._client()
        if dry_run:
            actions.append(f"list s3://{self.remote.bucket}/{self.remote.prefix.strip('/')}")
            return actions
        paginator = client.get_paginator("list_objects_v2")
        prefix = self.remote.prefix.strip("/")
        list_prefix = f"{prefix}/" if prefix else ""
        for page in paginator.paginate(Bucket=self.remote.bucket, Prefix=list_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                rel = key[len(list_prefix) :] if list_prefix else key
                if not rel:
                    continue
                dst = vault / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                actions.append(f"download s3://{self.remote.bucket}/{key}")
                client.download_file(self.remote.bucket, key, str(dst))
        return actions
