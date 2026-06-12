import hashlib
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


@dataclass(frozen=True)
class LocalStoredObject:
    key: str
    bytes_written: int
    checksum: str


class LocalStorageProvider:
    def __init__(self, base_dir: str | None = None):
        self.base_dir = Path(base_dir or get_settings().upload_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, filename: str, chunks) -> LocalStoredObject:
        suffix = Path(filename).suffix or ".csv"
        key = f"uploads/{uuid4()}{suffix}"
        path = await self.resolve_local_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256()
        bytes_written = 0
        with path.open("wb") as output:
            async for chunk in chunks:
                digest.update(chunk)
                bytes_written += len(chunk)
                output.write(chunk)
        return LocalStoredObject(key=key, bytes_written=bytes_written, checksum=digest.hexdigest())

    async def exists(self, key: str) -> bool:
        path = await self.resolve_local_path(key)
        return path.exists()

    async def resolve_local_path(self, key: str) -> Path:
        safe_key = key.lstrip("/").replace("..", "")
        return self.base_dir / safe_key
