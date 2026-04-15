"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Badge } from "@qes-ui/components/Badge";
import { Button } from "@qes-ui/components/Button";
import { Card, CardHeader } from "@qes-ui/components/Card";
import { Modal } from "@qes-ui/components/Modal";
import { Spinner } from "@qes-ui/components/Spinner";
import { TextField } from "@qes-ui/components/TextField";
import { apiFetch, formatApiError } from "@qes-ui/lib/api";

interface VerificationResult {
  id: string;
  status: string;
  qtsp_provider: string;
  qtsp_request_id: string | null;
  verified_at: string | null;
  signature_intact: boolean | null;
  signature_algorithm: string | null;
  certificate: {
    common_name: string | null;
    serial_number: string | null;
    organization: string | null;
    issuer: string | null;
    valid_from: string | null;
    valid_to: string | null;
    is_qualified: boolean | null;
  } | null;
  timestamp: {
    status: string | null;
    time: string | null;
    authority: string | null;
    is_qualified: boolean | null;
  } | null;
  trust_list_status: string | null;
  requires_manual_review: boolean;
  manual_review_decision: string | null;
  error_code: string | null;
  error_message: string | null;
}

interface PrescriptionDetail {
  id: string;
  status: string;
  verification_status: string | null;
  dispensing_status: string | null;
  doctor_id: string;
  patient_id: string;
  clinic_id: string;
  upload_checksum: string;
  prescribed_date: string | null;
  created_at: string | null;
  external_prescription_id: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  is_under_legal_hold: boolean;
  metadata: {
    medication_name: string | null;
    dosage: string | null;
    treatment_duration: string | null;
    instructions: string | null;
    is_compounded: boolean;
    formulation_registration_number: string | null;
  } | null;
  verification: VerificationResult | null;
  evidence: Array<{
    id: string;
    evidence_type: string;
    mime_type: string;
    file_size_bytes: number;
    created_at: string | null;
  }>;
}

function statusTone(status: string): "success" | "warning" | "danger" | "neutral" {
  if (status === "verified" || status === "available") return "success";
  if (["failed_verification", "revoked", "cancelled", "failed"].includes(status)) return "danger";
  if (["pending_verification", "manual_review", "indeterminate"].includes(status)) return "warning";
  return "neutral";
}

function verTone(status: string | null): "success" | "warning" | "danger" | "neutral" {
  if (!status) return "neutral";
  if (status === "verified") return "success";
  if (["failed", "revoked", "expired"].includes(status)) return "danger";
  if (["indeterminate", "error", "pending"].includes(status)) return "warning";
  return "neutral";
}

