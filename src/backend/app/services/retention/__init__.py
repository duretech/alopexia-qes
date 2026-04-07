"""Retention and deletion service — schedules, legal holds, dual-approval deletes.

Implements C-RET-01 through C-RET-06 from the controls catalog.
"""

from app.services.retention.service import (
    get_retention_schedule,
    apply_retention_schedules,
    execute_approved_deletions,
    check_legal_hold,
)

__all__ = [
    "get_retention_schedule",
    "apply_retention_schedules",
    "execute_approved_deletions",
    "check_legal_hold",
]
