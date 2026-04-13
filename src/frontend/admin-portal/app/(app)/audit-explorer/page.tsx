"use client";

import { useState } from "react";
import { Badge } from "@qes-ui/components/Badge";
import { Button } from "@qes-ui/components/Button";
import { Card, CardHeader } from "@qes-ui/components/Card";
import { EmptyState } from "@qes-ui/components/EmptyState";
import { Spinner } from "@qes-ui/components/Spinner";
import { TextField } from "@qes-ui/components/TextField";
import { apiFetch } from "@qes-ui/lib/api";

interface AuditEvent {
  id: string;
  sequence_number: number;
  event_type: string;
  event_category: string;
  severity: string;
  actor_id: string | null;
  actor_type: string | null;
  actor_role: string | null;
  actor_email: string | null;
  object_type: string | null;
  object_id: string | null;
  action: string;
  outcome: string;
  event_timestamp: string | null;
  source_ip: string | null;
  detail: Record<string, unknown>;
}

interface SearchResult {
  total: number;
  offset: number;
  limit: number;
  events: AuditEvent[];
}

function severityTone(s: string): "success" | "warning" | "danger" | "neutral" {
  if (s === "critical" || s === "error") return "danger";
  if (s === "warning") return "warning";
  return "neutral";
}

function outcomeTone(o: string): "success" | "warning" | "danger" | "neutral" {
  if (o === "success") return "success";
  if (o === "failure" || o === "denied") return "danger";
  return "neutral";
}

