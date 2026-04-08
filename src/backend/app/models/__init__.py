"""SQLAlchemy ORM models — all tables imported here for Alembic discovery."""

from app.models.tenant import Tenant, Clinic
from app.models.users import Doctor, PharmacyUser, AdminUser, Auditor
from app.models.patient import Patient
from app.models.prescription import Prescription, PrescriptionMetadata
from app.models.document import UploadedDocument
from app.models.verification import SignatureVerificationResult
from app.models.evidence import EvidenceFile
from app.models.pharmacy import PharmacyEvent, DispensingEvent
from app.models.audit import AuditEvent
from app.models.retention import LegalHold, RetentionSchedule, DeletionRequest
from app.models.incident import Incident
from app.models.reference import ExternalSystemReference
from app.models.access_review import AccessReview
from app.models.break_glass import BreakGlassEvent
from app.models.api_credential import ApiCredentialMetadata
from app.models.session import SessionRecord
from app.models.mfa_totp import TotpCredential

__all__ = [
    "Tenant", "Clinic",
    "Doctor", "PharmacyUser", "AdminUser", "Auditor",
    "Patient",
    "Prescription", "PrescriptionMetadata",
    "UploadedDocument",
    "SignatureVerificationResult",
    "EvidenceFile",
    "PharmacyEvent", "DispensingEvent",
    "AuditEvent",
    "LegalHold", "RetentionSchedule", "DeletionRequest",
    "Incident",
    "ExternalSystemReference",
    "AccessReview",
    "BreakGlassEvent",
    "ApiCredentialMetadata",
    "SessionRecord",
    "TotpCredential",
]
