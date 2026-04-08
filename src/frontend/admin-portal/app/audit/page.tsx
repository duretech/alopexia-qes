"use client";

import { useState } from "react";

export default function AuditExportPage() {
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [exporting, setExporting] = useState(false);

  async function handleExport() {
    setExporting(true);
    try {
      const res = await fetch("/api/v1/admin/audit/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
        alert("Export failed — check permissions");
      }
    } catch {
      alert("Network error");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div>
      <h2>Audit Export</h2>
      <p style={{ color: "#666" }}>
        Export audit events as JSON Lines for external audit tools.
      </p>

      <div
        style={{
          display: "flex",
          gap: "1rem",
          alignItems: "end",
          marginTop: "1rem",
        }}
      >
        <label>
          Start Date
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            style={{ display: "block", padding: "0.5rem", marginTop: "0.25rem" }}
          />
        </label>
        <label>
          End Date
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            style={{ display: "block", padding: "0.5rem", marginTop: "0.25rem" }}
          />
        </label>
        <button
          onClick={handleExport}
          disabled={exporting}
          style={{
            padding: "0.5rem 1.5rem",
            background: exporting ? "#999" : "#742a2a",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: exporting ? "wait" : "pointer",
          }}
        >
          {exporting ? "Exporting..." : "Export"}
        </button>
      </div>
    </div>
  );
}
