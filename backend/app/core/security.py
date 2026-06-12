from fastapi import HTTPException, UploadFile, status

from app.core.config import get_settings


def validate_upload(file: UploadFile) -> None:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV uploads are supported"
        )
    content_type = file.content_type or ""
    if content_type and content_type not in {
        "text/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid upload content type"
        )


def enforce_upload_size(size_bytes: int) -> None:
    if size_bytes > get_settings().upload_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="CSV is too large"
        )
