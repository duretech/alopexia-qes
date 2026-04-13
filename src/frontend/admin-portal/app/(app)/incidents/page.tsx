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

interface Incident {
  id: string;
  title: string;
  description: string;
  severity: string;
  status: string;
  incident_type: string;
  reported_by: string;
  reported_at: string | null;
  assigned_to: string | null;
  related_object_type: string | null;
  related_object_id: string | null;
  resolution: string | null;
  root_cause: string | null;
  resolved_at: string | null;
  created_at: string | null;
}

function severityTone(s: string): "success" | "warning" | "danger" | "neutral" {
  if (s === "critical") return "danger";
  if (s === "high") return "danger";
  if (s === "medium") return "warning";
  return "neutral";
}

function statusTone(s: string): "success" | "warning" | "danger" | "neutral" {
  if (s === "resolved" || s === "closed") return "success";
  if (s === "open") return "danger";
  if (s === "investigating" || s === "mitigated") return "warning";
  return "neutral";
}

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterSeverity, setFilterSeverity] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [detailIncident, setDetailIncident] = useState<Incident | null>(null);
  const [updateForm, setUpdateForm] = useState({ status: "", resolution: "", root_cause: "", corrective_actions: "" });
  const [createForm, setCreateForm] = useState({
    title: "",
    description: "",
    severity: "medium",
    incident_type: "other",
    related_object_type: "",
    related_object_id: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: "100" });
      if (filterStatus) params.set("status", filterStatus);
      if (filterSeverity) params.set("severity", filterSeverity);
      const res = await apiFetch("admin", `/api/v1/admin/incidents?${params}`);
      if (!res.ok) { setError("Could not load incidents."); return; }
      const data = await res.json();
      setIncidents(Array.isArray(data) ? data : []);
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [filterStatus, filterSeverity]);

  async function handleCreate() {
    if (!createForm.title || !createForm.description) {
      setSubmitError("Title and description are required.");
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await apiFetch("admin", "/api/v1/admin/incidents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...createForm,
          related_object_type: createForm.related_object_type || undefined,
          related_object_id: createForm.related_object_id || undefined,
        }),
      });
      if (res.ok) {
        const created = await res.json();
        setIncidents((prev) => [created, ...prev]);
        setCreateOpen(false);
        setCreateForm({ title: "", description: "", severity: "medium", incident_type: "other", related_object_type: "", related_object_id: "" });
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

  async function handleUpdate() {
    if (!detailIncident) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const body: Record<string, string> = {};
      if (updateForm.status) body.status = updateForm.status;
      if (updateForm.resolution) body.resolution = updateForm.resolution;
      if (updateForm.root_cause) body.root_cause = updateForm.root_cause;
      if (updateForm.corrective_actions) body.corrective_actions = updateForm.corrective_actions;
      const res = await apiFetch("admin", `/api/v1/admin/incidents/${detailIncident.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const updated = await res.json();
        setIncidents((prev) => prev.map((i) => i.id === updated.id ? updated : i));
        setDetailIncident(null);
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
          title="Incident management"
          description="Track and resolve security and compliance incidents."
          action={
            <Button variant="primary" onClick={() => setCreateOpen(true)}>Report incident</Button>
          }
        />

        <div style={{ display: "flex", gap: "1rem", marginBottom: "1.25rem" }}>
          <div className="qes-field" style={{ margin: 0, minWidth: "150px" }}>
            <label className="qes-label">Status</label>
            <select className="qes-input" value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="">All</option>
              <option value="open">Open</option>
              <option value="investigating">Investigating</option>
              <option value="mitigated">Mitigated</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
          </div>
          <div className="qes-field" style={{ margin: 0, minWidth: "150px" }}>
            <label className="qes-label">Severity</label>
            <select className="qes-input" value={filterSeverity} onChange={(e) => setFilterSeverity(e.target.value)}>
              <option value="">Any</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <Button variant="secondary" onClick={load} style={{ alignSelf: "flex-end" }}>Refresh</Button>
        </div>

        {error && <div className="qes-alert qes-alert--error" style={{ marginBottom: "1rem" }}>{error}</div>}

        {loading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "2rem" }}><Spinner label="Loading incidents…" /></div>
        ) : incidents.length === 0 ? (
          <EmptyState title="No incidents" description="No incidents match the current filters." />
        ) : (
          <div className="qes-table-wrap">
            <table className="qes-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Type</th>
                  <th>Severity</th>
                  <th>Status</th>
                  <th>Reported</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((i) => (
                  <tr key={i.id}>
                    <td style={{ fontWeight: 500, maxWidth: "240px" }}>{i.title}</td>
                    <td style={{ fontSize: "0.8125rem" }}>{i.incident_type.replace(/_/g, " ")}</td>
                    <td><Badge tone={severityTone(i.severity)}>{i.severity}</Badge></td>
                    <td><Badge tone={statusTone(i.status)}>{i.status}</Badge></td>
                    <td style={{ fontSize: "0.875rem", whiteSpace: "nowrap" }}>
                      {i.reported_at ? new Date(i.reported_at).toLocaleDateString("es-ES") : "—"}
                    </td>
                    <td>
                      <Button
                        variant="ghost"
                        onClick={() => { setDetailIncident(i); setUpdateForm({ status: i.status, resolution: i.resolution ?? "", root_cause: i.root_cause ?? "", corrective_actions: "" }); }}
                        style={{ padding: "0.25rem 0.75rem", fontSize: "0.8125rem" }}
                      >
                        Manage
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Create modal */}
      <Modal
        open={createOpen}
        title="Report new incident"
        onClose={() => { setCreateOpen(false); setSubmitError(null); }}
        footer={
          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
            <Button variant="ghost" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button variant="primary" disabled={submitting} onClick={handleCreate}>
              {submitting ? "Reporting…" : "Report incident"}
            </Button>
          </div>
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <TextField label="Title" value={createForm.title} onChange={(e) => setCreateForm((f) => ({ ...f, title: e.target.value }))} placeholder="Brief incident title" required />
          <div className="qes-field" style={{ margin: 0 }}>
            <label className="qes-label">Description</label>
            <textarea className="qes-input" rows={3} value={createForm.description} onChange={(e) => setCreateForm((f) => ({ ...f, description: e.target.value }))} placeholder="Describe what happened" />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div className="qes-field" style={{ margin: 0 }}>
              <label className="qes-label">Severity</label>
              <select className="qes-input" value={createForm.severity} onChange={(e) => setCreateForm((f) => ({ ...f, severity: e.target.value }))}>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
            <div className="qes-field" style={{ margin: 0 }}>
              <label className="qes-label">Incident type</label>
              <select className="qes-input" value={createForm.incident_type} onChange={(e) => setCreateForm((f) => ({ ...f, incident_type: e.target.value }))}>
                <option value="unauthorized_access">Unauthorized access</option>
                <option value="data_breach">Data breach</option>
                <option value="audit_integrity">Audit integrity</option>
                <option value="verification_failure">Verification failure</option>
                <option value="system_compromise">System compromise</option>
                <option value="policy_violation">Policy violation</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
          <TextField label="Related object type (optional)" value={createForm.related_object_type} onChange={(e) => setCreateForm((f) => ({ ...f, related_object_type: e.target.value }))} placeholder="e.g. prescription" />
          <TextField label="Related object ID (optional)" value={createForm.related_object_id} onChange={(e) => setCreateForm((f) => ({ ...f, related_object_id: e.target.value }))} placeholder="UUID" />
          {submitError && <div className="qes-alert qes-alert--error">{submitError}</div>}
        </div>
      </Modal>

      {/* Manage modal */}
      <Modal
        open={!!detailIncident}
        title={detailIncident?.title ?? ""}
        onClose={() => { setDetailIncident(null); setSubmitError(null); }}
        footer={
          <div style={{ display: "flex", gap: "0.75rem", justifyContent: "flex-end" }}>
            <Button variant="ghost" onClick={() => setDetailIncident(null)}>Close</Button>
            <Button variant="primary" disabled={submitting} onClick={handleUpdate}>
              {submitting ? "Saving…" : "Save changes"}
            </Button>
          </div>
        }
      >
        {detailIncident && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div style={{ padding: "0.75rem 1rem", background: "var(--color-neutral-50)", borderRadius: "var(--radius-md)", fontSize: "0.875rem" }}>
              {detailIncident.description}
            </div>
            <div className="qes-field" style={{ margin: 0 }}>
              <label className="qes-label">Status</label>
              <select className="qes-input" value={updateForm.status} onChange={(e) => setUpdateForm((f) => ({ ...f, status: e.target.value }))}>
                <option value="open">Open</option>
                <option value="investigating">Investigating</option>
                <option value="mitigated">Mitigated</option>
                <option value="resolved">Resolved</option>
                <option value="closed">Closed</option>
              </select>
            </div>
            <div className="qes-field" style={{ margin: 0 }}>
              <label className="qes-label">Resolution</label>
              <textarea className="qes-input" rows={2} value={updateForm.resolution} onChange={(e) => setUpdateForm((f) => ({ ...f, resolution: e.target.value }))} placeholder="How was this resolved?" />
            </div>
            <div className="qes-field" style={{ margin: 0 }}>
              <label className="qes-label">Root cause</label>
              <textarea className="qes-input" rows={2} value={updateForm.root_cause} onChange={(e) => setUpdateForm((f) => ({ ...f, root_cause: e.target.value }))} placeholder="What caused this incident?" />
            </div>
            <div className="qes-field" style={{ margin: 0 }}>
              <label className="qes-label">Corrective actions</label>
              <textarea className="qes-input" rows={2} value={updateForm.corrective_actions} onChange={(e) => setUpdateForm((f) => ({ ...f, corrective_actions: e.target.value }))} placeholder="What steps will prevent recurrence?" />
            </div>
            {submitError && <div className="qes-alert qes-alert--error">{submitError}</div>}
          </div>
        )}
      </Modal>
    </div>
  );
}
