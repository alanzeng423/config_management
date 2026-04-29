from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


MANIFEST_VERSION = 1


@dataclass(slots=True)
class ConfigItem:
    name: str
    source: str
    kind: str
    checksum: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfigItem":
        return cls(
            name=str(data["name"]),
            source=str(data["source"]),
            kind=str(data["kind"]),
            checksum=str(data.get("checksum", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "kind": self.kind,
            "checksum": self.checksum,
        }

    @property
    def source_path(self) -> Path:
        return Path(self.source).expanduser()


@dataclass(slots=True)
class RemoteConfig:
    provider: str = ""
    bucket: str = ""
    prefix: str = ""
    endpoint_url: str = ""
    region: str = "auto"
    access_key_id: str = ""
    secret_access_key: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "RemoteConfig":
        data = data or {}
        return cls(
            provider=str(data.get("provider", "")),
            bucket=str(data.get("bucket", "")),
            prefix=str(data.get("prefix", "")),
            endpoint_url=str(data.get("endpoint_url", "")),
            region=str(data.get("region", "auto")),
            access_key_id=str(data.get("access_key_id", "")),
            secret_access_key=str(data.get("secret_access_key", "")),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "provider": self.provider,
            "bucket": self.bucket,
            "prefix": self.prefix,
            "endpoint_url": self.endpoint_url,
            "region": self.region,
        }


@dataclass(slots=True)
class Manifest:
    version: int = MANIFEST_VERSION
    items: dict[str, ConfigItem] = field(default_factory=dict)
    remote: RemoteConfig = field(default_factory=RemoteConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Manifest":
        items = {
            name: ConfigItem.from_dict(item_data)
            for name, item_data in data.get("items", {}).items()
        }
        return cls(
            version=int(data.get("version", MANIFEST_VERSION)),
            items=items,
            remote=RemoteConfig.from_dict(data.get("remote")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "items": {
                name: item.to_dict()
                for name, item in sorted(self.items.items(), key=lambda kv: kv[0])
            },
            "remote": self.remote.to_dict(),
        }
