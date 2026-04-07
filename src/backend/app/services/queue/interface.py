"""Job queue interface — contract for all queue implementations.

The queue abstraction supports the async verification flow:
  1. Ingestion service enqueues a verification job
  2. Worker picks up the job and runs verification
  3. On failure, the job is retried or moved to dead-letter

Implementations: in-memory (dev/test), SQS-compatible (production).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class JobStatus(StrEnum):
    """Job lifecycle status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


@dataclass(frozen=True)
class JobMessage:
    """A job message on the queue."""
    job_id: str
    job_type: str
    payload: dict[str, Any]
    attempt: int = 1
    max_attempts: int = 3
    created_at: datetime | None = None
    receipt_handle: str | None = None  # For SQS-style acknowledgement


@dataclass
class JobResult:
    """Result of processing a job."""
    job_id: str
    status: JobStatus
    result: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


@runtime_checkable
class JobQueue(Protocol):
    """Protocol for job queue implementations."""

    async def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any],
        *,
        delay_seconds: int = 0,
        deduplication_id: str | None = None,
    ) -> str:
        """Enqueue a job. Returns the job ID."""
        ...

    async def dequeue(
        self,
        *,
        max_messages: int = 1,
        visibility_timeout: int = 30,
    ) -> list[JobMessage]:
        """Dequeue one or more jobs. Returns empty list if none available."""
        ...

    async def acknowledge(self, receipt_handle: str) -> None:
        """Acknowledge successful processing (delete from queue)."""
        ...

    async def nack(self, receipt_handle: str, *, delay_seconds: int = 0) -> None:
        """Negative acknowledge — return job to queue for retry."""
        ...

    async def queue_depth(self) -> int:
        """Return approximate number of pending messages."""
        ...
