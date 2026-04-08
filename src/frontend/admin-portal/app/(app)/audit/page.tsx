"use client";

import { useState } from "react";
import { Button } from "@qes-ui/components/Button";
import { Card, CardHeader } from "@qes-ui/components/Card";
import { TextField } from "@qes-ui/components/TextField";
import { apiFetch } from "@qes-ui/lib/api";

export default function AuditExportPage() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleExport() {
    setExporting(true);
    setError(null);
    try {
      const res = await apiFetch("admin", "/api/v1/admin/audit/export", {
        method: "POST",
        body: JSON.stringify({
          start_date: startDate || null,
          end_date: endDate || null,
        }),
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `audit_export_${new Date().toISOString().slice(0, 10)}.jsonl`;
        a.click();
        URL.revokeObjectURL(url);
      } else {
        setError("Export failed — check permissions or date range.");
      }
    } catch {
      setError("Network error");
    } finally {
      setExporting(false);
    }
  }

  return (
    <Card padding="lg">
      <CardHeader
        title="Audit export"
        description="Stream audit events as JSON Lines (NDJSON) for SIEM or external audit tools."
      />
      {error && (
        <div className="qes-alert qes-alert--error" role="alert" style={{ marginBottom: "1rem" }}>
          {error}
        </div>
      )}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem", alignItems: "flex-end", maxWidth: "640px" }}>
        <TextField label="Start date" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
        <TextField label="End date" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
        <Button variant="primary" onClick={handleExport} disabled={exporting}>
          {exporting ? "Exporting…" : "Download export"}
        </Button>
      </div>
    </Card>
  );
}