export default function PrescriptionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [rx, setRx] = useState<PrescriptionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch("doctor", `/api/v1/prescriptions/${id}`);
        if (!res.ok) {
          if (!cancelled) setError("Prescription not found.");
          return;
        }
        const data = (await res.json()) as PrescriptionDetail;
        if (!cancelled) setRx(data);
      } catch {
        if (!cancelled) setError("Network error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [id]);

  async function handleCancel() {
    if (!cancelReason.trim()) {
      setCancelError("Please provide a cancellation reason.");
      return;
    }
    setCancelling(true);
    setCancelError(null);
    try {
      const res = await apiFetch("doctor", `/api/v1/prescriptions/${id}/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: cancelReason }),
      });
      if (res.ok) {
        const data = await res.json();
        setRx((prev) => prev ? { ...prev, status: data.status, cancelled_at: data.cancelled_at, cancellation_reason: data.reason } : prev);
        setCancelOpen(false);
        setCancelReason("");
      } else {
        const err = await res.json();
        setCancelError(formatApiError(err));
      }
    } catch {
      setCancelError("Network error");
    } finally {
      setCancelling(false);
    }
  }

  if (loading) {
    return (
      <Card padding="lg">
        <div style={{ display: "flex", justifyContent: "center", padding: "3rem" }}>
          <Spinner label="Loading prescription…" />
        </div>
      </Card>
    );
  }

  if (error || !rx) {
    return (
      <Card padding="lg">
        <div className="qes-alert qes-alert--error">{error ?? "Not found"}</div>
        <Button variant="ghost" onClick={() => router.back()} style={{ marginTop: "1rem" }}>← Back</Button>
      </Card>
    );
  }

  const canCancel = !["dispensed", "cancelled", "revoked"].includes(rx.status) && !rx.is_under_legal_hold;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* Header */}
      <Card padding="lg">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <Button variant="ghost" onClick={() => router.back()} style={{ marginBottom: "0.75rem", padding: "0.25rem 0" }}>
              ← My prescriptions
            </Button>
            <h2 style={{ fontSize: "1.125rem", fontWeight: 600, margin: 0 }}>
              Prescription <span className="qes-mono" style={{ fontSize: "0.875rem", color: "var(--color-neutral-500)" }}>{rx.id}</span>
            </h2>
          </div>
          <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
            <Badge tone={statusTone(rx.status)}>{rx.status.replace(/_/g, " ")}</Badge>
            {canCancel && (
              <Button variant="danger" onClick={() => setCancelOpen(true)}>
                Cancel / Revoke
              </Button>
            )}
          </div>
        </div>

        {rx.is_under_legal_hold && (
          <div className="qes-alert qes-alert--warning" style={{ marginTop: "1rem" }}>
            ⚠ This prescription is under a legal hold and cannot be cancelled or deleted.
          </div>
        )}
        {rx.cancelled_at && (
          <div className="qes-alert qes-alert--error" style={{ marginTop: "1rem" }}>
            Cancelled on {new Date(rx.cancelled_at).toLocaleString("es-ES")}. Reason: {rx.cancellation_reason}
          </div>
        )}
      </Card>

      {/* Details grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
        <Card padding="lg">
          <CardHeader title="Prescription details" />
          <dl className="qes-dl">
            <dt>Clinic ID</dt><dd className="qes-mono">{rx.patient_id}</dd>
            <dt>Doctor ID</dt><dd className="qes-mono">{rx.doctor_id}</dd>
            <dt>Prescribed date</dt><dd>{rx.prescribed_date ? new Date(rx.prescribed_date).toLocaleDateString("es-ES") : "—"}</dd>
            <dt>Created</dt><dd>{rx.created_at ? new Date(rx.created_at).toLocaleString("es-ES") : "—"}</dd>
            <dt>External ref</dt><dd>{rx.external_prescription_id ?? "—"}</dd>
            <dt>Checksum</dt><dd className="qes-mono" style={{ fontSize: "0.75rem" }}>{rx.upload_checksum.slice(0, 32)}…</dd>
          </dl>
        </Card>

        {rx.metadata && (
          <Card padding="lg">
            <CardHeader title="Medication" />
            <dl className="qes-dl">
              <dt>Medication</dt><dd>{rx.metadata.medication_name ?? "—"}</dd>
              <dt>Dosage</dt><dd>{rx.metadata.dosage ?? "—"}</dd>
              <dt>Duration</dt><dd>{rx.metadata.treatment_duration ?? "—"}</dd>
              <dt>Instructions</dt><dd>{rx.metadata.instructions ?? "—"}</dd>
              <dt>Compounded</dt><dd>{rx.metadata.is_compounded ? "Yes (formulación magistral)" : "No"}</dd>
              {rx.metadata.formulation_registration_number && (
                <><dt>Reg #</dt><dd className="qes-mono">{rx.metadata.formulation_registration_number}</dd></>
              )}
            </dl>
          </Card>
        )}
      </div>

      {/* Verification result */}
      <Card padding="lg">
        <CardHeader
          title="Signature verification"
          description="Result from the Qualified Trust Service Provider (QTSP)."
        />
        {!rx.verification ? (
          <div style={{ color: "var(--color-neutral-500)", padding: "1rem 0" }}>
            No verification result yet. Verification runs asynchronously after upload.
          </div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1.25rem" }}>
            {/* Overall status */}
            <div style={{ padding: "1rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-neutral-200)" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Verification status</div>
              <Badge tone={verTone(rx.verification.status)}>{rx.verification.status.replace(/_/g, " ")}</Badge>
              {rx.verification.verified_at && (
                <div style={{ fontSize: "0.8125rem", marginTop: "0.5rem", color: "var(--color-neutral-600)" }}>
                  {new Date(rx.verification.verified_at).toLocaleString("es-ES")}
                </div>
              )}
              <div style={{ fontSize: "0.8125rem", marginTop: "0.25rem", color: "var(--color-neutral-500)" }}>
                Provider: {rx.verification.qtsp_provider}
              </div>
            </div>

            {/* Signature */}
            <div style={{ padding: "1rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-neutral-200)" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Signature integrity</div>
              {rx.verification.signature_intact === null ? (
                <span style={{ color: "var(--color-neutral-400)" }}>Unknown</span>
              ) : (
                <Badge tone={rx.verification.signature_intact ? "success" : "danger"}>
                  {rx.verification.signature_intact ? "Intact" : "Compromised"}
                </Badge>
              )}
              {rx.verification.signature_algorithm && (
                <div style={{ fontSize: "0.8125rem", marginTop: "0.5rem", color: "var(--color-neutral-600)", fontFamily: "var(--font-mono)" }}>
                  {rx.verification.signature_algorithm}
                </div>
              )}
            </div>

            {/* Trust list */}
            <div style={{ padding: "1rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-neutral-200)" }}>
              <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>EU Trust List</div>
              <Badge tone={rx.verification.trust_list_status === "trusted" ? "success" : rx.verification.trust_list_status === "untrusted" ? "danger" : "neutral"}>
                {rx.verification.trust_list_status ?? "Unknown"}
              </Badge>
              {rx.verification.requires_manual_review && (
                <div style={{ marginTop: "0.5rem" }}>
                  <Badge tone="warning">Manual review required</Badge>
                  {rx.verification.manual_review_decision && (
                    <div style={{ fontSize: "0.8125rem", marginTop: "0.25rem" }}>
                      Decision: {rx.verification.manual_review_decision}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Certificate */}
            {rx.verification.certificate && (
              <div style={{ gridColumn: "1 / -1", padding: "1rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-neutral-200)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginBottom: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  Signing certificate
                  {rx.verification.certificate.is_qualified && (
                    <Badge tone="success">Qualified eIDAS</Badge>
                  )}
                </div>
                <dl className="qes-dl" style={{ gridTemplateColumns: "repeat(3, max-content 1fr)", columnGap: "2rem" }}>
                  <dt>Common name</dt><dd>{rx.verification.certificate.common_name ?? "—"}</dd>
                  <dt>Organization</dt><dd>{rx.verification.certificate.organization ?? "—"}</dd>
                  <dt>Issuer</dt><dd>{rx.verification.certificate.issuer ?? "—"}</dd>
                  <dt>Serial</dt><dd className="qes-mono">{rx.verification.certificate.serial_number ?? "—"}</dd>
                  <dt>Valid from</dt><dd>{rx.verification.certificate.valid_from ? new Date(rx.verification.certificate.valid_from).toLocaleDateString("es-ES") : "—"}</dd>
                  <dt>Valid to</dt><dd>{rx.verification.certificate.valid_to ? new Date(rx.verification.certificate.valid_to).toLocaleDateString("es-ES") : "—"}</dd>
                </dl>
              </div>
            )}

            {/* Timestamp */}
            {rx.verification.timestamp && (
              <div style={{ gridColumn: "1 / span 2", padding: "1rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-neutral-200)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Timestamp</div>
                <dl className="qes-dl">
                  <dt>Status</dt>
                  <dd>
                    <Badge tone={rx.verification.timestamp.status === "qualified" || rx.verification.timestamp.status === "valid" ? "success" : rx.verification.timestamp.status === "invalid" ? "danger" : "neutral"}>
                      {rx.verification.timestamp.status ?? "missing"}
                    </Badge>
                    {rx.verification.timestamp.is_qualified && <span style={{ marginLeft: "0.5rem" }}><Badge tone="success">Qualified</Badge></span>}
                  </dd>
                  <dt>Time</dt><dd>{rx.verification.timestamp.time ? new Date(rx.verification.timestamp.time).toLocaleString("es-ES") : "—"}</dd>
                  <dt>Authority</dt><dd>{rx.verification.timestamp.authority ?? "—"}</dd>
                </dl>
              </div>
            )}

            {/* Error */}
            {rx.verification.error_code && (
              <div style={{ gridColumn: "1 / -1" }}>
                <div className="qes-alert qes-alert--error">
                  Error: {rx.verification.error_code} — {rx.verification.error_message}
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Evidence */}
      {rx.evidence.length > 0 && (
        <Card padding="lg">
          <CardHeader title="Evidence files" description="Raw QTSP evidence artifacts stored for audit." />
          <div className="qes-table-wrap">
            <table className="qes-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>MIME</th>
                  <th>Size</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {rx.evidence.map((e) => (
                  <tr key={e.id}>
                    <td><Badge tone="neutral">{e.evidence_type.replace(/_/g, " ")}</Badge></td>
                    <td className="qes-mono" style={{ fontSize: "0.8125rem" }}>{e.mime_type}</td>
                    <td>{(e.file_size_bytes / 1024).toFixed(1)} KB</td>
                    <td>{e.created_at ? new Date(e.created_at).toLocaleString("es-ES") : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Cancel modal */}
      <Modal
        open={cancelOpen}
        onClose={() => { setCancelOpen(false); setCancelReason(""); setCancelError(null); }}
        title={rx.status === "verified" ? "Revoke prescription" : "Cancel prescription"}
        footer={
          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
            <Button variant="ghost" onClick={() => setCancelOpen(false)}>Keep prescription</Button>
            <Button variant="danger" onClick={handleCancel} disabled={cancelling}>
              {cancelling ? "Cancelling…" : rx.status === "verified" ? "Revoke" : "Cancel"}
            </Button>
          </div>
        }
      >
        <p style={{ marginBottom: "1rem", color: "var(--color-neutral-600)", fontSize: "0.9375rem" }}>
          {rx.status === "verified"
            ? "This prescription has been verified. Revoking it will prevent it from being dispensed."
            : "Cancelling this prescription will prevent verification and dispensing."}
          {" "}This action is recorded in the audit trail and cannot be undone.
        </p>
        <TextField
          label="Reason"
          value={cancelReason}
          onChange={(e: any) => setCancelReason(e.target.value)}
          placeholder="Mandatory — explain why this prescription is being cancelled"
          required
        />
        {cancelError && (
          <div className="qes-alert qes-alert--error" style={{ marginTop: "1rem" }}>{cancelError}</div>
        )}
      </Modal>
    </div>
  );
}
