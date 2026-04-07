"""Tests for the in-memory job queue."""

import pytest

from app.services.queue.memory_queue import InMemoryQueue


@pytest.fixture
def queue():
    return InMemoryQueue()


class TestInMemoryQueue:
    async def test_enqueue_returns_job_id(self, queue):
        job_id = await queue.enqueue("verification", {"prescription_id": "abc"})
        assert isinstance(job_id, str)
        assert len(job_id) > 0

    async def test_dequeue_returns_message(self, queue):
        await queue.enqueue("verification", {"prescription_id": "abc"})
        messages = await queue.dequeue()
        assert len(messages) == 1
        assert messages[0].job_type == "verification"
        assert messages[0].payload == {"prescription_id": "abc"}
        assert messages[0].attempt == 1

    async def test_dequeue_empty_queue(self, queue):
        messages = await queue.dequeue()
        assert len(messages) == 0

    async def test_fifo_ordering(self, queue):
        await queue.enqueue("type_a", {"order": 1})
        await queue.enqueue("type_b", {"order": 2})
        msgs = await queue.dequeue(max_messages=2)
        assert msgs[0].payload["order"] == 1
        assert msgs[1].payload["order"] == 2

    async def test_acknowledge_removes_from_inflight(self, queue):
        await queue.enqueue("test", {"data": "value"})
        msgs = await queue.dequeue()
        await queue.acknowledge(msgs[0].receipt_handle)
        # Queue should be empty now
        assert await queue.queue_depth() == 0

    async def test_nack_requeues_with_incremented_attempt(self, queue):
        await queue.enqueue("test", {"data": "value"})
        msgs = await queue.dequeue()
        assert msgs[0].attempt == 1
        await queue.nack(msgs[0].receipt_handle)
        # Message should be back in queue
        msgs2 = await queue.dequeue()
        assert len(msgs2) == 1
        assert msgs2[0].attempt == 2
        assert msgs2[0].payload == {"data": "value"}

    async def test_queue_depth(self, queue):
        assert await queue.queue_depth() == 0
        await queue.enqueue("a", {})
        await queue.enqueue("b", {})
        assert await queue.queue_depth() == 2
        await queue.dequeue()
        assert await queue.queue_depth() == 1

    async def test_max_messages_limit(self, queue):
        for i in range(5):
            await queue.enqueue("test", {"i": i})
        msgs = await queue.dequeue(max_messages=3)
        assert len(msgs) == 3
        assert await queue.queue_depth() == 2
