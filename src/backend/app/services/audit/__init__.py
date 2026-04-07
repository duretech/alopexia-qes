"""Immutable audit service — hash-chained, append-only event log.

Public API:
    emit_audit_event()  — Emit a new audit event (hash-chained, sequenced)
    verify_chain_integrity() — Verify the hash chain (detective control)
    detect_gaps()       — Detect sequence number gaps (detective control)
    export_events()     — Export events as JSON Lines for auditors

Types:
    AuditEventType      — Enum of all valid event types
    AuditCategory       — Event category enum
    AuditSeverity       — Event severity enum
    AuditOutcome        — Action outcome enum

Imports are lazy to avoid pulling in ORM models (and their full dependency
chain) when only the pure-function modules (hash_chain, event_types) are
needed — e.g., in unit tests or external verification scripts.
"""

from app.services.audit.event_types import (
    AuditEventType,
    AuditCategory,
    AuditSeverity,
    AuditOutcome,
)
from app.services.audit.hash_chain import GENESIS_HASH, compute_event_hash


def __getattr__(name: str):
    """Lazy import for modules that depend on ORM / database."""
    if name == "emit_audit_event":
        from app.services.audit.service import emit_audit_event
        return emit_audit_event
    if name == "verify_chain_integrity":
        from app.services.audit.verification import verify_chain_integrity
        return verify_chain_integrity
    if name == "detect_gaps":
        from app.services.audit.verification import detect_gaps
        return detect_gaps
    if name == "ChainVerificationResult":
        from app.services.audit.verification import ChainVerificationResult
        return ChainVerificationResult
    if name == "GapDetectionResult":
        from app.services.audit.verification import GapDetectionResult
        return GapDetectionResult
    if name == "export_events":
        from app.services.audit.export import export_events
        return export_events
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Core operations (lazy)
    "emit_audit_event",
    "verify_chain_integrity",
    "detect_gaps",
    "export_events",
    # Types (eager — no heavy deps)
    "AuditEventType",
    "AuditCategory",
    "AuditSeverity",
    "AuditOutcome",
    # Hash chain (eager — pure functions)
    "GENESIS_HASH",
    "compute_event_hash",
    # Result types (lazy)
    "ChainVerificationResult",
    "GapDetectionResult",
]
