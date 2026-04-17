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
  upload_checksum: string;
  created_at: string | null;
}

function statusTone(status: string): "success" | "warning" | "danger" | "neutral" {
  if (status === "verified" || status === "available") return "success";
  if (status === "failed_verification" || status === "revoked" || status === "cancelled") return "danger";
  if (status === "pending_verification" || status === "manual_review") return "warning";
  return "neutral";
}

export default function PrescriptionsPage() {
  const [prescriptions, setPrescriptions] = useState<Prescription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch("clinic", "/api/v1/prescriptions");
        if (!res.ok) {
          if (!cancelled) setError("Could not load prescriptions.");
          return;
        }
        const data = (await res.json()) as Prescription[];
        if (!cancelled) setPrescriptions(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelled) setError("Network error");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

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
        title="My prescriptions"
        description="Prescriptions you uploaded for this tenant."
        action={
          <Link href="/">
            <Button variant="primary">Upload new</Button>
          </Link>
        }
      />
      {error && (
        <div className="qes-alert qes-alert--error" role="alert" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}
      {prescriptions.length === 0 ? (
        <EmptyState
          title="No prescriptions yet"
          description="Upload a signed PDF from the Upload page to see it listed here."
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
                  <td>
                    <Badge tone={statusTone(rx.status)}>{rx.status.replace(/_/g, " ")}</Badge>
                  </td>
                  <td>{rx.verification_status ?? "—"}</td>
                  <td>{rx.dispensing_status ?? "—"}</td>
                  <td>{rx.created_at ? new Date(rx.created_at).toLocaleDateString("es-ES") : "—"}</td>
                  <td>
                    <Link href={`/prescriptions/${rx.id}`}>
                      <Button variant="ghost" style={{ padding: "0.25rem 0.75rem", fontSize: "0.8125rem" }}>
                        View
                      </Button>
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
