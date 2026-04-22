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

type ViewType = "json" | "xml" | "text" | "pdf" | "image" | "binary";

interface ViewerState {
  file: EvidenceFile;
  type: ViewType;
  blobUrl?: string;
  text?: string;
}

// ── formatters ────────────────────────────────────────────────────────────────

function escHtml(s: string) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function highlightJson(raw: string): string {
  const escaped = escHtml(raw);
  return escaped.replace(
    /("(?:\\u[0-9a-fA-F]{4}|\\[^u]|[^\\"])*"(\s*:)?|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    (m) => {
      if (m.startsWith('"')) {
        if (m.trimEnd().endsWith(":"))
          return `<span style="color:var(--accent-600);font-weight:600">${m}</span>`;
        return `<span style="color:#16a34a">${m}</span>`;
      }
      if (m === "true" || m === "false")
        return `<span style="color:#2563eb;font-weight:500">${m}</span>`;
      if (m === "null")
        return `<span style="color:#9333ea">${m}</span>`;
      return `<span style="color:#ea580c">${m}</span>`;
    },
  );
}

function highlightXml(raw: string): string {
  // First indent, then highlight
  let formatted = "";
  let depth = 0;
  const nodes = raw.replace(/>\s*</g, ">\n<").split("\n");
  for (const node of nodes) {
    const t = node.trim();
    if (!t) continue;
    if (t.startsWith("</")) depth = Math.max(0, depth - 1);
    formatted += "  ".repeat(depth) + t + "\n";
    if (t.startsWith("<") && !t.startsWith("</") && !t.startsWith("<?") && !t.startsWith("<!--") && !t.endsWith("/>"))
      depth++;
  }

  const esc = escHtml(formatted.trim());
  return esc
    // comments
    .replace(/(&lt;!--[\s\S]*?--&gt;)/g, '<span style="color:#6b7280;font-style:italic">$1</span>')
    // CDATA
    .replace(/(&lt;!\[CDATA\[[\s\S]*?\]\]&gt;)/g, '<span style="color:#78716c">$1</span>')
    // closing tags
    .replace(/(&lt;\/)([\w:.-]+)(&gt;)/g, '<span style="color:#7c3aed">$1</span><span style="color:#4f46e5;font-weight:600">$2</span><span style="color:#7c3aed">$3</span>')
    // opening tags + self-closing: tag name then attrs
    .replace(/(&lt;)([\w:.-]+)((?:\s[^&]*?)?)(\/&gt;|&gt;)/g, (_, open, tag, attrs, close) => {
      const styledAttrs = attrs.replace(
        /([\w:.-]+)(\s*=\s*)(&quot;[^&quot;]*&quot;)/g,
        '<span style="color:#b45309">$1</span>$2<span style="color:#16a34a">$3</span>',
      );
      return `<span style="color:#7c3aed">${open}</span><span style="color:#4f46e5;font-weight:600">${tag}</span>${styledAttrs}<span style="color:#7c3aed">${close}</span>`;
    })
    // PI / DOCTYPE
    .replace(/(&lt;\?[\s\S]*?\?&gt;)/g, '<span style="color:#6b7280">$1</span>');
}

