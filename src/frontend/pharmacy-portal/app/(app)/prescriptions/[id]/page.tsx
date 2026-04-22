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

interface PrescriptionDetail {
  id: string;
  status: string;
  verification_status: string | null;
  dispensing_status: string | null;
  doctor_id: string;
  patient_id: string | null;
  clinic_id: string;
  prescribed_date: string | null;
  created_at: string | null;
  external_prescription_id: string | null;
  metadata: {
    medication_name: string | null;
    dosage: string | null;
    treatment_duration: string | null;
    instructions: string | null;
    is_compounded: boolean;
    formulation_registration_number: string | null;
  } | null;
  verification: {
    id: string;
    status: string;
    qtsp_provider: string;
    verified_at: string | null;
    signature_intact: boolean | null;
    certificate: {
      common_name: string | null;
      organization: string | null;
      issuer: string | null;
      valid_from: string | null;
      valid_to: string | null;
      is_qualified: boolean | null;
    } | null;
    timestamp_status: string | null;
    timestamp_is_qualified: boolean | null;
    trust_list_status: string | null;
    requires_manual_review: boolean;
    error_code: string | null;
  } | null;
  evidence_count: number;
  evidence: Array<{
    id: string;
    evidence_type: string;
    mime_type: string;
    file_size_bytes: number;
    created_at: string | null;
  }>;
}

interface PharmacyEvent {
  id: string;
  event_type: string;
  event_detail: string | null;
  pharmacy_user_id: string;
  event_timestamp: string | null;
}

function statusTone(status: string): "success" | "warning" | "danger" | "neutral" {
  if (status === "verified" || status === "available") return "success";
  if (status === "dispensed") return "neutral";
  if (["failed_verification", "cancelled", "revoked"].includes(status)) return "danger";
  return "warning";
}

