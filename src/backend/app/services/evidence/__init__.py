"""Evidence processor — stores and manages QTSP verification artifacts.

Evidence storage is handled inline by the verification service
(app/services/qtsp/verification_service.py) which stores artifacts
to the evidence bucket and creates EvidenceFile DB records.

This module provides convenience functions for evidence retrieval
and integrity verification.
"""

from app.services.evidence.service import (
    get_evidence_files,
    verify_evidence_integrity,
)

__all__ = [
    "get_evidence_files",
    "verify_evidence_integrity",
]
