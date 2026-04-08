"use client";

import { useEffect, useState } from "react";
import { Badge } from "@qes-ui/components/Badge";
import { Button } from "@qes-ui/components/Button";
import { Card, CardHeader } from "@qes-ui/components/Card";
import { EmptyState } from "@qes-ui/components/EmptyState";
import { Modal } from "@qes-ui/components/Modal";
import { Spinner } from "@qes-ui/components/Spinner";
import { TextField } from "@qes-ui/components/TextField";
import { apiFetch, formatApiError } from "@qes-ui/lib/api";

interface LegalHold {
  id: string;
  target_type: string;
  target_id: string;
  reason: string;
  reference_number: string | null;
  placed_at: string;
  is_active: boolean;
}

export default function LegalHoldsPage() {
  const [holds, setHolds] = useState<LegalHold[]>([]);
  const [loading, setLoading] = useState(true);
  const [targetType, setTargetType] = useState("prescription");
  const [targetId, setTargetId] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [releaseId, setReleaseId] = useState<string | null>(null);
  const [releaseReason, setReleaseReason] = useState("");
  const [busy, setBusy] = useState(false);

  async function fetchHolds() {
    try {
      const res = await apiFetch("admin", "/api/v1/admin/legal-holds?active_only=false");
      if (res.ok) setHolds(await res.json());
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchHolds();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await apiFetch("admin", "/api/v1/admin/legal-holds", {
        method: "POST",
        body: JSON.stringify({
          target_type: targetType,
          target_id: targetId,
          reason,
        }),
      });
      if (res.ok) {
        setTargetId("");
        setReason("");
        fetchHolds();
      } else {
        const err = await res.json();
        setError(formatApiError(err as { detail?: string }));
      }
    } catch {
      setError("Network error");
    } finally {
      setBusy(false);
    }
  }

  async function confirmRelease() {
    if (!releaseId || !releaseReason.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const res = await apiFetch("admin", `/api/v1/admin/legal-holds/${releaseId}/release`, {
        method: "POST",
        body: JSON.stringify({ release_reason: releaseReason }),
      });
      if (res.ok) {
        setReleaseId(null);
        setReleaseReason("");
        fetchHolds();
      } else {
        const err = await res.json();
        setError(formatApiError(err as { detail?: string }));
      }
    } catch {
      setError("Network error");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <Card padding="lg">
        <div style={{ display: "flex", justifyContent: "center", padding: "3rem" }}>
          <Spinner label="Loading legal holds…" />
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card padding="lg">
        <CardHeader title="Legal holds" description="Prevent deletion while an investigation or matter is open." />
        {error && (
          <div className="qes-alert qes-alert--error" role="alert" style={{ marginBottom: "1rem" }}>
            {error}
          </div>
        )}
        <form
          onSubmit={handleCreate}
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
            gap: "1rem",
            alignItems: "end",
            marginBottom: "2rem",
          }}
        >
          <div className="qes-field">
            <label className="qes-label" htmlFor="hold-type">
              Target type
            </label>
            <select
              id="hold-type"
              className="qes-input"
              value={targetType}
              onChange={(e) => setTargetType(e.target.value)}
            >
              <option value="prescription">Prescription</option>
              <option value="patient">Patient</option>
              <option value="audit_event">Audit event</option>
            </select>
          </div>
          <TextField label="Target ID (UUID)" value={targetId} onChange={(e) => setTargetId(e.target.value)} required />
          <TextField label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} required />
          <Button type="submit" variant="primary" disabled={busy}>
            Place hold
          </Button>
        </form>

        {holds.length === 0 ? (
          <EmptyState title="No legal holds" description="Active holds will be listed here." />
        ) : (
          <div className="qes-table-wrap">
            <table className="qes-table">
              <thead>
                <tr>
                  <th>Target</th>
                  <th>Reason</th>
                  <th>Placed</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {holds.map((h) => (
                  <tr key={h.id}>
                    <td className="qes-mono" style={{ fontSize: "0.8125rem" }}>
                      {h.target_type} / {h.target_id.slice(0, 8)}…
                    </td>
                    <td>{h.reason}</td>
                    <td>{new Date(h.placed_at).toLocaleDateString("es-ES")}</td>
                    <td>
                      <Badge tone={h.is_active ? "warning" : "neutral"}>{h.is_active ? "Active" : "Released"}</Badge>
                    </td>
                    <td>
                      {h.is_active && (
                        <Button variant="danger" onClick={() => setReleaseId(h.id)}>
                          Release
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal
        open={!!releaseId}
        title="Release legal hold"
        onClose={() => !busy && setReleaseId(null)}
        footer={
          <>
            <Button variant="secondary" disabled={busy} onClick={() => setReleaseId(null)}>
              Cancel
            </Button>
            <Button variant="primary" disabled={busy || !releaseReason.trim()} onClick={confirmRelease}>
              {busy ? "Releasing…" : "Release hold"}
            </Button>
          </>
        }
      >
        <TextField label="Release reason" value={releaseReason} onChange={(e) => setReleaseReason(e.target.value)} required />
      </Modal>
    </>
  );
}
