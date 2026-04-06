"""Application-level field encryption for PII columns.

Uses AES-256-GCM for authenticated encryption. The key is loaded from
FIELD_ENCRYPTION_KEY environment variable (base64-encoded 32 bytes).

This encrypts data BEFORE it reaches PostgreSQL, so the DB only ever
sees ciphertext. Key management stays in the application / vault layer.

Fields that use this:
- patients.full_name_encrypted
- patients.date_of_birth_encrypted
- prescription_metadata.medication_name (when encrypted)
- prescription_metadata.dosage (when encrypted)
- prescription_metadata.instructions (when encrypted)

The ciphertext format stored in the DB is:
    base64(nonce || ciphertext || tag)

where nonce=12 bytes, tag=16 bytes (appended by GCM).
"""

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class FieldEncryptor:
    """Encrypts and decrypts individual field values using AES-256-GCM."""

    def __init__(self, key_b64: str):
        """
        Args:
            key_b64: Base64-encoded 32-byte key. Generate with:
                     python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
        """
        if not key_b64:
            raise ValueError(
                "FIELD_ENCRYPTION_KEY is required. "
                "Generate with: python -c \"import os,base64; print(base64.b64encode(os.urandom(32)).decode())\""
            )
        key_bytes = base64.b64decode(key_b64)
        if len(key_bytes) != 32:
            raise ValueError("FIELD_ENCRYPTION_KEY must be exactly 32 bytes (256 bits) when decoded")
        self._aesgcm = AESGCM(key_bytes)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string field value. Returns base64-encoded ciphertext.

        Each call generates a unique random nonce, so encrypting the same
        value twice produces different ciphertext (semantic security).
        """
        if not plaintext:
            return ""
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        # Store as: base64(nonce + ciphertext_with_tag)
        return base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, ciphertext_b64: str) -> str:
        """Decrypt a base64-encoded ciphertext back to plaintext string."""
        if not ciphertext_b64:
            return ""
        raw = base64.b64decode(ciphertext_b64)
        nonce = raw[:12]
        ciphertext = raw[12:]
        plaintext_bytes = self._aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext_bytes.decode("utf-8")


def hash_identifier(value: str) -> str:
    """One-way SHA-256 hash for identifier deduplication (patient ID, etc.).

    This is NOT reversible. Used for lookup/dedup, not display.
    The original value must be encrypted separately if it needs to be retrieved.
    """
    if not value:
        return ""
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


# Singleton instance — initialized on first use from settings
_encryptor: FieldEncryptor | None = None


def get_encryptor() -> FieldEncryptor:
    """Get or create the singleton FieldEncryptor from app settings."""
    global _encryptor
    if _encryptor is None:
        from app.core.config import get_settings
        settings = get_settings()
        _encryptor = FieldEncryptor(settings.field_encryption_key)
    return _encryptor


def encrypt_field(value: str) -> str:
    """Convenience: encrypt a PII field value."""
    return get_encryptor().encrypt(value)


def decrypt_field(value: str) -> str:
    """Convenience: decrypt a PII field value."""
    return get_encryptor().decrypt(value)
