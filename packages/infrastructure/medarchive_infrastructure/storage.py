from __future__ import annotations

from pathlib import Path
from typing import BinaryIO


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self._root = root

    async def upload(self, key: str, content: BinaryIO, content_type: str) -> None:
        target = self._resolve_key(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        content.seek(0)
        target.write_bytes(content.read())
        metadata_path = target.with_suffix(target.suffix + ".content-type")
        metadata_path.write_text(content_type, encoding="utf-8")

    async def download(self, key: str) -> bytes:
        return self._resolve_key(key).read_bytes()

    def _resolve_key(self, key: str) -> Path:
        normalized_parts = [part for part in key.replace("\\", "/").split("/") if part]
        candidate = self._root.joinpath(*normalized_parts).resolve()
        root = self._root.resolve()
        if root not in candidate.parents and candidate != root:
            raise ValueError("storage key escapes local storage root")
        return candidate
