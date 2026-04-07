"""Local filesystem storage backend for development and testing.

Stores objects as files on disk, organised by bucket/key. Provides the
same interface as the S3 backend but without any external dependencies.

This backend does NOT implement:
  - Server-side encryption (files are stored as plaintext on disk)
  - WORM/Object Lock (files can be freely deleted)
  - Signed URLs (returns file:// URLs instead)

These limitations are acceptable for local dev and testing. The interface
contract is the same, so switching to S3StorageBackend in production
requires no code changes in the service layer.
"""

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path

from app.core.logging import get_logger
from app.services.storage.interface import (
    StorageResult,
    ObjectMetadata,
    StorageError,
    ObjectNotFoundError,
    ChecksumMismatchError,
)

logger = get_logger(component="local_storage")


class LocalStorageBackend:
    """Filesystem-based storage backend for local development."""

    def __init__(self, base_dir: str | Path = "/tmp/qesflow-storage"):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _object_path(self, bucket: str, key: str) -> Path:
        path = self._base_dir / bucket / key
        # Prevent path traversal
        resolved = path.resolve()
        if not str(resolved).startswith(str(self._base_dir.resolve())):
            raise StorageError(f"Invalid key (path traversal detected): {key}")
        return path

    async def store_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
        checksum_sha256: str | None = None,
        server_side_encryption: bool = True,
        object_lock_days: int | None = None,
    ) -> StorageResult:
        actual_checksum = hashlib.sha256(data).hexdigest()
        if checksum_sha256 and actual_checksum != checksum_sha256:
            raise ChecksumMismatchError(expected=checksum_sha256, actual=actual_checksum)

        path = self._object_path(bucket, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

        # Store content type in a sidecar metadata file
        meta_path = Path(str(path) + ".meta")
        meta_path.write_text(
            f"content_type={content_type}\n"
            f"checksum_sha256={actual_checksum}\n"
            f"size_bytes={len(data)}\n"
            f"stored_at={datetime.now(timezone.utc).isoformat()}\n"
        )

        logger.info(
            "object_stored_local",
            bucket=bucket,
            key=key,
            size_bytes=len(data),
            path=str(path),
        )

        return StorageResult(
            bucket=bucket,
            key=key,
            version_id=None,
            checksum_sha256=actual_checksum,
            size_bytes=len(data),
            server_side_encryption=None,
        )

    async def get_object(
        self,
        bucket: str,
        key: str,
        *,
        version_id: str | None = None,
    ) -> bytes:
        path = self._object_path(bucket, key)
        if not path.exists():
            raise ObjectNotFoundError(f"Object not found: {bucket}/{key}")
        return path.read_bytes()

    async def get_object_metadata(
        self,
        bucket: str,
        key: str,
        *,
        version_id: str | None = None,
    ) -> ObjectMetadata:
        path = self._object_path(bucket, key)
        if not path.exists():
            raise ObjectNotFoundError(f"Object not found: {bucket}/{key}")

        stat = path.stat()
        content_type = "application/octet-stream"
        checksum = None

        meta_path = Path(str(path) + ".meta")
        if meta_path.exists():
            for line in meta_path.read_text().strip().split("\n"):
                if line.startswith("content_type="):
                    content_type = line.split("=", 1)[1]
                elif line.startswith("checksum_sha256="):
                    checksum = line.split("=", 1)[1]

        return ObjectMetadata(
            bucket=bucket,
            key=key,
            size_bytes=stat.st_size,
            content_type=content_type,
            checksum_sha256=checksum,
            last_modified=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        )

    async def generate_signed_url(
        self,
        bucket: str,
        key: str,
        *,
        expires_seconds: int = 300,
        version_id: str | None = None,
    ) -> str:
        path = self._object_path(bucket, key)
        if not path.exists():
            raise ObjectNotFoundError(f"Object not found: {bucket}/{key}")
        # Return a file:// URL for local dev (not a real signed URL)
        return path.as_uri()

    async def delete_object(
        self,
        bucket: str,
        key: str,
        *,
        version_id: str | None = None,
    ) -> bool:
        path = self._object_path(bucket, key)
        if not path.exists():
            return False
        path.unlink()
        meta_path = Path(str(path) + ".meta")
        if meta_path.exists():
            meta_path.unlink()
        return True

    async def object_exists(
        self,
        bucket: str,
        key: str,
    ) -> bool:
        return self._object_path(bucket, key).exists()
