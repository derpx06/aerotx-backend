from collections.abc import AsyncIterator

from fastapi import UploadFile

from app.core.security import enforce_upload_size, validate_upload
from app.ports.storage import StorageProvider, StoredObject


class UploadService:
    def __init__(self, storage: StorageProvider):
        self.storage = storage

    async def store(self, file: UploadFile) -> StoredObject:
        validate_upload(file)
        return await self.storage.save_upload(
            file.filename or "transactions.csv", self._bounded_chunks(file)
        )

    async def _bounded_chunks(self, file: UploadFile) -> AsyncIterator[bytes]:
        total_bytes = 0
        while chunk := await file.read(1024 * 1024):
            total_bytes += len(chunk)
            enforce_upload_size(total_bytes)
            yield chunk
