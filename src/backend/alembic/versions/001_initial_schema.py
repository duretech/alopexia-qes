"""Initial schema — all 24 tables in the 'alopexiaqes' PostgreSQL schema.

Revision ID: 001_initial
Revises: None
Create Date: 2026-04-03

This migration:
- Creates the 'alopexiaqes' schema
- Enables pgcrypto extension (for gen_random_uuid and hashing functions)
- Creates all 24 tables with proper indexes, constraints, and FK relationships
- Adds DB-level triggers to protect audit_events (append-only)
- Adds an auto-updating updated_at trigger for all mutable tables
- Creates the audit_event_seq sequence for hash-chain ordering

All PII fields that require application-level encryption are stored as TEXT
columns with names ending in '_encrypted'. The actual AES-256-GCM encryption
happens in the application layer (see app/utils/encryption.py), NOT in the DB.
This means the DB sees ciphertext, and key management stays in the app/vault.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "alopexiaqes"


def upgrade() -> None:
    # =========================================================================
    # 0. Schema and extensions
    # =========================================================================
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    # pgcrypto: gen_random_uuid() is built-in since PG13.
    # CREATE EXTENSION requires superuser — use a savepoint so failure
    # doesn't abort the migration transaction.
    conn = op.get_bind()
    conn.execute(sa.text("SAVEPOINT pgcrypto_sp"))
    try:
        conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        conn.execute(sa.text("RELEASE SAVEPOINT pgcrypto_sp"))
    except Exception:
        conn.execute(sa.text("ROLLBACK TO SAVEPOINT pgcrypto_sp"))

    # Auto-update updated_at on any row modification
    op.execute(f"""
        CREATE OR REPLACE FUNCTION {SCHEMA}.set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # =========================================================================
    # 1. Tenants
    # =========================================================================
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("settings", JSONB, nullable=False, server_default="{}"),
        sa.Column("primary_contact_email", sa.String(320), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    _add_updated_at_trigger("tenants")

    # =========================================================================
    # 2. Clinics
    # =========================================================================
    op.create_table(
        "clinics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("license_number", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("settings", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_clinic_tenant_id", "clinics", ["tenant_id"], schema=SCHEMA)
    op.create_unique_constraint("uq_clinic_tenant_name", "clinics", ["tenant_id", "name"], schema=SCHEMA)
    _add_updated_at_trigger("clinics")

    # =========================================================================
    # 3. Doctors
    # =========================================================================
    op.create_table(
        "doctors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("external_idp_id", sa.String(500), nullable=False,
                  comment="Immutable — identity from external IdP (OIDC sub claim)"),
        sa.Column("email", sa.String(320), nullable=False,
                  comment="ENCRYPTION_SENSITIVE — doctor email"),
        sa.Column("full_name", sa.String(500), nullable=False,
                  comment="ENCRYPTION_SENSITIVE — doctor full name"),
        sa.Column("license_number", sa.String(100), nullable=True,
                  comment="Medical license / colegiado number"),
        sa.Column("clinic_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.clinics.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_doctor_tenant_id", "doctors", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_doctor_clinic_id", "doctors", ["clinic_id"], schema=SCHEMA)
    op.create_index("ix_doctor_tenant_clinic", "doctors", ["tenant_id", "clinic_id"], schema=SCHEMA)
    op.create_unique_constraint("uq_doctor_tenant_idp", "doctors", ["tenant_id", "external_idp_id"], schema=SCHEMA)
    op.create_unique_constraint("uq_doctor_tenant_email", "doctors", ["tenant_id", "email"], schema=SCHEMA)
    _add_updated_at_trigger("doctors")

    # =========================================================================
    # 4. Pharmacy Users
    # =========================================================================
    op.create_table(
        "pharmacy_users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("external_idp_id", sa.String(500), nullable=False),
        sa.Column("email", sa.String(320), nullable=False,
                  comment="ENCRYPTION_SENSITIVE"),
        sa.Column("full_name", sa.String(500), nullable=False,
                  comment="ENCRYPTION_SENSITIVE"),
        sa.Column("pharmacy_name", sa.String(500), nullable=False),
        sa.Column("pharmacy_license_number", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_pharma_tenant_id", "pharmacy_users", ["tenant_id"], schema=SCHEMA)
    op.create_unique_constraint("uq_pharma_tenant_idp", "pharmacy_users", ["tenant_id", "external_idp_id"], schema=SCHEMA)
    op.create_unique_constraint("uq_pharma_tenant_email", "pharmacy_users", ["tenant_id", "email"], schema=SCHEMA)
    _add_updated_at_trigger("pharmacy_users")

    # =========================================================================
    # 5. Admin Users
    # =========================================================================
    op.create_table(
        "admin_users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("external_idp_id", sa.String(500), nullable=False),
        sa.Column("email", sa.String(320), nullable=False, comment="ENCRYPTION_SENSITIVE"),
        sa.Column("full_name", sa.String(500), nullable=False, comment="ENCRYPTION_SENSITIVE"),
        sa.Column("role", sa.String(50), nullable=False,
                  comment="clinic_admin, tenant_admin, compliance_officer, platform_admin, support"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requires_justification", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_admin_tenant_id", "admin_users", ["tenant_id"], schema=SCHEMA)
    op.create_unique_constraint("uq_admin_tenant_idp", "admin_users", ["tenant_id", "external_idp_id"], schema=SCHEMA)
    op.create_unique_constraint("uq_admin_tenant_email", "admin_users", ["tenant_id", "email"], schema=SCHEMA)
    _add_updated_at_trigger("admin_users")

    # =========================================================================
    # 6. Auditors
    # =========================================================================
    op.create_table(
        "auditors",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("external_idp_id", sa.String(500), nullable=False),
        sa.Column("email", sa.String(320), nullable=False, comment="ENCRYPTION_SENSITIVE"),
        sa.Column("full_name", sa.String(500), nullable=False, comment="ENCRYPTION_SENSITIVE"),
        sa.Column("organization", sa.String(500), nullable=True),
        sa.Column("scope", sa.String(100), nullable=False, server_default="read_only"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_auditor_tenant_id", "auditors", ["tenant_id"], schema=SCHEMA)
    op.create_unique_constraint("uq_auditor_tenant_idp", "auditors", ["tenant_id", "external_idp_id"], schema=SCHEMA)
    _add_updated_at_trigger("auditors")

    # =========================================================================
    # 7. Patients (PII encrypted at application layer)
    # =========================================================================
    op.create_table(
        "patients",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("identifier_hash", sa.String(128), nullable=False,
                  comment="SHA-256 hash of national ID — for dedup, not display"),
        sa.Column("full_name_encrypted", sa.Text, nullable=False,
                  comment="AES-256-GCM ciphertext of full name"),
        sa.Column("date_of_birth_encrypted", sa.Text, nullable=True,
                  comment="AES-256-GCM ciphertext of date of birth"),
        sa.Column("national_id_hash", sa.String(128), nullable=True,
                  comment="SHA-256 hash of DNI/NIE — for lookup, not display"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_patient_tenant_id", "patients", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_patient_tenant_active", "patients", ["tenant_id", "is_active"], schema=SCHEMA)
    op.create_unique_constraint("uq_patient_tenant_identifier", "patients", ["tenant_id", "identifier_hash"], schema=SCHEMA)
    _add_updated_at_trigger("patients")

    # =========================================================================
    # 8. Prescriptions
    # =========================================================================
    op.create_table(
        "prescriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.doctors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("patient_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.patients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("clinic_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.clinics.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assigned_pharmacy_user_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.pharmacy_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending_verification"),
        sa.Column("verification_status", sa.String(50), nullable=True),
        sa.Column("dispensing_status", sa.String(50), nullable=True),
        sa.Column("upload_checksum", sa.String(128), nullable=False,
                  comment="Immutable — SHA-256 of uploaded PDF"),
        sa.Column("document_storage_key", sa.String(1000), nullable=False),
        sa.Column("idempotency_key", sa.String(100), nullable=False,
                  comment="Immutable — client-provided for upload dedup"),
        sa.Column("prescribed_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("external_prescription_id", sa.String(500), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", UUID(as_uuid=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text, nullable=True),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_under_legal_hold", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "status IN ('draft','pending_verification','verified','failed_verification',"
            "'manual_review','available','dispensed','cancelled','revoked','expired')",
            name="ck_rx_status",
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_rx_tenant_id", "prescriptions", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_rx_tenant_status", "prescriptions", ["tenant_id", "status"], schema=SCHEMA)
    op.create_index("ix_rx_tenant_doctor", "prescriptions", ["tenant_id", "doctor_id"], schema=SCHEMA)
    op.create_index("ix_rx_tenant_patient", "prescriptions", ["tenant_id", "patient_id"], schema=SCHEMA)
    op.create_index("ix_rx_tenant_pharmacy", "prescriptions", ["tenant_id", "assigned_pharmacy_user_id"], schema=SCHEMA)
    op.create_unique_constraint("uq_rx_tenant_idempotency", "prescriptions", ["tenant_id", "idempotency_key"], schema=SCHEMA)
    _add_updated_at_trigger("prescriptions")

    # =========================================================================
    # 9. Prescription Metadata (medication fields encrypted at app layer)
    # =========================================================================
    op.create_table(
        "prescription_metadata",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("prescription_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.prescriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("medication_name", sa.Text, nullable=True, comment="ENCRYPTION_SENSITIVE"),
        sa.Column("dosage", sa.Text, nullable=True, comment="ENCRYPTION_SENSITIVE"),
        sa.Column("treatment_duration", sa.String(200), nullable=True),
        sa.Column("instructions", sa.Text, nullable=True, comment="ENCRYPTION_SENSITIVE"),
        sa.Column("is_compounded", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("formulation_details", JSONB, nullable=True),
        sa.Column("formulation_registration_number", sa.String(200), nullable=True),
        sa.Column("additional_metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_rx_meta_prescription", "prescription_metadata", ["prescription_id"], schema=SCHEMA)
    op.create_unique_constraint("uq_rx_meta_prescription", "prescription_metadata", ["prescription_id"], schema=SCHEMA)
    _add_updated_at_trigger("prescription_metadata")

    # =========================================================================
    # 10. Uploaded Documents
    # =========================================================================
    op.create_table(
        "uploaded_documents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("prescription_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.prescriptions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("storage_key", sa.String(1000), nullable=False),
        sa.Column("storage_bucket", sa.String(255), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("original_filename_hash", sa.String(64), nullable=True),
        sa.Column("scan_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scan_result_detail", sa.String(500), nullable=True),
        sa.Column("is_quarantined", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("quarantine_reason", sa.String(500), nullable=True),
        sa.Column("pdf_validated", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("pdf_page_count", sa.BigInteger, nullable=True),
        sa.Column("storage_version_id", sa.String(500), nullable=True),
        sa.Column("object_lock_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "scan_status IN ('pending','clean','infected','error','skipped')",
            name="ck_doc_scan_status",
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_doc_tenant_prescription", "uploaded_documents", ["tenant_id", "prescription_id"], schema=SCHEMA)
    op.create_index("ix_doc_checksum", "uploaded_documents", ["checksum_sha256"], schema=SCHEMA)
    _add_updated_at_trigger("uploaded_documents")

    # =========================================================================
    # 11. Signature Verification Results (ALL fields immutable after insert)
    # =========================================================================
    op.create_table(
        "signature_verification_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("prescription_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.prescriptions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("attempt_number", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("idempotency_key", sa.String(100), nullable=False, unique=True),
        sa.Column("qtsp_provider", sa.String(100), nullable=False),
        sa.Column("qtsp_request_id", sa.String(500), nullable=True),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        # Certificate details
        sa.Column("signer_common_name", sa.String(500), nullable=True),
        sa.Column("signer_serial_number", sa.String(200), nullable=True),
        sa.Column("signer_organization", sa.String(500), nullable=True),
        sa.Column("certificate_issuer", sa.String(500), nullable=True),
        sa.Column("certificate_valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("certificate_valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("certificate_is_qualified", sa.Boolean, nullable=True),
        # Timestamp details
        sa.Column("timestamp_status", sa.String(50), nullable=True),
        sa.Column("timestamp_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timestamp_authority", sa.String(500), nullable=True),
        sa.Column("timestamp_is_qualified", sa.Boolean, nullable=True),
        # Trust list
        sa.Column("trust_list_status", sa.String(50), nullable=True),
        sa.Column("trust_list_checked_at", sa.DateTime(timezone=True), nullable=True),
        # Signature integrity
        sa.Column("signature_intact", sa.Boolean, nullable=True),
        sa.Column("signature_algorithm", sa.String(100), nullable=True),
        # Raw QTSP response (stored in S3, referenced here)
        sa.Column("raw_response_storage_key", sa.String(1000), nullable=True),
        sa.Column("raw_response_checksum", sa.String(64), nullable=True,
                  comment="SHA-256 of raw QTSP response for integrity"),
        # Error
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        # Manual review
        sa.Column("requires_manual_review", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("manual_review_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("manual_review_by", UUID(as_uuid=True), nullable=True),
        sa.Column("manual_review_decision", sa.String(50), nullable=True),
        sa.Column("manual_review_notes", sa.Text, nullable=True),
        # Normalized response
        sa.Column("normalized_response", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "verification_status IN ('pending','verified','failed','error','expired','revoked')",
            name="ck_sigver_status",
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_sigver_tenant_rx", "signature_verification_results",
                    ["tenant_id", "prescription_id"], schema=SCHEMA)
    op.create_index("ix_sigver_status", "signature_verification_results",
                    ["tenant_id", "verification_status"], schema=SCHEMA)

    # =========================================================================
    # 12. Evidence Files (ALL fields immutable after insert)
    # =========================================================================
    op.create_table(
        "evidence_files",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("prescription_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.prescriptions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("verification_result_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.signature_verification_results.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("storage_key", sa.String(1000), nullable=False),
        sa.Column("storage_bucket", sa.String(255), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("evidence_type", sa.String(100), nullable=False,
                  comment="validation_report, evidence_record, certificate_chain, timestamp_token"),
        sa.Column("storage_version_id", sa.String(500), nullable=True),
        sa.Column("object_lock_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("certificate_chain_data", JSONB, nullable=True),
        sa.Column("trust_list_provider", sa.String(500), nullable=True),
        sa.Column("trust_list_status", sa.String(50), nullable=True),
        sa.Column("trust_list_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timestamp_details", JSONB, nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_evidence_tenant_rx", "evidence_files",
                    ["tenant_id", "prescription_id"], schema=SCHEMA)
    op.create_index("ix_evidence_tenant_verification", "evidence_files",
                    ["tenant_id", "verification_result_id"], schema=SCHEMA)

    # =========================================================================
    # 13. Pharmacy Events (immutable audit records)
    # =========================================================================
    op.create_table(
        "pharmacy_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("prescription_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.prescriptions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("pharmacy_user_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.pharmacy_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_detail", sa.Text, nullable=True),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "event_type IN ('viewed','downloaded','notes_added','status_updated',"
            "'formulation_registered','returned','flagged','other')",
            name="ck_pharma_evt_type",
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_pharma_evt_tenant_rx", "pharmacy_events",
                    ["tenant_id", "prescription_id"], schema=SCHEMA)
    op.create_index("ix_pharma_evt_tenant_user", "pharmacy_events",
                    ["tenant_id", "pharmacy_user_id"], schema=SCHEMA)

    # =========================================================================
    # 14. Dispensing Events (immutable legal records)
    # =========================================================================
    op.create_table(
        "dispensing_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("prescription_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.prescriptions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("pharmacy_user_id", UUID(as_uuid=True),
                  sa.ForeignKey(f"{SCHEMA}.pharmacy_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("dispensing_status", sa.String(50), nullable=False),
        sa.Column("dispensed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("formulation_registration_number", sa.String(200), nullable=True),
        sa.Column("batch_number", sa.String(200), nullable=True),
        sa.Column("quantity_dispensed", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "dispensing_status IN ('dispensed','partially_dispensed','cancelled','returned')",
            name="ck_disp_status",
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_disp_evt_tenant_rx", "dispensing_events",
                    ["tenant_id", "prescription_id"], schema=SCHEMA)

    # =========================================================================
    # 15. Audit Events — APPEND-ONLY, HASH-CHAINED
    #     No updated_at trigger. No UPDATE/DELETE allowed.
    # =========================================================================
    op.create_table(
        "audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("sequence_number", sa.BigInteger, nullable=False, unique=True),
        sa.Column("previous_hash", sa.String(64), nullable=False),
        sa.Column("current_hash", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("event_category", sa.String(50), nullable=False, server_default="application"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.String(50), nullable=True),
        sa.Column("actor_role", sa.String(50), nullable=True),
        sa.Column("actor_email", sa.String(320), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("object_type", sa.String(100), nullable=True),
        sa.Column("object_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("detail", JSONB, nullable=False, server_default="{}"),
        sa.Column("outcome", sa.String(20), nullable=False, server_default="success"),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(1000), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_sensitive", sa.String(10), nullable=False, server_default=sa.text("'false'")),
        sa.Column("justification", sa.Text, nullable=True),
        sa.Column("state_before", JSONB, nullable=True),
        sa.Column("state_after", JSONB, nullable=True),
        schema=SCHEMA,
    )
    op.create_index("ix_audit_tenant", "audit_events", ["tenant_id"], schema=SCHEMA)
    op.create_index("ix_audit_actor", "audit_events", ["actor_id"], schema=SCHEMA)
    op.create_index("ix_audit_object", "audit_events", ["object_type", "object_id"], schema=SCHEMA)
    op.create_index("ix_audit_event_type", "audit_events", ["event_type"], schema=SCHEMA)
    op.create_index("ix_audit_timestamp", "audit_events", ["event_timestamp"], schema=SCHEMA)
    op.create_index("ix_audit_sequence", "audit_events", ["sequence_number"], unique=True, schema=SCHEMA)
    op.create_index("ix_audit_correlation", "audit_events", ["correlation_id"], schema=SCHEMA)

    # =========================================================================
    # 16. Legal Holds
    # =========================================================================
    op.create_table(
        "legal_holds",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("reference_number", sa.String(200), nullable=True),
        sa.Column("placed_by", UUID(as_uuid=True), nullable=False),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("released_by", UUID(as_uuid=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_reason", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_legal_hold_target", "legal_holds",
                    ["tenant_id", "target_type", "target_id"], schema=SCHEMA)
    op.create_index("ix_legal_hold_active", "legal_holds",
                    ["tenant_id", "is_active"], schema=SCHEMA)
    _add_updated_at_trigger("legal_holds")

    # =========================================================================
    # 17. Retention Schedules
    # =========================================================================
    op.create_table(
        "retention_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("retention_days", sa.Integer, nullable=False,
                  comment="REQUIRES CONFIRMATION BY SPANISH HEALTHCARE / PHARMA COUNSEL"),
        sa.Column("retention_basis", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_legal_default", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("approved_by", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_ret_sched_tenant_resource", "retention_schedules",
                    ["tenant_id", "resource_type"], unique=True, schema=SCHEMA)
    _add_updated_at_trigger("retention_schedules")

    # =========================================================================
    # 18. Deletion Requests
    # =========================================================================
    op.create_table(
        "deletion_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("deletion_type", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("legal_basis", sa.String(500), nullable=True),
        sa.Column("requested_by", UUID(as_uuid=True), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_first_approval"),
        sa.Column("first_approver_id", UUID(as_uuid=True), nullable=True),
        sa.Column("first_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("second_approver_id", UUID(as_uuid=True), nullable=True),
        sa.Column("second_approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("rejected_by", UUID(as_uuid=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("execution_evidence", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "status IN ('pending_first_approval','pending_second_approval',"
            "'approved','rejected','executed','cancelled')",
            name="ck_del_req_status",
        ),
        sa.CheckConstraint(
            "deletion_type IN ('soft','hard','cryptographic_erase')",
            name="ck_del_req_type",
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_del_req_tenant_status", "deletion_requests",
                    ["tenant_id", "status"], schema=SCHEMA)
    op.create_index("ix_del_req_target", "deletion_requests",
                    ["tenant_id", "target_type", "target_id"], schema=SCHEMA)
    _add_updated_at_trigger("deletion_requests")

    # =========================================================================
    # 19. Incidents
    # =========================================================================
    op.create_table(
        "incidents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("incident_type", sa.String(100), nullable=False),
        sa.Column("reported_by", UUID(as_uuid=True), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_to", UUID(as_uuid=True), nullable=True),
        sa.Column("related_object_type", sa.String(100), nullable=True),
        sa.Column("related_object_id", UUID(as_uuid=True), nullable=True),
        sa.Column("related_audit_event_ids", JSONB, nullable=True),
        sa.Column("resolution", sa.Text, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", UUID(as_uuid=True), nullable=True),
        sa.Column("root_cause", sa.Text, nullable=True),
        sa.Column("corrective_actions", sa.Text, nullable=True),
        sa.Column("timeline", JSONB, nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("status IN ('open','investigating','mitigated','resolved','closed')", name="ck_incident_status"),
        sa.CheckConstraint("severity IN ('low','medium','high','critical')", name="ck_incident_severity"),
        schema=SCHEMA,
    )
    op.create_index("ix_incident_tenant_status", "incidents", ["tenant_id", "status"], schema=SCHEMA)
    op.create_index("ix_incident_tenant_severity", "incidents", ["tenant_id", "severity"], schema=SCHEMA)
    _add_updated_at_trigger("incidents")

    # =========================================================================
    # 20. External System References
    # =========================================================================
    op.create_table(
        "external_system_references",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("internal_type", sa.String(100), nullable=False),
        sa.Column("internal_id", UUID(as_uuid=True), nullable=False),
        sa.Column("external_system", sa.String(200), nullable=False),
        sa.Column("external_id", sa.String(500), nullable=False),
        sa.Column("external_url", sa.String(2000), nullable=True),
        sa.Column("is_active", sa.String(10), nullable=False, server_default="true"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_ext_ref_internal", "external_system_references",
                    ["tenant_id", "internal_type", "internal_id"], schema=SCHEMA)
    op.create_index("ix_ext_ref_external", "external_system_references",
                    ["tenant_id", "external_system", "external_id"], schema=SCHEMA)
    _add_updated_at_trigger("external_system_references")

    # =========================================================================
    # 21. Access Reviews
    # =========================================================================
    op.create_table(
        "access_reviews",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_user_type", sa.String(50), nullable=False),
        sa.Column("reviewer_id", UUID(as_uuid=True), nullable=False),
        sa.Column("review_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("access_changes_made", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("decision IN ('approved','revoked','modified','pending')", name="ck_access_review_decision"),
        schema=SCHEMA,
    )
    op.create_index("ix_access_review_tenant_period", "access_reviews",
                    ["tenant_id", "review_period_end"], schema=SCHEMA)
    op.create_index("ix_access_review_target", "access_reviews",
                    ["tenant_id", "target_user_type", "target_user_id"], schema=SCHEMA)
    _add_updated_at_trigger("access_reviews")

    # =========================================================================
    # 22. Break Glass Events (immutable)
    # =========================================================================
    op.create_table(
        "break_glass_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", sa.String(50), nullable=False),
        sa.Column("actor_role", sa.String(50), nullable=False),
        sa.Column("justification", sa.Text, nullable=False),
        sa.Column("target_resource_type", sa.String(100), nullable=True),
        sa.Column("target_resource_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actions_performed", JSONB, nullable=False, server_default="[]"),
        sa.Column("event_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_ip", sa.String(45), nullable=True),
        sa.Column("session_id", UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("reviewed_by", UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_outcome", sa.String(50), nullable=True),
        sa.Column("review_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_break_glass_tenant_actor", "break_glass_events",
                    ["tenant_id", "actor_id"], schema=SCHEMA)
    op.create_index("ix_break_glass_timestamp", "break_glass_events",
                    ["event_timestamp"], schema=SCHEMA)

    # =========================================================================
    # 23. API Credentials Metadata
    # =========================================================================
    op.create_table(
        "api_credentials_metadata",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("key_prefix", sa.String(10), nullable=False),
        sa.Column("key_hash", sa.String(128), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), nullable=False),
        sa.Column("scopes", JSONB, nullable=False, server_default="[]"),
        sa.Column("allowed_ips", JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_ip", sa.String(45), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", UUID(as_uuid=True), nullable=True),
        sa.Column("revocation_reason", sa.String(500), nullable=True),
        sa.Column("rotated_from_id", UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_api_cred_tenant_active", "api_credentials_metadata",
                    ["tenant_id", "is_active"], schema=SCHEMA)
    _add_updated_at_trigger("api_credentials_metadata")

    # =========================================================================
    # 24. Session Records
    # =========================================================================
    op.create_table(
        "session_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("user_type", sa.String(50), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("login_ip", sa.String(45), nullable=False),
        sa.Column("login_user_agent", sa.String(1000), nullable=True),
        sa.Column("login_method", sa.String(50), nullable=False, server_default="oidc"),
        sa.Column("mfa_verified", sa.Boolean, nullable=False, server_default=sa.text("FALSE")),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_reason", sa.String(50), nullable=True),
        sa.Column("device_fingerprint", sa.String(128), nullable=True),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        schema=SCHEMA,
    )
    op.create_index("ix_session_tenant_user", "session_records",
                    ["tenant_id", "user_id"], schema=SCHEMA)
    op.create_index("ix_session_active", "session_records",
                    ["tenant_id", "user_id", "is_active"], schema=SCHEMA)
    op.create_index("ix_session_token_hash", "session_records",
                    ["token_hash"], unique=True, schema=SCHEMA)
    _add_updated_at_trigger("session_records")

    # =========================================================================
    # AUDIT TABLE PROTECTION — Prevent UPDATE and DELETE at DB level
    # =========================================================================
    op.execute(f"""
        CREATE OR REPLACE FUNCTION {SCHEMA}.prevent_audit_modification()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'SECURITY VIOLATION: audit_events is append-only. UPDATE and DELETE are prohibited.';
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute(f"""
        CREATE TRIGGER trg_audit_no_update
        BEFORE UPDATE ON {SCHEMA}.audit_events
        FOR EACH ROW
        EXECUTE FUNCTION {SCHEMA}.prevent_audit_modification();
    """)

    op.execute(f"""
        CREATE TRIGGER trg_audit_no_delete
        BEFORE DELETE ON {SCHEMA}.audit_events
        FOR EACH ROW
        EXECUTE FUNCTION {SCHEMA}.prevent_audit_modification();
    """)

    # Sequence for audit event ordering (monotonically increasing, no gaps allowed)
    op.execute(f"CREATE SEQUENCE IF NOT EXISTS {SCHEMA}.audit_event_seq START WITH 1 INCREMENT BY 1 NO CYCLE;")


def downgrade() -> None:
    op.execute(f"DROP TRIGGER IF EXISTS trg_audit_no_delete ON {SCHEMA}.audit_events;")
    op.execute(f"DROP TRIGGER IF EXISTS trg_audit_no_update ON {SCHEMA}.audit_events;")
    op.execute(f"DROP FUNCTION IF EXISTS {SCHEMA}.prevent_audit_modification();")
    op.execute(f"DROP SEQUENCE IF EXISTS {SCHEMA}.audit_event_seq;")
    op.execute(f"DROP FUNCTION IF EXISTS {SCHEMA}.set_updated_at();")

    tables = [
        "session_records", "api_credentials_metadata", "break_glass_events",
        "access_reviews", "external_system_references", "incidents",
        "deletion_requests", "retention_schedules", "legal_holds",
        "audit_events", "dispensing_events", "pharmacy_events",
        "evidence_files", "signature_verification_results",
        "uploaded_documents", "prescription_metadata", "prescriptions",
        "patients", "auditors", "admin_users", "pharmacy_users",
        "doctors", "clinics", "tenants",
    ]
    for table in tables:
        op.drop_table(table, schema=SCHEMA)

    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")


def _add_updated_at_trigger(table_name: str) -> None:
    """Add auto-updating updated_at trigger to a table."""
    op.execute(f"""
        CREATE TRIGGER trg_{table_name}_updated_at
        BEFORE UPDATE ON {SCHEMA}.{table_name}
        FOR EACH ROW
        EXECUTE FUNCTION {SCHEMA}.set_updated_at();
    """)