export default function AuditExplorerPage() {
  const [filters, setFilters] = useState({
    event_type: "",
    actor_id: "",
    object_type: "",
    object_id: "",
    severity: "",
    outcome: "",
    start_date: "",
    end_date: "",
  });
  const [result, setResult] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  async function search(offset = 0) {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: "50", offset: String(offset) });
      Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v); });
      const res = await apiFetch("admin", `/api/v1/admin/audit/events?${params}`);
      if (!res.ok) { setError("Could not load audit events."); return; }
      setResult(await res.json());
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  }

  function updateFilter(key: string, value: string) {
    setFilters((f) => ({ ...f, [key]: value }));
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      {/* Filters */}
      <Card padding="lg">
        <CardHeader title="Audit event explorer" description="Search and filter the immutable hash-chained audit log." />
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
          <TextField label="Event type" value={filters.event_type} onChange={(e) => updateFilter("event_type", e.target.value)} placeholder="e.g. prescription.upload" />
          <TextField label="Actor ID (UUID)" value={filters.actor_id} onChange={(e) => updateFilter("actor_id", e.target.value)} placeholder="User UUID" />
          <TextField label="Object type" value={filters.object_type} onChange={(e) => updateFilter("object_type", e.target.value)} placeholder="e.g. prescription" />
          <TextField label="Object ID (UUID)" value={filters.object_id} onChange={(e) => updateFilter("object_id", e.target.value)} placeholder="Object UUID" />
          <div className="qes-field" style={{ margin: 0 }}>
            <label className="qes-label">Severity</label>
            <select className="qes-input" value={filters.severity} onChange={(e) => updateFilter("severity", e.target.value)}>
              <option value="">Any</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
              <option value="critical">Critical</option>
            </select>
          </div>
          <div className="qes-field" style={{ margin: 0 }}>
            <label className="qes-label">Outcome</label>
            <select className="qes-input" value={filters.outcome} onChange={(e) => updateFilter("outcome", e.target.value)}>
              <option value="">Any</option>
              <option value="success">Success</option>
              <option value="failure">Failure</option>
              <option value="denied">Denied</option>
              <option value="error">Error</option>
            </select>
          </div>
          <TextField label="Start date" type="datetime-local" value={filters.start_date} onChange={(e) => updateFilter("start_date", e.target.value)} />
          <TextField label="End date" type="datetime-local" value={filters.end_date} onChange={(e) => updateFilter("end_date", e.target.value)} />
        </div>
        <div style={{ marginTop: "1rem", display: "flex", gap: "0.75rem" }}>
          <Button variant="primary" onClick={() => search(0)} disabled={loading}>
            {loading ? "Searching…" : "Search"}
          </Button>
          <Button variant="ghost" onClick={() => { setFilters({ event_type: "", actor_id: "", object_type: "", object_id: "", severity: "", outcome: "", start_date: "", end_date: "" }); setResult(null); }}>
            Clear
          </Button>
        </div>
      </Card>

      {/* Results */}
      {error && <div className="qes-alert qes-alert--error">{error}</div>}

      {loading ? (
        <Card padding="lg"><div style={{ display: "flex", justifyContent: "center", padding: "2rem" }}><Spinner label="Searching…" /></div></Card>
      ) : result ? (
        <Card padding="lg">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <span style={{ fontSize: "0.9375rem", color: "var(--color-neutral-600)" }}>
              {result.total.toLocaleString()} event{result.total !== 1 ? "s" : ""} found
              {result.total > result.limit && ` — showing ${result.offset + 1}–${Math.min(result.offset + result.limit, result.total)}`}
            </span>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              {result.offset > 0 && (
                <Button variant="secondary" onClick={() => search(result.offset - result.limit)}>← Previous</Button>
              )}
              {result.offset + result.limit < result.total && (
                <Button variant="secondary" onClick={() => search(result.offset + result.limit)}>Next →</Button>
              )}
            </div>
          </div>

          {result.events.length === 0 ? (
            <EmptyState title="No events match your filters" description="Try broadening the search criteria." />
          ) : (
            <div className="qes-table-wrap">
              <table className="qes-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Event type</th>
                    <th>Actor</th>
                    <th>Object</th>
                    <th>Action</th>
                    <th>Outcome</th>
                    <th>Severity</th>
                    <th>When</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {result.events.map((e) => (
                    <>
                      <tr key={e.id} onClick={() => setExpandedId(expandedId === e.id ? null : e.id)} style={{ cursor: "pointer" }}>
                        <td className="qes-mono" style={{ fontSize: "0.75rem", color: "var(--color-neutral-400)" }}>{e.sequence_number}</td>
                        <td style={{ fontSize: "0.8125rem", maxWidth: "180px", overflow: "hidden", textOverflow: "ellipsis" }}>{e.event_type}</td>
                        <td style={{ fontSize: "0.8125rem" }}>
                          {e.actor_email ?? (e.actor_id ? e.actor_id.slice(0, 8) : "system")}
                          {e.actor_role && <span style={{ color: "var(--color-neutral-400)", marginLeft: "0.25rem" }}>({e.actor_role})</span>}
                        </td>
                        <td style={{ fontSize: "0.8125rem" }}>
                          {e.object_type ?? "—"}
                          {e.object_id && <span className="qes-mono" style={{ marginLeft: "0.25rem", fontSize: "0.75rem" }}>{e.object_id.slice(0, 8)}</span>}
                        </td>
                        <td style={{ fontSize: "0.8125rem" }}>{e.action}</td>
                        <td><Badge tone={outcomeTone(e.outcome)}>{e.outcome}</Badge></td>
                        <td><Badge tone={severityTone(e.severity)}>{e.severity}</Badge></td>
                        <td style={{ fontSize: "0.8125rem", whiteSpace: "nowrap" }}>{e.event_timestamp ? new Date(e.event_timestamp).toLocaleString("es-ES") : "—"}</td>
                        <td style={{ color: "var(--color-neutral-400)", fontSize: "0.875rem" }}>{expandedId === e.id ? "▲" : "▼"}</td>
                      </tr>
                      {expandedId === e.id && (
                        <tr key={`${e.id}-detail`}>
                          <td colSpan={9} style={{ background: "var(--color-neutral-50)", padding: "1rem" }}>
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                              <div>
                                <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginBottom: "0.25rem" }}>Event ID</div>
                                <div className="qes-mono" style={{ fontSize: "0.8125rem" }}>{e.id}</div>
                              </div>
                              <div>
                                <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginBottom: "0.25rem" }}>Source IP</div>
                                <div className="qes-mono" style={{ fontSize: "0.8125rem" }}>{e.source_ip ?? "—"}</div>
                              </div>
                              <div style={{ gridColumn: "1 / -1" }}>
                                <div style={{ fontSize: "0.75rem", color: "var(--color-neutral-500)", marginBottom: "0.25rem" }}>Detail</div>
                                <pre style={{ fontSize: "0.75rem", margin: 0, padding: "0.75rem", background: "white", borderRadius: "var(--radius-sm)", border: "1px solid var(--color-neutral-200)", overflow: "auto" }}>
                                  {JSON.stringify(e.detail, null, 2)}
                                </pre>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      ) : null}
    </div>
  );
}
