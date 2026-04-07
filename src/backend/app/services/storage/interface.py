"""Storage backend interface — contract for all storage implementations.

Every storage backend (S3, MinIO, local filesystem) MUST implement this
protocol. The interface is designed around the requirements of the QES Flow
document lifecycle:

  1. Store opaque blobs (PDFs) — never mutate after write
  2. Generate time-limited signed URLs for download — no public access
  3. Support WORM/Object Lock semantics for compliance
  4. Server-side encryption at rest
  5. Checksum verification on read

Design notes:
  - Storage keys are system-generated (randomized), never user-controlled
  - Original filenames are hashed and stored separately, never used as keys
  - Separate buckets for prescriptions, evidence, and audit exports
  - All operations are async

Implements C-DOC-08 (signed URLs only), C-DOC-09 (immutability),
C-DOC-10 (WORM storage) from the controls catalog.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class StorageResult:
    """Result of a successful store operation."""
    bucket: str
    key: str
    version_id: str | None = None
    checksum_sha256: str | None = None
    size_bytes: int = 0
    server_side_encryption: str | None = None


@dataclass(frozen=True)
class ObjectMetadata:
    """Metadata about a stored object."""
    bucket: str
    key: str
    size_bytes: int = 0
    content_type: str = ""
    checksum_sha256: str | None = None
    version_id: str | None = None
    last_modified: datetime | None = None
    server_side_encryption: str | None = None
    object_lock_mode: str | None = None
    object_lock_retain_until: datetime | None = None


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for object storage backends."""

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
        """Store a blob in the specified bucket.

        Args:
            bucket: Target bucket name.
            key: Object key (system-generated, not user-controlled).
            data: Raw bytes to store.
            content_type: MIME type of the object.
            checksum_sha256: Expected SHA-256 hex digest for verification.
            server_side_encryption: Whether to enable SSE.
            object_lock_days: If set, apply WORM retention for this many days.

        Returns:
            StorageResult with storage details.

        Raises:
            StorageError: If the store operation fails.
            ChecksumMismatchError: If the provided checksum doesn't match.
        """
        ...

    async def get_object(
        self,
        bucket: str,
        key: str,
        *,
        version_id: str | None = None,
    ) -> bytes:
        """Retrieve a stored object's raw bytes.

        For large files, prefer generate_signed_url() and let the client
        download directly. This method is for internal processing only.

        Raises:
            ObjectNotFoundError: If the object doesn't exist.
        """
        ...

    async def get_object_metadata(
        self,
        bucket: str,
        key: str,
        *,
        version_id: str | None = None,
    ) -> ObjectMetadata:
        """Get metadata about a stored object without downloading it.

        Raises:
            ObjectNotFoundError: If the object doesn't exist.
        """
        ...

    async def generate_signed_url(
        self,
        bucket: str,
        key: str,
        *,
        expires_seconds: int = 300,
        version_id: str | None = None,
    ) -> str:
        """Generate a time-limited signed download URL.

        Default expiry is 5 minutes — short TTL for security.
        No public URLs are ever generated.

        Raises:
            ObjectNotFoundError: If the object doesn't exist.
        """
        ...

    async def delete_object(
        self,
        bucket: str,
        key: str,
        *,
        version_id: str | None = None,
    ) -> bool:
        """Delete an object. Returns True if deleted, False if not found.

        WARNING: This will fail on objects under WORM/Object Lock retention.
        Callers must check retention status before attempting deletion.
        """
        ...

    async def object_exists(
        self,
        bucket: str,
        key: str,
    ) -> bool:
        """Check if an object exists without downloading it."""
        ...


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class ObjectNotFoundError(StorageError):
    """Raised when a requested object does not exist."""
    pass


class ChecksumMismatchError(StorageError):
    """Raised when a checksum verification fails on store/retrieve."""
    def __init__(self, expected: str, actual: str):
        self.expected = expected
        self.actual = actual
        super().__init__(f"Checksum mismatch: expected {expected}, got {actual}")
