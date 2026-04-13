"use client";

import { useEffect, useState } from "react";
import { Badge } from "@qes-ui/components/Badge";
import { Button } from "@qes-ui/components/Button";
import { Card, CardHeader } from "@qes-ui/components/Card";
import { EmptyState } from "@qes-ui/components/EmptyState";
import { Spinner } from "@qes-ui/components/Spinner";
import { apiFetch } from "@qes-ui/lib/api";

interface SuspiciousEvent {
  id: string;
  sequence_number: number;
  event_type: string;
  event_category: string;
  severity: string;
  actor_id: string | null;
  actor_type: string | null;
  actor_email: string | null;
  object_type: string | null;
  object_id: string | null;
  action: string;
  outcome: string;
  event_timestamp: string | null;
  source_ip: string | null;
  detail: Record<string, unknown>;
  is_sensitive: string;
}

function severityTone(s: string): "success" | "warning" | "danger" | "neutral" {
  if (s === "critical") return "danger";
  if (s === "error") return "danger";
  if (s === "warning") return "warning";
  return "neutral";
}

export default function SuspiciousEventsPage() {
  const [events, setEvents] = useState<SuspiciousEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch("admin", "/api/v1/admin/suspicious-events?limit=100");
      if (!res.ok) { setError("Could not load suspicious events."); return; }
      const data = await res.json();
      setEvents(Array.isArray(data) ? data : []);
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <Card padding="lg">
        <CardHeader
          title="Suspicious event review queue"
          description="High-severity and failure audit events requiring review. Click any row to expand details."
          action={<Button variant="secondary" onClick={load} disabled={loading}>Refresh</Button>}
        />

        {error && <div className="qes-alert qes-alert--error" style={{ marginBottom: "1rem" }}>{error}</div>}

        {loading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "2rem" }}><Spinner label="Loading events…" /></div>
        ) : events.length === 0 ? (
          <EmptyState title="No suspicious events" description="No warning, error, or critical events found. System appears healthy." />
        ) : (
          <>
            <div style={{ marginBottom: "0.75rem", fontSize: "0.875rem", color: "var(--color-neutral-600)" }}>
              {events.length} event{events.length !== 1 ? "s" : ""} requiring review
            </div>
            <div className="qes-table-wrap">
              <table className="qes-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Severity</th>
                    <th>Event type</th>
                    <th>Actor</th>
                    <th>Object</th>
                    <th>Outcome</th>
                    <th>IP</th>
                    <th>When</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((e) => (
                    <>
                      <tr
                        key={e.id}
                        onClick={() => setExpandedId(expandedId === e.id ? null : e.id)}
                        style={{ cursor: "pointer", background: e.severity === "critical" ? "rgba(220, 38, 38, 0.04)" : e.severity === "error" ? "rgba(239, 68, 68, 0.03)" : undefined }}
                      >
                        <td className="qes-mono" style={{ fontSize: "0.75rem", color: "var(--color-neutral-400)" }}>{e.sequence_number}</td>
                        <td><Badge tone={severityTone(e.severity)}>{e.severity}</Badge></td>
                        <td style={{ fontSize: "0.8125rem", maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{e.event_type}</td>
                        <td style={{ fontSize: "0.875rem" }}>
                          {e.actor_email ?? (e.actor_id ? <span className="qes-mono">{e.actor_id.slice(0, 8)}</span> : <span style={{ color: "var(--color-neutral-400)" }}>system</span>)}
                        </td>
                        <td style={{ fontSize: "0.8125rem" }}>
                          {e.object_type ?? "—"}
                          {e.object_id && <span className="qes-mono" style={{ marginLeft: "0.25rem", fontSize: "0.75rem", color: "var(--color-neutral-500)" }}>{e.object_id.slice(0, 8)}</span>}
                        </td>
                        <td>
                          <Badge tone={e.outcome === "success" ? "success" : e.outcome === "failure" || e.outcome === "denied" ? "danger" : "neutral"}>
                            {e.outcome}
                          </Badge>
                        </td>
                        <td className="qes-mono" style={{ fontSize: "0.8125rem" }}>{e.source_ip ?? "—"}</td>
                        <td style={{ fontSize: "0.8125rem", whiteSpace: "nowrap" }}>{e.event_timestamp ? new Date(e.event_timestamp).toLocaleString("es-ES") : "—"}</td>
                        <td style={{ color: "var(--color-neutral-400)", fontSize: "0.875rem" }}>{expandedId === e.id ? "▲" : "▼"}</td>
                      </tr>
                      {expandedId === e.id && (
                        <tr key={`${e.id}-exp`}>
                          <td colSpan={9} style={{ background: "var(--color-neutral-50)", padding: "1rem 1.5rem" }}>
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem", marginBottom: "0.75rem" }}>
                              <div>
                                <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginBottom: "0.25rem" }}>Full event ID</div>
                                <div className="qes-mono" style={{ fontSize: "0.8125rem" }}>{e.id}</div>
                              </div>
                              <div>
                                <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginBottom: "0.25rem" }}>Category</div>
                                <div style={{ fontSize: "0.875rem" }}>{e.event_category}</div>
                              </div>
                              <div>
                                <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginBottom: "0.25rem" }}>Sensitive</div>
                                <Badge tone={e.is_sensitive === "true" ? "danger" : "neutral"}>{e.is_sensitive === "true" ? "Sensitive" : "Standard"}</Badge>
                              </div>
                            </div>
                            <div>
                              <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginBottom: "0.25rem" }}>Event detail</div>
                              <pre style={{ fontSize: "0.75rem", margin: 0, padding: "0.75rem", background: "white", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-neutral-200)", overflow: "auto", maxHeight: "200px" }}>
                                {JSON.stringify(e.detail, null, 2)}
                              </pre>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