export default function PharmacyPrescriptionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [rx, setRx] = useState<PrescriptionDetail | null>(null);
  const [events, setEvents] = useState<PharmacyEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dispenseOpen, setDispenseOpen] = useState(false);
  const [dispenseForm, setDispenseForm] = useState({
    dispensing_status: "dispensed",
    formulation_registration_number: "",
    batch_number: "",
    quantity_dispensed: "",
    notes: "",
  });
  const [dispensing, setDispensing] = useState(false);
  const [dispenseError, setDispenseError] = useState<string | null>(null);
  const [noteOpen, setNoteOpen] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [addingNote, setAddingNote] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      try {
        const [rxRes, evRes] = await Promise.all([
          apiFetch("pharmacy", `/api/v1/pharmacy/prescriptions/${id}`),
          apiFetch("pharmacy", `/api/v1/pharmacy/prescriptions/${id}/events`),
        ]);
        if (!rxRes.ok) {
          if (!cancelled) setError("Prescription not found.");
          return;
        }
        const [rxData, evData] = await Promise.all([rxRes.json(), evRes.ok ? evRes.json() : []]);
        if (!cancelled) {
          setRx(rxData as PrescriptionDetail);
          setEvents(Array.isArray(evData) ? evData : []);
        }
      } catch {
        if (!cancelled) setError("Network error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [id]);

  async function handleDownload() {
    try {
      const res = await apiFetch("pharmacy", `/api/v1/pharmacy/prescriptions/${id}/download`);
      if (res.ok) {
        const data = (await res.json()) as { signed_url: string };
        window.open(data.signed_url, "_blank", "noopener,noreferrer");
      } else {
        setError("Failed to generate download URL");
      }
    } catch {
      setError("Network error");
    }
  }

  async function handleViewPdf() {
    setPdfLoading(true);
    try {
      const res = await apiFetch("pharmacy", `/api/v1/pharmacy/prescriptions/${id}/pdf`);
      if (res.ok) {
        const blob = await res.blob();
        setPdfUrl(URL.createObjectURL(blob));
      } else {
        setError("Failed to load PDF");
      }
    } catch {
      setError("Network error loading PDF");
    } finally {
      setPdfLoading(false);
    }
  }

  function handleClosePdf() {
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    setPdfUrl(null);
  }

  async function handleDispense() {
    setDispensing(true);
    setDispenseError(null);
    try {
      const res = await apiFetch("pharmacy", `/api/v1/pharmacy/prescriptions/${id}/dispense`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dispensing_status: dispenseForm.dispensing_status,
          formulation_registration_number: dispenseForm.formulation_registration_number || undefined,
          batch_number: dispenseForm.batch_number || undefined,
          quantity_dispensed: dispenseForm.quantity_dispensed || undefined,
          notes: dispenseForm.notes || undefined,
        }),
      });
      if (res.ok) {
        setRx((prev) => prev ? { ...prev, status: "dispensed", dispensing_status: dispenseForm.dispensing_status } : prev);
        setDispenseOpen(false);
        // Reload events
        const evRes = await apiFetch("pharmacy", `/api/v1/pharmacy/prescriptions/${id}/events`);
        if (evRes.ok) setEvents(await evRes.json());
      } else {
        const err = await res.json();
        setDispenseError(formatApiError(err));
      }
    } catch {
      setDispenseError("Network error");
    } finally {
      setDispensing(false);
    }
  }

  async function handleAddNote() {
    if (!noteText.trim()) return;
    setAddingNote(true);
    try {
      const res = await apiFetch("pharmacy", `/api/v1/pharmacy/prescriptions/${id}/events`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event_type: "notes_added", detail: noteText }),
      });
      if (res.ok) {
        setNoteOpen(false);
        setNoteText("");
        const evRes = await apiFetch("pharmacy", `/api/v1/pharmacy/prescriptions/${id}/events`);
        if (evRes.ok) setEvents(await evRes.json());
      }
    } catch { /* ignore */ }
    finally { setAddingNote(false); }
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

  const canDispense = ["verified", "available"].includes(rx.status);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* Header */}
      <Card padding="lg">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <Button variant="ghost" onClick={() => router.back()} style={{ marginBottom: "0.75rem", padding: "0.25rem 0" }}>
              ← Prescriptions
            </Button>
            <h2 style={{ fontSize: "1.125rem", fontWeight: 600, margin: 0 }}>
              Prescription <span className="qes-mono" style={{ fontSize: "0.875rem", color: "var(--color-neutral-500)" }}>{rx.id}</span>
            </h2>
          </div>
          <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
            <Badge tone={statusTone(rx.status)}>{rx.status.replace(/_/g, " ")}</Badge>
            <Button variant="secondary" onClick={handleViewPdf} disabled={pdfLoading}>
              {pdfLoading ? "Loading…" : "View PDF"}
            </Button>
            {/* <Button variant="secondary" onClick={handleDownload}>Download PDF</Button> */}
            {canDispense && (
              <Button variant="primary" onClick={() => setDispenseOpen(true)}>Confirm dispensing</Button>
            )}
          </div>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.25rem" }}>
        {/* Prescription info */}
        <Card padding="lg">
          <CardHeader title="Prescription details" />
          <dl className="qes-dl">
            <dt>Clinic ID</dt><dd className="qes-mono">{rx.clinic_id ?? "—"}</dd>
            {/* <dt>Doctor ID</dt><dd className="qes-mono">{rx.doctor_id}</dd> */}
            <dt>Prescribed</dt><dd>{rx.prescribed_date ? new Date(rx.prescribed_date).toLocaleDateString("es-ES") : "—"}</dd>
            <dt>Created</dt><dd>{rx.created_at ? new Date(rx.created_at).toLocaleString("es-ES") : "—"}</dd>
            <dt>External ref</dt><dd>{rx.external_prescription_id ?? "—"}</dd>
          </dl>
        </Card>

        {/* Medication */}
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
                <><dt>Formula reg #</dt><dd className="qes-mono">{rx.metadata.formulation_registration_number}</dd></>
              )}
            </dl>
          </Card>
        )}
      </div>

      {/* Verification status */}
      <Card padding="lg">
        <CardHeader title="Verification & evidence status" />
        {!rx.verification ? (
          <div style={{ color: "var(--color-neutral-500)", padding: "0.5rem 0" }}>No verification result available.</div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem" }}>
            {[
              {
                label: "Overall",
                value: <Badge tone={rx.verification.status === "verified" ? "success" : rx.verification.status === "failed" ? "danger" : "warning"}>{rx.verification.status}</Badge>,
              },
              {
                label: "Signature",
                value: <Badge tone={rx.verification.signature_intact === true ? "success" : rx.verification.signature_intact === false ? "danger" : "neutral"}>{rx.verification.signature_intact === true ? "Intact" : rx.verification.signature_intact === false ? "Compromised" : "Unknown"}</Badge>,
              },
              {
                label: "Timestamp",
                value: <Badge tone={rx.verification.timestamp_status === "qualified" || rx.verification.timestamp_status === "valid" ? "success" : rx.verification.timestamp_status === "invalid" ? "danger" : "neutral"}>{rx.verification.timestamp_status ?? "missing"}{rx.verification.timestamp_is_qualified ? " (QTS)" : ""}</Badge>,
              },
              {
                label: "EU Trust List",
                value: <Badge tone={rx.verification.trust_list_status === "trusted" ? "success" : rx.verification.trust_list_status === "untrusted" ? "danger" : "neutral"}>{rx.verification.trust_list_status ?? "unknown"}</Badge>,
              },
            ].map(({ label, value }) => (
              <div key={label} style={{ padding: "1rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-neutral-200)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</div>
                {value}
              </div>
            ))}

            {rx.verification.certificate && (
              <div style={{ gridColumn: "1 / -1", padding: "1rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", border: "1px solid var(--color-neutral-200)" }}>
                <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Signing certificate</div>
                <dl className="qes-dl" style={{ gridTemplateColumns: "repeat(3, max-content 1fr)", columnGap: "2rem" }}>
                  <dt>Signer</dt><dd>{rx.verification.certificate.common_name ?? "—"}</dd>
                  <dt>Organization</dt><dd>{rx.verification.certificate.organization ?? "—"}</dd>
                  <dt>Issuer</dt><dd>{rx.verification.certificate.issuer ?? "—"}</dd>
                  <dt>Valid from</dt><dd>{rx.verification.certificate.valid_from ? new Date(rx.verification.certificate.valid_from).toLocaleDateString("es-ES") : "—"}</dd>
                  <dt>Valid to</dt><dd>{rx.verification.certificate.valid_to ? new Date(rx.verification.certificate.valid_to).toLocaleDateString("es-ES") : "—"}</dd>
                  <dt>Qualified</dt><dd>{rx.verification.certificate.is_qualified ? "Yes (eIDAS)" : rx.verification.certificate.is_qualified === false ? "No" : "Unknown"}</dd>
                </dl>
              </div>
            )}

            {rx.verification.requires_manual_review && (
              <div style={{ gridColumn: "1 / -1" }}>
                <div className="qes-alert qes-alert--warning">This verification requires manual review by a compliance officer before dispensing is approved.</div>
              </div>
            )}
          </div>
        )}

        {rx.evidence.length > 0 && (
          <div style={{ marginTop: "1.5rem" }}>
            <div style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: "0.75rem" }}>
              Evidence artifacts ({rx.evidence_count})
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
              {rx.evidence.map((e) => (
                <div key={e.id} style={{ padding: "0.5rem 0.75rem", background: "var(--color-neutral-100)", borderRadius: "var(--radius-sm)", fontSize: "0.8125rem" }}>
                  <Badge tone="neutral">{e.evidence_type.replace(/_/g, " ")}</Badge>
                  <span style={{ marginLeft: "0.5rem", color: "var(--color-neutral-500)" }}>{(e.file_size_bytes / 1024).toFixed(1)} KB</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Pharmacy events */}
      <Card padding="lg">
        <CardHeader
          title="Pharmacy event log"
          description="All actions recorded against this prescription."
          action={
            <Button variant="secondary" onClick={() => setNoteOpen(true)}>Add note</Button>
          }
        />
        {events.length === 0 ? (
          <div style={{ color: "var(--color-neutral-500)", padding: "0.5rem 0", fontSize: "0.9375rem" }}>No events recorded yet.</div>
        ) : (
          <div className="qes-table-wrap">
            <table className="qes-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Detail</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {events.map((e) => (
                  <tr key={e.id}>
                    <td><Badge tone="neutral">{e.event_type.replace(/_/g, " ")}</Badge></td>
                    <td style={{ fontSize: "0.875rem" }}>{e.event_detail ?? "—"}</td>
                    <td style={{ fontSize: "0.875rem", whiteSpace: "nowrap" }}>
                      {e.event_timestamp ? new Date(e.event_timestamp).toLocaleString("es-ES") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Dispense modal */}
      <Modal
        open={dispenseOpen}
        title="Confirm dispensing"
        onClose={() => { if (!dispensing) { setDispenseOpen(false); setDispenseError(null); } }}
        footer={
          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
            <Button variant="ghost" disabled={dispensing} onClick={() => setDispenseOpen(false)}>Cancel</Button>
            <Button variant="primary" disabled={dispensing} onClick={handleDispense}>
              {dispensing ? "Confirming…" : "Confirm dispense"}
            </Button>
          </div>
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <p style={{ margin: 0, fontSize: "0.9375rem", color: "var(--color-neutral-600)" }}>
            This records an immutable dispensing event. Fill in all relevant details for compounded medicines.
          </p>

          <div className="qes-field">
            <label className="qes-label">Dispensing outcome</label>
            <select
              className="qes-input"
              value={dispenseForm.dispensing_status}
              onChange={(e) => setDispenseForm((f) => ({ ...f, dispensing_status: e.target.value }))}
            >
              <option value="dispensed">Dispensed (full)</option>
              <option value="partially_dispensed">Partially dispensed</option>
              <option value="returned">Returned</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>

          <TextField
            label="Formulation registration number (Reg#)"
            value={dispenseForm.formulation_registration_number}
            onChange={({ target: { value } }: { target: { value: string } }) => setDispenseForm((f) => ({ ...f, formulation_registration_number: value }))}
            placeholder="e.g. FM-2024-00123"
            hint="Required for compounded medicines (formulación magistral)"
          />

          <TextField
            label="Batch / lot number"
            value={dispenseForm.batch_number}
            onChange={({ target: { value } }: { target: { value: string } }) => setDispenseForm((f) => ({ ...f, batch_number: value }))}
            placeholder="e.g. LOT-20240315"
          />

          <TextField
            label="Quantity dispensed"
            value={dispenseForm.quantity_dispensed}
            onChange={({ target: { value } }: { target: { value: string } }) => setDispenseForm((f) => ({ ...f, quantity_dispensed: value }))}
            placeholder="e.g. 30 capsules / 250ml"
          />

          <TextField
            label="Pharmacist notes"
            value={dispenseForm.notes}
            onChange={({ target: { value } }: { target: { value: string } }) => setDispenseForm((f) => ({ ...f, notes: value }))}
            placeholder="Optional notes about dispensing"
          />

          {dispenseError && (
            <div className="qes-alert qes-alert--error">{dispenseError}</div>
          )}
        </div>
      </Modal>

      {/* Add note modal */}
      <Modal
        open={noteOpen}
        title="Add note"
        onClose={() => { setNoteOpen(false); setNoteText(""); }}
        footer={
          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
            <Button variant="ghost" onClick={() => setNoteOpen(false)}>Cancel</Button>
            <Button variant="primary" disabled={addingNote || !noteText.trim()} onClick={handleAddNote}>
              {addingNote ? "Saving…" : "Add note"}
            </Button>
          </div>
        }
      >
        <TextField
          label="Note"
          value={noteText}
          onChange={(e) => setNoteText(e.target.value)}
          placeholder="Enter your note about this prescription"
        />
      </Modal>

      {/* PDF Viewer Modal */}
      {pdfUrl && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 2000 }}
          onClick={handleClosePdf}
        >
          <div
            style={{ width: "90%", height: "90vh", maxWidth: "960px", background: "white", borderRadius: "var(--radius-lg)", display: "flex", flexDirection: "column", overflow: "hidden" }}
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
          >
            <div style={{ padding: "1rem 1.5rem", borderBottom: "1px solid var(--color-neutral-200)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h2 style={{ margin: 0, fontSize: "1rem", fontWeight: 600 }}>Prescription PDF</h2>
                <p style={{ margin: "0.25rem 0 0", fontSize: "0.875rem", color: "var(--color-neutral-500)" }}>
                  {rx.id}
                </p>
              </div>
              <Button variant="ghost" onClick={handleClosePdf} style={{ padding: "0.5rem" }}>✕</Button>
            </div>
            <div style={{ flex: 1, overflow: "hidden", background: "var(--color-neutral-100)" }}>
              <iframe src={pdfUrl} style={{ width: "100%", height: "100%", border: "none" }} title="Prescription PDF" />
            </div>
            <div style={{ padding: "1rem 1.5rem", borderTop: "1px solid var(--color-neutral-200)", background: "var(--color-neutral-50)", display: "flex", justifyContent: "flex-end", gap: "0.75rem" }}>
              <Button variant="secondary" onClick={handleDownload}>Download</Button>
              <Button variant="ghost" onClick={handleClosePdf}>Close</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
