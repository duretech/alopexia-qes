"""Job queue abstraction — async job dispatch and processing.

Public API:
    JobQueue       — Protocol for queue implementations
    JobMessage     — Queue message structure
    InMemoryQueue  — Dev/test queue implementation
    enqueue_verification_job() — Convenience for verification dispatch
"""

from app.services.queue.interface import (
    JobQueue,
    JobMessage,
    JobStatus,
    JobResult,
)
from app.services.queue.memory_queue import InMemoryQueue


# Module-level queue instance (initialized on first use)
_queue_instance: InMemoryQueue | None = None


def get_queue() -> InMemoryQueue:
    """Get or create the queue instance."""
    global _queue_instance
    if _queue_instance is None:
        _queue_instance = InMemoryQueue()
    return _queue_instance


async def enqueue_verification_job(
    prescription_id: str,
    tenant_id: str,
) -> str:
    """Convenience function to enqueue a verification job."""
    queue = get_queue()
    return await queue.enqueue(
        "verification",
        {
            "prescription_id": prescription_id,
            "tenant_id": tenant_id,
        },
        deduplication_id=f"verify-{prescription_id}",
    )


__all__ = [
    "JobQueue",
    "JobMessage",
    "JobStatus",
    "JobResult",
    "InMemoryQueue",
    "get_queue",
    "enqueue_verification_job",
]
