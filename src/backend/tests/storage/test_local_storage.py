"""Tests for the local filesystem storage backend.

These tests exercise the full StorageBackend interface against the local
implementation — no S3/MinIO required. The same test patterns can be
reused for integration testing against a real S3 backend.
"""

import hashlib
import tempfile
from pathlib import Path

import pytest

from app.services.storage.local import LocalStorageBackend
from app.services.storage.interface import (
    ObjectNotFoundError,
    ChecksumMismatchError,
    StorageError,
)


@pytest.fixture
def storage(tmp_path):
    """Create a LocalStorageBackend pointed at a temporary directory."""
    return LocalStorageBackend(base_dir=tmp_path)


@pytest.fixture
def sample_pdf():
    """A minimal valid-ish PDF blob for testing."""
    return b"%PDF-1.4 fake prescription content for testing"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TestStoreObject:
    async def test_store_and_retrieve(self, storage, sample_pdf):
        result = await storage.store_object(
            "prescriptions", "tenant-a/doc-001.pdf", sample_pdf,
            content_type="application/pdf",
        )
        assert result.bucket == "prescriptions"
        assert result.key == "tenant-a/doc-001.pdf"
        assert result.size_bytes == len(sample_pdf)
        assert result.checksum_sha256 == _sha256(sample_pdf)

        # Retrieve
        data = await storage.get_object("prescriptions", "tenant-a/doc-001.pdf")
        assert data == sample_pdf

    async def test_store_with_correct_checksum(self, storage, sample_pdf):
        checksum = _sha256(sample_pdf)
        result = await storage.store_object(
            "prescriptions", "doc.pdf", sample_pdf,
            checksum_sha256=checksum,
        )
        assert result.checksum_sha256 == checksum

    async def test_store_with_wrong_checksum_raises(self, storage, sample_pdf):
        with pytest.raises(ChecksumMismatchError) as exc_info:
            await storage.store_object(
                "prescriptions", "doc.pdf", sample_pdf,
                checksum_sha256="0" * 64,
            )
        assert exc_info.value.expected == "0" * 64
        assert exc_info.value.actual == _sha256(sample_pdf)

    async def test_store_creates_nested_directories(self, storage, sample_pdf):
        result = await storage.store_object(
            "evidence", "tenant-a/prescription-123/evidence-456.json",
            sample_pdf,
        )
        assert result.bucket == "evidence"


class TestGetObject:
    async def test_get_nonexistent_raises(self, storage):
        with pytest.raises(ObjectNotFoundError):
            await storage.get_object("prescriptions", "nonexistent.pdf")


class TestGetObjectMetadata:
    async def test_metadata_after_store(self, storage, sample_pdf):
        await storage.store_object(
            "prescriptions", "doc.pdf", sample_pdf,
            content_type="application/pdf",
        )
        meta = await storage.get_object_metadata("prescriptions", "doc.pdf")
        assert meta.bucket == "prescriptions"
        assert meta.key == "doc.pdf"
        assert meta.size_bytes == len(sample_pdf)
        assert meta.content_type == "application/pdf"
        assert meta.checksum_sha256 == _sha256(sample_pdf)

    async def test_metadata_nonexistent_raises(self, storage):
        with pytest.raises(ObjectNotFoundError):
            await storage.get_object_metadata("prescriptions", "nope.pdf")


class TestGenerateSignedUrl:
    async def test_returns_file_url(self, storage, sample_pdf):
        await storage.store_object("prescriptions", "doc.pdf", sample_pdf)
        url = await storage.generate_signed_url("prescriptions", "doc.pdf")
        assert url.startswith("file://")

    async def test_signed_url_nonexistent_raises(self, storage):
        with pytest.raises(ObjectNotFoundError):
            await storage.generate_signed_url("prescriptions", "nope.pdf")


class TestDeleteObject:
    async def test_delete_existing(self, storage, sample_pdf):
        await storage.store_object("prescriptions", "doc.pdf", sample_pdf)
        assert await storage.delete_object("prescriptions", "doc.pdf") is True
        assert await storage.object_exists("prescriptions", "doc.pdf") is False

    async def test_delete_nonexistent_returns_false(self, storage):
        assert await storage.delete_object("prescriptions", "nope.pdf") is False


class TestObjectExists:
    async def test_exists_after_store(self, storage, sample_pdf):
        await storage.store_object("prescriptions", "doc.pdf", sample_pdf)
        assert await storage.object_exists("prescriptions", "doc.pdf") is True

    async def test_not_exists(self, storage):
        assert await storage.object_exists("prescriptions", "nope.pdf") is False


class TestPathTraversal:
    async def test_traversal_blocked(self, storage, sample_pdf):
        with pytest.raises(StorageError):
            await storage.store_object(
                "prescriptions", "../../etc/passwd", sample_pdf,
            )
