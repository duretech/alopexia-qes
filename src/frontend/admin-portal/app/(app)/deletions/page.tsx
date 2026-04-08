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

interface DeletionRequestRow {
  id: string;
  target_type: string;
  target_id: string;
  deletion_type: string;
  reason: string;
  status: string;
  requested_by: string;
  requested_at: string;
}

export default function DeletionsPage() {
  const [rows, setRows] = useState<DeletionRequestRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [targetType, setTargetType] = useState("prescription");
  const [targetId, setTargetId] = useState("");
  const [deletionType, setDeletionType] = useState("soft");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [approveId, setApproveId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const res = await apiFetch("admin", "/api/v1/admin/deletion-requests");
      if (res.ok) {
        const data = await res.json();
        setRows(Array.isArray(data) ? data : []);
      } else {
        setError("Could not load deletion requests.");
      }
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createRequest(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await apiFetch("admin", "/api/v1/admin/deletion-requests", {
        method: "POST",
        body: JSON.stringify({
          target_type: targetType,
          target_id: targetId,
          deletion_type: deletionType,
          reason,
        }),
      });
      if (res.ok) {
        setTargetId("");
        setReason("");
        load();
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

  async function submitDecision(decision: "approve" | "reject") {
    if (!approveId) return;
    setBusy(true);
    setError(null);
    try {
      const res = await apiFetch("admin", `/api/v1/admin/deletion-requests/${approveId}/approve`, {
        method: "POST",
        body: JSON.stringify({ decision }),
      });
      if (res.ok) {
        setApproveId(null);
        load();
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
          <Spinner label="Loading requests…" />
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card padding="lg">
        <CardHeader
          title="Deletion requests"
          description="Hard deletes require two distinct approvers. You cannot approve your own request."
        />
        {error && (
          <div className="qes-alert qes-alert--error" role="alert" style={{ marginBottom: "1rem" }}>
            {error}
          </div>
        )}
        <form
          onSubmit={createRequest}
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
            gap: "1rem",
            alignItems: "end",
            marginBottom: "2rem",
          }}
        >
          <div className="qes-field">
            <label className="qes-label" htmlFor="del-type">
              Target type
            </label>
            <select
              id="del-type"
              className="qes-input"
              value={targetType}
              onChange={(e) => setTargetType(e.target.value)}
            >
              <option value="prescription">Prescription</option>
              <option value="patient">Patient</option>
            </select>
          </div>
          <TextField label="Target ID" value={targetId} onChange={(e) => setTargetId(e.target.value)} required />
          <div className="qes-field">
            <label className="qes-label" htmlFor="del-mode">
              Deletion type
            </label>
            <select
              id="del-mode"
              className="qes-input"
              value={deletionType}
              onChange={(e) => setDeletionType(e.target.value)}
            >
              <option value="soft">Soft</option>
              <option value="hard">Hard</option>
              <option value="cryptographic_erase">Cryptographic erase</option>
            </select>
          </div>
          <TextField label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} required />
          <Button type="submit" variant="primary" disabled={busy}>
            Submit request
          </Button>
        </form>

        {rows.length === 0 ? (
          <EmptyState title="No deletion requests" description="Submitted requests will appear in this table." />
        ) : (
          <div className="qes-table-wrap">
            <table className="qes-table">
              <thead>
                <tr>
                  <th>Target</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Requested</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td className="qes-mono" style={{ fontSize: "0.8125rem" }}>
                      {r.target_type} / {r.target_id.slice(0, 8)}…
                    </td>
                    <td>{r.deletion_type}</td>
                    <td>
                      <Badge tone="neutral">{r.status.replace(/_/g, " ")}</Badge>
                    </td>
                    <td>{new Date(r.requested_at).toLocaleString("es-ES")}</td>
                    <td>
                      {(r.status === "pending_first_approval" || r.status === "pending_second_approval") && (
                        <Button variant="secondary" onClick={() => setApproveId(r.id)}>
                          Review
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
        open={!!approveId}
        title="Approve or reject"
        onClose={() => !busy && setApproveId(null)}
        footer={
          <>
            <Button variant="secondary" disabled={busy} onClick={() => setApproveId(null)}>
              Cancel
            </Button>
            <Button variant="danger" disabled={busy} onClick={() => submitDecision("reject")}>
              Reject
            </Button>
            <Button variant="primary" disabled={busy} onClick={() => submitDecision("approve")}>
              Approve
            </Button>
          </>
        }
      >
        <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--neutral-600)" }}>
          Approving advances the workflow. For hard deletes, a second approver is required after the first approval.
        </p>
      </Modal>
    </>
  );
}
