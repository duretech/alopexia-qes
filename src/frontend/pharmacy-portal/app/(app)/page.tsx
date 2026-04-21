"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@qes-ui/components/Badge";
import { Button } from "@qes-ui/components/Button";
import { Card, CardHeader } from "@qes-ui/components/Card";
import { EmptyState } from "@qes-ui/components/EmptyState";
import { Spinner } from "@qes-ui/components/Spinner";
import { apiFetch } from "@qes-ui/lib/api";

interface Prescription {
  id: string;
  status: string;
  verification_status: string | null;
  dispensing_status: string | null;
  doctor_id: string;
  patient_id: string | null;
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

  useEffect(() => { load(); }, []);

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
    <Card padding="lg">
      <CardHeader
        title="Prescriptions"
        description="Verified and available prescriptions. Click a row to view details, evidence, and dispense."
        action={
          <Button variant="secondary" onClick={load}>Refresh</Button>
        }
      />
      {error && (
        <div className="qes-alert qes-alert--error" role="alert" style={{ marginBottom: "1rem" }}>
          {error}
          <Button variant="ghost" style={{ marginLeft: "0.75rem" }} onClick={() => setError(null)}>Dismiss</Button>
        </div>
      )}
      {prescriptions.length === 0 ? (
        <EmptyState
          title="No prescriptions"
          description="When doctors upload verified prescriptions, they will appear here."
          action={<Button variant="secondary" onClick={load}>Refresh</Button>}
        />
      ) : (
        <div className="qes-table-wrap">
          <table className="qes-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Status</th>
                <th>Verification</th>
                <th>Dispensing</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {prescriptions.map((rx) => (
                <tr key={rx.id}>
                  <td className="qes-mono">{rx.id.slice(0, 8)}…</td>
                  <td><Badge tone={statusTone(rx.status)}>{rx.status.replace(/_/g, " ")}</Badge></td>
                  <td>{rx.verification_status ?? "—"}</td>
                  <td>{rx.dispensing_status ?? "—"}</td>
                  <td>{rx.created_at ? new Date(rx.created_at).toLocaleDateString("es-ES") : "—"}</td>
                  <td>
                    <Link href={`/prescriptions/${rx.id}`}>
                      <Button variant="ghost" style={{ padding: "0.25rem 0.75rem", fontSize: "0.8125rem" }}>View →</Button>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
