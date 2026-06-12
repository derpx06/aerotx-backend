import asyncio
import hashlib
from pathlib import Path
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings


class S3StoredObject:
    def __init__(self, key: str, bytes_written: int, checksum: str):
        self.key = key
        self.bytes_written = bytes_written
        self.checksum = checksum


class S3StorageProvider:
    def __init__(self, bucket_name: str | None = None, local_cache_dir: str | None = None):
        settings = get_settings()
        self.bucket_name = bucket_name or settings.s3_bucket_name
        self.local_cache_dir = Path(local_cache_dir or settings.upload_dir)
        self.local_cache_dir.mkdir(parents=True, exist_ok=True)
        self.s3_client = boto3.client("s3")

    async def save_upload(self, filename: str, chunks) -> S3StoredObject:
        suffix = Path(filename).suffix or ".csv"
        key = f"uploads/{uuid4()}{suffix}"

        # Resolve local path (which creates directories)
        local_temp_path = await self.resolve_local_path(key)
        local_temp_path.parent.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256()
        bytes_written = 0
        with local_temp_path.open("wb") as output:
            async for chunk in chunks:
                digest.update(chunk)
                bytes_written += len(chunk)
                output.write(chunk)

        # Upload to S3 in a non-blocking background thread
        await asyncio.to_thread(
            self.s3_client.upload_file, str(local_temp_path), self.bucket_name, key
        )

        return S3StoredObject(key=key, bytes_written=bytes_written, checksum=digest.hexdigest())

    async def exists(self, key: str) -> bool:
        try:
            # Query S3 in a non-blocking background thread
            await asyncio.to_thread(
                self.s3_client.head_object, Bucket=self.bucket_name, Key=key
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            raise

    async def resolve_local_path(self, key: str) -> Path:
        safe_key = key.lstrip("/").replace("..", "")
        local_path = self.local_cache_dir / safe_key
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # If file is not present locally, retrieve it from the S3 bucket in a non-blocking thread
        if not local_path.exists():
            try:
                await asyncio.to_thread(
                    self.s3_client.download_file, self.bucket_name, key, str(local_path)
                )
            except ClientError:
                # Silently catch download errors if the object hasn't been uploaded yet
                pass
        return local_path
