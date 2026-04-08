"use client";

import { useEffect, useState } from "react";
import { Badge } from "@qes-ui/components/Badge";
import { Button } from "@qes-ui/components/Button";
import { Card, CardHeader } from "@qes-ui/components/Card";
import { EmptyState } from "@qes-ui/components/EmptyState";
import { Modal } from "@qes-ui/components/Modal";
import { Spinner } from "@qes-ui/components/Spinner";
import { apiFetch, formatApiError } from "@qes-ui/lib/api";

interface Prescription {
  id: string;
  status: string;
  verification_status: string | null;
  dispensing_status: string | null;
  doctor_id: string;
  patient_id: string;
  created_at: string | null;
}

function statusTone(status: string): "success" | "warning" | "danger" | "neutral" {
  if (status === "verified" || status === "available") return "success";
  if (status === "dispensed") return "neutral";
  if (status === "failed_verification") return "danger";
  return "warning";
}

export default function PharmacyPrescriptionsPage() {
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dispenseId, setDispenseId] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch("pharmacy", "/api/v1/pharmacy/prescriptions");
      if (!res.ok) {
        setError("Could not load prescriptions.");
        setPrescriptions([]);
        return;
      }
      const data = (await res.json()) as Prescription[];
      setPrescriptions(Array.isArray(data) ? data : []);
    } catch {
      setError("Network error");
      setPrescriptions([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleDownload(prescriptionId: string) {
    try {
      const res = await apiFetch("pharmacy", `/api/v1/pharmacy/prescriptions/${prescriptionId}/download`);
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

  async function confirmDispense() {
    if (!dispenseId) return;
    setActionLoading(true);
    try {
      const res = await apiFetch("pharmacy", `/api/v1/pharmacy/prescriptions/${dispenseId}/dispense`, {
        method: "POST",
        body: JSON.stringify({ dispensing_status: "dispensed" }),
      });
      if (res.ok) {
        setPrescriptions((prev) =>
          prev.map((rx) =>
            rx.id === dispenseId ? { ...rx, status: "dispensed", dispensing_status: "dispensed" } : rx,
          ),
        );
        setDispenseId(null);
      } else {
        const err = await res.json();
        setError(formatApiError(err as { detail?: string }));
      }
    } catch {
      setError("Network error");
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return (
      <Card padding="lg">
        <div style={{ display: "flex", justifyContent: "center", padding: "3rem" }}>
          <Spinner label="Loading prescriptions…" />
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card padding="lg">
        <CardHeader
          title="Prescriptions"
          description="Verified and available prescriptions for your tenant. Download PDFs and confirm dispensing."
        />
        {error && (
          <div className="qes-alert qes-alert--error" role="alert" style={{ marginBottom: "1rem" }}>
            {error}
            <Button variant="ghost" style={{ marginLeft: "0.75rem" }} onClick={() => setError(null)}>
              Dismiss
            </Button>
          </div>
        )}
        {prescriptions.length === 0 ? (
          <EmptyState
            title="No prescriptions"
            description="When doctors upload verified prescriptions, they will appear here."
            action={
              <Button variant="secondary" onClick={() => load()}>
                Refresh
              </Button>
            }
          />
        ) : (
          <div className="qes-table-wrap">
            <table className="qes-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Status</th>
                  <th>Dispensing</th>
                  <th>Created</th>
                  <th style={{ width: "220px" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {prescriptions.map((rx) => (
                  <tr key={rx.id}>
                    <td className="qes-mono">{rx.id.slice(0, 8)}…</td>
                    <td>
                      <Badge tone={statusTone(rx.status)}>{rx.status.replace(/_/g, " ")}</Badge>
                    </td>
                    <td>{rx.dispensing_status ?? "—"}</td>
                    <td>{rx.created_at ? new Date(rx.created_at).toLocaleDateString("es-ES") : "—"}</td>
                    <td>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                        <Button variant="secondary" onClick={() => handleDownload(rx.id)}>
                          Download
                        </Button>
                        {(rx.status === "verified" || rx.status === "available") && (
                          <Button variant="primary" onClick={() => setDispenseId(rx.id)}>
                            Dispense
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal
        open={!!dispenseId}
        title="Confirm dispensing"
        onClose={() => !actionLoading && setDispenseId(null)}
        footer={
          <>
            <Button variant="secondary" disabled={actionLoading} onClick={() => setDispenseId(null)}>
              Cancel
            </Button>
            <Button variant="primary" disabled={actionLoading} onClick={() => confirmDispense()}>
              {actionLoading ? "Confirming…" : "Confirm dispense"}
            </Button>
          </>
        }
      >
        <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--neutral-600)" }}>
          This records a dispensing event for the selected prescription. Ensure the medication has been supplied to the
          patient.
        </p>
      </Modal>
    </>
  );
}
