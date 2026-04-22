"""Azure Blob Storage backend.

Implements the StorageBackend protocol using the azure-storage-blob SDK.

Credential options (in order of precedence):
  1. Connection string  (AZURE_STORAGE_CONNECTION_STRING)
  2. Account name + key (AZURE_STORAGE_ACCOUNT_NAME + AZURE_STORAGE_ACCOUNT_KEY)

Mapping to S3 concepts:
  bucket  → container
  key     → blob name
  signed  → SAS URL (time-limited, read-only)

Azure encrypts all data at rest by default — no SSE flag needed.
Object Lock / WORM is container-level in Azure (immutability policy),
not blob-level. object_lock_days is logged but not enforced here.
"""

import hashlib
from datetime import datetime, timedelta, timezone

from azure.core.exceptions import ResourceNotFoundError, AzureError
from azure.storage.blob import (
    BlobServiceClient,
    BlobSasPermissions,
    ContentSettings,
    generate_blob_sas,
)

from app.core.logging import get_logger
from app.services.storage.interface import (
    ChecksumMismatchError,
    ObjectMetadata,
    ObjectNotFoundError,
    StorageError,
    StorageResult,
)

logger = get_logger(component="azure_blob_storage")


class AzureBlobStorageBackend:
    """Azure Blob Storage implementation of StorageBackend."""

    def __init__(
        self,
        *,
        connection_string: str = "",
        account_name: str = "",
        account_key: str = "",
    ):
        if connection_string:
            self._client = BlobServiceClient.from_connection_string(connection_string)
            parsed = _parse_connection_string(connection_string)
            self._account_name = parsed.get("AccountName", account_name)
            self._account_key = parsed.get("AccountKey", account_key)
        elif account_name and account_key:
            account_url = f"https://{account_name}.blob.core.windows.net"
            self._client = BlobServiceClient(account_url=account_url, credential=account_key)
            self._account_name = account_name
            self._account_key = account_key
        else:
            raise ValueError(
                "Azure storage requires either AZURE_STORAGE_CONNECTION_STRING "
                "or both AZURE_STORAGE_ACCOUNT_NAME and AZURE_STORAGE_ACCOUNT_KEY"
            )

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

        if object_lock_days:
            logger.warning(
                "azure_object_lock_not_blob_level",
                key=key,
                hint="Configure an immutability policy on the container in the Azure portal instead.",
            )

        try:
            blob_client = self._client.get_blob_client(container=bucket, blob=key)
            response = blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
            )
        except AzureError as e:
            logger.error("azure_store_failed", bucket=bucket, key=key, error=str(e))
            raise StorageError(f"Failed to store object {bucket}/{key}: {e}") from e

        version_id = response.get("version_id")
        logger.info("object_stored", bucket=bucket, key=key, size_bytes=len(data), version_id=version_id)

        return StorageResult(
            bucket=bucket,
            key=key,
            version_id=version_id,
            checksum_sha256=actual_checksum,
            size_bytes=len(data),
            server_side_encryption="AzureStorageServiceEncryption",
        )

    async def get_object(
        self,
        bucket: str,
        key: str,
        *,
        version_id: str | None = None,
    ) -> bytes:
        try:
            blob_client = self._client.get_blob_client(container=bucket, blob=key)
            downloader = blob_client.download_blob(version_id=version_id)
            return downloader.readall()
        except ResourceNotFoundError as e:
            raise ObjectNotFoundError(f"Object not found: {bucket}/{key}") from e
        except AzureError as e:
            raise StorageError(f"Failed to get object {bucket}/{key}: {e}") from e

    async def get_object_metadata(
        self,
        bucket: str,
        key: str,
        *,
        version_id: str | None = None,
    ) -> ObjectMetadata:
        try:
            blob_client = self._client.get_blob_client(container=bucket, blob=key)
            props = blob_client.get_blob_properties(version_id=version_id)
        except ResourceNotFoundError as e:
            raise ObjectNotFoundError(f"Object not found: {bucket}/{key}") from e
        except AzureError as e:
            raise StorageError(f"Failed to get metadata for {bucket}/{key}: {e}") from e

        return ObjectMetadata(
            bucket=bucket,
            key=key,
            size_bytes=props.size,
            content_type=props.content_settings.content_type or "",
            version_id=props.get("version_id"),
            last_modified=props.last_modified,
            server_side_encryption="AzureStorageServiceEncryption",
        )

    async def generate_signed_url(
        self,
        bucket: str,
        key: str,
        *,
        expires_seconds: int = 300,
        version_id: str | None = None,
    ) -> str:
        try:
            expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_seconds)
            sas_token = generate_blob_sas(
                account_name=self._account_name,
                container_name=bucket,
                blob_name=key,
                account_key=self._account_key,
                permission=BlobSasPermissions(read=True),
                expiry=expiry,
                version_id=version_id,
            )
            return (
                f"https://{self._account_name}.blob.core.windows.net"
                f"/{bucket}/{key}?{sas_token}"
            )
        except AzureError as e:
            raise StorageError(f"Failed to generate signed URL for {bucket}/{key}: {e}") from e

    async def delete_object(
        self,
        bucket: str,
        key: str,
        *,
        version_id: str | None = None,
    ) -> bool:
        try:
            blob_client = self._client.get_blob_client(container=bucket, blob=key)
            blob_client.delete_blob(version_id=version_id)
            return True
        except ResourceNotFoundError:
            return False
        except AzureError as e:
            raise StorageError(f"Failed to delete object {bucket}/{key}: {e}") from e

    async def object_exists(
        self,
        bucket: str,
        key: str,
    ) -> bool:
        blob_client = self._client.get_blob_client(container=bucket, blob=key)
        return blob_client.exists()


def _parse_connection_string(connection_string: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in connection_string.split(";"):
        if "=" in part:
            k, _, v = part.partition("=")
            result[k] = v
    return result
