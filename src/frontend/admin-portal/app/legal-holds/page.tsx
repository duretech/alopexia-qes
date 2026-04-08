"use client";

import { useEffect, useState } from "react";

interface LegalHold {
  id: string;
  target_type: string;
  target_id: string;
  reason: string;
  reference_number: string | null;
  placed_at: string;
  is_active: boolean;
}

export default function LegalHoldsPage() {
  const [holds, setHolds] = useState<LegalHold[]>([]);
  const [loading, setLoading] = useState(true);
  const [targetType, setTargetType] = useState("prescription");
  const [targetId, setTargetId] = useState("");
  const [reason, setReason] = useState("");

  useEffect(() => {
    fetchHolds();
  }, []);

  async function fetchHolds() {
    try {
      const res = await fetch("/api/v1/admin/legal-holds");
      if (res.ok) setHolds(await res.json());
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    try {
      const res = await fetch("/api/v1/admin/legal-holds", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_type: targetType,
          target_id: targetId,
          reason,
        }),
      });
      if (res.ok) {
        setTargetId("");
        setReason("");
        fetchHolds();
      } else {
        alert("Failed to create legal hold");
      }
    } catch {
      alert("Network error");
    }
  }

  async function handleRelease(holdId: string) {
    const releaseReason = prompt("Release reason:");
    if (!releaseReason) return;

    try {
      const res = await fetch(`/api/v1/admin/legal-holds/${holdId}/release`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ release_reason: releaseReason }),
      });
      if (res.ok) fetchHolds();
      else alert("Failed to release hold");
    } catch {
      alert("Network error");
    }
  }

  if (loading) return <p>Loading legal holds...</p>;

  return (
    <div>
      <h2>Legal Holds</h2>

      <form
        onSubmit={handleCreate}
        style={{
          display: "flex",
          gap: "1rem",
          alignItems: "end",
          marginBottom: "2rem",
          flexWrap: "wrap",
        }}
      >
        <label>
          Target Type
          <select
            value={targetType}
            onChange={(e) => setTargetType(e.target.value)}
            style={{ display: "block", padding: "0.5rem", marginTop: "0.25rem" }}
          >
            <option value="prescription">Prescription</option>
            <option value="patient">Patient</option>
            <option value="audit_event">Audit Event</option>
          </select>
        </label>
        <label>
          Target ID (UUID)
          <input
            type="text"
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            required
            style={{ display: "block", padding: "0.5rem", marginTop: "0.25rem" }}
          />
        </label>
        <label>
          Reason
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
            style={{ display: "block", padding: "0.5rem", marginTop: "0.25rem", minWidth: "250px" }}
          />
        </label>
        <button
          type="submit"
          style={{
            padding: "0.5rem 1.5rem",
            background: "#742a2a",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: "pointer",
          }}
        >
          Place Hold
        </button>
      </form>

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ borderBottom: "2px solid #e2e8f0" }}>
            <th style={{ textAlign: "left", padding: "0.75rem" }}>Target</th>
            <th style={{ textAlign: "left", padding: "0.75rem" }}>Reason</th>
            <th style={{ textAlign: "left", padding: "0.75rem" }}>Placed</th>
            <th style={{ textAlign: "left", padding: "0.75rem" }}>Status</th>
            <th style={{ textAlign: "left", padding: "0.75rem" }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {holds.map((h) => (
            <tr key={h.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
              <td style={{ padding: "0.75rem", fontSize: "0.85rem" }}>
                {h.target_type}/{h.target_id.slice(0, 8)}...
              </td>
              <td style={{ padding: "0.75rem" }}>{h.reason}</td>
              <td style={{ padding: "0.75rem" }}>
                {new Date(h.placed_at).toLocaleDateString("es-ES")}
              </td>
              <td style={{ padding: "0.75rem" }}>
                {h.is_active ? "Active" : "Released"}
              </td>
              <td style={{ padding: "0.75rem" }}>
                {h.is_active && (
                  <button
                    onClick={() => handleRelease(h.id)}
                    style={{
                      padding: "0.25rem 0.75rem",
                      background: "#e53e3e",
                      color: "white",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                    }}
                  >
                    Release
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
