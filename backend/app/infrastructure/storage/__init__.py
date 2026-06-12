from app.core.config import get_settings
from app.ports.storage import StorageProvider


def get_storage_provider() -> StorageProvider:
    settings = get_settings()
    if settings.storage_provider == "s3":
        from app.infrastructure.storage.s3 import S3StorageProvider

        return S3StorageProvider()
    else:
        from app.infrastructure.storage.local import LocalStorageProvider

        return LocalStorageProvider()
