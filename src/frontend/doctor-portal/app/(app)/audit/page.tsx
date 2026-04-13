"use client";

import { useEffect, useState } from "react";
import { Badge } from "@qes-ui/components/Badge";
import { Card, CardHeader } from "@qes-ui/components/Card";
import { EmptyState } from "@qes-ui/components/EmptyState";
import { Spinner } from "@qes-ui/components/Spinner";
import { apiFetch } from "@qes-ui/lib/api";

interface AuditEvent {
  id: string;
  sequence_number: number;
  event_type: string;
  event_category: string;
  severity: string;
  action: string;
  outcome: string;
  object_type: string | null;
  object_id: string | null;
  event_timestamp: string | null;
  detail: Record<string, unknown>;
}

function severityTone(severity: string): "success" | "warning" | "danger" | "neutral" {
  if (severity === "critical" || severity === "error") return "danger";
  if (severity === "warning") return "warning";
  if (severity === "info") return "success";
  return "neutral";
}

function outcomeTone(outcome: string): "success" | "warning" | "danger" | "neutral" {
  if (outcome === "success") return "success";
  if (outcome === "failure" || outcome === "denied") return "danger";
  return "neutral";
}

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch("doctor", "/api/v1/prescriptions/audit/own?limit=100");
        if (!res.ok) {
          if (!cancelled) setError("Could not load audit trail.");
          return;
        }
        const data = (await res.json()) as AuditEvent[];
        if (!cancelled) setEvents(Array.isArray(data) ? data : []);
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
          <Spinner label="Loading audit trail…" />
        </div>
      </Card>
    );
  }

  return (
    <Card padding="lg">
      <CardHeader
        title="My audit trail"
        description="A read-only log of all your actions recorded in this system."
      />
      {error && (
        <div className="qes-alert qes-alert--error" style={{ marginBottom: "1rem" }}>{error}</div>
      )}
      {events.length === 0 ? (
        <EmptyState title="No audit events yet" description="Your actions will appear here once recorded." />
      ) : (
        <div className="qes-table-wrap">
          <table className="qes-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Event type</th>
                <th>Action</th>
                <th>Object</th>
                <th>Outcome</th>
                <th>Severity</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id}>
                  <td className="qes-mono" style={{ fontSize: "0.75rem", color: "var(--color-neutral-400)" }}>{e.sequence_number}</td>
                  <td style={{ fontSize: "0.8125rem" }}>{e.event_type.replace(/_/g, " ")}</td>
                  <td style={{ fontSize: "0.8125rem" }}>{e.action}</td>
                  <td style={{ fontSize: "0.8125rem", color: "var(--color-neutral-500)" }}>
                    {e.object_type ? `${e.object_type}` : "—"}
                    {e.object_id ? <span className="qes-mono" style={{ marginLeft: "0.25rem", fontSize: "0.75rem" }}>{e.object_id.slice(0, 8)}</span> : null}
                  </td>
                  <td><Badge tone={outcomeTone(e.outcome)}>{e.outcome}</Badge></td>
                  <td><Badge tone={severityTone(e.severity)}>{e.severity}</Badge></td>
                  <td style={{ fontSize: "0.8125rem", whiteSpace: "nowrap" }}>
                    {e.event_timestamp ? new Date(e.event_timestamp).toLocaleString("es-ES") : "—"}
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
