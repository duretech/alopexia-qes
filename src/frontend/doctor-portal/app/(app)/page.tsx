"use client";

import { useState } from "react";
import { Badge } from "@qes-ui/components/Badge";
import { Button } from "@qes-ui/components/Button";
import { Card, CardHeader } from "@qes-ui/components/Card";
import { TextField } from "@qes-ui/components/TextField";
import { apiFetch, formatApiError } from "@qes-ui/lib/api";

const DEMO_PATIENT = "66666666-6666-6666-6666-666666666666";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [patientId, setPatientId] = useState(DEMO_PATIENT);
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError(null);
    setStatus(null);

    const formData = new FormData();
    formData.append("file", file);
    formData.append(
      "metadata",
      JSON.stringify({
        patient_id: patientId,
        idempotency_key: idempotencyKey || `upload-${Date.now()}`,
      }),
    );

    try {
      const res = await apiFetch("doctor", "/api/v1/prescriptions/upload", {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = (await res.json()) as { prescription_id: string };
        setStatus(`Prescription ingested successfully. ID: ${data.prescription_id}`);
      } else {
        const err = (await res.json()) as { detail?: unknown };
        setError(formatApiError(err as { detail?: string }));
      }
    } catch {
      setError("Network error — is the API running?");
    } finally {
      setUploading(false);
    }
  }

  return (
    <Card padding="lg">
      <CardHeader
        title="Upload signed prescription"
        description="PDF only. Files are validated, scanned, and stored with tenant isolation."
      />
      <form onSubmit={handleUpload} style={{ display: "flex", flexDirection: "column", gap: "1.25rem", maxWidth: "520px" }}>
        <TextField
          label="Patient ID (UUID)"
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          required
          placeholder={DEMO_PATIENT}
          hint="Dev seed patient UUID (see scripts/seed_dev_users.sql)"
        />
        <TextField
          label="Idempotency key"
          value={idempotencyKey}
          onChange={(e) => setIdempotencyKey(e.target.value)}
          hint="Optional. Auto-generated if left empty."
        />
        <div className="qes-field">
          <label className="qes-label" htmlFor="rx-file">
            Prescription PDF
          </label>
          <input
            id="rx-file"
            className="qes-input"
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            required
          />
        </div>
        {error && (
          <div className="qes-alert qes-alert--error" role="alert">
            {error}
          </div>
        )}
        {status && (
          <div className="qes-alert qes-alert--success" role="status">
            {status}
          </div>
        )}
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <Button type="submit" variant="primary" disabled={uploading || !file}>
            {uploading ? "Uploading…" : "Upload prescription"}
          </Button>
          {uploading && <Badge tone="neutral">Processing</Badge>}
        </div>
      </form>
    </Card>
  );
}
