"use client";

import { useState } from "react";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [patientId, setPatientId] = useState("");
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
      })
    );

    try {
      const res = await fetch("/api/v1/prescriptions/upload", {
        method: "POST",
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setStatus(
          `Uploaded successfully. Prescription ID: ${data.prescription_id}`
        );
      } else {
        const err = await res.json();
        setError(err.detail?.message || err.detail || "Upload failed");
      }
    } catch (err) {
      setError("Network error — is the API running?");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div>
      <h2>Upload Signed Prescription</h2>
      <p style={{ color: "#666" }}>
        Upload a signed PDF prescription for QES verification.
      </p>

      <form
        onSubmit={handleUpload}
        style={{ display: "flex", flexDirection: "column", gap: "1rem", maxWidth: "500px" }}
      >
        <label>
          Patient ID (UUID)
          <input
            type="text"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
            placeholder="e.g., 550e8400-e29b-41d4-a716-446655440000"
            required
            style={{ display: "block", width: "100%", padding: "0.5rem", marginTop: "0.25rem" }}
          />
        </label>

        <label>
          Idempotency Key (optional)
          <input
            type="text"
            value={idempotencyKey}
            onChange={(e) => setIdempotencyKey(e.target.value)}
            placeholder="Auto-generated if empty"
            style={{ display: "block", width: "100%", padding: "0.5rem", marginTop: "0.25rem" }}
          />
        </label>

        <label>
          Prescription PDF
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            required
            style={{ display: "block", marginTop: "0.25rem" }}
          />
        </label>

        <button
          type="submit"
          disabled={uploading || !file}
          style={{
            padding: "0.75rem 1.5rem",
            background: uploading ? "#999" : "#2b6cb0",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: uploading ? "wait" : "pointer",
            fontSize: "1rem",
          }}
        >
          {uploading ? "Uploading..." : "Upload Prescription"}
        </button>
      </form>

      {status && (
        <div
          style={{
            marginTop: "1rem",
            padding: "1rem",
            background: "#c6f6d5",
            borderRadius: "4px",
          }}
        >
          {status}
        </div>
      )}
      {error && (
        <div
          style={{
            marginTop: "1rem",
            padding: "1rem",
            background: "#fed7d7",
            borderRadius: "4px",
          }}
        >
          {error}
        </div>
      )}
    </div>
  );
}
