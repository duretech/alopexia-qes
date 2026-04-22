"use client";

import { useEffect, useState } from "react";
import { Badge } from "@qes-ui/components/Badge";
import { Button } from "@qes-ui/components/Button";
import { Card, CardHeader } from "@qes-ui/components/Card";
import { EmptyState } from "@qes-ui/components/EmptyState";
import { Spinner } from "@qes-ui/components/Spinner";
import { TextField } from "@qes-ui/components/TextField";
import { apiFetch } from "@qes-ui/lib/api";

interface EvidenceFile {
  id: string;
  prescription_id: string;
  verification_result_id: string;
  evidence_type: string;
  mime_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
  trust_list_status: string | null;
  created_at: string | null;
}

interface ViewerState {
  file: EvidenceFile;
  url: string;
}

export default function EvidencePage() {
  const [files, setFiles] = useState<EvidenceFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterPrescription, setFilterPrescription] = useState("");
  const [filterType, setFilterType] = useState("");
  const [viewer, setViewer] = useState<ViewerState | null>(null);
  const [viewerLoading, setViewerLoading] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: "100" });
      if (filterPrescription) params.set("prescription_id", filterPrescription);
      if (filterType) params.set("evidence_type", filterType);
      const res = await apiFetch("admin", `/api/v1/admin/evidence?${params}`);
      if (!res.ok) { setError("Could not load evidence files."); return; }
      const data = await res.json();
      setFiles(Array.isArray(data) ? data : []);
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [filterPrescription, filterType]);

  async function handleView(f: EvidenceFile) {
    setViewerLoading(f.id);
    try {
      const res = await apiFetch("admin", `/api/v1/admin/evidence/${f.id}/view`);
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        setViewer({ file: f, url });
      } else {
        setError("Failed to load evidence file");
      }
    } catch {
      setError("Network error loading file");
    } finally {
      setViewerLoading(null);
    }
  }

  function closeViewer() {
    if (viewer) URL.revokeObjectURL(viewer.url);
    setViewer(null);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <Card padding="lg">
        <CardHeader
          title="Evidence files"
          description="QTSP validation reports and evidence artifacts stored for audit and compliance."
          action={<Button variant="secondary" onClick={load}>Refresh</Button>}
        />

        <div style={{ display: "flex", gap: "1rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
          <TextField
            label="Filter by prescription ID"
            value={filterPrescription}
            onChange={(e: any) => setFilterPrescription(e.target.value)}
            placeholder="UUID"
            hint="Leave empty to show all"
          />
          <div className="qes-field" style={{ margin: 0, minWidth: "180px" }}>
            <label className="qes-label">Evidence type</label>
            <select className="qes-input" value={filterType} onChange={(e: any) => setFilterType(e.target.value)}>
              <option value="">All types</option>
              <option value="validation_report">Validation report</option>
              <option value="diagnostic_data">Diagnostic data</option>
              <option value="evidence_record">Evidence record</option>
              <option value="certificate_chain">Certificate chain</option>
              <option value="timestamp_token">Timestamp token</option>
            </select>
          </div>
        </div>

        {error && <div className="qes-alert qes-alert--error" style={{ marginBottom: "1rem" }}>{error}</div>}

        {loading ? (
          <div style={{ display: "flex", justifyContent: "center", padding: "2rem" }}><Spinner label="Loading evidence…" /></div>
        ) : files.length === 0 ? (
          <EmptyState title="No evidence files" description="Evidence files are generated when prescriptions are verified by the QTSP." />
        ) : (
          <div className="qes-table-wrap">
            <table className="qes-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Prescription</th>
                  <th>MIME</th>
                  <th>Size</th>
                  <th>Trust list</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {files.map((f) => (
                  <tr key={f.id}>
                    <td><Badge tone="neutral">{f.evidence_type.replace(/_/g, " ")}</Badge></td>
                    <td className="qes-mono" style={{ fontSize: "0.8125rem" }}>{f.prescription_id.slice(0, 8)}…</td>
                    <td className="qes-mono" style={{ fontSize: "0.8125rem" }}>{f.mime_type}</td>
                    <td style={{ fontSize: "0.875rem" }}>{(f.file_size_bytes / 1024).toFixed(1)} KB</td>
                    <td>
                      <Badge tone={f.trust_list_status === "trusted" ? "success" : f.trust_list_status === "untrusted" ? "danger" : "neutral"}>
                        {f.trust_list_status ?? "—"}
                      </Badge>
                    </td>
                    <td style={{ fontSize: "0.875rem", whiteSpace: "nowrap" }}>
                      {f.created_at ? new Date(f.created_at).toLocaleDateString("es-ES") : "—"}
                    </td>
                    <td>
                      <Button
                        variant="secondary"
                        onClick={() => handleView(f)}
                        disabled={viewerLoading === f.id}
                        style={{ padding: "0.25rem 0.75rem", fontSize: "0.8125rem" }}
                      >
                        {viewerLoading === f.id ? "Loading…" : "View"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Evidence Viewer Modal */}
      {viewer && (
        <div
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 2000 }}
          onClick={closeViewer}
        >
          <div
            style={{ width: "90%", height: "90vh", maxWidth: "1024px", background: "white", borderRadius: "var(--radius-lg)", display: "flex", flexDirection: "column", overflow: "hidden" }}
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
          >
            <div style={{ padding: "1rem 1.5rem", borderBottom: "1px solid var(--color-neutral-200)", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <h2 style={{ margin: 0, fontSize: "1rem", fontWeight: 600 }}>
                  {viewer.file.evidence_type.replace(/_/g, " ")}
                </h2>
                <div style={{ marginTop: "0.25rem", display: "flex", gap: "0.75rem", fontSize: "0.8125rem", color: "var(--color-neutral-500)" }}>
                  <span className="qes-mono">{viewer.file.mime_type}</span>
                  <span>{(viewer.file.file_size_bytes / 1024).toFixed(1)} KB</span>
                  <span className="qes-mono">rx: {viewer.file.prescription_id.slice(0, 8)}…</span>
                </div>
              </div>
              <Button variant="ghost" onClick={closeViewer} style={{ padding: "0.5rem" }}>✕</Button>
            </div>
            <div style={{ flex: 1, overflow: "hidden", background: "var(--color-neutral-100)" }}>
              <iframe
                src={viewer.url}
                style={{ width: "100%", height: "100%", border: "none" }}
                title="Evidence file"
              />
            </div>
            <div style={{ padding: "1rem 1.5rem", borderTop: "1px solid var(--color-neutral-200)", background: "var(--color-neutral-50)", display: "flex", justifyContent: "flex-end" }}>
              <Button variant="ghost" onClick={closeViewer}>Close</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
