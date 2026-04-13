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

interface PendingReview {
  id: string;
  prescription_id: string;
  verification_status: string;
  qtsp_provider: string;
  verified_at: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string | null;
}

export default function VerificationsPage() {
  const [pending, setPending] = useState<PendingReview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewItem, setReviewItem] = useState<PendingReview | null>(null);
  const [decision, setDecision] = useState("accept");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch("admin", "/api/v1/admin/verifications/pending-review");
      if (!res.ok) { setError("Could not load pending reviews."); return; }
      const data = await res.json();
      setPending(Array.isArray(data) ? data : []);
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleSubmitReview() {
    if (!reviewItem) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await apiFetch("admin", `/api/v1/admin/verifications/${reviewItem.id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, notes: notes || undefined }),
      });
      if (res.ok) {
        setPending((prev) => prev.filter((p) => p.id !== reviewItem.id));
        setReviewItem(null);
        setNotes("");
        setDecision("accept");
      } else {
        const err = await res.json();
        setSubmitError(formatApiError(err));
      }
    } catch {
      setSubmitError("Network error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <Card padding="lg">
        <CardHeader
          title="Manual verification review queue"
          description="Signature verifications that require human review before a prescription can be dispensed."
          action={<Button variant="secondary" onClick={load}>Refresh</Button>}
        />

        {error && <div className="qes-alert qes-alert--error" style={{ marginBottom: "1rem" }}>{error}</div>}

        {loading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "2rem" }}><Spinner label="Loading…" /></div>
        ) : pending.length === 0 ? (
          <EmptyState title="No pending reviews" description="All verification results have been reviewed or don't require review." />
        ) : (
          <>
            <div style={{ marginBottom: "0.75rem" }}>
              <Badge tone="warning">{pending.length} pending review{pending.length !== 1 ? "s" : ""}</Badge>
            </div>
            <div className="qes-table-wrap">
              <table className="qes-table">
                <thead>
                  <tr>
                    <th>Verification ID</th>
                    <th>Prescription</th>
                    <th>Status</th>
                    <th>Provider</th>
                    <th>Error</th>
                    <th>Date</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {pending.map((p) => (
                    <tr key={p.id}>
                      <td className="qes-mono" style={{ fontSize: "0.8125rem" }}>{p.id.slice(0, 8)}…</td>
                      <td className="qes-mono" style={{ fontSize: "0.8125rem" }}>{p.prescription_id.slice(0, 8)}…</td>
                      <td><Badge tone={p.verification_status === "failed" ? "danger" : "warning"}>{p.verification_status}</Badge></td>
                      <td style={{ fontSize: "0.875rem" }}>{p.qtsp_provider}</td>
                      <td style={{ fontSize: "0.8125rem", color: "var(--color-neutral-500)" }}>{p.error_code ?? "—"}</td>
                      <td style={{ fontSize: "0.875rem" }}>{p.created_at ? new Date(p.created_at).toLocaleDateString("es-ES") : "—"}</td>
                      <td>
                        <Button variant="primary" onClick={() => { setReviewItem(p); setDecision("accept"); setNotes(""); }} style={{ padding: "0.25rem 0.75rem", fontSize: "0.8125rem" }}>
                          Review
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Card>

      {/* Review modal */}
      <Modal
        open={!!reviewItem}
        title="Manual verification review"
        onClose={() => { if (!submitting) { setReviewItem(null); setSubmitError(null); } }}
        footer={
          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
            <Button variant="ghost" disabled={submitting} onClick={() => setReviewItem(null)}>Cancel</Button>
            <Button
              variant={decision === "reject" ? "danger" : "primary"}
              disabled={submitting}
              onClick={handleSubmitReview}
            >
              {submitting ? "Submitting…" : `Submit — ${decision}`}
            </Button>
          </div>
        }
      >
        {reviewItem && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", padding: "0.75rem 1rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", fontSize: "0.875rem" }}>
              <div><span style={{ color: "var(--color-neutral-500)" }}>Status: </span>{reviewItem.verification_status}</div>
              <div><span style={{ color: "var(--color-neutral-500)" }}>Provider: </span>{reviewItem.qtsp_provider}</div>
              {reviewItem.error_code && <div style={{ gridColumn: "1 / -1" }}><span style={{ color: "var(--color-neutral-500)" }}>Error: </span>{reviewItem.error_code} — {reviewItem.error_message}</div>}
            </div>

            <p style={{ margin: 0, fontSize: "0.9375rem", color: "var(--color-neutral-600)" }}>
              Review this verification result and submit your decision. Your decision and notes are permanently recorded in the audit trail.
            </p>

            <div className="qes-field" style={{ margin: 0 }}>
              <label className="qes-label">Decision</label>
              <select className="qes-input" value={decision} onChange={(e) => setDecision(e.target.value)}>
                <option value="accept">Accept — allow dispensing</option>
                <option value="reject">Reject — block dispensing</option>
                <option value="escalate">Escalate — requires further review</option>
              </select>
            </div>

            <div className="qes-field" style={{ margin: 0 }}>
              <label className="qes-label">Review notes</label>
              <textarea className="qes-input" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Document your reasoning for this decision" />
            </div>

            {submitError && <div className="qes-alert qes-alert--error">{submitError}</div>}
          </div>
        )}
      </Modal>
    </div>
  );
}
