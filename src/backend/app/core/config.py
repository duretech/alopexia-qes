"""Application configuration loaded from environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

# Resolve .env from project root (two levels up from app/core/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env" if (_PROJECT_ROOT / ".env").exists() else ".env"


class Settings(BaseSettings):
    # Application
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_secret_key: str = Field(..., alias="APP_SECRET_KEY")
    app_allowed_hosts: str = Field(default="localhost", alias="APP_ALLOWED_HOSTS")
    app_cors_origins: str = Field(default="http://localhost:3000", alias="APP_CORS_ORIGINS")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")
    database_schema: str = Field(default="alopexiaqes", alias="DATABASE_SCHEMA")
    database_pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")

    # S3
    s3_endpoint_url: Optional[str] = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_access_key_id: str = Field(default="", alias="S3_ACCESS_KEY_ID")
    s3_secret_access_key: str = Field(default="", alias="S3_SECRET_ACCESS_KEY")
    s3_region: str = Field(default="eu-west-1", alias="S3_REGION")
    s3_prescription_bucket: str = Field(default="qesflow-prescriptions", alias="S3_PRESCRIPTION_BUCKET")
    s3_evidence_bucket: str = Field(default="qesflow-evidence", alias="S3_EVIDENCE_BUCKET")
    s3_audit_export_bucket: str = Field(default="qesflow-audit-exports", alias="S3_AUDIT_EXPORT_BUCKET")
    s3_use_ssl: bool = Field(default=True, alias="S3_USE_SSL")

    # Azure Blob Storage (alternative to S3; takes precedence when set)
    azure_storage_connection_string: str = Field(default="", alias="AZURE_STORAGE_CONNECTION_STRING")
    azure_storage_account_name: str = Field(default="", alias="AZURE_STORAGE_ACCOUNT_NAME")
    azure_storage_account_key: str = Field(default="", alias="AZURE_STORAGE_ACCOUNT_KEY")
    azure_prescription_container: str = Field(default="prescriptions", alias="AZURE_PRESCRIPTION_CONTAINER")
    azure_evidence_container: str = Field(default="evidence", alias="AZURE_EVIDENCE_CONTAINER")
    azure_audit_export_container: str = Field(default="audit-exports", alias="AZURE_AUDIT_EXPORT_CONTAINER")

    # SQS
    sqs_endpoint_url: Optional[str] = Field(default=None, alias="SQS_ENDPOINT_URL")
    sqs_region: str = Field(default="eu-west-1", alias="SQS_REGION")
    sqs_verification_queue_url: str = Field(default="", alias="SQS_VERIFICATION_QUEUE_URL")
    sqs_evidence_queue_url: str = Field(default="", alias="SQS_EVIDENCE_QUEUE_URL")

    # QTSP
    qtsp_provider: str = Field(default="mock", alias="QTSP_PROVIDER")
    qtsp_api_url: str = Field(default="", alias="QTSP_API_URL")
    qtsp_api_key: str = Field(default="", alias="QTSP_API_KEY")
    qtsp_timeout_seconds: int = Field(default=30, alias="QTSP_TIMEOUT_SECONDS")
    qtsp_max_retries: int = Field(default=3, alias="QTSP_MAX_RETRIES")

    # Auth
    auth_provider: str = Field(default="mock", alias="AUTH_PROVIDER")
    oidc_issuer_url: str = Field(default="", alias="OIDC_ISSUER_URL")
    oidc_client_id: str = Field(default="", alias="OIDC_CLIENT_ID")
    oidc_client_secret: str = Field(default="", alias="OIDC_CLIENT_SECRET")
    oidc_redirect_uri: str = Field(default="", alias="OIDC_REDIRECT_URI")

    # Session
    session_idle_timeout_minutes: int = Field(default=30, alias="SESSION_IDLE_TIMEOUT_MINUTES")
    session_absolute_timeout_minutes: int = Field(default=480, alias="SESSION_ABSOLUTE_TIMEOUT_MINUTES")
    session_max_concurrent: int = Field(default=3, alias="SESSION_MAX_CONCURRENT")

    # Security
    rate_limit_default: str = Field(default="100/minute", alias="RATE_LIMIT_DEFAULT")
    rate_limit_login: str = Field(default="10/minute", alias="RATE_LIMIT_LOGIN")
    rate_limit_upload: str = Field(default="20/minute", alias="RATE_LIMIT_UPLOAD")
    max_upload_size_mb: int = Field(default=25, alias="MAX_UPLOAD_SIZE_MB")

    # Malware
    malware_scanner: str = Field(default="mock", alias="MALWARE_SCANNER")
    clamav_host: str = Field(default="localhost", alias="CLAMAV_HOST")
    clamav_port: int = Field(default=3310, alias="CLAMAV_PORT")

    # Observability
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")

    # Encryption
    field_encryption_key: str = Field(default="", alias="FIELD_ENCRYPTION_KEY")

    # SMS OTP (GatewayAPI)
    sms_gateway_url: str = Field(default="https://gatewayapi.eu/rest/mtsms", alias="SMS_GATEWAY_URL")
    sms_gateway_token: str = Field(default="", alias="SMS_GATEWAY_TOKEN")
    sms_sender_name: str = Field(default="QESFlow", alias="SMS_SENDER_NAME")
    sms_otp_ttl_seconds: int = Field(default=300, alias="SMS_OTP_TTL_SECONDS")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.app_cors_origins.split(",")]

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.app_allowed_hosts.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def _use_azure(self) -> bool:
        return bool(self.azure_storage_connection_string or self.azure_storage_account_name)

    @property
    def prescription_storage_container(self) -> str:
        return self.azure_prescription_container if self._use_azure else self.s3_prescription_bucket

    @property
    def evidence_storage_container(self) -> str:
        return self.azure_evidence_container if self._use_azure else self.s3_evidence_bucket

    @property
    def audit_storage_container(self) -> str:
        return self.azure_audit_export_container if self._use_azure else self.s3_audit_export_bucket

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    model_config = {
        "env_file": str(_ENV_FILE),
        "case_sensitive": False,
    }


def get_settings() -> Settings:
    return Settings()