// ── component ─────────────────────────────────────────────────────────────────

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
      if (!res.ok) { setError("Failed to load evidence file"); return; }

      const mime = (f.mime_type || "").toLowerCase();

      if (mime.includes("json")) {
        const text = await res.text();
        try {
          const pretty = JSON.stringify(JSON.parse(text), null, 2);
          setViewer({ file: f, type: "json", text: pretty });
        } catch {
          setViewer({ file: f, type: "text", text });
        }
      } else if (mime.includes("xml") || mime.includes("html")) {
        const text = await res.text();
        setViewer({ file: f, type: "xml", text });
      } else if (mime.startsWith("text/")) {
        const text = await res.text();
        setViewer({ file: f, type: "text", text });
      } else if (mime === "application/pdf") {
        const blob = await res.blob();
        setViewer({ file: f, type: "pdf", blobUrl: URL.createObjectURL(blob) });
      } else if (mime.startsWith("image/")) {
        const blob = await res.blob();
        setViewer({ file: f, type: "image", blobUrl: URL.createObjectURL(blob) });
      } else {
        // try as text anyway (PEM certs, etc.)
        const text = await res.text();
        setViewer({ file: f, type: "binary", text });
      }
    } catch {
      setError("Network error loading file");
    } finally {
      setViewerLoading(null);
    }
  }

  function closeViewer() {
    if (viewer?.blobUrl) URL.revokeObjectURL(viewer.blobUrl);
    setViewer(null);
  }

  function renderViewerBody() {
    if (!viewer) return null;

    const codeBase: React.CSSProperties = {
      flex: 1,
      overflow: "auto",
      background: "#0f172a",
      padding: "1.25rem 1.5rem",
      margin: 0,
      fontFamily: "var(--font-mono)",
      fontSize: "0.8rem",
      lineHeight: 1.7,
      color: "#e2e8f0",
      whiteSpace: "pre",
      tabSize: 2,
    };

    switch (viewer.type) {
      case "json":
        return (
          <pre style={codeBase}
            dangerouslySetInnerHTML={{ __html: highlightJson(viewer.text ?? "") }}
          />
        );
      case "xml":
        return (
          <pre style={codeBase}
            dangerouslySetInnerHTML={{ __html: highlightXml(viewer.text ?? "") }}
          />
        );
      case "text":
      case "binary":
        return <pre style={{ ...codeBase, color: "#cbd5e1" }}>{viewer.text}</pre>;
      case "pdf":
        return (
          <iframe
            src={viewer.blobUrl}
            style={{ width: "100%", height: "100%", border: "none" }}
            title="Evidence file"
          />
        );
      case "image":
        return (
          <div style={{ flex: 1, overflow: "auto", display: "flex", alignItems: "center", justifyContent: "center", background: "#0f172a", padding: "1rem" }}>
            <img src={viewer.blobUrl} alt="Evidence" style={{ maxWidth: "100%", maxHeight: "100%", borderRadius: "var(--radius-md)" }} />
          </div>
        );
    }
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
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 2000 }}
          onClick={closeViewer}
        >
          <div
            style={{ width: "92%", height: "92vh", maxWidth: "1100px", background: "white", borderRadius: "var(--radius-lg)", display: "flex", flexDirection: "column", overflow: "hidden", boxShadow: "0 25px 60px rgba(0,0,0,0.5)" }}
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
          >
            {/* Header */}
            <div style={{ padding: "1rem 1.5rem", borderBottom: "1px solid var(--color-neutral-200)", display: "flex", justifyContent: "space-between", alignItems: "flex-start", background: "white", flexShrink: 0 }}>
              <div>
                <h2 style={{ margin: 0, fontSize: "1rem", fontWeight: 600, textTransform: "capitalize" }}>
                  {viewer.file.evidence_type.replace(/_/g, " ")}
                </h2>
                <div style={{ marginTop: "0.35rem", display: "flex", gap: "1rem", fontSize: "0.8125rem", color: "var(--color-neutral-500)", flexWrap: "wrap" }}>
                  <span className="qes-mono">{viewer.file.mime_type}</span>
                  <span>{(viewer.file.file_size_bytes / 1024).toFixed(1)} KB</span>
                  <span className="qes-mono">rx: {viewer.file.prescription_id.slice(0, 8)}…</span>
                  <Badge tone={
                    viewer.type === "json" ? "success" :
                    viewer.type === "xml" ? "info" :
                    viewer.type === "pdf" ? "danger" : "neutral"
                  }>
                    {viewer.type.toUpperCase()}
                  </Badge>
                </div>
              </div>
              <Button variant="ghost" onClick={closeViewer} style={{ padding: "0.5rem", fontSize: "1rem" }}>✕</Button>
            </div>

            {/* Body */}
            <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
              {renderViewerBody()}
            </div>

            {/* Footer */}
            <div style={{ padding: "0.75rem 1.5rem", borderTop: "1px solid var(--color-neutral-200)", background: "var(--color-neutral-50)", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
              <span style={{ fontSize: "0.75rem", color: "var(--color-neutral-400)", fontFamily: "var(--font-mono)" }}>
                SHA-256: {viewer.file.checksum_sha256.slice(0, 16)}…
              </span>
              <Button variant="ghost" onClick={closeViewer}>Close</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
