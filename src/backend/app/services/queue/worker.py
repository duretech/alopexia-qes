"""Verification worker — processes verification jobs from the queue.

The worker runs as an async loop:
  1. Dequeue a message
  2. Parse the payload (prescription_id, tenant_id)
  3. Call verify_prescription()
  4. Acknowledge on success, nack on retryable failure
  5. Move to dead-letter after max attempts

In production this would run as a separate process. For local dev,
it can be started alongside the API server.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.logging import get_logger
from app.services.queue.interface import JobMessage, JobStatus, JobResult

logger = get_logger(component="verification_worker")


async def process_verification_job(
    message: JobMessage,
    *,
    db_session_factory: Any,
    qtsp_provider: Any | None = None,
    storage_backend: Any | None = None,
) -> JobResult:
    """Process a single verification job.

    Args:
        message: The job message from the queue.
        db_session_factory: Async session factory for DB access.
        qtsp_provider: Optional QTSP provider override.
        storage_backend: Optional storage backend override.

    Returns:
        JobResult with processing outcome.
    """
    from uuid import UUID
    from app.services.qtsp.verification_service import (
        verify_prescription,
        VerificationServiceError,
    )

    payload = message.payload
    prescription_id = UUID(payload["prescription_id"])
    tenant_id = UUID(payload["tenant_id"])

    logger.info(
        "verification_job_started",
        job_id=message.job_id,
        prescription_id=str(prescription_id),
        attempt=message.attempt,
    )

    try:
        async with db_session_factory() as db:
            try:
                outcome = await verify_prescription(
                    db,
                    prescription_id=prescription_id,
                    tenant_id=tenant_id,
                    qtsp_provider=qtsp_provider,
                    storage_backend=storage_backend,
                )
                await db.commit()

                logger.info(
                    "verification_job_completed",
                    job_id=message.job_id,
                    prescription_id=str(prescription_id),
                    status=outcome.status,
                )

                return JobResult(
                    job_id=message.job_id,
                    status=JobStatus.COMPLETED,
                    result={
                        "verification_id": str(outcome.verification_id),
                        "status": outcome.status,
                        "requires_manual_review": outcome.requires_manual_review,
                    },
                )
            except VerificationServiceError as e:
                await db.rollback()
                if e.retryable and message.attempt < message.max_attempts:
                    logger.warning(
                        "verification_job_retryable",
                        job_id=message.job_id,
                        error=str(e),
                        attempt=message.attempt,
                    )
                    return JobResult(
                        job_id=message.job_id,
                        status=JobStatus.FAILED,
                        error_message=str(e),
                    )
                else:
                    logger.error(
                        "verification_job_failed_permanently",
                        job_id=message.job_id,
                        error=str(e),
                        attempt=message.attempt,
                    )
                    return JobResult(
                        job_id=message.job_id,
                        status=JobStatus.DEAD_LETTER,
                        error_message=str(e),
                    )
            except Exception as e:
                await db.rollback()
                logger.error(
                    "verification_job_unexpected_error",
                    job_id=message.job_id,
                    error=str(e),
                )
                return JobResult(
                    job_id=message.job_id,
                    status=JobStatus.FAILED,
                    error_message=f"Unexpected error: {e}",
                )
    except Exception as e:
        logger.error(
            "verification_job_db_error",
            job_id=message.job_id,
            error=str(e),
        )
        return JobResult(
            job_id=message.job_id,
            status=JobStatus.FAILED,
            error_message=f"DB session error: {e}",
        )


async def run_worker_loop(
    queue: Any,
    *,
    db_session_factory: Any,
    qtsp_provider: Any | None = None,
    storage_backend: Any | None = None,
    poll_interval: float = 1.0,
    shutdown_event: asyncio.Event | None = None,
) -> None:
    """Run the worker loop, polling the queue for verification jobs.

    Args:
        queue: JobQueue implementation.
        db_session_factory: Async session factory.
        qtsp_provider: Optional QTSP provider override.
        storage_backend: Optional storage backend override.
        poll_interval: Seconds between polls when queue is empty.
        shutdown_event: Event to signal graceful shutdown.
    """
    _shutdown = shutdown_event or asyncio.Event()
    logger.info("worker_started")

    while not _shutdown.is_set():
        messages = await queue.dequeue(max_messages=1)

        if not messages:
            try:
                await asyncio.wait_for(_shutdown.wait(), timeout=poll_interval)
                break  # Shutdown requested
            except asyncio.TimeoutError:
                continue

        for msg in messages:
            result = await process_verification_job(
                msg,
                db_session_factory=db_session_factory,
                qtsp_provider=qtsp_provider,
                storage_backend=storage_backend,
            )

            if result.status == JobStatus.COMPLETED:
                await queue.acknowledge(msg.receipt_handle)
            elif result.status == JobStatus.DEAD_LETTER:
                await queue.acknowledge(msg.receipt_handle)
                # TODO: move to dead-letter queue for manual investigation
            else:
                # Retryable failure — nack with backoff
                delay = min(2 ** msg.attempt, 60)
                await queue.nack(msg.receipt_handle, delay_seconds=delay)

    logger.info("worker_stopped")
