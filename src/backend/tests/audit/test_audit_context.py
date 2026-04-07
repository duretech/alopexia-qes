"""Tests for the AuditContext middleware helper."""

import uuid
from datetime import datetime, timezone

from app.middleware.audit_emission import AuditContext, get_audit_context


class TestAuditContext:
    def test_default_values(self):
        ctx = AuditContext()
        assert ctx.request_id == ""
        assert ctx.correlation_id == ""
        assert ctx.actor_id is None
        assert ctx.tenant_id is None

    def test_to_dict_includes_all_fields(self):
        ctx = AuditContext(
            request_id="req-123",
            correlation_id="cor-456",
            source_ip="10.0.0.1",
            user_agent="TestAgent/1.0",
            actor_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            actor_type="doctor",
            actor_role="doctor",
            tenant_id="11111111-2222-3333-4444-555555555555",
        )
        d = ctx.to_dict()
        assert d["request_id"] == "req-123"
        assert d["source_ip"] == "10.0.0.1"
        assert d["actor_type"] == "doctor"
        assert "timestamp" in d

    def test_as_emit_kwargs_minimal(self):
        """With no actor info, emit kwargs should have only request context."""
        ctx = AuditContext(
            request_id="req-1",
            correlation_id="cor-1",
            source_ip="127.0.0.1",
        )
        kwargs = ctx.as_emit_kwargs()
        assert kwargs["source_ip"] == "127.0.0.1"
        assert kwargs["request_id"] == "req-1"
        assert kwargs["correlation_id"] == "cor-1"
        assert "actor_id" not in kwargs
        assert "tenant_id" not in kwargs

    def test_as_emit_kwargs_with_actor(self):
        """Actor fields should be converted to UUID when present."""
        uid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        tid = "11111111-2222-3333-4444-555555555555"
        ctx = AuditContext(
            request_id="req-1",
            correlation_id="cor-1",
            source_ip="10.0.0.1",
            actor_id=uid,
            actor_type="doctor",
            actor_role="doctor",
            tenant_id=tid,
        )
        kwargs = ctx.as_emit_kwargs()
        assert kwargs["actor_id"] == uuid.UUID(uid)
        assert kwargs["actor_type"] == "doctor"
        assert kwargs["tenant_id"] == uuid.UUID(tid)

    def test_frozen_immutability(self):
        """AuditContext should be frozen (immutable)."""
        ctx = AuditContext(request_id="req-1")
        try:
            ctx.request_id = "modified"  # type: ignore
            assert False, "Should have raised FrozenInstanceError"
        except AttributeError:
            pass  # Expected


class TestGetAuditContext:
    def test_returns_empty_context_when_missing(self):
        """Should return an empty AuditContext when request.state has none."""

        class FakeRequest:
            class state:
                pass

        ctx = get_audit_context(FakeRequest())
        assert ctx.request_id == ""
        assert ctx.actor_id is None
