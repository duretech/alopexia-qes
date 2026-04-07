"""Object storage abstraction — S3-compatible with local dev fallback.

Public API:
    StorageBackend      — Protocol for all storage implementations
    get_storage_backend() — Factory that returns the configured backend
    StorageResult       — Result of a store operation
    ObjectMetadata      — Metadata about a stored object
    StorageError, ObjectNotFoundError, ChecksumMismatchError — Exceptions
"""

from app.services.storage.interface import (
    StorageBackend,
    StorageResult,
    ObjectMetadata,
    StorageError,
    ObjectNotFoundError,
    ChecksumMismatchError,
)


def get_storage_backend() -> StorageBackend:
    """Factory: return the configured storage backend.

    Uses S3StorageBackend if S3 credentials are configured,
    otherwise falls back to LocalStorageBackend for dev/testing.
    """
    from app.core.config import get_settings
    settings = get_settings()

    if settings.s3_access_key_id and settings.s3_secret_access_key:
        from app.services.storage.s3 import S3StorageBackend
        return S3StorageBackend(
            endpoint_url=settings.s3_endpoint_url,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
            region=settings.s3_region,
            use_ssl=settings.s3_use_ssl,
        )

    from app.services.storage.local import LocalStorageBackend
    return LocalStorageBackend()


__all__ = [
    "StorageBackend",
    "StorageResult",
    "ObjectMetadata",
    "StorageError",
    "ObjectNotFoundError",
    "ChecksumMismatchError",
    "get_storage_backend",
]
