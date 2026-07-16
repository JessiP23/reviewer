from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Protocol


class DocumentStore(Protocol):
    """Persist and retrieve raw uploaded document bytes by review id."""

    async def store(self, review_id: str, filename: str, content: bytes) -> str: ...

    async def retrieve(self, key: str) -> bytes | None: ...

    def content_type(self, filename: str) -> str: ...


class FilesystemDocumentStore:
    """Local filesystem-backed document store."""

    def __init__(self, base_path: str | Path = "./document_store") -> None:
        self._base = Path(base_path).resolve()

    async def store(self, review_id: str, filename: str, content: bytes) -> str:
        safe_name = Path(filename).name
        directory = self._base / review_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / safe_name
        path.write_bytes(content)
        return f"{review_id}/{safe_name}"

    async def retrieve(self, key: str) -> bytes | None:
        path = self._base / key
        if not path.is_relative_to(self._base) or not path.is_file():
            return None
        return path.read_bytes()

    def content_type(self, filename: str) -> str:
        guessed, _ = mimetypes.guess_type(filename)
        return guessed or "application/octet-stream"
