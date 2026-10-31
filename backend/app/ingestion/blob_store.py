"""Encrypted blob store on local disk (NFR-9). One file per document, named by document id."""

from pathlib import Path

from app.core.config import Settings
from app.core.crypto import decrypt, encrypt


class BlobStore:
    def __init__(self, settings: Settings) -> None:
        self.root = settings.blob_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        if "/" in name or "\\" in name or ".." in name:
            raise ValueError("invalid blob name")
        return self.root / name

    def put(self, document_id: str, data: bytes) -> str:
        name = f"{document_id}.bin"
        tmp = self._path(name + ".tmp")
        tmp.write_bytes(encrypt(data))
        tmp.replace(self._path(name))
        return name

    def get(self, name: str) -> bytes:
        return decrypt(self._path(name).read_bytes())

    def exists(self, name: str) -> bool:
        return self._path(name).exists()

    def delete(self, name: str) -> None:
        self._path(name).unlink(missing_ok=True)
