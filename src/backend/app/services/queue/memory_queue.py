"""In-memory job queue for development and testing.

Uses asyncio.Queue under the hood. Jobs are lost on process restart,
which is acceptable for local dev. In production, use SQS.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.services.queue.interface import JobMessage

logger = get_logger(component="memory_queue")


class InMemoryQueue:
    """In-memory job queue backed by asyncio primitives."""

    def __init__(self):
        self._pending: deque[JobMessage] = deque()
        self._in_flight: dict[str, JobMessage] = {}
        self._lock = asyncio.Lock()

    async def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any],
        *,
        delay_seconds: int = 0,
        deduplication_id: str | None = None,
    ) -> str:
        job_id = uuid.uuid4().hex
        message = JobMessage(
            job_id=job_id,
            job_type=job_type,
            payload=payload,
            attempt=1,
            max_attempts=3,
            created_at=datetime.now(timezone.utc),
            receipt_handle=uuid.uuid4().hex,
        )
        async with self._lock:
            self._pending.append(message)
        logger.info("job_enqueued", job_id=job_id, job_type=job_type)
        return job_id

    async def dequeue(
        self,
        *,
        max_messages: int = 1,
        visibility_timeout: int = 30,
    ) -> list[JobMessage]:
        messages: list[JobMessage] = []
        async with self._lock:
            for _ in range(min(max_messages, len(self._pending))):
                msg = self._pending.popleft()
                self._in_flight[msg.receipt_handle] = msg
                messages.append(msg)
        return messages

    async def acknowledge(self, receipt_handle: str) -> None:
        async with self._lock:
            msg = self._in_flight.pop(receipt_handle, None)
            if msg:
                logger.debug("job_acknowledged", job_id=msg.job_id)

    async def nack(self, receipt_handle: str, *, delay_seconds: int = 0) -> None:
        async with self._lock:
            msg = self._in_flight.pop(receipt_handle, None)
            if msg:
                # Re-enqueue with incremented attempt
                retry_msg = JobMessage(
                    job_id=msg.job_id,
                    job_type=msg.job_type,
                    payload=msg.payload,
                    attempt=msg.attempt + 1,
                    max_attempts=msg.max_attempts,
                    created_at=msg.created_at,
                    receipt_handle=uuid.uuid4().hex,
                )
                self._pending.append(retry_msg)
                logger.info(
                    "job_requeued",
                    job_id=msg.job_id,
                    attempt=retry_msg.attempt,
                )

    async def queue_depth(self) -> int:
        return len(self._pending)
