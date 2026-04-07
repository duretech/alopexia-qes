"""Tests for the retention service."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.retention.service import (
    check_legal_hold,
    get_retention_schedule,
)


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def mock_db():
    return AsyncMock()


class TestGetRetentionSchedule:
    async def test_returns_schedule_when_found(self, mock_db, tenant_id):
        schedule = MagicMock()
        schedule.retention_days = 1825
        schedule.resource_type = "prescription"

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = schedule
        mock_db.execute.return_value = result_mock

        result = await get_retention_schedule(
            mock_db, tenant_id=tenant_id, resource_type="prescription",
        )
        assert result is not None
        assert result.retention_days == 1825

    async def test_returns_none_when_not_found(self, mock_db, tenant_id):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        result = await get_retention_schedule(
            mock_db, tenant_id=tenant_id, resource_type="prescription",
        )
        assert result is None


class TestCheckLegalHold:
    async def test_returns_true_when_hold_active(self, mock_db, tenant_id):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = uuid.uuid4()
        mock_db.execute.return_value = result_mock

        has_hold = await check_legal_hold(
            mock_db,
            tenant_id=tenant_id,
            target_type="prescription",
            target_id=uuid.uuid4(),
        )
        assert has_hold is True

    async def test_returns_false_when_no_hold(self, mock_db, tenant_id):
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = result_mock

        has_hold = await check_legal_hold(
            mock_db,
            tenant_id=tenant_id,
            target_type="prescription",
            target_id=uuid.uuid4(),
        )
        assert has_hold is False
