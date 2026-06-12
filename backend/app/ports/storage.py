from pathlib import Path
from typing import Protocol


class StoredObject(Protocol):
    key: str
    bytes_written: int
    checksum: str


class StorageProvider(Protocol):
    async def save_upload(self, filename: str, chunks) -> StoredObject:
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        raise NotImplementedError

    async def resolve_local_path(self, key: str) -> Path:
        raise NotImplementedError
