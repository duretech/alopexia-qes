"""S3-compatible storage backend.

Works with AWS S3, MinIO, and any S3-compatible object store.
Configured via settings (S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, etc.).

For local development with MinIO:
  - Set S3_ENDPOINT_URL=http://localhost:9000
  - Set S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY to MinIO credentials
  - Set S3_USE_SSL=false

For production with AWS S3:
  - Leave S3_ENDPOINT_URL unset (uses AWS default)
  - Configure IAM credentials or instance roles
  - Enable S3_USE_SSL=true (default)

Implements C-DOC-08 (signed URLs), C-DOC-10 (WORM via Object Lock).
"""

import hashlib
from datetime import datetime, timedelta, timezone

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.logging import get_logger
from app.services.storage.interface import (
    StorageBackend,
    StorageResult,
    ObjectMetadata,
    StorageError,
    ObjectNotFoundError,
    ChecksumMismatchError,
)

logger = get_logger(component="s3_storage")


class S3StorageBackend:
    """S3-compatible storage backend using boto3 (synchronous client).

    Uses the synchronous boto3 client wrapped in async methods. For true
    async S3 operations, swap to aioboto3 when the dependency conflict
    in requirements.txt is resolved.
    """

    def __init__(
        self,
        *,
        endpoint_url: str | None = None,
        access_key_id: str = "",
        secret_access_key: str = "",
        region: str = "eu-west-1",
        use_ssl: bool = True,
    ):
        # When a custom endpoint_url is set we're talking to MinIO (or another
        # S3-compatible store).  MinIO does not support AES256 SSE without KMS,
        # so we must skip server-side-encryption headers for non-AWS targets.
        self._is_minio = endpoint_url is not None

        kwargs: dict = {
            "region_name": region,
            "config": BotoConfig(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        }
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        if access_key_id:
            kwargs["aws_access_key_id"] = access_key_id
        if secret_access_key:
            kwargs["aws_secret_access_key"] = secret_access_key
        kwargs["use_ssl"] = use_ssl

        self._client = boto3.client("s3", **kwargs)

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
        # Verify checksum if provided
        actual_checksum = hashlib.sha256(data).hexdigest()
        if checksum_sha256 and actual_checksum != checksum_sha256:
            raise ChecksumMismatchError(expected=checksum_sha256, actual=actual_checksum)

        put_kwargs: dict = {
            "Bucket": bucket,
            "Key": key,
            "Body": data,
            "ContentType": content_type,
        }

        # MinIO (custom endpoint) does not support AES256 SSE without KMS.
        # Skip the header when talking to a non-AWS endpoint.
        if server_side_encryption and not self._is_minio:
            put_kwargs["ServerSideEncryption"] = "AES256"

        if object_lock_days is not None and object_lock_days > 0:
            retain_until = datetime.now(timezone.utc) + timedelta(days=object_lock_days)
            put_kwargs["ObjectLockMode"] = "COMPLIANCE"
            put_kwargs["ObjectLockRetainUntilDate"] = retain_until

        try:
            response = self._client.put_object(**put_kwargs)
        except ClientError as e:
            logger.error("s3_store_failed", bucket=bucket, key=key, error=str(e))
            raise StorageError(f"Failed to store object {bucket}/{key}: {e}") from e

        version_id = response.get("VersionId")
        sse = response.get("ServerSideEncryption")

        logger.info(
            "object_stored",
            bucket=bucket,
            key=key,
            size_bytes=len(data),
            version_id=version_id,
            sse=sse,
        )

        return StorageResult(
            bucket=bucket,
            key=key,
            version_id=version_id,
            checksum_sha256=actual_checksum,
            size_bytes=len(data),
            server_side_encryption=sse,
        )

    async def get_object(
        self,
        bucket: str,
        key: str,
        *,
        version_id: str | None = None,
    ) -> bytes:
        get_kwargs: dict = {"Bucket": bucket, "Key": key}
        if version_id:
            get_kwargs["VersionId"] = version_id

        try:
            response = self._client.get_object(**get_kwargs)
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                raise ObjectNotFoundError(f"Object not found: {bucket}/{key}") from e
            raise StorageError(f"Failed to get object {bucket}/{key}: {e}") from e

    async def get_object_metadata(
        self,
        bucket: str,
        key: str,
        *,
        version_id: str | None = None,
    ) -> ObjectMetadata:
        head_kwargs: dict = {"Bucket": bucket, "Key": key}
        if version_id:
            head_kwargs["VersionId"] = version_id

        try:
            response = self._client.head_object(**head_kwargs)
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                raise ObjectNotFoundError(f"Object not found: {bucket}/{key}") from e
            raise StorageError(f"Failed to get metadata for {bucket}/{key}: {e}") from e

        return ObjectMetadata(
            bucket=bucket,
            key=key,
            size_bytes=response.get("ContentLength", 0),
            content_type=response.get("ContentType", ""),
            version_id=response.get("VersionId"),
            last_modified=response.get("LastModified"),
            server_side_encryption=response.get("ServerSideEncryption"),
            object_lock_mode=response.get("ObjectLockMode"),
            object_lock_retain_until=response.get("ObjectLockRetainUntilDate"),
        )

    async def generate_signed_url(
        self,
        bucket: str,
        key: str,
        *,
        expires_seconds: int = 300,
        version_id: str | None = None,
    ) -> str:
        params: dict = {"Bucket": bucket, "Key": key}
        if version_id:
            params["VersionId"] = version_id

        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expires_seconds,
            )
            return url
        except ClientError as e:
            raise StorageError(f"Failed to generate signed URL for {bucket}/{key}: {e}") from e

    async def delete_object(
        self,
        bucket: str,
        key: str,
        *,
        version_id: str | None = None,
    ) -> bool:
        del_kwargs: dict = {"Bucket": bucket, "Key": key}
        if version_id:
            del_kwargs["VersionId"] = version_id

        try:
            self._client.delete_object(**del_kwargs)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                return False
            raise StorageError(f"Failed to delete object {bucket}/{key}: {e}") from e

    async def object_exists(
        self,
        bucket: str,
        key: str,
    ) -> bool:
        try:
            self._client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False
